<?php
/**
 * Home hero with the headline and the practice-area + city search form.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;
?>
<section class="counsel-hero" aria-labelledby="counsel-hero-title">
	<div class="counsel-container counsel-hero__inner">

		<p class="counsel-kicker counsel-hero__kicker">
			<?php esc_html_e( 'Independent. Editorial. On your side.', 'counsel' ); ?>
		</p>

		<h1 id="counsel-hero-title" class="counsel-hero__title">
			<?php esc_html_e( 'Hiring a lawyer shouldn\'t be the hardest part.', 'counsel' ); ?>
		</h1>

		<p class="counsel-hero__lede">
			<?php esc_html_e( 'Counsel is an independent guide to finding the right attorney — calm, researched profiles instead of a wall of ads. We are not a law firm, and consumers never pay us.', 'counsel' ); ?>
		</p>

		<div class="counsel-hero__search">
			<?php
			get_search_form(
				array(
					'counsel_search_variant' => 'hero',
				)
			);
			?>
		</div>

		<p class="counsel-hero__trust">
			<?php esc_html_e( 'Every profile is researched independently. Sponsored placements are always clearly labeled.', 'counsel' ); ?>
		</p>

	</div>
</section>
