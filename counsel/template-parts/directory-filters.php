<?php
/**
 * The directory filter rail (left column).
 *
 * Practice area, city, and firm size. Submits via GET to the firm archive so
 * the filters compose with the search form's query args.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

$counsel_archive = get_post_type_archive_link( 'firm' );
$counsel_archive = $counsel_archive ? $counsel_archive : home_url( '/' );

$counsel_sel_pa   = isset( $_GET['practice_area'] ) ? sanitize_title( wp_unslash( $_GET['practice_area'] ) ) : ''; // phpcs:ignore WordPress.Security.NonceVerification.Recommended
$counsel_sel_city = isset( $_GET['city'] ) ? sanitize_title( wp_unslash( $_GET['city'] ) ) : ''; // phpcs:ignore WordPress.Security.NonceVerification.Recommended
$counsel_sel_size = isset( $_GET['firm_size'] ) ? sanitize_text_field( wp_unslash( $_GET['firm_size'] ) ) : ''; // phpcs:ignore WordPress.Security.NonceVerification.Recommended

// On a taxonomy archive, lock the matching filter to the current term.
if ( is_tax( 'practice_area' ) ) {
	$counsel_term   = get_queried_object();
	$counsel_sel_pa = isset( $counsel_term->slug ) ? $counsel_term->slug : $counsel_sel_pa;
}
if ( is_tax( 'city' ) ) {
	$counsel_term     = get_queried_object();
	$counsel_sel_city = isset( $counsel_term->slug ) ? $counsel_term->slug : $counsel_sel_city;
}

$counsel_pa_terms   = get_terms( array( 'taxonomy' => 'practice_area', 'hide_empty' => false ) );
$counsel_city_terms = get_terms( array( 'taxonomy' => 'city', 'hide_empty' => false ) );
?>
<aside class="counsel-directory__filters" aria-label="<?php esc_attr_e( 'Filter firms', 'counsel' ); ?>">
	<form method="get" action="<?php echo esc_url( $counsel_archive ); ?>" class="counsel-filters">

		<h2 class="counsel-filters__title"><?php esc_html_e( 'Filter', 'counsel' ); ?></h2>

		<fieldset class="counsel-filters__group">
			<legend><?php esc_html_e( 'Practice area', 'counsel' ); ?></legend>
			<label class="screen-reader-text" for="filter-pa"><?php esc_html_e( 'Practice area', 'counsel' ); ?></label>
			<select id="filter-pa" name="practice_area">
				<option value=""><?php esc_html_e( 'All practice areas', 'counsel' ); ?></option>
				<?php
				if ( ! is_wp_error( $counsel_pa_terms ) ) {
					foreach ( $counsel_pa_terms as $counsel_t ) {
						printf(
							'<option value="%1$s" %2$s>%3$s</option>',
							esc_attr( $counsel_t->slug ),
							selected( $counsel_sel_pa, $counsel_t->slug, false ),
							esc_html( $counsel_t->name )
						);
					}
				}
				?>
			</select>
		</fieldset>

		<fieldset class="counsel-filters__group">
			<legend><?php esc_html_e( 'City', 'counsel' ); ?></legend>
			<label class="screen-reader-text" for="filter-city"><?php esc_html_e( 'City', 'counsel' ); ?></label>
			<select id="filter-city" name="city">
				<option value=""><?php esc_html_e( 'All cities', 'counsel' ); ?></option>
				<?php
				if ( ! is_wp_error( $counsel_city_terms ) ) {
					foreach ( $counsel_city_terms as $counsel_t ) {
						printf(
							'<option value="%1$s" %2$s>%3$s</option>',
							esc_attr( $counsel_t->slug ),
							selected( $counsel_sel_city, $counsel_t->slug, false ),
							esc_html( $counsel_t->name )
						);
					}
				}
				?>
			</select>
		</fieldset>

		<fieldset class="counsel-filters__group">
			<legend><?php esc_html_e( 'Firm size', 'counsel' ); ?></legend>
			<label class="screen-reader-text" for="filter-size"><?php esc_html_e( 'Firm size', 'counsel' ); ?></label>
			<select id="filter-size" name="firm_size">
				<option value=""><?php esc_html_e( 'Any size', 'counsel' ); ?></option>
				<?php
				$counsel_sizes = array(
					'Solo'   => __( 'Solo practice', 'counsel' ),
					'Small'  => __( 'Small (2–10)', 'counsel' ),
					'Mid'    => __( 'Mid-size (11–50)', 'counsel' ),
					'Large'  => __( 'Large (50+)', 'counsel' ),
				);
				foreach ( $counsel_sizes as $counsel_val => $counsel_label ) {
					printf(
						'<option value="%1$s" %2$s>%3$s</option>',
						esc_attr( $counsel_val ),
						selected( $counsel_sel_size, $counsel_val, false ),
						esc_html( $counsel_label )
					);
				}
				?>
			</select>
		</fieldset>

		<div class="counsel-filters__actions">
			<button type="submit" class="counsel-btn counsel-btn--primary"><?php esc_html_e( 'Apply filters', 'counsel' ); ?></button>
			<a class="counsel-filters__reset" href="<?php echo esc_url( $counsel_archive ); ?>"><?php esc_html_e( 'Reset', 'counsel' ); ?></a>
		</div>

	</form>
</aside>
