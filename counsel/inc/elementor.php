<?php
/**
 * Elementor & page-builder compatibility.
 *
 * Makes Counsel a first-class Elementor theme:
 *
 *  - Registers the core Elementor Theme Builder locations (header, footer,
 *    single, archive) so Elementor Pro can visually design them. The theme's
 *    own header.php / footer.php / single*.php act as the fallback whenever a
 *    location is NOT overridden in Elementor, so the site works with or without
 *    the plugin.
 *  - Ships Full Width and Blank Canvas page templates so any page can be built
 *    100% in Elementor with no width constraints, sidebar, or forced title.
 *  - Declares the content widths Elementor reads for its default layout.
 *
 * Nothing here requires Elementor to be installed — every call is guarded.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

/**
 * Register all core Elementor Theme Builder locations.
 *
 * Requires Elementor Pro to actually assign templates to these locations; with
 * free Elementor (or no Elementor) the theme templates render as normal.
 *
 * @param object $elementor_theme_manager Elementor locations manager.
 * @return void
 */
function counsel_register_elementor_locations( $elementor_theme_manager ) {
	if ( method_exists( $elementor_theme_manager, 'register_all_core_location' ) ) {
		$elementor_theme_manager->register_all_core_location();
	}
}
add_action( 'elementor/theme/register_locations', 'counsel_register_elementor_locations' );

/**
 * Render an Elementor Theme Builder location if one is assigned.
 *
 * @param string $location Location slug: header, footer, single, archive.
 * @return bool True if Elementor rendered the location (so skip the theme's
 *              own markup); false to fall back to the theme template.
 */
function counsel_do_elementor_location( $location ) {
	if ( function_exists( 'elementor_theme_do_location' ) ) {
		return elementor_theme_do_location( $location );
	}
	return false;
}

/**
 * Whether Elementor (free or Pro) is active.
 *
 * @return bool
 */
function counsel_is_elementor_active() {
	return did_action( 'elementor/loaded' ) || defined( 'ELEMENTOR_VERSION' );
}

/**
 * Register the theme's Full Width and Blank Canvas page templates so they
 * appear in the Page Attributes → Template dropdown even before Elementor adds
 * its own. These give a clean, unconstrained canvas for page-builder content.
 *
 * @param array $templates Existing templates.
 * @return array
 */
function counsel_register_builder_templates( $templates ) {
	$templates['page-templates/template-full-width.php'] = __( 'Full Width (page builder)', 'counsel' );
	$templates['page-templates/template-canvas.php']     = __( 'Blank Canvas (page builder)', 'counsel' );
	return $templates;
}
add_filter( 'theme_page_templates', 'counsel_register_builder_templates' );

/**
 * Give Elementor sensible default content widths that match the theme.
 *
 * @return void
 */
function counsel_elementor_content_width() {
	if ( ! counsel_is_elementor_active() ) {
		return;
	}
	// Matches --container (1200) and the reading measure for boxed content.
	if ( ! isset( $GLOBALS['content_width'] ) ) {
		$GLOBALS['content_width'] = 1200;
	}
}
add_action( 'after_setup_theme', 'counsel_elementor_content_width', 20 );

/**
 * Add a helpful body class when a page uses a builder template.
 *
 * @param string[] $classes Body classes.
 * @return string[]
 */
function counsel_builder_body_class( $classes ) {
	if ( is_page_template( 'page-templates/template-full-width.php' ) ) {
		$classes[] = 'counsel-full-width';
	}
	if ( is_page_template( 'page-templates/template-canvas.php' ) ) {
		$classes[] = 'counsel-canvas';
	}
	return $classes;
}
add_filter( 'body_class', 'counsel_builder_body_class' );
