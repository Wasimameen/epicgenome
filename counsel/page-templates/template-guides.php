<?php
/**
 * Template Name: Guides Landing
 *
 * The Guides landing page. Renders any editor intro from the page itself, then
 * grids the posts in the "Guides" (slug: guides) category as cards.
 *
 * Author guides as standard Posts assigned to the "Guides" category; they
 * appear here automatically and open in single.php with the guide reading
 * width + disclaimer.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

get_header();
?>
<main id="primary" class="site-main counsel-container" role="main">

	<?php counsel_breadcrumbs(); ?>

	<header class="page-header counsel-cat-header">
		<p class="counsel-kicker"><?php esc_html_e( 'Guides', 'counsel' ); ?></p>
		<?php
		while ( have_posts() ) :
			the_post();
			?>
			<h1 class="page-title"><?php the_title(); ?></h1>
			<?php
			if ( '' !== trim( wp_strip_all_tags( get_the_content() ) ) ) :
				?>
				<div class="counsel-prose entry-content"><?php the_content(); ?></div>
				<?php
			else :
				?>
				<p class="counsel-cat-header__lede"><?php esc_html_e( 'Evergreen explainers on what legal help costs and how the process works — so there are no surprises.', 'counsel' ); ?></p>
				<?php
			endif;
		endwhile;
		?>
	</header>

	<?php
	$counsel_guides = new WP_Query(
		array(
			'post_type'      => 'post',
			'category_name'  => 'guides',
			'posts_per_page' => 12,
			'paged'          => max( 1, get_query_var( 'paged' ), get_query_var( 'page' ) ),
		)
	);

	if ( $counsel_guides->have_posts() ) :
		?>
		<div class="counsel-card-grid counsel-card-grid--articles">
			<?php
			while ( $counsel_guides->have_posts() ) :
				$counsel_guides->the_post();
				?>
				<article id="post-<?php the_ID(); ?>" <?php post_class( 'counsel-card counsel-card--article' ); ?>>
					<?php if ( has_post_thumbnail() ) : ?>
						<a class="counsel-card__media" href="<?php the_permalink(); ?>" tabindex="-1" aria-hidden="true">
							<?php the_post_thumbnail( 'counsel-firm-card', array( 'loading' => 'lazy' ) ); ?>
						</a>
					<?php endif; ?>
					<div class="counsel-card__body">
						<?php counsel_entry_meta(); ?>
						<h2 class="counsel-card__title">
							<a href="<?php the_permalink(); ?>"><?php the_title(); ?></a>
						</h2>
						<p class="counsel-card__summary"><?php echo esc_html( wp_trim_words( get_the_excerpt(), 24 ) ); ?></p>
						<a class="counsel-card__link" href="<?php the_permalink(); ?>">
							<?php esc_html_e( 'Read the guide', 'counsel' ); ?>
							<span aria-hidden="true">&rarr;</span>
						</a>
					</div>
				</article>
				<?php
			endwhile;
			?>
		</div>

		<?php
		echo wp_kses_post(
			paginate_links(
				array(
					'total'   => $counsel_guides->max_num_pages,
					'current' => max( 1, get_query_var( 'paged' ), get_query_var( 'page' ) ),
					'prev_text' => __( '&larr; Newer', 'counsel' ),
					'next_text' => __( 'Older &rarr;', 'counsel' ),
				)
			)
		);
		wp_reset_postdata();
		?>

	<?php else : ?>
		<section class="counsel-empty">
			<div class="counsel-empty__inner">
				<h2 class="counsel-empty__title"><?php esc_html_e( 'No guides published yet.', 'counsel' ); ?></h2>
				<p class="counsel-empty__lede">
					<?php esc_html_e( 'Guides will appear here. Create a Post, assign it to the "Guides" category, and it shows up automatically.', 'counsel' ); ?>
				</p>
				<a class="counsel-arrow-link" href="<?php echo esc_url( get_post_type_archive_link( 'firm' ) ); ?>">
					<?php esc_html_e( 'Find a Lawyer', 'counsel' ); ?>
					<span aria-hidden="true">&rarr;</span>
				</a>
			</div>
		</section>
	<?php endif; ?>

	<?php counsel_render_disclaimer( 'not_legal_advice', 'block' ); ?>

</main>
<?php
get_footer();
