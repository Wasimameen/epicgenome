<?php
/**
 * OCEANMARKETING.COM Lander — theme functions.
 *
 * - Enqueues fonts, styles, and the front-end script.
 * - Registers a custom "Offers" post type shown in the WP admin sidebar.
 * - Handles the on-page offer form over AJAX: verifies a nonce, checks the
 *   honeypot, saves every submission to the database as an Offer, and emails
 *   the owner. The DB copy is the backup; the email is the live notification.
 */

if ( ! defined( 'ABSPATH' ) ) { exit; }

define( 'OCEANMARKETING_OWNER_EMAIL', 'contact@oceanmarketing.com' );

/* ---------------------------------------------------------------------------
 * Assets
 * ------------------------------------------------------------------------- */
function oceanmarketing_assets() {
	wp_enqueue_style(
		'oceanmarketing-fonts',
		'https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,400&family=Inter+Tight:wght@300;400;500;600&display=swap',
		array(),
		null
	);
	wp_enqueue_style(
		'oceanmarketing-style',
		get_template_directory_uri() . '/assets/style.css',
		array(),
		'1.0'
	);
	wp_enqueue_script(
		'oceanmarketing-main',
		get_template_directory_uri() . '/assets/main.js',
		array(),
		'1.0',
		true
	);
	wp_localize_script( 'oceanmarketing-main', 'OCEANMARKETING_AJAX', array(
		'url'   => admin_url( 'admin-ajax.php' ),
		'nonce' => wp_create_nonce( 'oceanmarketing_offer_nonce' ),
	) );
}
add_action( 'wp_enqueue_scripts', 'oceanmarketing_assets' );

/* ---------------------------------------------------------------------------
 * "Offers" custom post type
 * ------------------------------------------------------------------------- */
function oceanmarketing_register_offers_cpt() {
	$labels = array(
		'name'               => 'Offers',
		'singular_name'      => 'Offer',
		'menu_name'          => 'Offers',
		'all_items'          => 'All Offers',
		'add_new'            => 'Add Offer',
		'add_new_item'       => 'Add Offer',
		'edit_item'          => 'View / Edit Offer',
		'view_item'          => 'View Offer',
		'search_items'       => 'Search Offers',
		'not_found'          => 'No offers yet',
		'not_found_in_trash' => 'No offers in trash',
	);
	register_post_type( 'oceanmarketing_offer', array(
		'labels'        => $labels,
		'public'        => false,
		'show_ui'       => true,
		'show_in_menu'  => true,
		'menu_icon'     => 'dashicons-email-alt',
		'menu_position' => 26,
		'supports'      => array( 'title' ),
		'capability_type' => 'post',
	) );
}
add_action( 'init', 'oceanmarketing_register_offers_cpt' );

/* Show the captured fields as a meta box on the Offer edit screen. */
function oceanmarketing_offer_metabox() {
	add_meta_box( 'oceanmarketing_offer_details', 'Offer details', 'oceanmarketing_offer_metabox_html', 'oceanmarketing_offer', 'normal', 'high' );
}
add_action( 'add_meta_boxes', 'oceanmarketing_offer_metabox' );

function oceanmarketing_offer_metabox_html( $post ) {
	$fields = array(
		'oceanmarketing_name'    => 'Name',
		'oceanmarketing_company' => 'Company',
		'oceanmarketing_email'   => 'Email',
		'oceanmarketing_offer'   => 'Offer',
		'oceanmarketing_message' => 'Message',
		'oceanmarketing_ip'      => 'IP',
		'oceanmarketing_date'    => 'Submitted',
	);
	echo '<table class="widefat striped"><tbody>';
	foreach ( $fields as $key => $label ) {
		$val = get_post_meta( $post->ID, $key, true );
		echo '<tr><th style="width:140px;text-align:left;">' . esc_html( $label ) . '</th><td>' . nl2br( esc_html( $val ) ) . '</td></tr>';
	}
	echo '</tbody></table>';
}

/* Friendlier columns in the Offers list. */
function oceanmarketing_offer_columns( $cols ) {
	return array(
		'cb'                => $cols['cb'],
		'title'             => 'Name',
		'oceanmarketing_company' => 'Company',
		'oceanmarketing_email'   => 'Email',
		'oceanmarketing_offer'   => 'Offer',
		'date'              => 'Received',
	);
}
add_filter( 'manage_oceanmarketing_offer_posts_columns', 'oceanmarketing_offer_columns' );

function oceanmarketing_offer_column_content( $col, $post_id ) {
	if ( in_array( $col, array( 'oceanmarketing_company', 'oceanmarketing_email', 'oceanmarketing_offer' ), true ) ) {
		echo esc_html( get_post_meta( $post_id, $col, true ) );
	}
}
add_action( 'manage_oceanmarketing_offer_posts_custom_column', 'oceanmarketing_offer_column_content', 10, 2 );

/* ---------------------------------------------------------------------------
 * AJAX handler — save to DB + email owner
 * ------------------------------------------------------------------------- */
function oceanmarketing_handle_offer() {
	check_ajax_referer( 'oceanmarketing_offer_nonce', 'nonce' );

	// Honeypot: a real user never fills "website".
	if ( ! empty( $_POST['website'] ) ) {
		wp_send_json_success( array( 'message' => 'Received.' ) ); // pretend success, drop silently
	}

	$name    = isset( $_POST['name'] ) ? sanitize_text_field( wp_unslash( $_POST['name'] ) ) : '';
	$company = isset( $_POST['company'] ) ? sanitize_text_field( wp_unslash( $_POST['company'] ) ) : '';
	$email   = isset( $_POST['email'] ) ? sanitize_email( wp_unslash( $_POST['email'] ) ) : '';
	$offer   = isset( $_POST['offer'] ) ? sanitize_text_field( wp_unslash( $_POST['offer'] ) ) : '';
	$message = isset( $_POST['message'] ) ? sanitize_textarea_field( wp_unslash( $_POST['message'] ) ) : '';

	if ( '' === $name || ! is_email( $email ) ) {
		wp_send_json_error( array( 'message' => 'Please include your name and a valid email.' ) );
	}

	$ip   = isset( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( $_SERVER['REMOTE_ADDR'] ) ) : '';
	$when = current_time( 'mysql' );

	// 1) Save to the database as an Offer (the backup record).
	$post_id = wp_insert_post( array(
		'post_type'   => 'oceanmarketing_offer',
		'post_status' => 'publish',
		'post_title'  => $name . ( $company ? ' — ' . $company : '' ),
	) );

	if ( $post_id && ! is_wp_error( $post_id ) ) {
		update_post_meta( $post_id, 'oceanmarketing_name', $name );
		update_post_meta( $post_id, 'oceanmarketing_company', $company );
		update_post_meta( $post_id, 'oceanmarketing_email', $email );
		update_post_meta( $post_id, 'oceanmarketing_offer', $offer );
		update_post_meta( $post_id, 'oceanmarketing_message', $message );
		update_post_meta( $post_id, 'oceanmarketing_ip', $ip );
		update_post_meta( $post_id, 'oceanmarketing_date', $when );
	}

	// 2) Email the owner (the live notification).
	//    NOTE: on shared hosting, PHP mail() to external inboxes (esp. Gmail) is
	//    unreliable without SMTP. We send to the on-domain mailbox and set an
	//    explicit From on the domain to maximise acceptance. The DB copy above
	//    is the authoritative record regardless of whether this email lands.
	$subject = 'OCEANMARKETING.COM — new offer from ' . $name;
	$body  = "New inquiry on OCEANMARKETING.COM\n\n";
	$body .= "Name:     {$name}\n";
	$body .= "Company:  {$company}\n";
	$body .= "Email:    {$email}\n";
	$body .= "Offer:    {$offer}\n";
	$body .= "Message:\n{$message}\n\n";
	$body .= "IP: {$ip}\nReceived: {$when}\n";
	$body .= "Saved to Offers (post #{$post_id}).";

	$headers = array(
		'Content-Type: text/plain; charset=UTF-8',
		'From: OCEANMARKETING.COM <' . OCEANMARKETING_OWNER_EMAIL . '>',
		'Reply-To: ' . $name . ' <' . $email . '>',
	);

	$sent = wp_mail( OCEANMARKETING_OWNER_EMAIL, $subject, $body, $headers );

	// Report honestly: the offer is safe in the DB either way, but tell the
	// front-end whether the email actually went out so the message can adapt.
	wp_send_json_success( array(
		'saved'   => ( $post_id && ! is_wp_error( $post_id ) ),
		'emailed' => (bool) $sent,
	) );
}
add_action( 'wp_ajax_oceanmarketing_offer', 'oceanmarketing_handle_offer' );
add_action( 'wp_ajax_nopriv_oceanmarketing_offer', 'oceanmarketing_handle_offer' );

/* Minimal theme support. */
function oceanmarketing_theme_support() {
	add_theme_support( 'title-tag' );
	add_theme_support( 'html5', array( 'script', 'style' ) );
}
add_action( 'after_setup_theme', 'oceanmarketing_theme_support' );

/* Fixed document title for the lander. */
function oceanmarketing_document_title( $parts ) {
	$parts['title']   = 'OCEANMARKETING.COM — A brand that already sounds like an agency.';
	$parts['tagline'] = '';
	unset( $parts['site'] );
	return $parts;
}
add_filter( 'document_title_parts', 'oceanmarketing_document_title' );
