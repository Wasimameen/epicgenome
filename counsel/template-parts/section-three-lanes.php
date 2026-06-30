<?php
/**
 * The "three lanes" section on the home page.
 *
 * Find the right firm / Get your bearings / Know the costs.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

$counsel_lanes = array(
	array(
		'kicker' => __( 'Directory', 'counsel' ),
		'title'  => __( 'Find the right firm', 'counsel' ),
		'desc'   => __( 'Browse independent profiles of law firms by practice area and city. No pay-to-rank listings — just researched overviews to help you shortlist.', 'counsel' ),
		'cta'    => __( 'Find a Lawyer', 'counsel' ),
		'url'    => get_post_type_archive_link( 'firm' ),
	),
	array(
		'kicker' => __( 'Ask Counsel', 'counsel' ),
		'title'  => __( 'Get your bearings', 'counsel' ),
		'desc'   => __( 'Plain-language answers to the questions people actually ask before hiring a lawyer — what to expect, what to watch for, and what good looks like.', 'counsel' ),
		'cta'    => __( 'Read Ask Counsel', 'counsel' ),
		'url'    => home_url( '/advice/' ),
	),
	array(
		'kicker' => __( 'Guides', 'counsel' ),
		'title'  => __( 'Know the costs', 'counsel' ),
		'desc'   => __( 'Evergreen guides on what legal help costs, how fees work, and how the process unfolds — so there are no surprises.', 'counsel' ),
		'cta'    => __( 'Browse guides', 'counsel' ),
		'url'    => home_url( '/guides/' ),
	),
);
?>
<section class="counsel-lanes" aria-labelledby="counsel-lanes-title">
	<div class="counsel-container">

		<?php counsel_section_heading( __( 'Three ways Counsel helps', 'counsel' ), 'h2', __( 'Where to start', 'counsel' ) ); ?>

		<div class="counsel-lanes__grid">
			<?php foreach ( $counsel_lanes as $counsel_lane ) : ?>
				<article class="counsel-lane">
					<span class="counsel-kicker"><?php echo esc_html( $counsel_lane['kicker'] ); ?></span>
					<h3 class="counsel-lane__title"><?php echo esc_html( $counsel_lane['title'] ); ?></h3>
					<p class="counsel-lane__desc"><?php echo esc_html( $counsel_lane['desc'] ); ?></p>
					<a class="counsel-arrow-link" href="<?php echo esc_url( $counsel_lane['url'] ); ?>">
						<?php echo esc_html( $counsel_lane['cta'] ); ?>
						<span aria-hidden="true">&rarr;</span>
					</a>
				</article>
			<?php endforeach; ?>
		</div>

	</div>
</section>
