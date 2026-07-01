<?php
/**
 * Dynamic CSS + font engine.
 *
 * Turns the Customizer settings into live CSS by overriding the brand tokens in
 * :root, and builds the Google Fonts request from the chosen font families.
 * This is what lets a non-developer customize colours, typography, and layout
 * from Appearance → Customize with no code.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

/**
 * Single source of truth for every customizable default.
 *
 * Keeping defaults here means the controls (inc/customizer.php) and the CSS
 * output stay in sync. Values mirror the original brand tokens exactly, so a
 * fresh install looks identical to the hand-built design.
 *
 * @return array<string,mixed>
 */
function counsel_defaults() {
	return array(
		// Colours.
		'counsel_color_oxblood'   => '#8A2326',
		'counsel_color_brass'     => '#B68A4E',
		'counsel_color_parchment' => '#F1E8D8',
		'counsel_color_ink'       => '#14110F',
		'counsel_color_paper'     => '#FBF9F5',
		'counsel_color_muted'     => '#57534E',
		'counsel_color_line'      => '#E4DDD0',
		'counsel_color_sponsored' => '#6B4E2E',

		// Typography.
		'counsel_font_heading'    => 'Fraunces',
		'counsel_font_body'       => 'Inter',
		'counsel_base_font_size'  => 18,   // px
		'counsel_heading_weight'  => 600,
		'counsel_measure'         => 68,   // ch

		// Layout.
		'counsel_container_width' => 1200, // px
		'counsel_radius'          => 4,    // px

		// Header.
		'counsel_sticky_header'   => true,
		'counsel_show_header_cta' => true,
		'counsel_header_cta_label' => 'Find a Lawyer',
		'counsel_header_cta_url'  => '',   // empty = firm archive

		// Hero.
		'counsel_show_hero'        => true,
		'counsel_show_hero_search' => true,
		'counsel_hero_kicker'      => 'Independent. Editorial. On your side.',
		'counsel_hero_title'       => 'Hiring a lawyer shouldn\'t be the hardest part.',
		'counsel_hero_lede'        => 'Counsel is an independent guide to finding the right attorney — calm, researched profiles instead of a wall of ads. We are not a law firm, and consumers never pay us.',
		'counsel_hero_trust'       => 'Every profile is researched independently. Sponsored placements are always clearly labeled.',

		// Homepage sections.
		'counsel_show_lanes'       => true,
		'counsel_show_trust'       => true,
		'counsel_show_areas'       => true,
		'counsel_show_closing'     => true,
		'counsel_closing_title'    => 'Start with the right questions.',
		'counsel_closing_lede'     => 'Find a firm, read an honest profile, and walk into your first call knowing what to ask.',

		// Footer.
		'counsel_footer_tagline'   => 'An independent guide to hiring a lawyer.',
	);
}

/**
 * Get a theme mod with the Counsel default fallback.
 *
 * @param string $key Setting key.
 * @return mixed
 */
function counsel_mod( $key ) {
	$defaults = counsel_defaults();
	$default  = isset( $defaults[ $key ] ) ? $defaults[ $key ] : '';
	return get_theme_mod( $key, $default );
}

/**
 * Heading font choices: label, Google Fonts spec, and CSS stack.
 *
 * @return array<string,array>
 */
function counsel_heading_fonts() {
	return array(
		'Fraunces'           => array(
			'label'  => __( 'Fraunces (default)', 'counsel' ),
			'google' => 'Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700',
			'stack'  => '"Fraunces", Georgia, "Times New Roman", serif',
		),
		'Playfair Display'   => array(
			'label'  => __( 'Playfair Display', 'counsel' ),
			'google' => 'Playfair+Display:wght@400;500;600;700',
			'stack'  => '"Playfair Display", Georgia, serif',
		),
		'Lora'               => array(
			'label'  => __( 'Lora', 'counsel' ),
			'google' => 'Lora:wght@400;500;600;700',
			'stack'  => '"Lora", Georgia, serif',
		),
		'Cormorant Garamond' => array(
			'label'  => __( 'Cormorant Garamond', 'counsel' ),
			'google' => 'Cormorant+Garamond:wght@400;500;600;700',
			'stack'  => '"Cormorant Garamond", Georgia, serif',
		),
		'Libre Baskerville'  => array(
			'label'  => __( 'Libre Baskerville', 'counsel' ),
			'google' => 'Libre+Baskerville:wght@400;700',
			'stack'  => '"Libre Baskerville", Georgia, serif',
		),
		'Georgia'            => array(
			'label'  => __( 'Georgia (system, no download)', 'counsel' ),
			'google' => '',
			'stack'  => 'Georgia, "Times New Roman", serif',
		),
	);
}

/**
 * Body font choices: label, Google Fonts spec, and CSS stack.
 *
 * @return array<string,array>
 */
function counsel_body_fonts() {
	return array(
		'Inter'         => array(
			'label'  => __( 'Inter (default)', 'counsel' ),
			'google' => 'Inter:wght@400;500;600;700',
			'stack'  => '"Inter", -apple-system, "Segoe UI", sans-serif',
		),
		'Work Sans'     => array(
			'label'  => __( 'Work Sans', 'counsel' ),
			'google' => 'Work+Sans:wght@400;500;600;700',
			'stack'  => '"Work Sans", -apple-system, sans-serif',
		),
		'Source Sans 3' => array(
			'label'  => __( 'Source Sans 3', 'counsel' ),
			'google' => 'Source+Sans+3:wght@400;500;600;700',
			'stack'  => '"Source Sans 3", -apple-system, sans-serif',
		),
		'Nunito Sans'   => array(
			'label'  => __( 'Nunito Sans', 'counsel' ),
			'google' => 'Nunito+Sans:wght@400;500;600;700',
			'stack'  => '"Nunito Sans", -apple-system, sans-serif',
		),
		'System'        => array(
			'label'  => __( 'System UI (system, no download)', 'counsel' ),
			'google' => '',
			'stack'  => '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
		),
	);
}

/**
 * Resolve the chosen heading font to its CSS stack.
 *
 * @return string
 */
function counsel_heading_font_stack() {
	$fonts  = counsel_heading_fonts();
	$choice = counsel_mod( 'counsel_font_heading' );
	return isset( $fonts[ $choice ] ) ? $fonts[ $choice ]['stack'] : $fonts['Fraunces']['stack'];
}

/**
 * Resolve the chosen body font to its CSS stack.
 *
 * @return string
 */
function counsel_body_font_stack() {
	$fonts  = counsel_body_fonts();
	$choice = counsel_mod( 'counsel_font_body' );
	return isset( $fonts[ $choice ] ) ? $fonts[ $choice ]['stack'] : $fonts['Inter']['stack'];
}

/**
 * Build the Google Fonts stylesheet URL from the chosen families.
 *
 * Returns '' when both selections are system fonts (nothing to download).
 *
 * @return string
 */
function counsel_google_fonts_url() {
	$families = array();

	$heading_fonts = counsel_heading_fonts();
	$heading       = counsel_mod( 'counsel_font_heading' );
	if ( isset( $heading_fonts[ $heading ] ) && '' !== $heading_fonts[ $heading ]['google'] ) {
		$families[] = $heading_fonts[ $heading ]['google'];
	}

	$body_fonts = counsel_body_fonts();
	$body       = counsel_mod( 'counsel_font_body' );
	if ( isset( $body_fonts[ $body ] ) && '' !== $body_fonts[ $body ]['google'] ) {
		$families[] = $body_fonts[ $body ]['google'];
	}

	if ( empty( $families ) ) {
		return '';
	}

	$url = 'https://fonts.googleapis.com/css2';
	foreach ( $families as $family ) {
		$url = add_query_arg( 'family', $family, $url );
	}
	$url = add_query_arg( 'display', 'swap', $url );

	// add_query_arg url-encodes the ':' and ',' which Google accepts, but keep
	// the '+' readable; Google requires literal '+' for spaces.
	return str_replace( '%2B', '+', $url );
}

/**
 * Compose the dynamic CSS that overrides the :root tokens.
 *
 * @return string
 */
function counsel_dynamic_css() {
	$radius    = (int) counsel_mod( 'counsel_radius' );
	$container = (int) counsel_mod( 'counsel_container_width' );
	$measure   = (int) counsel_mod( 'counsel_measure' );
	$base      = (float) counsel_mod( 'counsel_base_font_size' );
	$hw        = (int) counsel_mod( 'counsel_heading_weight' );

	$css  = ':root{';
	$css .= '--oxblood:' . sanitize_hex_color( counsel_mod( 'counsel_color_oxblood' ) ) . ';';
	$css .= '--brass:' . sanitize_hex_color( counsel_mod( 'counsel_color_brass' ) ) . ';';
	$css .= '--parchment:' . sanitize_hex_color( counsel_mod( 'counsel_color_parchment' ) ) . ';';
	$css .= '--ink:' . sanitize_hex_color( counsel_mod( 'counsel_color_ink' ) ) . ';';
	$css .= '--paper:' . sanitize_hex_color( counsel_mod( 'counsel_color_paper' ) ) . ';';
	$css .= '--muted:' . sanitize_hex_color( counsel_mod( 'counsel_color_muted' ) ) . ';';
	$css .= '--line:' . sanitize_hex_color( counsel_mod( 'counsel_color_line' ) ) . ';';
	$css .= '--sponsored:' . sanitize_hex_color( counsel_mod( 'counsel_color_sponsored' ) ) . ';';
	$css .= '--font-serif:' . counsel_heading_font_stack() . ';';
	$css .= '--font-sans:' . counsel_body_font_stack() . ';';

	if ( $container >= 800 && $container <= 1600 ) {
		$css .= '--container:' . $container . 'px;';
	}
	if ( $measure >= 45 && $measure <= 90 ) {
		$css .= '--measure:' . $measure . 'ch;';
	}
	if ( $radius >= 0 && $radius <= 40 ) {
		$css .= '--radius:' . $radius . 'px;';
	}
	if ( $base >= 15 && $base <= 22 ) {
		// Override the base body step; keep it responsive-friendly.
		$css .= '--step-0:' . ( $base / 16 ) . 'rem;';
	}
	$css .= '}';

	// Derived accent shades from oxblood/brass so hovers still feel right.
	$css .= ':root{--oxblood-dark:' . counsel_shade( counsel_mod( 'counsel_color_oxblood' ), -0.18 ) . ';';
	$css .= '--brass-dark:' . counsel_shade( counsel_mod( 'counsel_color_brass' ), -0.15 ) . ';}';

	if ( $hw >= 400 && $hw <= 800 ) {
		$css .= 'h1,h2,h3,h4,h5,h6{font-weight:' . $hw . ';}';
	}

	return $css;
}

/**
 * Darken or lighten a hex colour by a ratio (-1..1).
 *
 * @param string $hex   Hex colour.
 * @param float  $ratio Negative to darken, positive to lighten.
 * @return string Hex colour.
 */
function counsel_shade( $hex, $ratio ) {
	$hex = sanitize_hex_color( $hex );
	if ( ! $hex ) {
		return '#000000';
	}
	$hex = ltrim( $hex, '#' );
	if ( 3 === strlen( $hex ) ) {
		$hex = $hex[0] . $hex[0] . $hex[1] . $hex[1] . $hex[2] . $hex[2];
	}

	$r = hexdec( substr( $hex, 0, 2 ) );
	$g = hexdec( substr( $hex, 2, 2 ) );
	$b = hexdec( substr( $hex, 4, 2 ) );

	if ( $ratio < 0 ) {
		$r = (int) round( $r * ( 1 + $ratio ) );
		$g = (int) round( $g * ( 1 + $ratio ) );
		$b = (int) round( $b * ( 1 + $ratio ) );
	} else {
		$r = (int) round( $r + ( 255 - $r ) * $ratio );
		$g = (int) round( $g + ( 255 - $g ) * $ratio );
		$b = (int) round( $b + ( 255 - $b ) * $ratio );
	}

	$r = max( 0, min( 255, $r ) );
	$g = max( 0, min( 255, $g ) );
	$b = max( 0, min( 255, $b ) );

	return sprintf( '#%02x%02x%02x', $r, $g, $b );
}

/**
 * Attach the dynamic CSS after the main stylesheet.
 *
 * @return void
 */
function counsel_output_dynamic_css() {
	if ( wp_style_is( 'counsel-main', 'enqueued' ) || wp_style_is( 'counsel-main', 'registered' ) ) {
		wp_add_inline_style( 'counsel-main', counsel_dynamic_css() );
	}
}
add_action( 'wp_enqueue_scripts', 'counsel_output_dynamic_css', 20 );

/**
 * Add a sticky-header body class based on the setting.
 *
 * @param string[] $classes Body classes.
 * @return string[]
 */
function counsel_dynamic_body_classes( $classes ) {
	$classes[] = counsel_mod( 'counsel_sticky_header' ) ? 'has-sticky-header' : 'no-sticky-header';
	return $classes;
}
add_filter( 'body_class', 'counsel_dynamic_body_classes' );

/**
 * Enqueue the Customizer live-preview script.
 *
 * @return void
 */
function counsel_customize_preview_js() {
	$path = COUNSEL_DIR . '/assets/js/customize-preview.js';
	wp_enqueue_script(
		'counsel-customize-preview',
		COUNSEL_URI . '/assets/js/customize-preview.js',
		array( 'customize-preview' ),
		file_exists( $path ) ? filemtime( $path ) : COUNSEL_VERSION,
		true
	);
}
add_action( 'customize_preview_init', 'counsel_customize_preview_js' );
