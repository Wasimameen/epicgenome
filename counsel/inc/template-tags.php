<?php
/**
 * Reusable template tags for Counsel.
 *
 * These helpers keep templates clean and ensure consistent, escaped output.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

/**
 * Get a firm meta value with a fallback.
 *
 * @param string   $key     Meta key (e.g. 'firm_phone').
 * @param int|null $post_id Optional post ID; defaults to current post.
 * @param string   $default Default value.
 * @return string
 */
function counsel_get_firm_meta( $key, $post_id = null, $default = '' ) {
	$post_id = $post_id ? $post_id : get_the_ID();
	$value   = get_post_meta( $post_id, $key, true );
	return ( '' === $value || false === $value || null === $value ) ? $default : $value;
}

/**
 * Whether a firm is sponsored.
 *
 * @param int|null $post_id Optional post ID.
 * @return bool
 */
function counsel_is_sponsored( $post_id = null ) {
	return '1' === counsel_get_firm_meta( 'firm_is_sponsored', $post_id, '' );
}

/**
 * Output the Sponsored badge.
 *
 * A first-class disclosure element: always obviously visible, never hidden.
 * Pass a $post_id to force; otherwise it only renders when the current firm is
 * flagged sponsored — unless $force is true.
 *
 * @param array $args {
 *     Optional arguments.
 *
 *     @type int    $post_id Post ID to check. Default current post.
 *     @type bool   $force   Render even if not flagged. Default false.
 *     @type bool   $echo    Echo (true) or return (false). Default true.
 *     @type string $size    'sm' or 'md'. Default 'md'.
 * }
 * @return string The badge markup (also echoed unless $echo is false).
 */
function counsel_sponsored_badge( $args = array() ) {
	$args = wp_parse_args(
		$args,
		array(
			'post_id' => null,
			'force'   => false,
			'echo'    => true,
			'size'    => 'md',
		)
	);

	if ( ! $args['force'] && ! counsel_is_sponsored( $args['post_id'] ) ) {
		return '';
	}

	$class = 'counsel-sponsored';
	if ( 'sm' === $args['size'] ) {
		$class .= ' counsel-sponsored--sm';
	}

	$html = sprintf(
		'<span class="%1$s" title="%2$s">%3$s</span>',
		esc_attr( $class ),
		esc_attr__( 'This firm pays for an exclusive sponsorship. It does not affect our independent reviews.', 'counsel' ),
		esc_html__( 'Sponsored', 'counsel' )
	);

	if ( $args['echo'] ) {
		echo $html; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Built from escaped parts above.
	}

	return $html;
}

/**
 * Render the "at a glance" fact box for a firm profile.
 *
 * Built entirely from custom fields. Only rows with data appear.
 *
 * @param int|null $post_id Optional post ID.
 * @return void
 */
function counsel_fact_box( $post_id = null ) {
	$post_id = $post_id ? $post_id : get_the_ID();

	$rows = array(
		'firm_founded'      => array(
			'label' => __( 'Founded', 'counsel' ),
			'icon'  => 'calendar',
		),
		'firm_size'         => array(
			'label' => __( 'Size', 'counsel' ),
			'icon'  => 'team',
		),
		'firm_consultation' => array(
			'label' => __( 'Consultation', 'counsel' ),
			'icon'  => 'chat',
		),
		'firm_fees'         => array(
			'label' => __( 'Fees', 'counsel' ),
			'icon'  => 'fees',
		),
		'firm_languages'    => array(
			'label' => __( 'Languages', 'counsel' ),
			'icon'  => 'globe',
		),
	);

	$has_any = false;
	foreach ( array_keys( $rows ) as $key ) {
		if ( '' !== counsel_get_firm_meta( $key, $post_id, '' ) ) {
			$has_any = true;
			break;
		}
	}

	$phone   = counsel_get_firm_meta( 'firm_phone', $post_id, '' );
	$website = counsel_get_firm_meta( 'firm_website', $post_id, '' );

	if ( ! $has_any && '' === $phone && '' === $website ) {
		return;
	}

	echo '<aside class="counsel-factbox" aria-label="' . esc_attr__( 'Firm at a glance', 'counsel' ) . '">';
	echo '<h2 class="counsel-factbox__title">' . esc_html__( 'At a glance', 'counsel' ) . '</h2>';
	echo '<dl class="counsel-factbox__list">';

	foreach ( $rows as $key => $row ) {
		$value = counsel_get_firm_meta( $key, $post_id, '' );
		if ( '' === $value ) {
			continue;
		}
		printf(
			'<div class="counsel-factbox__row"><dt>%1$s</dt><dd>%2$s</dd></div>',
			esc_html( $row['label'] ),
			esc_html( $value )
		);
	}

	echo '</dl>';

	if ( '' !== $phone || '' !== $website ) {
		echo '<div class="counsel-factbox__contact">';
		if ( '' !== $phone ) {
			printf(
				'<a class="counsel-btn counsel-btn--primary counsel-factbox__cta" href="%1$s">%2$s</a>',
				esc_url( 'tel:' . preg_replace( '/[^0-9+]/', '', $phone ) ),
				/* translators: %s: phone number */
				esc_html( sprintf( __( 'Call %s', 'counsel' ), $phone ) )
			);
		}
		if ( '' !== $website ) {
			printf(
				'<a class="counsel-btn counsel-btn--ghost counsel-factbox__cta" href="%1$s" rel="nofollow noopener" target="_blank">%2$s</a>',
				esc_url( $website ),
				esc_html__( 'Visit website', 'counsel' )
			);
		}
		echo '</div>';
	}

	echo '</aside>';
}

/**
 * Output the practice-area term links for a firm as pill tags.
 *
 * @param int|null $post_id  Optional post ID.
 * @param int      $limit    Max number of tags (0 = all).
 * @return void
 */
function counsel_practice_area_tags( $post_id = null, $limit = 0 ) {
	$post_id = $post_id ? $post_id : get_the_ID();
	$terms   = get_the_terms( $post_id, 'practice_area' );

	if ( empty( $terms ) || is_wp_error( $terms ) ) {
		return;
	}

	if ( $limit > 0 ) {
		$terms = array_slice( $terms, 0, $limit );
	}

	echo '<ul class="counsel-tags" aria-label="' . esc_attr__( 'Practice areas', 'counsel' ) . '">';
	foreach ( $terms as $term ) {
		printf(
			'<li><a class="counsel-tag" href="%1$s">%2$s</a></li>',
			esc_url( get_term_link( $term ) ),
			esc_html( $term->name )
		);
	}
	echo '</ul>';
}

/**
 * Get a comma-separated, linked list of a firm's cities.
 *
 * @param int|null $post_id Optional post ID.
 * @return string
 */
function counsel_firm_cities( $post_id = null ) {
	$post_id = $post_id ? $post_id : get_the_ID();
	$terms   = get_the_terms( $post_id, 'city' );

	if ( empty( $terms ) || is_wp_error( $terms ) ) {
		return '';
	}

	$links = array();
	foreach ( $terms as $term ) {
		$links[] = sprintf(
			'<a href="%1$s">%2$s</a>',
			esc_url( get_term_link( $term ) ),
			esc_html( $term->name )
		);
	}

	return implode( ', ', $links );
}

/**
 * Output an entry meta line (date + category) for posts.
 *
 * @return void
 */
function counsel_entry_meta() {
	echo '<div class="counsel-entry-meta">';
	printf(
		'<time class="counsel-entry-date" datetime="%1$s">%2$s</time>',
		esc_attr( get_the_date( DATE_W3C ) ),
		esc_html( get_the_date() )
	);

	$cats = get_the_category_list( ', ' );
	if ( $cats ) {
		echo '<span class="counsel-entry-cats">' . wp_kses_post( $cats ) . '</span>';
	}
	echo '</div>';
}

/**
 * Output a simple breadcrumb trail. SEO-friendly and accessible.
 *
 * @return void
 */
function counsel_breadcrumbs() {
	if ( is_front_page() ) {
		return;
	}

	$items   = array();
	$items[] = sprintf(
		'<a href="%1$s">%2$s</a>',
		esc_url( home_url( '/' ) ),
		esc_html__( 'Home', 'counsel' )
	);

	if ( is_singular( 'firm' ) ) {
		$items[] = sprintf(
			'<a href="%1$s">%2$s</a>',
			esc_url( get_post_type_archive_link( 'firm' ) ),
			esc_html__( 'Find a Lawyer', 'counsel' )
		);
		$cities = get_the_terms( get_the_ID(), 'city' );
		if ( ! empty( $cities ) && ! is_wp_error( $cities ) ) {
			$city    = array_shift( $cities );
			$items[] = sprintf(
				'<a href="%1$s">%2$s</a>',
				esc_url( get_term_link( $city ) ),
				esc_html( $city->name )
			);
		}
		$items[] = esc_html( get_the_title() );
	} elseif ( is_post_type_archive( 'firm' ) ) {
		$items[] = esc_html__( 'Find a Lawyer', 'counsel' );
	} elseif ( is_tax( array( 'practice_area', 'city' ) ) ) {
		$items[] = sprintf(
			'<a href="%1$s">%2$s</a>',
			esc_url( get_post_type_archive_link( 'firm' ) ),
			esc_html__( 'Find a Lawyer', 'counsel' )
		);
		$items[] = esc_html( single_term_title( '', false ) );
	} elseif ( is_singular() ) {
		$items[] = esc_html( get_the_title() );
	} elseif ( is_search() ) {
		$items[] = esc_html__( 'Search', 'counsel' );
	} elseif ( is_archive() ) {
		$items[] = esc_html( get_the_archive_title() );
	} else {
		$items[] = esc_html( wp_get_document_title() );
	}

	echo '<nav class="counsel-breadcrumbs" aria-label="' . esc_attr__( 'Breadcrumb', 'counsel' ) . '">';
	echo wp_kses_post( implode( ' <span class="counsel-breadcrumbs__sep" aria-hidden="true">/</span> ', $items ) );
	echo '</nav>';
}

/**
 * Output a section heading with the editorial hairline rule.
 *
 * @param string $text  Heading text.
 * @param string $tag   Heading tag (h2, h3...). Default h2.
 * @param string $kicker Optional small kicker above the heading.
 * @return void
 */
function counsel_section_heading( $text, $tag = 'h2', $kicker = '' ) {
	$tag = preg_match( '/^h[1-6]$/', $tag ) ? $tag : 'h2';
	echo '<header class="counsel-section-heading">';
	if ( '' !== $kicker ) {
		echo '<span class="counsel-kicker">' . esc_html( $kicker ) . '</span>';
	}
	printf( '<%1$s class="counsel-section-heading__title">%2$s</%1$s>', esc_attr( $tag ), esc_html( $text ) );
	echo '</header>';
}

/**
 * Render a disclaimer block by key.
 *
 * @param string $type One of: not_legal_advice, results, advertising, profile,
 *                     roundup, footer, composite.
 * @param string $variant 'block' (default) or 'inline'.
 * @return void
 */
function counsel_render_disclaimer( $type = 'not_legal_advice', $variant = 'block' ) {
	$map = array(
		'not_legal_advice' => 'counsel_disclaimer_not_legal_advice',
		'results'          => 'counsel_disclaimer_results',
		'advertising'      => 'counsel_disclaimer_advertising',
		'profile'          => 'counsel_disclaimer_profile',
		'roundup'          => 'counsel_disclaimer_roundup',
		'footer'           => 'counsel_disclaimer_footer',
		'composite'        => 'counsel_disclaimer_composite',
	);

	if ( ! isset( $map[ $type ] ) || ! function_exists( $map[ $type ] ) ) {
		return;
	}

	$text = call_user_func( $map[ $type ] );

	if ( 'inline' === $variant ) {
		printf( '<p class="counsel-disclaimer counsel-disclaimer--inline">%s</p>', esc_html( $text ) );
		return;
	}

	echo '<aside class="counsel-disclaimer" role="note">';
	echo '<span class="counsel-disclaimer__label">' . esc_html__( 'Please note', 'counsel' ) . '</span>';
	echo '<p>' . esc_html( $text ) . '</p>';
	echo '</aside>';
}
