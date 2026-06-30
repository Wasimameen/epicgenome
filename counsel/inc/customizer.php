<?php
/**
 * Customizer settings: "Counsel Settings".
 *
 * Lets non-developers edit contact details, social links, and footer
 * disclaimer text without touching code.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

/**
 * Register Customizer settings and controls.
 *
 * @param WP_Customize_Manager $wp_customize The Customizer manager.
 * @return void
 */
function counsel_customize_register( $wp_customize ) {

	$wp_customize->add_section(
		'counsel_settings',
		array(
			'title'       => __( 'Counsel Settings', 'counsel' ),
			'priority'    => 30,
			'description' => __( 'Contact details, social links, and footer disclaimer text used across the site.', 'counsel' ),
		)
	);

	// Contact email --------------------------------------------------------.
	$wp_customize->add_setting(
		'counsel_contact_email',
		array(
			'default'           => get_option( 'admin_email' ),
			'sanitize_callback' => 'sanitize_email',
			'transport'         => 'refresh',
		)
	);
	$wp_customize->add_control(
		'counsel_contact_email',
		array(
			'label'   => __( 'General contact email', 'counsel' ),
			'section' => 'counsel_settings',
			'type'    => 'email',
		)
	);

	// Attorney-inquiry email ----------------------------------------------.
	$wp_customize->add_setting(
		'counsel_attorney_email',
		array(
			'default'           => get_option( 'admin_email' ),
			'sanitize_callback' => 'sanitize_email',
			'transport'         => 'refresh',
		)
	);
	$wp_customize->add_control(
		'counsel_attorney_email',
		array(
			'label'       => __( 'Attorney-inquiry email', 'counsel' ),
			'description' => __( 'Where "For Attorneys" availability requests are sent.', 'counsel' ),
			'section'     => 'counsel_settings',
			'type'        => 'email',
		)
	);

	// Phone ----------------------------------------------------------------.
	$wp_customize->add_setting(
		'counsel_contact_phone',
		array(
			'default'           => '',
			'sanitize_callback' => 'sanitize_text_field',
			'transport'         => 'refresh',
		)
	);
	$wp_customize->add_control(
		'counsel_contact_phone',
		array(
			'label'   => __( 'Contact phone', 'counsel' ),
			'section' => 'counsel_settings',
			'type'    => 'text',
		)
	);

	// Social links ---------------------------------------------------------.
	$socials = array(
		'counsel_social_linkedin' => __( 'LinkedIn URL', 'counsel' ),
		'counsel_social_x'        => __( 'X / Twitter URL', 'counsel' ),
		'counsel_social_facebook' => __( 'Facebook URL', 'counsel' ),
		'counsel_social_instagram' => __( 'Instagram URL', 'counsel' ),
	);

	foreach ( $socials as $key => $label ) {
		$wp_customize->add_setting(
			$key,
			array(
				'default'           => '',
				'sanitize_callback' => 'esc_url_raw',
				'transport'         => 'refresh',
			)
		);
		$wp_customize->add_control(
			$key,
			array(
				'label'   => $label,
				'section' => 'counsel_settings',
				'type'    => 'url',
			)
		);
	}

	// Footer disclaimer override ------------------------------------------.
	$wp_customize->add_setting(
		'counsel_footer_disclaimer',
		array(
			'default'           => '',
			'sanitize_callback' => 'wp_kses_post',
			'transport'         => 'refresh',
		)
	);
	$wp_customize->add_control(
		'counsel_footer_disclaimer',
		array(
			'label'       => __( 'Footer disclaimer text', 'counsel' ),
			'description' => __( 'Leave blank to use the default independent-service disclaimer.', 'counsel' ),
			'section'     => 'counsel_settings',
			'type'        => 'textarea',
		)
	);

	// Toggle: show footer disclaimer --------------------------------------.
	$wp_customize->add_setting(
		'counsel_show_footer_disclaimer',
		array(
			'default'           => true,
			'sanitize_callback' => 'counsel_sanitize_checkbox',
			'transport'         => 'refresh',
		)
	);
	$wp_customize->add_control(
		'counsel_show_footer_disclaimer',
		array(
			'label'   => __( 'Show the global footer disclaimer', 'counsel' ),
			'section' => 'counsel_settings',
			'type'    => 'checkbox',
		)
	);

	// Selective refresh for the footer disclaimer.
	if ( isset( $wp_customize->selective_refresh ) ) {
		$wp_customize->selective_refresh->add_partial(
			'counsel_footer_disclaimer',
			array(
				'selector'        => '.counsel-footer__disclaimer',
				'render_callback' => 'counsel_disclaimer_footer',
			)
		);
	}
}
add_action( 'customize_register', 'counsel_customize_register' );

/**
 * Get a social-links array of populated entries only.
 *
 * @return array<string,string> Label => URL.
 */
function counsel_get_social_links() {
	$map = array(
		'LinkedIn'  => 'counsel_social_linkedin',
		'X'         => 'counsel_social_x',
		'Facebook'  => 'counsel_social_facebook',
		'Instagram' => 'counsel_social_instagram',
	);

	$links = array();
	foreach ( $map as $label => $mod ) {
		$url = get_theme_mod( $mod, '' );
		if ( $url ) {
			$links[ $label ] = $url;
		}
	}
	return $links;
}

/**
 * Convenience getter for the general contact email.
 *
 * @return string
 */
function counsel_get_contact_email() {
	return sanitize_email( get_theme_mod( 'counsel_contact_email', get_option( 'admin_email' ) ) );
}

/**
 * Convenience getter for the attorney-inquiry email.
 *
 * @return string
 */
function counsel_get_attorney_email() {
	return sanitize_email( get_theme_mod( 'counsel_attorney_email', get_option( 'admin_email' ) ) );
}
