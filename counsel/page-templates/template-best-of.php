<?php
/**
 * Template Name: Best Of Roundup
 *
 * A curated "best [practice area] lawyers in [city]" page.
 *
 * IMPORTANT — EDITORIAL INTEGRITY:
 * A "Best Of" roundup must NEVER be sold or used as pay-to-rank. Placement and
 * ordering are editorial decisions only. Sponsorship may not buy a spot here,
 * and any sponsored firm that legitimately earns a place is still labeled.
 * The mandatory methodology box near the top makes the selection process
 * transparent. Do not remove it.
 *
 * Structure:
 *   1. Magazine-style headline (the page title + optional subtitle field).
 *   2. Mandatory methodology box (template-parts/methodology-box.php).
 *   3. The curated list — authored in the editor; each entry should link to a
 *      firm profile.
 *   4. A "how to choose" closing section.
 *   5. The roundup disclaimer.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

get_header();

while ( have_posts() ) :
	the_post();

	$counsel_subtitle = get_post_meta( get_the_ID(), 'counsel_subtitle', true );
	?>
	<main id="primary" class="site-main page-bestof" role="main">

		<header class="counsel-bestof__header">
			<div class="counsel-container">
				<?php counsel_breadcrumbs(); ?>
				<p class="counsel-kicker"><?php esc_html_e( 'Best Of', 'counsel' ); ?></p>
				<h1 class="counsel-bestof__title"><?php the_title(); ?></h1>
				<?php if ( $counsel_subtitle ) : ?>
					<p class="counsel-bestof__subtitle"><?php echo esc_html( $counsel_subtitle ); ?></p>
				<?php endif; ?>
			</div>
		</header>

		<?php if ( has_post_thumbnail() ) : ?>
			<figure class="counsel-bestof__media">
				<?php the_post_thumbnail( 'counsel-profile-hero', array( 'loading' => 'eager' ) ); ?>
			</figure>
		<?php endif; ?>

		<div class="counsel-container counsel-bestof__layout">

			<?php // Mandatory methodology box, near the top. ?>
			<?php get_template_part( 'template-parts/methodology-box' ); ?>

			<?php // The curated list, authored in the editor (each entry links to a firm profile). ?>
			<div class="counsel-prose counsel-bestof__list entry-content">
				<?php the_content(); ?>
			</div>

			<?php // "How to choose" closing section. ?>
			<section class="counsel-bestof__choose">
				<?php counsel_section_heading( __( 'How to choose from this list', 'counsel' ), 'h2' ); ?>
				<div class="counsel-prose">
					<p><?php esc_html_e( 'A "best of" list is a starting point, not a verdict. Read each firm\'s full profile, confirm they handle your specific situation, ask how fees work, and pay attention to how clearly they communicate. The right firm for your neighbor may not be the right firm for you.', 'counsel' ); ?></p>
				</div>
			</section>

			<?php counsel_render_disclaimer( 'roundup', 'block' ); ?>
		</div>

	</main>
	<?php
endwhile;

get_footer();
