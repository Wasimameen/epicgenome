<?php
/**
 * AIMEE.AI Landing — theme functions
 */

if ( ! defined( 'ABSPATH' ) ) { exit; }

function aimee_enqueue_assets() {
    // Google Fonts (Fraunces + Inter Tight)
    wp_enqueue_style(
        'aimee-fonts',
        'https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,300;1,9..144,400&family=Inter+Tight:wght@300;400;500;600&display=swap',
        array(),
        null
    );

    // Main theme stylesheet (style.css in theme root)
    wp_enqueue_style(
        'aimee-style',
        get_stylesheet_uri(),
        array( 'aimee-fonts' ),
        wp_get_theme()->get( 'Version' )
    );

    // Page interactions (wordmark build, scroll reveal, offer form, floating tab)
    wp_enqueue_script(
        'aimee-script',
        get_template_directory_uri() . '/assets/main.js',
        array(),
        wp_get_theme()->get( 'Version' ),
        true // load in footer
    );
}
add_action( 'wp_enqueue_scripts', 'aimee_enqueue_assets' );

// Minimal theme support
function aimee_theme_setup() {
    add_theme_support( 'title-tag' );
    add_theme_support( 'html5', array( 'style', 'script' ) );
}
add_action( 'after_setup_theme', 'aimee_theme_setup' );

/**
 * Pass AJAX config to the front-end script.
 */
function aimee_localize_ajax() {
    wp_localize_script( 'aimee-script', 'aimeeAjax', array(
        'url'   => admin_url( 'admin-ajax.php' ),
        'nonce' => wp_create_nonce( 'aimee_offer' ),
    ) );
}
add_action( 'wp_enqueue_scripts', 'aimee_localize_ajax' );

/**
 * Where offer inquiries are emailed.
 */
function aimee_offer_recipient() {
    return 'contact@aimee.ai';
}

/**
 * Handle the offer-form submission (AJAX, both logged-in and not).
 * Saves every inquiry as a private CPT entry (never lost) and emails it.
 */
function aimee_handle_offer() {
    // Security: verify nonce
    if ( ! isset( $_POST['nonce'] ) || ! wp_verify_nonce( $_POST['nonce'], 'aimee_offer' ) ) {
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
        'post_type'    => 'aimee_offer',
        'post_status'  => 'private',
        'post_title'   => sprintf( '%s%s — %s', $name, ( $offer ? ' / ' . $offer : '' ), gmdate( 'Y-m-d H:i' ) ),
        'post_content' => $message,
    ) );
    if ( $post_id && ! is_wp_error( $post_id ) ) {
        update_post_meta( $post_id, 'aimee_name', $name );
        update_post_meta( $post_id, 'aimee_email', $email );
        update_post_meta( $post_id, 'aimee_company', $company );
        update_post_meta( $post_id, 'aimee_offer', $offer );
    }

    // 2) Email the inquiry
    $to      = aimee_offer_recipient();
    $subject = sprintf( 'AIMEE.AI — Offer%s%s', ( $offer ? ' ' . $offer : '' ), ( $name ? ' / ' . $name : '' ) );
    $body    = "New AIMEE.AI inquiry:\n\n"
             . "Name: {$name}\n"
             . "Email: {$email}\n"
             . ( $company ? "Company / product: {$company}\n" : '' )
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
add_action( 'wp_ajax_aimee_offer', 'aimee_handle_offer' );
add_action( 'wp_ajax_nopriv_aimee_offer', 'aimee_handle_offer' );

/**
 * Register a private post type so inquiries are viewable in wp-admin
 * (Dashboard → Offers) as a guaranteed backup to email.
 */
function aimee_register_offer_cpt() {
    register_post_type( 'aimee_offer', array(
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
add_action( 'init', 'aimee_register_offer_cpt' );

/**
 * Show the submitter's contact details as columns in the Offers admin list.
 */
function aimee_offer_columns( $cols ) {
    $cols['aimee_email'] = 'Email';
    $cols['aimee_offer'] = 'Offer';
    return $cols;
}
add_filter( 'manage_aimee_offer_posts_columns', 'aimee_offer_columns' );

function aimee_offer_column_content( $col, $post_id ) {
    if ( $col === 'aimee_email' ) {
        echo esc_html( get_post_meta( $post_id, 'aimee_email', true ) );
    } elseif ( $col === 'aimee_offer' ) {
        echo esc_html( get_post_meta( $post_id, 'aimee_offer', true ) );
    }
}
add_action( 'manage_aimee_offer_posts_custom_column', 'aimee_offer_column_content', 10, 2 );
