<?php
/**
 * Methodology box for "Best Of" roundup pages.
 *
 * This is mandatory on every roundup — the transparent methodology is what
 * separates Counsel's editorial selections from a pay-to-rank list.
 *
 * The text can be authored per-page in a custom field ('counsel_methodology')
 * or it falls back to the standard statement below.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

$counsel_method = get_post_meta( get_the_ID(), 'counsel_methodology', true );
?>
<aside class="counsel-methodology" aria-labelledby="counsel-methodology-title">
	<h2 id="counsel-methodology-title" class="counsel-methodology__title">
		<?php esc_html_e( 'How we chose', 'counsel' ); ?>
	</h2>

	<?php if ( $counsel_method ) : ?>
		<div class="counsel-methodology__body">
			<?php echo wp_kses_post( wpautop( $counsel_method ) ); ?>
		</div>
	<?php else : ?>
		<div class="counsel-methodology__body">
			<p>
				<?php esc_html_e( 'Counsel\'s editorial team selects firms for this list independently. We review public records, disciplinary history, years in practice, depth of relevant experience, client feedback across multiple sources, and the clarity of each firm\'s fee and communication practices. We contact firms to verify facts where possible.', 'counsel' ); ?>
			</p>
			<ul class="counsel-methodology__criteria">
				<li><?php esc_html_e( 'Relevant experience in the specific practice area and venue', 'counsel' ); ?></li>
				<li><?php esc_html_e( 'A clean and verifiable professional record', 'counsel' ); ?></li>
				<li><?php esc_html_e( 'Transparent fees and clear client communication', 'counsel' ); ?></li>
				<li><?php esc_html_e( 'Consistent feedback across independent sources', 'counsel' ); ?></li>
			</ul>
			<p class="counsel-methodology__note">
				<strong><?php esc_html_e( 'Placement on this list cannot be purchased.', 'counsel' ); ?></strong>
				<?php esc_html_e( 'Sponsorship never influences selection or order. Any sponsored firm that also appears here is labeled.', 'counsel' ); ?>
			</p>
		</div>
	<?php endif; ?>
</aside>
