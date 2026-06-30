<?php
/**
 * Search results.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

get_header();
?>
<main id="primary" class="site-main counsel-container" role="main">

	<?php counsel_breadcrumbs(); ?>

	<header class="page-header">
		<h1 class="page-title">
			<?php
			/* translators: %s: search query */
			printf( esc_html__( 'Search results for: %s', 'counsel' ), '<span>' . esc_html( get_search_query() ) . '</span>' );
			?>
		</h1>
		<div class="page-header__search">
			<?php get_search_form(); ?>
		</div>
	</header>

	<?php if ( have_posts() ) : ?>

		<div class="counsel-post-list">
			<?php
			while ( have_posts() ) :
				the_post();
				?>
				<article id="post-<?php the_ID(); ?>" <?php post_class( 'counsel-post-list__item' ); ?>>
					<div class="counsel-post-list__body">
						<span class="counsel-result-type"><?php echo esc_html( get_post_type_object( get_post_type() )->labels->singular_name ); ?></span>
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
