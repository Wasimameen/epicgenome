<?php
/**
 * The main template file — fallback loop.
 *
 * Used when no more specific template matches. Renders the standard post loop
 * in an editorial blog layout.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

get_header();
?>
<main id="primary" class="site-main counsel-container" role="main">

	<?php counsel_breadcrumbs(); ?>

	<?php if ( have_posts() ) : ?>

		<?php if ( is_home() && ! is_front_page() ) : ?>
			<header class="page-header">
				<h1 class="page-title"><?php single_post_title(); ?></h1>
			</header>
		<?php endif; ?>

		<div class="counsel-post-list">
			<?php
			while ( have_posts() ) :
				the_post();
				?>
				<article id="post-<?php the_ID(); ?>" <?php post_class( 'counsel-post-list__item' ); ?>>
					<?php if ( has_post_thumbnail() ) : ?>
						<a class="counsel-post-list__media" href="<?php the_permalink(); ?>">
							<?php the_post_thumbnail( 'counsel-firm-card', array( 'loading' => 'lazy' ) ); ?>
						</a>
					<?php endif; ?>
					<div class="counsel-post-list__body">
						<?php counsel_entry_meta(); ?>
						<h2 class="counsel-post-list__title">
							<a href="<?php the_permalink(); ?>"><?php the_title(); ?></a>
						</h2>
						<div class="counsel-post-list__excerpt"><?php the_excerpt(); ?></div>
						<a class="counsel-arrow-link" href="<?php the_permalink(); ?>">
							<?php esc_html_e( 'Continue reading', 'counsel' ); ?>
							<span aria-hidden="true">&rarr;</span>
						</a>
					</div>
				</article>
				<?php
			endwhile;
			?>
		</div>

		<?php
		the_posts_pagination(
			array(
				'mid_size'  => 1,
				'prev_text' => __( '&larr; Newer', 'counsel' ),
				'next_text' => __( 'Older &rarr;', 'counsel' ),
			)
		);
		?>

	<?php else : ?>

		<?php get_template_part( 'template-parts/content', 'none' ); ?>

	<?php endif; ?>

</main>
<?php
get_footer();
