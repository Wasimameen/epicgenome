<?php
/**
 * Generic disclaimer block partial.
 *
 * Pass the disclaimer type via the second arg to get_template_part():
 *   get_template_part( 'template-parts/disclaimer-block', null,
 *       array( 'type' => 'not_legal_advice' ) );
 *
 * Supported types: not_legal_advice, results, advertising, profile, roundup,
 * footer, composite.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

$counsel_type = 'not_legal_advice';
if ( isset( $args ) && is_array( $args ) && ! empty( $args['type'] ) ) {
	$counsel_type = $args['type'];
}

$counsel_variant = ( isset( $args ) && ! empty( $args['variant'] ) ) ? $args['variant'] : 'block';

counsel_render_disclaimer( $counsel_type, $counsel_variant );
