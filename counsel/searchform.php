<?php
/**
 * The reusable practice-area + city search form.
 *
 * Used by template-parts/hero-search.php and the directory. Posts (GET) to the
 * firm archive so results can be filtered by query args (see
 * counsel_filter_firm_archive() in functions.php).
 *
 * Optional context via the $args global set before get_search_form():
 *   - 'counsel_search_variant' => 'hero' | 'compact'
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

$counsel_variant = 'default';
if ( isset( $args ) && is_array( $args ) && ! empty( $args['counsel_search_variant'] ) ) {
	$counsel_variant = $args['counsel_search_variant'];
}

$counsel_archive = get_post_type_archive_link( 'firm' );
$counsel_archive = $counsel_archive ? $counsel_archive : home_url( '/' );

// Current selections (so the form remembers state on the results page).
$counsel_sel_pa   = isset( $_GET['practice_area'] ) ? sanitize_title( wp_unslash( $_GET['practice_area'] ) ) : ''; // phpcs:ignore WordPress.Security.NonceVerification.Recommended
$counsel_sel_city = isset( $_GET['city'] ) ? sanitize_title( wp_unslash( $_GET['city'] ) ) : ''; // phpcs:ignore WordPress.Security.NonceVerification.Recommended

$counsel_practice_terms = get_terms(
	array(
		'taxonomy'   => 'practice_area',
		'hide_empty' => false,
	)
);
$counsel_city_terms = get_terms(
	array(
		'taxonomy'   => 'city',
		'hide_empty' => false,
	)
);
?>
<form
	role="search"
	method="get"
	class="counsel-search counsel-search--<?php echo esc_attr( $counsel_variant ); ?>"
	action="<?php echo esc_url( $counsel_archive ); ?>"
>
	<div class="counsel-search__field">
		<label for="counsel-pa-<?php echo esc_attr( $counsel_variant ); ?>"><?php esc_html_e( 'What kind of help do you need?', 'counsel' ); ?></label>
		<select id="counsel-pa-<?php echo esc_attr( $counsel_variant ); ?>" name="practice_area">
			<option value=""><?php esc_html_e( 'All practice areas', 'counsel' ); ?></option>
			<?php
			if ( ! is_wp_error( $counsel_practice_terms ) ) {
				foreach ( $counsel_practice_terms as $counsel_term ) {
					printf(
						'<option value="%1$s" %2$s>%3$s</option>',
						esc_attr( $counsel_term->slug ),
						selected( $counsel_sel_pa, $counsel_term->slug, false ),
						esc_html( $counsel_term->name )
					);
				}
			}
			?>
		</select>
	</div>

	<div class="counsel-search__field">
		<label for="counsel-city-<?php echo esc_attr( $counsel_variant ); ?>"><?php esc_html_e( 'Where?', 'counsel' ); ?></label>
		<select id="counsel-city-<?php echo esc_attr( $counsel_variant ); ?>" name="city">
			<option value=""><?php esc_html_e( 'All cities', 'counsel' ); ?></option>
			<?php
			if ( ! is_wp_error( $counsel_city_terms ) ) {
				foreach ( $counsel_city_terms as $counsel_term ) {
					printf(
						'<option value="%1$s" %2$s>%3$s</option>',
						esc_attr( $counsel_term->slug ),
						selected( $counsel_sel_city, $counsel_term->slug, false ),
						esc_html( $counsel_term->name )
					);
				}
			}
			?>
		</select>
	</div>

	<div class="counsel-search__submit">
		<button type="submit" class="counsel-btn counsel-btn--primary">
			<?php esc_html_e( 'Find a Lawyer', 'counsel' ); ?>
		</button>
	</div>
</form>
