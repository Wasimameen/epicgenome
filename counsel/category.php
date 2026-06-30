<?php
/**
 * Category archive — also serves as the Ask Counsel landing (the "advice"
 * category) and the Guides landing (the "guides" category), gridding the
 * entries as editorial cards.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

get_header();

$counsel_is_advice = is_category( 'advice' ) || is_category( __( 'Ask Counsel', 'counsel' ) );
$counsel_is_guides = is_category( 'guides' );
?>
<main id="primary" class="site-main counsel-container" role="main">

	<?php counsel_breadcrumbs(); ?>

	<header class="page-header counsel-cat-header">
		<?php if ( $counsel_is_advice ) : ?>
			<p class="counsel-kicker"><?php esc_html_e( 'Ask Counsel', 'counsel' ); ?></p>
			<h1 class="page-title"><?php esc_html_e( 'Advice for hiring a lawyer', 'counsel' ); ?></h1>
			<p class="counsel-cat-header__lede"><?php esc_html_e( 'Plain-language answers to the questions people actually ask. Composite questions, real guidance.', 'counsel' ); ?></p>
		<?php elseif ( $counsel_is_guides ) : ?>
			<p class="counsel-kicker"><?php esc_html_e( 'Guides', 'counsel' ); ?></p>
			<h1 class="page-title"><?php esc_html_e( 'Cost & process guides', 'counsel' ); ?></h1>
			<p class="counsel-cat-header__lede"><?php esc_html_e( 'Evergreen explainers on what legal help costs and how the process works.', 'counsel' ); ?></p>
		<?php else : ?>
			<?php the_archive_title( '<h1 class="page-title">', '</h1>' ); ?>
			<?php the_archive_description( '<div class="archive-description counsel-prose">', '</div>' ); ?>
		<?php endif; ?>
	</header>

	<?php if ( have_posts() ) : ?>

		<div class="counsel-card-grid counsel-card-grid--articles">
			<?php
			while ( have_posts() ) :
				the_post();
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
							<?php esc_html_e( 'Read', 'counsel' ); ?>
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
