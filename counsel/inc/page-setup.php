<?php
/**
 * One-time content setup: create the core Pages and supporting categories so
 * the navigation works out of the box.
 *
 * Runs on theme activation AND once on the next admin load (guarded by a
 * version option) so it also takes effect when the theme is updated in place
 * without switching away and back.
 *
 * Everything here is idempotent: pages/categories are only created if a page
 * with the same slug (or a category with the same slug) does not already
 * exist, so re-running never produces duplicates and never overwrites content
 * you've edited.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

/**
 * The bump key. Increment COUNSEL_CONTENT_VERSION to re-run the seeder once
 * after a future change.
 */
define( 'COUNSEL_CONTENT_VERSION', '1' );

/**
 * The pages Counsel creates, in menu order.
 *
 * @return array<int,array>
 */
function counsel_default_pages() {
	return array(
		array(
			'title'    => __( 'Home', 'counsel' ),
			'slug'     => 'home',
			'template' => '', // Uses front-page.php automatically when set as the front page.
			'content'  => '', // Optional editor intro; the hero + sections render regardless.
		),
		array(
			'title'    => __( 'How It Works', 'counsel' ),
			'slug'     => 'how-it-works',
			'template' => 'page-templates/template-how-it-works.php',
			'content'  => '',
		),
		array(
			'title'    => __( 'About', 'counsel' ),
			'slug'     => 'about',
			'template' => '', // Default page.php editorial layout.
			'content'  => counsel_about_placeholder(),
		),
		array(
			'title'    => __( 'For Attorneys', 'counsel' ),
			'slug'     => 'for-attorneys',
			'template' => 'page-templates/template-for-attorneys.php',
			'content'  => '',
		),
		array(
			'title'    => __( 'Contact', 'counsel' ),
			'slug'     => 'contact',
			'template' => 'page-templates/template-contact.php',
			'content'  => '',
		),
	);
}

/**
 * Light, on-brand placeholder copy for the About page (which uses the default
 * template and would otherwise be blank). Replace with your real copy.
 *
 * @return string
 */
function counsel_about_placeholder() {
	return implode(
		"\n\n",
		array(
			'<!-- wp:paragraph --><p>Counsel is an independent guide to hiring a lawyer. We are not a law firm, and we don\'t take referral fees from the people we serve. Our job is to make a stressful, opaque decision feel clearer and calmer.</p><!-- /wp:paragraph -->',
			'<!-- wp:heading --><h2>What we believe</h2><!-- /wp:heading -->',
			'<!-- wp:paragraph --><p>People deciding who to trust with a legal problem deserve real information, written by humans, in plain language. They deserve to know when something is sponsored — and to trust that sponsorship never buys a better review.</p><!-- /wp:paragraph -->',
			'<!-- wp:heading --><h2>How we stay independent</h2><!-- /wp:heading -->',
			'<!-- wp:paragraph --><p>Our profiles and "Best Of" selections are made independently by our editorial team. Sponsored placements are exclusive, clearly labeled, and kept entirely separate from our editorial judgment.</p><!-- /wp:paragraph -->',
		)
	);
}

/**
 * The supporting categories used by the editorial landings.
 *
 * @return array<int,array>
 */
function counsel_default_categories() {
	return array(
		array(
			'name'        => __( 'Ask Counsel', 'counsel' ),
			'slug'        => 'advice',
			'description' => __( 'Plain-language answers to the questions people ask before hiring a lawyer.', 'counsel' ),
		),
		array(
			'name'        => __( 'Guides', 'counsel' ),
			'slug'        => 'guides',
			'description' => __( 'Evergreen explainers on what legal help costs and how the process works.', 'counsel' ),
		),
	);
}

/**
 * Create the core pages (idempotent) and assign their page templates.
 *
 * @return void
 */
function counsel_seed_pages() {
	$order   = 0;
	$home_id = 0;

	foreach ( counsel_default_pages() as $page ) {
		$order++;
		$existing = get_page_by_path( $page['slug'] );

		if ( $existing instanceof WP_Post ) {
			$page_id = $existing->ID;
		} else {
			$page_id = wp_insert_post(
				array(
					'post_title'   => $page['title'],
					'post_name'    => $page['slug'],
					'post_content' => $page['content'],
					'post_status'  => 'publish',
					'post_type'    => 'page',
					'menu_order'   => $order,
				)
			);
		}

		if ( ! $page_id || is_wp_error( $page_id ) ) {
			continue;
		}

		// Assign the page template if one is specified and not already set.
		if ( '' !== $page['template'] ) {
			$current = get_post_meta( $page_id, '_wp_page_template', true );
			if ( $current !== $page['template'] ) {
				update_post_meta( $page_id, '_wp_page_template', $page['template'] );
			}
		}

		if ( 'home' === $page['slug'] ) {
			$home_id = $page_id;
		}
	}

	// Set the static front page only if the site is still showing the default
	// "latest posts" — never override a homepage the owner already chose.
	if ( $home_id && 'page' !== get_option( 'show_on_front' ) ) {
		update_option( 'show_on_front', 'page' );
		update_option( 'page_on_front', $home_id );
	}
}

/**
 * Create the supporting categories (idempotent).
 *
 * @return void
 */
function counsel_seed_categories() {
	foreach ( counsel_default_categories() as $cat ) {
		if ( get_term_by( 'slug', $cat['slug'], 'category' ) ) {
			continue;
		}
		wp_insert_term(
			$cat['name'],
			'category',
			array(
				'slug'        => $cat['slug'],
				'description' => $cat['description'],
			)
		);
	}
}

/**
 * Build the primary and footer menus if they don't already exist, and assign
 * them to their theme locations. Idempotent — skips if the menus already exist.
 *
 * @return void
 */
function counsel_seed_menus() {
	$locations = get_theme_mod( 'nav_menu_locations', array() );
	if ( ! is_array( $locations ) ) {
		$locations = array();
	}

	$archive_url = get_post_type_archive_link( 'firm' );
	$archive_url = $archive_url ? $archive_url : home_url( '/attorneys/' );

	// --- Primary (header) menu ------------------------------------------.
	if ( empty( $locations['primary'] ) || ! wp_get_nav_menu_object( $locations['primary'] ) ) {
		$primary_name = __( 'Primary', 'counsel' );
		$primary      = wp_get_nav_menu_object( $primary_name );
		$primary_id   = $primary ? $primary->term_id : wp_create_nav_menu( $primary_name );

		if ( ! is_wp_error( $primary_id ) ) {
			// Only populate a freshly created, empty menu.
			if ( ! wp_get_nav_menu_items( $primary_id ) ) {
				counsel_add_menu_link( $primary_id, __( 'Find a Lawyer', 'counsel' ), $archive_url );
				counsel_add_menu_page_link( $primary_id, 'how-it-works', __( 'How It Works', 'counsel' ) );
				counsel_add_menu_page_link( $primary_id, 'about', __( 'About', 'counsel' ) );
				counsel_add_menu_link( $primary_id, __( 'Ask Counsel', 'counsel' ), home_url( '/advice/' ) );
				counsel_add_menu_link( $primary_id, __( 'Guides', 'counsel' ), home_url( '/guides/' ) );
				// The advertiser-facing link gets its distinguishing CSS class.
				counsel_add_menu_page_link( $primary_id, 'for-attorneys', __( 'For Attorneys', 'counsel' ), 'menu-item--attorneys' );
			}
			$locations['primary'] = $primary_id;
		}
	}

	// --- Footer menu ----------------------------------------------------.
	if ( empty( $locations['footer'] ) || ! wp_get_nav_menu_object( $locations['footer'] ) ) {
		$footer_name = __( 'Footer', 'counsel' );
		$footer      = wp_get_nav_menu_object( $footer_name );
		$footer_id   = $footer ? $footer->term_id : wp_create_nav_menu( $footer_name );

		if ( ! is_wp_error( $footer_id ) ) {
			if ( ! wp_get_nav_menu_items( $footer_id ) ) {
				counsel_add_menu_page_link( $footer_id, 'about', __( 'About', 'counsel' ) );
				counsel_add_menu_page_link( $footer_id, 'how-it-works', __( 'How It Works', 'counsel' ) );
				counsel_add_menu_page_link( $footer_id, 'for-attorneys', __( 'For Attorneys', 'counsel' ) );
				counsel_add_menu_page_link( $footer_id, 'contact', __( 'Contact', 'counsel' ) );
			}
			$locations['footer'] = $footer_id;
		}
	}

	set_theme_mod( 'nav_menu_locations', $locations );
}

/**
 * Add a custom-URL item to a menu.
 *
 * @param int    $menu_id Menu term ID.
 * @param string $title   Item title.
 * @param string $url     URL.
 * @param string $classes Optional CSS classes.
 * @return void
 */
function counsel_add_menu_link( $menu_id, $title, $url, $classes = '' ) {
	wp_update_nav_menu_item(
		$menu_id,
		0,
		array(
			'menu-item-title'   => $title,
			'menu-item-url'     => $url,
			'menu-item-status'  => 'publish',
			'menu-item-type'    => 'custom',
			'menu-item-classes' => $classes,
		)
	);
}

/**
 * Add a page item to a menu by slug.
 *
 * @param int    $menu_id Menu term ID.
 * @param string $slug    Page slug.
 * @param string $title   Item title.
 * @param string $classes Optional CSS classes.
 * @return void
 */
function counsel_add_menu_page_link( $menu_id, $slug, $title, $classes = '' ) {
	$page = get_page_by_path( $slug );
	if ( ! $page instanceof WP_Post ) {
		return;
	}
	wp_update_nav_menu_item(
		$menu_id,
		0,
		array(
			'menu-item-title'     => $title,
			'menu-item-object'    => 'page',
			'menu-item-object-id' => $page->ID,
			'menu-item-type'      => 'post_type',
			'menu-item-status'    => 'publish',
			'menu-item-classes'   => $classes,
		)
	);
}

/**
 * Run the full content setup once.
 *
 * @return void
 */
function counsel_run_content_setup() {
	counsel_seed_categories();
	counsel_seed_pages();
	counsel_seed_menus();
	update_option( 'counsel_content_version', COUNSEL_CONTENT_VERSION );
}

/**
 * One-time runner on the next admin load after activation/update.
 *
 * @return void
 */
function counsel_maybe_run_content_setup() {
	if ( ! is_admin() || ! current_user_can( 'manage_options' ) ) {
		return;
	}
	if ( get_option( 'counsel_content_version' ) === COUNSEL_CONTENT_VERSION ) {
		return;
	}
	counsel_run_content_setup();
}
add_action( 'admin_init', 'counsel_maybe_run_content_setup' );
