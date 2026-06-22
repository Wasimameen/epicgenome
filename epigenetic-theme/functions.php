<?php
/**
 * EPIGENETIC.COM Landing — theme functions
 */

if ( ! defined( 'ABSPATH' ) ) { exit; }

function epigenetic_enqueue_assets() {
    // Google Fonts (Fraunces + Inter Tight)
    wp_enqueue_style(
        'epigenetic-fonts',
        'https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,300;1,9..144,400&family=Inter+Tight:wght@300;400;500;600&display=swap',
        array(),
        null
    );

    // Main theme stylesheet (style.css in theme root)
    wp_enqueue_style(
        'epigenetic-style',
        get_stylesheet_uri(),
        array( 'epigenetic-fonts' ),
        wp_get_theme()->get( 'Version' )
    );

    // Page interactions (wordmark build, scroll reveal, offer form, floating tab)
    wp_enqueue_script(
        'epigenetic-script',
        get_template_directory_uri() . '/assets/main.js',
        array(),
        wp_get_theme()->get( 'Version' ),
        true // load in footer
    );

    // Pass AJAX config to the front-end script
    wp_localize_script( 'epigenetic-script', 'epigeneticAjax', array(
        'url'   => admin_url( 'admin-ajax.php' ),
        'nonce' => wp_create_nonce( 'epigenetic_offer' ),
    ) );
}
add_action( 'wp_enqueue_scripts', 'epigenetic_enqueue_assets' );

// Minimal theme support
function epigenetic_theme_setup() {
    add_theme_support( 'title-tag' );
    add_theme_support( 'html5', array( 'style', 'script' ) );
}
add_action( 'after_setup_theme', 'epigenetic_theme_setup' );

/**
 * Where offer inquiries are emailed.
 */
function epigenetic_offer_recipient() {
    return 'contact@epigenetic.com';
}

/**
 * Handle the offer-form submission (AJAX, both logged-in and not).
 * Saves every inquiry as a private CPT entry (never lost) and emails it.
 */
function epigenetic_handle_offer() {
    // Security: verify nonce
    if ( ! isset( $_POST['nonce'] ) || ! wp_verify_nonce( $_POST['nonce'], 'epigenetic_offer' ) ) {
        wp_send_json_error( array( 'message' => 'Security check failed. Please refresh the page and try again.' ), 400 );
    }

    // Honeypot: if filled, silently accept but drop (bot)
    if ( ! empty( $_POST['website'] ) ) {
        wp_send_json_success( array( 'message' => 'Thank you.' ) );
    }

    // Collect + sanitize
    $name    = isset( $_POST['name'] )    ? sanitize_text_field( wp_unslash( $_POST['name'] ) )    : '';
    $email   = isset( $_POST['email'] )   ? sanitize_email( wp_unslash( $_POST['email'] ) )         : '';
    $company = isset( $_POST['company'] ) ? sanitize_text_field( wp_unslash( $_POST['company'] ) )  : '';
    $offer   = isset( $_POST['offer'] )   ? sanitize_text_field( wp_unslash( $_POST['offer'] ) )    : '';
    $message = isset( $_POST['message'] ) ? sanitize_textarea_field( wp_unslash( $_POST['message'] ) ) : '';

    // Validate required
    if ( $name === '' || ! is_email( $email ) ) {
        wp_send_json_error( array( 'message' => 'Please enter your name and a valid email.' ), 422 );
    }

    // 1) Save to database first — so the lead is never lost even if email fails
    $post_id = wp_insert_post( array(
        'post_type'    => 'epigenetic_offer',
        'post_status'  => 'private',
        'post_title'   => sprintf( '%s%s — %s', $name, ( $offer ? ' / ' . $offer : '' ), gmdate( 'Y-m-d H:i' ) ),
        'post_content' => $message,
    ) );
    if ( $post_id && ! is_wp_error( $post_id ) ) {
        update_post_meta( $post_id, 'epigenetic_name', $name );
        update_post_meta( $post_id, 'epigenetic_email', $email );
        update_post_meta( $post_id, 'epigenetic_company', $company );
        update_post_meta( $post_id, 'epigenetic_offer', $offer );
    }

    // 2) Email the inquiry
    $to      = epigenetic_offer_recipient();
    $subject = sprintf( 'EPIGENETIC.COM — Offer%s%s', ( $offer ? ' ' . $offer : '' ), ( $name ? ' / ' . $name : '' ) );
    $body    = "New EPIGENETIC.COM inquiry:\n\n"
             . "Name: {$name}\n"
             . "Email: {$email}\n"
             . ( $company ? "Company: {$company}\n" : '' )
             . "Offer: " . ( $offer ? $offer : '—' ) . "\n\n"
             . "Message:\n" . ( $message ? $message : '(none)' ) . "\n";
    $headers = array(
        'Content-Type: text/plain; charset=UTF-8',
        'Reply-To: ' . $name . ' <' . $email . '>',
    );
    $sent = wp_mail( $to, $subject, $body, $headers );

    // Success as long as we captured it (DB save). Email may be delayed by host config.
    wp_send_json_success( array(
        'message' => 'Your offer has been sent.',
        'emailed' => (bool) $sent,
        'saved'   => (bool) ( $post_id && ! is_wp_error( $post_id ) ),
    ) );
}
add_action( 'wp_ajax_epigenetic_offer', 'epigenetic_handle_offer' );
add_action( 'wp_ajax_nopriv_epigenetic_offer', 'epigenetic_handle_offer' );

/**
 * Register a private post type so inquiries are viewable in wp-admin
 * (Dashboard → Offers) as a guaranteed backup to email.
 */
function epigenetic_register_offer_cpt() {
    register_post_type( 'epigenetic_offer', array(
        'labels' => array(
            'name'          => 'Offers',
            'singular_name' => 'Offer',
            'menu_name'     => 'Offers',
        ),
        'public'              => false,
        'show_ui'             => true,
        'show_in_menu'        => true,
        'menu_icon'           => 'dashicons-email-alt',
        'menu_position'       => 25,
        'capability_type'     => 'post',
        'supports'            => array( 'title', 'editor' ),
        'exclude_from_search' => true,
    ) );
}
add_action( 'init', 'epigenetic_register_offer_cpt' );

/**
 * Show the submitter's contact details as columns in the Offers admin list.
 */
function epigenetic_offer_columns( $cols ) {
    $cols['epigenetic_email'] = 'Email';
    $cols['epigenetic_offer'] = 'Offer';
    return $cols;
}
add_filter( 'manage_epigenetic_offer_posts_columns', 'epigenetic_offer_columns' );

function epigenetic_offer_column_content( $col, $post_id ) {
    if ( $col === 'epigenetic_email' ) {
        echo esc_html( get_post_meta( $post_id, 'epigenetic_email', true ) );
    } elseif ( $col === 'epigenetic_offer' ) {
        echo esc_html( get_post_meta( $post_id, 'epigenetic_offer', true ) );
    }
}
add_action( 'manage_epigenetic_offer_posts_custom_column', 'epigenetic_offer_column_content', 10, 2 );
