<?php
/**
 * Register the "firm" custom post type (Firm Profiles).
 *
 * URLs read /attorneys/... per the rewrite slug. The directory archive lives at
 * /attorneys/ (has_archive => true) and is rendered by archive-firm.php.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

/**
 * Register the Firm Profile post type.
 *
 * @return void
 */
function counsel_register_firm_post_type() {
	$labels = array(
		'name'                  => _x( 'Firm Profiles', 'Post type general name', 'counsel' ),
		'singular_name'         => _x( 'Firm Profile', 'Post type singular name', 'counsel' ),
		'menu_name'             => _x( 'Firm Profiles', 'Admin Menu text', 'counsel' ),
		'name_admin_bar'        => _x( 'Firm Profile', 'Add New on Toolbar', 'counsel' ),
		'add_new'               => __( 'Add New', 'counsel' ),
		'add_new_item'          => __( 'Add New Firm Profile', 'counsel' ),
		'new_item'              => __( 'New Firm Profile', 'counsel' ),
		'edit_item'             => __( 'Edit Firm Profile', 'counsel' ),
		'view_item'             => __( 'View Firm Profile', 'counsel' ),
		'all_items'             => __( 'All Firm Profiles', 'counsel' ),
		'search_items'          => __( 'Search Firm Profiles', 'counsel' ),
		'parent_item_colon'     => __( 'Parent Firm Profiles:', 'counsel' ),
		'not_found'             => __( 'No firm profiles found.', 'counsel' ),
		'not_found_in_trash'    => __( 'No firm profiles found in Trash.', 'counsel' ),
		'featured_image'        => __( 'Firm Photo', 'counsel' ),
		'set_featured_image'    => __( 'Set firm photo', 'counsel' ),
		'remove_featured_image' => __( 'Remove firm photo', 'counsel' ),
		'use_featured_image'    => __( 'Use as firm photo', 'counsel' ),
		'archives'              => __( 'Firm Directory', 'counsel' ),
		'insert_into_item'      => __( 'Insert into firm profile', 'counsel' ),
		'uploaded_to_this_item' => __( 'Uploaded to this firm profile', 'counsel' ),
		'filter_items_list'     => __( 'Filter firm profiles list', 'counsel' ),
		'items_list_navigation' => __( 'Firm profiles list navigation', 'counsel' ),
		'items_list'            => __( 'Firm profiles list', 'counsel' ),
	);

	$args = array(
		'labels'             => $labels,
		'description'        => __( 'Independent editorial profiles of individual law firms.', 'counsel' ),
		'public'             => true,
		'publicly_queryable' => true,
		'show_ui'            => true,
		'show_in_menu'       => true,
		'show_in_nav_menus'  => true,
		'show_in_rest'       => true, // Enables the block editor and REST API.
		'query_var'          => true,
		'rewrite'            => array(
			'slug'       => 'attorneys',
			'with_front' => false,
		),
		'capability_type'    => 'post',
		'has_archive'        => true,
		'hierarchical'       => false,
		'menu_position'      => 5,
		'menu_icon'          => 'dashicons-bank',
		'supports'           => array(
			'title',
			'editor',
			'thumbnail',
			'excerpt',
			'custom-fields',
			'revisions',
		),
	);

	register_post_type( 'firm', $args );
}
add_action( 'init', 'counsel_register_firm_post_type' );
