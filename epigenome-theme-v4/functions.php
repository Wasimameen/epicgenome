<?php
/**
 * EPIGENOME.COM Lander — theme functions.
 *
 * - Enqueues fonts, styles, and the front-end script.
 * - Registers a custom "Offers" post type shown in the WP admin sidebar.
 * - Handles the on-page offer form over AJAX: verifies a nonce, checks the
 *   honeypot, saves every submission to the database as an Offer, and emails
 *   the owner. The DB copy is the backup; the email is the live notification.
 */

if ( ! defined( 'ABSPATH' ) ) { exit; }

define( 'EPIGENOME_OWNER_EMAIL', 'contact@epigenome.com' );

/* ---------------------------------------------------------------------------
 * Assets
 * ------------------------------------------------------------------------- */
function epigenome_assets() {
	wp_enqueue_style(
		'epigenome-fonts',
		'https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,400&family=Inter+Tight:wght@300;400;500;600&display=swap',
		array(),
		null
	);
	wp_enqueue_style(
		'epigenome-style',
		get_template_directory_uri() . '/assets/style.css',
		array(),
		'1.0'
	);
	wp_enqueue_script(
		'epigenome-main',
		get_template_directory_uri() . '/assets/main.js',
		array(),
		'1.0',
		true
	);
	wp_localize_script( 'epigenome-main', 'EPIGENOME_AJAX', array(
		'url'   => admin_url( 'admin-ajax.php' ),
		'nonce' => wp_create_nonce( 'epigenome_offer_nonce' ),
	) );
}
add_action( 'wp_enqueue_scripts', 'epigenome_assets' );

/* ---------------------------------------------------------------------------
 * "Offers" custom post type
 * ------------------------------------------------------------------------- */
function epigenome_register_offers_cpt() {
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
	register_post_type( 'epigenome_offer', array(
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
add_action( 'init', 'epigenome_register_offers_cpt' );

/* Show the captured fields as a meta box on the Offer edit screen. */
function epigenome_offer_metabox() {
	add_meta_box( 'epigenome_offer_details', 'Offer details', 'epigenome_offer_metabox_html', 'epigenome_offer', 'normal', 'high' );
}
add_action( 'add_meta_boxes', 'epigenome_offer_metabox' );

function epigenome_offer_metabox_html( $post ) {
	$fields = array(
		'epigenome_name'    => 'Name',
		'epigenome_company' => 'Company',
		'epigenome_email'   => 'Email',
		'epigenome_offer'   => 'Offer',
		'epigenome_message' => 'Message',
		'epigenome_ip'      => 'IP',
		'epigenome_date'    => 'Submitted',
	);
	echo '<table class="widefat striped"><tbody>';
	foreach ( $fields as $key => $label ) {
		$val = get_post_meta( $post->ID, $key, true );
		echo '<tr><th style="width:140px;text-align:left;">' . esc_html( $label ) . '</th><td>' . nl2br( esc_html( $val ) ) . '</td></tr>';
	}
	echo '</tbody></table>';
}

/* Friendlier columns in the Offers list. */
function epigenome_offer_columns( $cols ) {
	return array(
		'cb'                => $cols['cb'],
		'title'             => 'Name',
		'epigenome_company' => 'Company',
		'epigenome_email'   => 'Email',
		'epigenome_offer'   => 'Offer',
		'date'              => 'Received',
	);
}
add_filter( 'manage_epigenome_offer_posts_columns', 'epigenome_offer_columns' );

function epigenome_offer_column_content( $col, $post_id ) {
	if ( in_array( $col, array( 'epigenome_company', 'epigenome_email', 'epigenome_offer' ), true ) ) {
		echo esc_html( get_post_meta( $post_id, $col, true ) );
	}
}
add_action( 'manage_epigenome_offer_posts_custom_column', 'epigenome_offer_column_content', 10, 2 );

/* ---------------------------------------------------------------------------
 * AJAX handler — save to DB + email owner
 * ------------------------------------------------------------------------- */
function epigenome_handle_offer() {
	check_ajax_referer( 'epigenome_offer_nonce', 'nonce' );

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
		'post_type'   => 'epigenome_offer',
		'post_status' => 'publish',
		'post_title'  => $name . ( $company ? ' — ' . $company : '' ),
	) );

	if ( $post_id && ! is_wp_error( $post_id ) ) {
		update_post_meta( $post_id, 'epigenome_name', $name );
		update_post_meta( $post_id, 'epigenome_company', $company );
		update_post_meta( $post_id, 'epigenome_email', $email );
		update_post_meta( $post_id, 'epigenome_offer', $offer );
		update_post_meta( $post_id, 'epigenome_message', $message );
		update_post_meta( $post_id, 'epigenome_ip', $ip );
		update_post_meta( $post_id, 'epigenome_date', $when );
	}

	// 2) Email the owner (the live notification).
	//    NOTE: on shared hosting, PHP mail() to external inboxes (esp. Gmail) is
	//    unreliable without SMTP. We send to the on-domain mailbox and set an
	//    explicit From on the domain to maximise acceptance. The DB copy above
	//    is the authoritative record regardless of whether this email lands.
	$subject = 'EPIGENOME.COM — new offer from ' . $name;
	$body  = "New inquiry on EPIGENOME.COM\n\n";
	$body .= "Name:     {$name}\n";
	$body .= "Company:  {$company}\n";
	$body .= "Email:    {$email}\n";
	$body .= "Offer:    {$offer}\n";
	$body .= "Message:\n{$message}\n\n";
	$body .= "IP: {$ip}\nReceived: {$when}\n";
	$body .= "Saved to Offers (post #{$post_id}).";

	$headers = array(
		'Content-Type: text/plain; charset=UTF-8',
		'From: EPIGENOME.COM <' . EPIGENOME_OWNER_EMAIL . '>',
		'Reply-To: ' . $name . ' <' . $email . '>',
	);

	$sent = wp_mail( EPIGENOME_OWNER_EMAIL, $subject, $body, $headers );

	// Report honestly: the offer is safe in the DB either way, but tell the
	// front-end whether the email actually went out so the message can adapt.
	wp_send_json_success( array(
		'saved'   => ( $post_id && ! is_wp_error( $post_id ) ),
		'emailed' => (bool) $sent,
	) );
}
add_action( 'wp_ajax_epigenome_offer', 'epigenome_handle_offer' );
add_action( 'wp_ajax_nopriv_epigenome_offer', 'epigenome_handle_offer' );

/* Minimal theme support. */
function epigenome_theme_support() {
	add_theme_support( 'title-tag' );
	add_theme_support( 'html5', array( 'script', 'style' ) );
}
add_action( 'after_setup_theme', 'epigenome_theme_support' );

/* Fixed document title for the lander. */
function epigenome_document_title( $parts ) {
	$parts['title']   = 'EPIGENOME.COM — One word. The whole field.';
	$parts['tagline'] = '';
	unset( $parts['site'] );
	return $parts;
}
add_filter( 'document_title_parts', 'epigenome_document_title' );
