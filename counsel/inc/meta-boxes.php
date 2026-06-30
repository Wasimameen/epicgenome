<?php
/**
 * Native meta boxes for the firm custom fields.
 *
 * These provide a plugin-free way to edit firm data. If Advanced Custom Fields
 * (ACF) is installed and you prefer a GUI, you can map the same meta keys there;
 * the template tags read the raw post meta either way, so both approaches work.
 * When ACF manages these fields, set the constant COUNSEL_DISABLE_NATIVE_META
 * to true (e.g. in wp-config.php) to hide the native boxes.
 *
 * Meta keys (all stored without leading underscore so they remain visible to
 * the Custom Fields panel and to ACF):
 *   firm_founded, firm_size, firm_languages, firm_consultation, firm_fees,
 *   firm_phone, firm_website, firm_best_for, firm_is_sponsored,
 *   firm_results (one per line), firm_sources
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

/**
 * The schema for every firm meta field.
 *
 * @return array<string,array> Keyed by meta key.
 */
function counsel_firm_meta_fields() {
	return array(
		'firm_best_for'    => array(
			'label'    => __( 'Best for (one-liner)', 'counsel' ),
			'type'     => 'text',
			'sanitize' => 'sanitize_text_field',
			'desc'     => __( 'A short summary shown on cards and at the top of the profile. e.g. "Serious injury cases that go to trial."', 'counsel' ),
		),
		'firm_founded'     => array(
			'label'    => __( 'Year founded', 'counsel' ),
			'type'     => 'number',
			'sanitize' => 'counsel_sanitize_year',
		),
		'firm_size'        => array(
			'label'    => __( 'Firm size (attorney count)', 'counsel' ),
			'type'     => 'text',
			'sanitize' => 'sanitize_text_field',
			'desc'     => __( 'e.g. "12 attorneys" or "Solo practice".', 'counsel' ),
		),
		'firm_languages'   => array(
			'label'    => __( 'Languages', 'counsel' ),
			'type'     => 'text',
			'sanitize' => 'sanitize_text_field',
			'desc'     => __( 'e.g. "English, Spanish".', 'counsel' ),
		),
		'firm_consultation' => array(
			'label'    => __( 'Consultation', 'counsel' ),
			'type'     => 'text',
			'sanitize' => 'sanitize_text_field',
			'desc'     => __( 'e.g. "Free" or "$150 / first hour".', 'counsel' ),
		),
		'firm_fees'        => array(
			'label'    => __( 'Fee structure', 'counsel' ),
			'type'     => 'text',
			'sanitize' => 'sanitize_text_field',
			'desc'     => __( 'e.g. "Contingency" or "Hourly / flat fee".', 'counsel' ),
		),
		'firm_phone'       => array(
			'label'    => __( 'Phone', 'counsel' ),
			'type'     => 'text',
			'sanitize' => 'sanitize_text_field',
		),
		'firm_website'     => array(
			'label'    => __( 'Website', 'counsel' ),
			'type'     => 'url',
			'sanitize' => 'esc_url_raw',
		),
		'firm_results'     => array(
			'label'    => __( 'Notable results (firm-reported, one per line)', 'counsel' ),
			'type'     => 'textarea',
			'sanitize' => 'counsel_sanitize_textarea_lines',
			'desc'     => __( 'Each line becomes one item. A "past results do not guarantee future outcomes" disclaimer is added automatically.', 'counsel' ),
		),
		'firm_sources'     => array(
			'label'    => __( 'Sources', 'counsel' ),
			'type'     => 'textarea',
			'sanitize' => 'wp_kses_post',
			'desc'     => __( 'Where the information in this profile came from. One per line; URLs become links.', 'counsel' ),
		),
		'firm_is_sponsored' => array(
			'label'    => __( 'This firm is a sponsor', 'counsel' ),
			'type'     => 'checkbox',
			'sanitize' => 'counsel_sanitize_checkbox',
			'desc'     => __( 'When checked, the "Sponsored" label is shown on this firm\'s card and profile. Disclosure is required — never hide it.', 'counsel' ),
		),
	);
}

/**
 * Sanitize a four-digit year.
 *
 * @param mixed $value Raw value.
 * @return string
 */
function counsel_sanitize_year( $value ) {
	$value = absint( $value );
	return ( $value >= 1700 && $value <= 2200 ) ? (string) $value : '';
}

/**
 * Sanitize a checkbox to '1' or ''.
 *
 * @param mixed $value Raw value.
 * @return string
 */
function counsel_sanitize_checkbox( $value ) {
	return ! empty( $value ) ? '1' : '';
}

/**
 * Sanitize a multi-line textarea, cleaning each line.
 *
 * @param mixed $value Raw value.
 * @return string
 */
function counsel_sanitize_textarea_lines( $value ) {
	$value = (string) $value;
	$lines = array_map( 'sanitize_text_field', preg_split( '/\r\n|\r|\n/', $value ) );
	$lines = array_filter( array_map( 'trim', $lines ), 'strlen' );
	return implode( "\n", $lines );
}

/**
 * Whether native meta boxes should be used.
 *
 * @return bool
 */
function counsel_use_native_meta() {
	if ( defined( 'COUNSEL_DISABLE_NATIVE_META' ) && COUNSEL_DISABLE_NATIVE_META ) {
		return false;
	}
	return true;
}

/**
 * Register the post meta so it is available in REST / block editor and
 * properly sanitized regardless of where it is set.
 *
 * @return void
 */
function counsel_register_firm_meta() {
	foreach ( counsel_firm_meta_fields() as $key => $field ) {
		register_post_meta(
			'firm',
			$key,
			array(
				'type'              => 'string',
				'single'            => true,
				'show_in_rest'      => true,
				'sanitize_callback' => $field['sanitize'],
				'auth_callback'     => function () {
					return current_user_can( 'edit_posts' );
				},
			)
		);
	}
}
add_action( 'init', 'counsel_register_firm_meta' );

/**
 * Add the meta box to the firm editor screen.
 *
 * @return void
 */
function counsel_add_firm_meta_box() {
	if ( ! counsel_use_native_meta() ) {
		return;
	}

	add_meta_box(
		'counsel_firm_details',
		__( 'Firm Details', 'counsel' ),
		'counsel_render_firm_meta_box',
		'firm',
		'normal',
		'high'
	);
}
add_action( 'add_meta_boxes', 'counsel_add_firm_meta_box' );

/**
 * Render the firm details meta box.
 *
 * @param WP_Post $post Current post object.
 * @return void
 */
function counsel_render_firm_meta_box( $post ) {
	wp_nonce_field( 'counsel_save_firm_meta', 'counsel_firm_meta_nonce' );

	echo '<style>.counsel-meta-field{margin:0 0 16px}.counsel-meta-field label{display:block;font-weight:600;margin-bottom:4px}.counsel-meta-field .description{color:#646970;font-style:italic}.counsel-meta-field input[type=text],.counsel-meta-field input[type=url],.counsel-meta-field input[type=number],.counsel-meta-field textarea{width:100%}</style>';

	foreach ( counsel_firm_meta_fields() as $key => $field ) {
		$value = get_post_meta( $post->ID, $key, true );
		$id    = 'counsel_' . $key;

		echo '<div class="counsel-meta-field">';

		if ( 'checkbox' === $field['type'] ) {
			printf(
				'<label for="%1$s"><input type="checkbox" id="%1$s" name="%2$s" value="1" %3$s /> %4$s</label>',
				esc_attr( $id ),
				esc_attr( $key ),
				checked( $value, '1', false ),
				esc_html( $field['label'] )
			);
		} else {
			printf(
				'<label for="%1$s">%2$s</label>',
				esc_attr( $id ),
				esc_html( $field['label'] )
			);

			if ( 'textarea' === $field['type'] ) {
				printf(
					'<textarea id="%1$s" name="%2$s" rows="5">%3$s</textarea>',
					esc_attr( $id ),
					esc_attr( $key ),
					esc_textarea( $value )
				);
			} else {
				printf(
					'<input type="%1$s" id="%2$s" name="%3$s" value="%4$s" />',
					esc_attr( $field['type'] ),
					esc_attr( $id ),
					esc_attr( $key ),
					esc_attr( $value )
				);
			}
		}

		if ( ! empty( $field['desc'] ) ) {
			printf( '<p class="description">%s</p>', esc_html( $field['desc'] ) );
		}

		echo '</div>';
	}
}

/**
 * Save the firm meta box fields.
 *
 * @param int $post_id Post ID.
 * @return void
 */
function counsel_save_firm_meta( $post_id ) {
	if ( ! counsel_use_native_meta() ) {
		return;
	}

	// Verify nonce.
	if ( ! isset( $_POST['counsel_firm_meta_nonce'] )
		|| ! wp_verify_nonce( sanitize_key( wp_unslash( $_POST['counsel_firm_meta_nonce'] ) ), 'counsel_save_firm_meta' ) ) {
		return;
	}

	if ( defined( 'DOING_AUTOSAVE' ) && DOING_AUTOSAVE ) {
		return;
	}

	if ( 'firm' !== get_post_type( $post_id ) || ! current_user_can( 'edit_post', $post_id ) ) {
		return;
	}

	foreach ( counsel_firm_meta_fields() as $key => $field ) {
		if ( 'checkbox' === $field['type'] ) {
			$raw = isset( $_POST[ $key ] ) ? '1' : '';
		} else {
			$raw = isset( $_POST[ $key ] ) ? wp_unslash( $_POST[ $key ] ) : '';
		}

		$clean = call_user_func( $field['sanitize'], $raw );

		if ( '' === $clean || null === $clean ) {
			delete_post_meta( $post_id, $key );
		} else {
			update_post_meta( $post_id, $key, $clean );
		}
	}
}
add_action( 'save_post_firm', 'counsel_save_firm_meta' );
