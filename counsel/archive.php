<?php
/**
 * Generic archive template (categories, tags, dates, author).
 *
 * The firm directory and taxonomy archives have their own templates.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

get_header();
?>
<main id="primary" class="site-main counsel-container" role="main">

	<?php counsel_breadcrumbs(); ?>

	<header class="page-header">
		<?php
		the_archive_title( '<h1 class="page-title">', '</h1>' );
		the_archive_description( '<div class="archive-description counsel-prose">', '</div>' );
		?>
	</header>

	<?php if ( have_posts() ) : ?>

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
					</div>
				</article>
				<?php
			endwhile;
			?>
		</div>

		<?php
		the_posts_pagination(
			array(
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
