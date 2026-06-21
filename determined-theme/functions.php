<?php
/**
 * DETERMINED.COM Landing — theme functions
 */

if ( ! defined( 'ABSPATH' ) ) { exit; }

function determined_enqueue_assets() {
    // Google Fonts (Fraunces + Inter Tight)
    wp_enqueue_style(
        'determined-fonts',
        'https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,300;1,9..144,400&family=Inter+Tight:wght@300;400;500;600&display=swap',
        array(),
        null
    );

    // Main theme stylesheet (style.css in theme root)
    wp_enqueue_style(
        'determined-style',
        get_stylesheet_uri(),
        array( 'determined-fonts' ),
        wp_get_theme()->get( 'Version' )
    );

    // Page interactions (wordmark build, scroll reveal, offer form, floating tab)
    wp_enqueue_script(
        'determined-script',
        get_template_directory_uri() . '/assets/main.js',
        array(),
        wp_get_theme()->get( 'Version' ),
        true // load in footer
    );

    // Pass AJAX config to the front-end script
    wp_localize_script( 'determined-script', 'determinedAjax', array(
        'url'   => admin_url( 'admin-ajax.php' ),
        'nonce' => wp_create_nonce( 'determined_offer' ),
    ) );
}
add_action( 'wp_enqueue_scripts', 'determined_enqueue_assets' );

// Minimal theme support
function determined_theme_setup() {
    add_theme_support( 'title-tag' );
    add_theme_support( 'html5', array( 'style', 'script' ) );
}
add_action( 'after_setup_theme', 'determined_theme_setup' );

/**
 * Where offer inquiries are emailed.
 */
function determined_offer_recipient() {
    return 'tom@determined.com';
}

/**
 * Handle the offer-form submission (AJAX, both logged-in and not).
 * Saves every inquiry as a private CPT entry (never lost) and emails it.
 */
function determined_handle_offer() {
    // Security: verify nonce
    if ( ! isset( $_POST['nonce'] ) || ! wp_verify_nonce( $_POST['nonce'], 'determined_offer' ) ) {
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
        'post_type'    => 'determined_offer',
        'post_status'  => 'private',
        'post_title'   => sprintf( '%s%s — %s', $name, ( $offer ? ' / ' . $offer : '' ), gmdate( 'Y-m-d H:i' ) ),
        'post_content' => $message,
    ) );
    if ( $post_id && ! is_wp_error( $post_id ) ) {
        update_post_meta( $post_id, 'determined_name', $name );
        update_post_meta( $post_id, 'determined_email', $email );
        update_post_meta( $post_id, 'determined_company', $company );
        update_post_meta( $post_id, 'determined_offer', $offer );
    }

    // 2) Email the inquiry
    $to      = determined_offer_recipient();
    $subject = sprintf( 'DETERMINED.COM — Offer%s%s', ( $offer ? ' ' . $offer : '' ), ( $name ? ' / ' . $name : '' ) );
    $body    = "New DETERMINED.COM inquiry:\n\n"
             . "Name: {$name}\n"
             . "Email: {$email}\n"
             . ( $company ? "Company / brand: {$company}\n" : '' )
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
add_action( 'wp_ajax_determined_offer', 'determined_handle_offer' );
add_action( 'wp_ajax_nopriv_determined_offer', 'determined_handle_offer' );

/**
 * Register a private post type so inquiries are viewable in wp-admin
 * (Dashboard → Offers) as a guaranteed backup to email.
 */
function determined_register_offer_cpt() {
    register_post_type( 'determined_offer', array(
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
add_action( 'init', 'determined_register_offer_cpt' );

/**
 * Show the submitter's contact details as columns in the Offers admin list.
 */
function determined_offer_columns( $cols ) {
    $cols['determined_email'] = 'Email';
    $cols['determined_offer'] = 'Offer';
    return $cols;
}
add_filter( 'manage_determined_offer_posts_columns', 'determined_offer_columns' );

function determined_offer_column_content( $col, $post_id ) {
    if ( $col === 'determined_email' ) {
        echo esc_html( get_post_meta( $post_id, 'determined_email', true ) );
    } elseif ( $col === 'determined_offer' ) {
        echo esc_html( get_post_meta( $post_id, 'determined_offer', true ) );
    }
}
add_action( 'manage_determined_offer_posts_custom_column', 'determined_offer_column_content', 10, 2 );
