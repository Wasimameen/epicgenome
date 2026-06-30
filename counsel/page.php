<?php
/**
 * The default page template.
 *
 * A clean editorial reading layout constrained to --measure. Used by About,
 * legal pages, and any standard page that doesn't pick a custom template.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

get_header();
?>
<main id="primary" class="site-main counsel-container" role="main">

	<?php counsel_breadcrumbs(); ?>

	<?php
	while ( have_posts() ) :
		the_post();
		?>
		<article id="post-<?php the_ID(); ?>" <?php post_class( 'counsel-page' ); ?>>

			<header class="counsel-page__header">
				<h1 class="counsel-page__title"><?php the_title(); ?></h1>
			</header>

			<?php if ( has_post_thumbnail() ) : ?>
				<figure class="counsel-page__media">
					<?php the_post_thumbnail( 'counsel-profile-hero', array( 'loading' => 'eager' ) ); ?>
				</figure>
			<?php endif; ?>

			<div class="counsel-prose entry-content">
				<?php
				the_content();

				wp_link_pages(
					array(
						'before' => '<nav class="page-links">' . esc_html__( 'Pages:', 'counsel' ),
						'after'  => '</nav>',
					)
				);
				?>
			</div>

		</article>

		<?php
		if ( comments_open() || get_comments_number() ) {
			comments_template();
		}
		?>
		<?php
	endwhile;
	?>

</main>
<?php
get_footer();
