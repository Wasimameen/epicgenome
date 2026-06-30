<?php
/**
 * The firm directory — "Find a Lawyer" results.
 *
 * Renders the search form, a left-column filter rail (practice area, city,
 * firm size), and a responsive grid of firm cards. Honors the query args from
 * the search form (see counsel_filter_firm_archive() in functions.php), and
 * shows a strong empty state for areas with no firms yet.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

get_header();
?>
<main id="primary" class="site-main counsel-directory" role="main">
	<div class="counsel-container">

		<?php counsel_breadcrumbs(); ?>

		<header class="counsel-directory__header">
			<p class="counsel-kicker"><?php esc_html_e( 'Directory', 'counsel' ); ?></p>
			<h1 class="counsel-directory__title"><?php esc_html_e( 'Find a Lawyer', 'counsel' ); ?></h1>
			<p class="counsel-directory__lede">
				<?php esc_html_e( 'Independent profiles of law firms, organized by practice area and city. Sponsored placements are always labeled.', 'counsel' ); ?>
			</p>
		</header>

		<div class="counsel-directory__search">
			<?php get_search_form( array( 'counsel_search_variant' => 'compact' ) ); ?>
		</div>

		<div class="counsel-directory__layout">

			<?php get_template_part( 'template-parts/directory', 'filters' ); ?>

			<div class="counsel-directory__results">
				<?php if ( have_posts() ) : ?>

					<p class="counsel-directory__count">
						<?php
						global $wp_query;
						$counsel_total = (int) $wp_query->found_posts;
						printf(
							/* translators: %s: number of firms */
							esc_html( _n( '%s firm', '%s firms', $counsel_total, 'counsel' ) ),
							esc_html( number_format_i18n( $counsel_total ) )
						);
						?>
					</p>

					<div class="counsel-card-grid">
						<?php
						while ( have_posts() ) :
							the_post();
							get_template_part( 'template-parts/card', 'firm' );
						endwhile;
						?>
					</div>

					<?php
					the_posts_pagination(
						array(
							'prev_text' => __( '&larr; Previous', 'counsel' ),
							'next_text' => __( 'Next &rarr;', 'counsel' ),
						)
					);
					?>

				<?php else : ?>
					<?php get_template_part( 'template-parts/content', 'none' ); ?>
				<?php endif; ?>
			</div>

		</div><!-- .counsel-directory__layout -->

	</div>
</main>
<?php
get_footer();
