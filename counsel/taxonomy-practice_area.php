<?php
/**
 * Firms filtered by practice area.
 *
 * Shares the directory layout: filter rail + card grid, with a term-specific
 * header and description.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

get_header();

$counsel_term = get_queried_object();
?>
<main id="primary" class="site-main counsel-directory" role="main">
	<div class="counsel-container">

		<?php counsel_breadcrumbs(); ?>

		<header class="counsel-directory__header">
			<p class="counsel-kicker"><?php esc_html_e( 'Practice area', 'counsel' ); ?></p>
			<h1 class="counsel-directory__title">
				<?php
				/* translators: %s: practice area name */
				printf( esc_html__( '%s lawyers', 'counsel' ), esc_html( single_term_title( '', false ) ) );
				?>
			</h1>
			<?php if ( ! empty( $counsel_term->description ) ) : ?>
				<div class="counsel-directory__lede counsel-prose"><?php echo wp_kses_post( wpautop( $counsel_term->description ) ); ?></div>
			<?php else : ?>
				<p class="counsel-directory__lede">
					<?php esc_html_e( 'Independent profiles of firms working in this practice area. Sponsored placements are clearly labeled.', 'counsel' ); ?>
				</p>
			<?php endif; ?>
		</header>

		<div class="counsel-directory__search">
			<?php get_search_form( array( 'counsel_search_variant' => 'compact' ) ); ?>
		</div>

		<div class="counsel-directory__layout">

			<?php get_template_part( 'template-parts/directory', 'filters' ); ?>

			<div class="counsel-directory__results">
				<?php if ( have_posts() ) : ?>
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

		</div>

	</div>
</main>
<?php
get_footer();
