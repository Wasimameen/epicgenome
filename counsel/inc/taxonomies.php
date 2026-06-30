<?php
/**
 * Register taxonomies attached to the "firm" post type.
 *
 * - practice_area (hierarchical): the kind of legal work a firm does.
 * - city (hierarchical): the metro/market a firm serves.
 *
 * Both are seeded with starter terms on theme activation (see functions.php →
 * counsel_after_switch_theme()).
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

/**
 * Register the practice_area and city taxonomies.
 *
 * @return void
 */
function counsel_register_taxonomies() {

	// Practice Area ---------------------------------------------------------.
	$practice_labels = array(
		'name'              => _x( 'Practice Areas', 'taxonomy general name', 'counsel' ),
		'singular_name'     => _x( 'Practice Area', 'taxonomy singular name', 'counsel' ),
		'search_items'      => __( 'Search Practice Areas', 'counsel' ),
		'all_items'         => __( 'All Practice Areas', 'counsel' ),
		'parent_item'       => __( 'Parent Practice Area', 'counsel' ),
		'parent_item_colon' => __( 'Parent Practice Area:', 'counsel' ),
		'edit_item'         => __( 'Edit Practice Area', 'counsel' ),
		'update_item'       => __( 'Update Practice Area', 'counsel' ),
		'add_new_item'      => __( 'Add New Practice Area', 'counsel' ),
		'new_item_name'     => __( 'New Practice Area Name', 'counsel' ),
		'menu_name'         => __( 'Practice Areas', 'counsel' ),
		'back_to_items'     => __( '← Back to Practice Areas', 'counsel' ),
	);

	register_taxonomy(
		'practice_area',
		array( 'firm' ),
		array(
			'labels'            => $practice_labels,
			'hierarchical'      => true,
			'public'            => true,
			'show_ui'           => true,
			'show_admin_column' => true,
			'show_in_nav_menus' => true,
			'show_in_rest'      => true,
			'query_var'         => true,
			'rewrite'           => array(
				'slug'       => 'practice-area',
				'with_front' => false,
			),
		)
	);

	// City ------------------------------------------------------------------.
	$city_labels = array(
		'name'              => _x( 'Cities', 'taxonomy general name', 'counsel' ),
		'singular_name'     => _x( 'City', 'taxonomy singular name', 'counsel' ),
		'search_items'      => __( 'Search Cities', 'counsel' ),
		'all_items'         => __( 'All Cities', 'counsel' ),
		'parent_item'       => __( 'Parent City', 'counsel' ),
		'parent_item_colon' => __( 'Parent City:', 'counsel' ),
		'edit_item'         => __( 'Edit City', 'counsel' ),
		'update_item'       => __( 'Update City', 'counsel' ),
		'add_new_item'      => __( 'Add New City', 'counsel' ),
		'new_item_name'     => __( 'New City Name', 'counsel' ),
		'menu_name'         => __( 'Cities', 'counsel' ),
		'back_to_items'     => __( '← Back to Cities', 'counsel' ),
	);

	register_taxonomy(
		'city',
		array( 'firm' ),
		array(
			'labels'            => $city_labels,
			'hierarchical'      => true,
			'public'            => true,
			'show_ui'           => true,
			'show_admin_column' => true,
			'show_in_nav_menus' => true,
			'show_in_rest'      => true,
			'query_var'         => true,
			'rewrite'           => array(
				'slug'       => 'city',
				'with_front' => false,
			),
		)
	);
}
add_action( 'init', 'counsel_register_taxonomies' );

/**
 * The starter practice-area terms seeded on activation.
 *
 * @return string[]
 */
function counsel_default_practice_areas() {
	return array(
		__( 'Personal Injury', 'counsel' ),
		__( 'Car Accidents', 'counsel' ),
		__( 'Criminal Defense & DUI', 'counsel' ),
		__( 'Family & Divorce', 'counsel' ),
		__( 'Bankruptcy', 'counsel' ),
		__( 'Immigration', 'counsel' ),
		__( 'Employment', 'counsel' ),
		__( 'Estate Planning', 'counsel' ),
		__( 'Business & Contracts', 'counsel' ),
		__( 'Real Estate', 'counsel' ),
	);
}

/**
 * The flagship city term seeded on activation.
 *
 * @return string[]
 */
function counsel_default_cities() {
	return array(
		__( 'Phoenix, AZ', 'counsel' ),
	);
}

/**
 * Seed the default taxonomy terms if they don't already exist.
 *
 * Called from counsel_after_switch_theme().
 *
 * @return void
 */
function counsel_seed_taxonomy_terms() {
	foreach ( counsel_default_practice_areas() as $term ) {
		if ( ! term_exists( $term, 'practice_area' ) ) {
			wp_insert_term( $term, 'practice_area' );
		}
	}

	foreach ( counsel_default_cities() as $term ) {
		if ( ! term_exists( $term, 'city' ) ) {
			wp_insert_term( $term, 'city' );
		}
	}
}
