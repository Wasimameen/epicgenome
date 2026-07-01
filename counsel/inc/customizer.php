<?php
/**
 * Customizer: full theme-options panel.
 *
 * Everything a non-developer needs to restyle Counsel — colours, typography,
 * layout, header, hero, homepage sections, footer, and contact/social — lives
 * under Appearance → Customize → "Counsel Theme". Colour and text changes
 * preview live (postMessage); structural changes preview on refresh.
 *
 * Defaults live in inc/dynamic-css.php (counsel_defaults()) so the controls and
 * the generated CSS never drift apart.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

/* -------------------------------------------------------------------------
 * Sanitizers
 * ---------------------------------------------------------------------- */

/**
 * Sanitize a boolean checkbox to a real bool.
 *
 * @param mixed $value Raw value.
 * @return bool
 */
function counsel_sanitize_bool( $value ) {
	return (bool) $value;
}

/**
 * Sanitize an integer within a range.
 *
 * @param mixed $value Raw value.
 * @param int   $min   Minimum.
 * @param int   $max   Maximum.
 * @param int   $fallback Fallback.
 * @return int
 */
function counsel_sanitize_int_range( $value, $min, $max, $fallback ) {
	$value = (int) $value;
	if ( $value < $min || $value > $max ) {
		return $fallback;
	}
	return $value;
}

/**
 * Whitelist sanitizer for the heading-font select.
 *
 * @param string $value Raw value.
 * @return string
 */
function counsel_sanitize_heading_font( $value ) {
	$choices = array_keys( counsel_heading_fonts() );
	return in_array( $value, $choices, true ) ? $value : 'Fraunces';
}

/**
 * Whitelist sanitizer for the body-font select.
 *
 * @param string $value Raw value.
 * @return string
 */
function counsel_sanitize_body_font( $value ) {
	$choices = array_keys( counsel_body_fonts() );
	return in_array( $value, $choices, true ) ? $value : 'Inter';
}

/* -------------------------------------------------------------------------
 * Registration
 * ---------------------------------------------------------------------- */

/**
 * Register the whole Counsel Customizer experience.
 *
 * @param WP_Customize_Manager $wp_customize Manager.
 * @return void
 */
function counsel_customize_register( $wp_customize ) {
	$defaults = counsel_defaults();

	// Make core sections preview live where it makes sense.
	$wp_customize->get_setting( 'blogname' )->transport        = 'postMessage';
	$wp_customize->get_setting( 'blogdescription' )->transport = 'postMessage';

	// Top-level panel ------------------------------------------------------.
	$wp_customize->add_panel(
		'counsel_theme',
		array(
			'title'       => __( 'Counsel Theme', 'counsel' ),
			'description' => __( 'Customize every part of the Counsel design — colours, fonts, layout, and content.', 'counsel' ),
			'priority'    => 10,
		)
	);

	/* --- Colours ------------------------------------------------------- */
	$wp_customize->add_section(
		'counsel_colors',
		array(
			'title' => __( 'Brand Colours', 'counsel' ),
			'panel' => 'counsel_theme',
		)
	);

	$colors = array(
		'counsel_color_oxblood'   => __( 'Oxblood (primary — headings, buttons)', 'counsel' ),
		'counsel_color_brass'     => __( 'Brass (secondary — rules, hovers)', 'counsel' ),
		'counsel_color_parchment' => __( 'Parchment (section/card tint)', 'counsel' ),
		'counsel_color_ink'       => __( 'Ink (body text)', 'counsel' ),
		'counsel_color_paper'     => __( 'Paper (page background)', 'counsel' ),
		'counsel_color_muted'     => __( 'Muted (captions, secondary text)', 'counsel' ),
		'counsel_color_line'      => __( 'Hairline (borders)', 'counsel' ),
		'counsel_color_sponsored' => __( 'Sponsored label', 'counsel' ),
	);

	foreach ( $colors as $key => $label ) {
		$wp_customize->add_setting(
			$key,
			array(
				'default'           => $defaults[ $key ],
				'sanitize_callback' => 'sanitize_hex_color',
				'transport'         => 'postMessage',
			)
		);
		$wp_customize->add_control(
			new WP_Customize_Color_Control(
				$wp_customize,
				$key,
				array(
					'label'   => $label,
					'section' => 'counsel_colors',
				)
			)
		);
	}

	/* --- Typography ---------------------------------------------------- */
	$wp_customize->add_section(
		'counsel_typography',
		array(
			'title' => __( 'Typography', 'counsel' ),
			'panel' => 'counsel_theme',
		)
	);

	$wp_customize->add_setting(
		'counsel_font_heading',
		array(
			'default'           => $defaults['counsel_font_heading'],
			'sanitize_callback' => 'counsel_sanitize_heading_font',
			'transport'         => 'refresh',
		)
	);
	$heading_choices = array();
	foreach ( counsel_heading_fonts() as $k => $f ) {
		$heading_choices[ $k ] = $f['label'];
	}
	$wp_customize->add_control(
		'counsel_font_heading',
		array(
			'label'   => __( 'Heading font', 'counsel' ),
			'section' => 'counsel_typography',
			'type'    => 'select',
			'choices' => $heading_choices,
		)
	);

	$wp_customize->add_setting(
		'counsel_font_body',
		array(
			'default'           => $defaults['counsel_font_body'],
			'sanitize_callback' => 'counsel_sanitize_body_font',
			'transport'         => 'refresh',
		)
	);
	$body_choices = array();
	foreach ( counsel_body_fonts() as $k => $f ) {
		$body_choices[ $k ] = $f['label'];
	}
	$wp_customize->add_control(
		'counsel_font_body',
		array(
			'label'   => __( 'Body font', 'counsel' ),
			'section' => 'counsel_typography',
			'type'    => 'select',
			'choices' => $body_choices,
		)
	);

	$wp_customize->add_setting(
		'counsel_base_font_size',
		array(
			'default'           => $defaults['counsel_base_font_size'],
			'sanitize_callback' => function ( $v ) {
				return counsel_sanitize_int_range( $v, 15, 22, 18 );
			},
			'transport'         => 'refresh',
		)
	);
	$wp_customize->add_control(
		'counsel_base_font_size',
		array(
			'label'       => __( 'Base body font size (px)', 'counsel' ),
			'description' => __( '15–22. Default 18.', 'counsel' ),
			'section'     => 'counsel_typography',
			'type'        => 'number',
			'input_attrs' => array(
				'min'  => 15,
				'max'  => 22,
				'step' => 1,
			),
		)
	);

	$wp_customize->add_setting(
		'counsel_heading_weight',
		array(
			'default'           => $defaults['counsel_heading_weight'],
			'sanitize_callback' => function ( $v ) {
				return counsel_sanitize_int_range( $v, 400, 800, 600 );
			},
			'transport'         => 'refresh',
		)
	);
	$wp_customize->add_control(
		'counsel_heading_weight',
		array(
			'label'   => __( 'Heading weight', 'counsel' ),
			'section' => 'counsel_typography',
			'type'    => 'select',
			'choices' => array(
				400 => __( '400 — Regular', 'counsel' ),
				500 => __( '500 — Medium', 'counsel' ),
				600 => __( '600 — Semibold (default)', 'counsel' ),
				700 => __( '700 — Bold', 'counsel' ),
			),
		)
	);

	$wp_customize->add_setting(
		'counsel_measure',
		array(
			'default'           => $defaults['counsel_measure'],
			'sanitize_callback' => function ( $v ) {
				return counsel_sanitize_int_range( $v, 45, 90, 68 );
			},
			'transport'         => 'refresh',
		)
	);
	$wp_customize->add_control(
		'counsel_measure',
		array(
			'label'       => __( 'Reading width (characters)', 'counsel' ),
			'description' => __( 'Max width of long-form text. 45–90. Default 68.', 'counsel' ),
			'section'     => 'counsel_typography',
			'type'        => 'number',
			'input_attrs' => array(
				'min'  => 45,
				'max'  => 90,
				'step' => 1,
			),
		)
	);

	/* --- Layout -------------------------------------------------------- */
	$wp_customize->add_section(
		'counsel_layout',
		array(
			'title' => __( 'Layout', 'counsel' ),
			'panel' => 'counsel_theme',
		)
	);

	$wp_customize->add_setting(
		'counsel_container_width',
		array(
			'default'           => $defaults['counsel_container_width'],
			'sanitize_callback' => function ( $v ) {
				return counsel_sanitize_int_range( $v, 800, 1600, 1200 );
			},
			'transport'         => 'refresh',
		)
	);
	$wp_customize->add_control(
		'counsel_container_width',
		array(
			'label'       => __( 'Site max width (px)', 'counsel' ),
			'description' => __( '800–1600. Default 1200.', 'counsel' ),
			'section'     => 'counsel_layout',
			'type'        => 'number',
			'input_attrs' => array(
				'min'  => 800,
				'max'  => 1600,
				'step' => 20,
			),
		)
	);

	$wp_customize->add_setting(
		'counsel_radius',
		array(
			'default'           => $defaults['counsel_radius'],
			'sanitize_callback' => function ( $v ) {
				return counsel_sanitize_int_range( $v, 0, 40, 4 );
			},
			'transport'         => 'refresh',
		)
	);
	$wp_customize->add_control(
		'counsel_radius',
		array(
			'label'       => __( 'Corner radius (px)', 'counsel' ),
			'description' => __( '0 = sharp, up to 40 = rounded. Default 4.', 'counsel' ),
			'section'     => 'counsel_layout',
			'type'        => 'number',
			'input_attrs' => array(
				'min'  => 0,
				'max'  => 40,
				'step' => 1,
			),
		)
	);

	/* --- Header -------------------------------------------------------- */
	$wp_customize->add_section(
		'counsel_header',
		array(
			'title' => __( 'Header', 'counsel' ),
			'panel' => 'counsel_theme',
		)
	);

	counsel_add_toggle( $wp_customize, 'counsel_sticky_header', __( 'Stick header to top on scroll', 'counsel' ), 'counsel_header', $defaults );
	counsel_add_toggle( $wp_customize, 'counsel_show_header_cta', __( 'Show the header button', 'counsel' ), 'counsel_header', $defaults );

	counsel_add_text( $wp_customize, 'counsel_header_cta_label', __( 'Header button label', 'counsel' ), 'counsel_header', $defaults, 'postMessage' );

	$wp_customize->add_setting(
		'counsel_header_cta_url',
		array(
			'default'           => $defaults['counsel_header_cta_url'],
			'sanitize_callback' => 'esc_url_raw',
			'transport'         => 'refresh',
		)
	);
	$wp_customize->add_control(
		'counsel_header_cta_url',
		array(
			'label'       => __( 'Header button link', 'counsel' ),
			'description' => __( 'Leave blank to link to the Find a Lawyer directory.', 'counsel' ),
			'section'     => 'counsel_header',
			'type'        => 'url',
		)
	);

	/* --- Hero ---------------------------------------------------------- */
	$wp_customize->add_section(
		'counsel_hero',
		array(
			'title'       => __( 'Homepage Hero', 'counsel' ),
			'panel'       => 'counsel_theme',
			'description' => __( 'The headline area at the top of the homepage.', 'counsel' ),
		)
	);

	counsel_add_toggle( $wp_customize, 'counsel_show_hero', __( 'Show the hero', 'counsel' ), 'counsel_hero', $defaults );
	counsel_add_toggle( $wp_customize, 'counsel_show_hero_search', __( 'Show the search form in the hero', 'counsel' ), 'counsel_hero', $defaults );
	counsel_add_text( $wp_customize, 'counsel_hero_kicker', __( 'Kicker (small label above the headline)', 'counsel' ), 'counsel_hero', $defaults, 'postMessage' );
	counsel_add_text( $wp_customize, 'counsel_hero_title', __( 'Headline', 'counsel' ), 'counsel_hero', $defaults, 'postMessage' );
	counsel_add_textarea( $wp_customize, 'counsel_hero_lede', __( 'Intro paragraph', 'counsel' ), 'counsel_hero', $defaults );
	counsel_add_text( $wp_customize, 'counsel_hero_trust', __( 'Trust line (below the search)', 'counsel' ), 'counsel_hero', $defaults, 'postMessage' );

	/* --- Homepage sections -------------------------------------------- */
	$wp_customize->add_section(
		'counsel_home',
		array(
			'title' => __( 'Homepage Sections', 'counsel' ),
			'panel' => 'counsel_theme',
		)
	);

	counsel_add_toggle( $wp_customize, 'counsel_show_lanes', __( 'Show the "three lanes" section', 'counsel' ), 'counsel_home', $defaults );
	counsel_add_toggle( $wp_customize, 'counsel_show_trust', __( 'Show the "why Counsel is different" row', 'counsel' ), 'counsel_home', $defaults );
	counsel_add_toggle( $wp_customize, 'counsel_show_areas', __( 'Show the practice-areas grid', 'counsel' ), 'counsel_home', $defaults );
	counsel_add_toggle( $wp_customize, 'counsel_show_closing', __( 'Show the closing call-to-action', 'counsel' ), 'counsel_home', $defaults );
	counsel_add_text( $wp_customize, 'counsel_closing_title', __( 'Closing CTA headline', 'counsel' ), 'counsel_home', $defaults, 'postMessage' );
	counsel_add_textarea( $wp_customize, 'counsel_closing_lede', __( 'Closing CTA text', 'counsel' ), 'counsel_home', $defaults );

	/* --- Footer -------------------------------------------------------- */
	$wp_customize->add_section(
		'counsel_footer',
		array(
			'title' => __( 'Footer', 'counsel' ),
			'panel' => 'counsel_theme',
		)
	);

	counsel_add_text( $wp_customize, 'counsel_footer_tagline', __( 'Footer tagline', 'counsel' ), 'counsel_footer', $defaults, 'postMessage' );

	$wp_customize->add_setting(
		'counsel_show_footer_disclaimer',
		array(
			'default'           => true,
			'sanitize_callback' => 'counsel_sanitize_bool',
			'transport'         => 'refresh',
		)
	);
	$wp_customize->add_control(
		'counsel_show_footer_disclaimer',
		array(
			'label'   => __( 'Show the global footer disclaimer', 'counsel' ),
			'section' => 'counsel_footer',
			'type'    => 'checkbox',
		)
	);

	$wp_customize->add_setting(
		'counsel_footer_disclaimer',
		array(
			'default'           => '',
			'sanitize_callback' => 'wp_kses_post',
			'transport'         => 'postMessage',
		)
	);
	$wp_customize->add_control(
		'counsel_footer_disclaimer',
		array(
			'label'       => __( 'Footer disclaimer text', 'counsel' ),
			'description' => __( 'Leave blank to use the default independent-service disclaimer.', 'counsel' ),
			'section'     => 'counsel_footer',
			'type'        => 'textarea',
		)
	);

	/* --- Contact & Social --------------------------------------------- */
	$wp_customize->add_section(
		'counsel_contact',
		array(
			'title' => __( 'Contact & Social', 'counsel' ),
			'panel' => 'counsel_theme',
		)
	);

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
			'section' => 'counsel_contact',
			'type'    => 'email',
		)
	);

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
			'section'     => 'counsel_contact',
			'type'        => 'email',
		)
	);

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
			'section' => 'counsel_contact',
			'type'    => 'text',
		)
	);

	$socials = array(
		'counsel_social_linkedin'  => __( 'LinkedIn URL', 'counsel' ),
		'counsel_social_x'         => __( 'X / Twitter URL', 'counsel' ),
		'counsel_social_facebook'  => __( 'Facebook URL', 'counsel' ),
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
				'section' => 'counsel_contact',
				'type'    => 'url',
			)
		);
	}

	/* --- Selective-refresh partials ----------------------------------- */
	if ( isset( $wp_customize->selective_refresh ) ) {
		$wp_customize->selective_refresh->add_partial(
			'counsel_footer_disclaimer',
			array(
				'selector'        => '.counsel-footer__disclaimer',
				'render_callback' => 'counsel_disclaimer_footer',
			)
		);
		$wp_customize->selective_refresh->add_partial(
			'blogname',
			array(
				'selector'        => '.site-branding__text',
				'render_callback' => function () {
					return get_bloginfo( 'name' );
				},
			)
		);
	}
}
add_action( 'customize_register', 'counsel_customize_register' );

/* -------------------------------------------------------------------------
 * Small control helpers (reduce repetition)
 * ---------------------------------------------------------------------- */

/**
 * Add a checkbox toggle.
 *
 * @param WP_Customize_Manager $wp_customize Manager.
 * @param string               $id       Setting id.
 * @param string               $label    Label.
 * @param string               $section  Section id.
 * @param array                $defaults Defaults.
 * @return void
 */
function counsel_add_toggle( $wp_customize, $id, $label, $section, $defaults ) {
	$wp_customize->add_setting(
		$id,
		array(
			'default'           => $defaults[ $id ],
			'sanitize_callback' => 'counsel_sanitize_bool',
			'transport'         => 'refresh',
		)
	);
	$wp_customize->add_control(
		$id,
		array(
			'label'   => $label,
			'section' => $section,
			'type'    => 'checkbox',
		)
	);
}

/**
 * Add a text control.
 *
 * @param WP_Customize_Manager $wp_customize Manager.
 * @param string               $id        Setting id.
 * @param string               $label     Label.
 * @param string               $section   Section id.
 * @param array                $defaults  Defaults.
 * @param string               $transport Transport.
 * @return void
 */
function counsel_add_text( $wp_customize, $id, $label, $section, $defaults, $transport = 'refresh' ) {
	$wp_customize->add_setting(
		$id,
		array(
			'default'           => $defaults[ $id ],
			'sanitize_callback' => 'sanitize_text_field',
			'transport'         => $transport,
		)
	);
	$wp_customize->add_control(
		$id,
		array(
			'label'   => $label,
			'section' => $section,
			'type'    => 'text',
		)
	);
}

/**
 * Add a textarea control.
 *
 * @param WP_Customize_Manager $wp_customize Manager.
 * @param string               $id       Setting id.
 * @param string               $label    Label.
 * @param string               $section  Section id.
 * @param array                $defaults Defaults.
 * @return void
 */
function counsel_add_textarea( $wp_customize, $id, $label, $section, $defaults ) {
	$wp_customize->add_setting(
		$id,
		array(
			'default'           => $defaults[ $id ],
			'sanitize_callback' => 'sanitize_textarea_field',
			'transport'         => 'postMessage',
		)
	);
	$wp_customize->add_control(
		$id,
		array(
			'label'   => $label,
			'section' => $section,
			'type'    => 'textarea',
		)
	);
}

/* -------------------------------------------------------------------------
 * Convenience getters (used by templates & functions.php)
 * ---------------------------------------------------------------------- */

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
 * General contact email.
 *
 * @return string
 */
function counsel_get_contact_email() {
	return sanitize_email( get_theme_mod( 'counsel_contact_email', get_option( 'admin_email' ) ) );
}

/**
 * Attorney-inquiry email.
 *
 * @return string
 */
function counsel_get_attorney_email() {
	return sanitize_email( get_theme_mod( 'counsel_attorney_email', get_option( 'admin_email' ) ) );
}

/**
 * The header CTA URL (falls back to the firm archive).
 *
 * @return string
 */
function counsel_header_cta_url() {
	$url = counsel_mod( 'counsel_header_cta_url' );
	if ( $url ) {
		return $url;
	}
	$archive = get_post_type_archive_link( 'firm' );
	return $archive ? $archive : home_url( '/' );
}
