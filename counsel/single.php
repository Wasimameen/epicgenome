<?php
/**
 * The default single-post template.
 *
 * Handles standard posts, including Ask Counsel advice columns (a post in the
 * "Ask Counsel" / "advice" category) and evergreen Guides. The advice format is
 * authored in the editor; the theme supplies the reading frame and the standing
 * disclaimers.
 *
 * Recommended authoring for an Ask Counsel column (using core blocks):
 *   1. The composite question as a Quote block (renders pulled-out).
 *   2. A short answer paragraph.
 *   3. "What to do now" as an ordered list.
 *   4. "What good looks like" and "What to look for next time" sections.
 *   5. A short FAQ (headings + paragraphs).
 * The composite editor's note and the "not legal advice" line are appended
 * automatically below.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

get_header();

// If Elementor Pro has a single template assigned for this post, let it render.
if ( function_exists( 'counsel_do_elementor_location' ) && counsel_do_elementor_location( 'single' ) ) {
	get_footer();
	return;
}

// Detect Ask Counsel columns by category slug 'advice' or name match.
$counsel_is_advice = has_category( 'advice' ) || has_category( __( 'Ask Counsel', 'counsel' ) );
// Detect Guides by category slug 'guides'.
$counsel_is_guide = has_category( 'guides' );
?>
<main id="primary" class="site-main counsel-container" role="main">

	<?php counsel_breadcrumbs(); ?>

	<?php
	while ( have_posts() ) :
		the_post();
		?>
		<article id="post-<?php the_ID(); ?>" <?php post_class( 'counsel-single' . ( $counsel_is_advice ? ' counsel-single--advice' : '' ) ); ?>>

			<header class="counsel-single__header">
				<?php if ( $counsel_is_advice ) : ?>
					<p class="counsel-kicker"><?php esc_html_e( 'Ask Counsel', 'counsel' ); ?></p>
				<?php endif; ?>
				<h1 class="counsel-single__title"><?php the_title(); ?></h1>
				<?php counsel_entry_meta(); ?>
			</header>

			<?php if ( has_post_thumbnail() ) : ?>
				<figure class="counsel-single__media">
					<?php the_post_thumbnail( 'counsel-profile-hero', array( 'loading' => 'eager' ) ); ?>
					<?php
					$counsel_caption = get_the_post_thumbnail_caption();
					if ( $counsel_caption ) {
						echo '<figcaption>' . esc_html( $counsel_caption ) . '</figcaption>';
					}
					?>
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

			<footer class="counsel-single__footer">
				<?php
				if ( $counsel_is_advice ) {
					counsel_render_disclaimer( 'composite', 'inline' );
					counsel_render_disclaimer( 'not_legal_advice', 'block' );
				} elseif ( $counsel_is_guide ) {
					counsel_render_disclaimer( 'not_legal_advice', 'block' );
				} else {
					$counsel_tags = get_the_tag_list( '<ul class="counsel-tags"><li>', '</li><li>', '</li></ul>' );
					if ( $counsel_tags ) {
						echo wp_kses_post( $counsel_tags );
					}
				}
				?>
			</footer>

		</article>

		<?php
		the_post_navigation(
			array(
				'prev_text' => '<span class="nav-subtitle">' . esc_html__( 'Previous', 'counsel' ) . '</span> <span class="nav-title">%title</span>',
				'next_text' => '<span class="nav-subtitle">' . esc_html__( 'Next', 'counsel' ) . '</span> <span class="nav-title">%title</span>',
			)
		);

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
