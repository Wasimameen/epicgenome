<?php
/**
 * The Home page.
 *
 * Renders the editorial home layout: hero search, three lanes, a "why Counsel
 * is different" trust row, a practice-areas grid, and a closing CTA.
 *
 * If the site owner has set a static front page with content in the editor,
 * that content is shown in the "from the editor" region between the hero and
 * the lanes. Otherwise the section is skipped.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

get_header();
?>
<main id="primary" class="site-main front-page" role="main">

	<?php get_template_part( 'template-parts/hero-search' ); ?>

	<?php
	// Optional editor-owned intro content from the assigned front page.
	if ( have_posts() ) :
		while ( have_posts() ) :
			the_post();
			$counsel_front_content = get_the_content();
			if ( '' !== trim( wp_strip_all_tags( $counsel_front_content ) ) ) :
				?>
				<section class="counsel-front-intro">
					<div class="counsel-container counsel-prose">
						<?php the_content(); ?>
					</div>
				</section>
				<?php
			endif;
		endwhile;
	endif;
	?>

	<?php get_template_part( 'template-parts/section-three-lanes' ); ?>

	<?php
	// Why Counsel is different — trust row.
	$counsel_trust = array(
		array(
			'title' => __( 'Independent by design', 'counsel' ),
			'desc'  => __( 'Consumers never pay us, and firms can\'t buy a better review. Sponsorship is clearly labeled and kept separate from our editorial judgment.', 'counsel' ),
		),
		array(
			'title' => __( 'Written by humans', 'counsel' ),
			'desc'  => __( 'Real research, plain language, and a calm point of view — not a wall of lead-gen listings or scare tactics.', 'counsel' ),
		),
		array(
			'title' => __( 'Disclosure, always', 'counsel' ),
			'desc'  => __( 'Every sponsored placement carries a visible label, and every profile cites where its information came from.', 'counsel' ),
		),
	);
	?>
	<section class="counsel-trust" aria-labelledby="counsel-trust-title">
		<div class="counsel-container">
			<?php counsel_section_heading( __( 'Why Counsel is different', 'counsel' ), 'h2', __( 'Trust is the product', 'counsel' ) ); ?>
			<div class="counsel-trust__grid">
				<?php foreach ( $counsel_trust as $counsel_item ) : ?>
					<div class="counsel-trust__item">
						<h3 class="counsel-trust__heading"><?php echo esc_html( $counsel_item['title'] ); ?></h3>
						<p><?php echo esc_html( $counsel_item['desc'] ); ?></p>
					</div>
				<?php endforeach; ?>
			</div>
		</div>
	</section>

	<?php
	// Practice-areas grid linking to each practice_area term.
	$counsel_pa_terms = get_terms(
		array(
			'taxonomy'   => 'practice_area',
			'hide_empty' => false,
			'number'     => 12,
		)
	);
	if ( ! empty( $counsel_pa_terms ) && ! is_wp_error( $counsel_pa_terms ) ) :
		?>
		<section class="counsel-areas" aria-labelledby="counsel-areas-title">
			<div class="counsel-container">
				<?php counsel_section_heading( __( 'Browse by practice area', 'counsel' ), 'h2', __( 'Directory', 'counsel' ) ); ?>
				<ul class="counsel-areas__grid">
					<?php foreach ( $counsel_pa_terms as $counsel_term ) : ?>
						<li>
							<a class="counsel-areas__link" href="<?php echo esc_url( get_term_link( $counsel_term ) ); ?>">
								<span class="counsel-areas__name"><?php echo esc_html( $counsel_term->name ); ?></span>
								<span class="counsel-areas__arrow" aria-hidden="true">&rarr;</span>
							</a>
						</li>
					<?php endforeach; ?>
				</ul>
			</div>
		</section>
		<?php
	endif;
	?>

	<section class="counsel-closing-cta">
		<div class="counsel-container counsel-closing-cta__inner">
			<h2 class="counsel-closing-cta__title">
				<?php esc_html_e( 'Start with the right questions.', 'counsel' ); ?>
			</h2>
			<p class="counsel-closing-cta__lede">
				<?php esc_html_e( 'Find a firm, read an honest profile, and walk into your first call knowing what to ask.', 'counsel' ); ?>
			</p>
			<div class="counsel-closing-cta__actions">
				<a class="counsel-btn counsel-btn--primary" href="<?php echo esc_url( get_post_type_archive_link( 'firm' ) ); ?>">
					<?php esc_html_e( 'Find a Lawyer', 'counsel' ); ?>
				</a>
				<a class="counsel-btn counsel-btn--ghost" href="<?php echo esc_url( home_url( '/how-it-works/' ) ); ?>">
					<?php esc_html_e( 'How it works', 'counsel' ); ?>
				</a>
			</div>
		</div>
	</section>

</main>
<?php
get_footer();
