<?php
/**
 * Template Name: How It Works
 *
 * A straightforward editorial page. Pulls the body from the editor and frames
 * it with a clear three-step explainer. If the page has no editor content, the
 * default steps below still render.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

get_header();
?>
<main id="primary" class="site-main page-how" role="main">

	<div class="counsel-container">
		<?php counsel_breadcrumbs(); ?>

		<header class="counsel-page__header">
			<p class="counsel-kicker"><?php esc_html_e( 'How it works', 'counsel' ); ?></p>
			<?php
			while ( have_posts() ) :
				the_post();
				?>
				<h1 class="counsel-page__title"><?php the_title(); ?></h1>
				<?php
				$counsel_body = trim( wp_strip_all_tags( get_the_content() ) );
				if ( '' !== $counsel_body ) :
					?>
					<div class="counsel-prose entry-content"><?php the_content(); ?></div>
					<?php
				endif;
			endwhile;
			?>
		</header>

		<section class="counsel-steps">
			<ol class="counsel-steps__list">
				<li class="counsel-steps__item">
					<span class="counsel-steps__num">1</span>
					<h2 class="counsel-steps__title"><?php esc_html_e( 'Get your bearings', 'counsel' ); ?></h2>
					<p><?php esc_html_e( 'Start with our guides and Ask Counsel columns so you understand the process, the likely costs, and what good representation looks like — before you talk to anyone.', 'counsel' ); ?></p>
				</li>
				<li class="counsel-steps__item">
					<span class="counsel-steps__num">2</span>
					<h2 class="counsel-steps__title"><?php esc_html_e( 'Compare firms independently', 'counsel' ); ?></h2>
					<p><?php esc_html_e( 'Browse researched profiles by practice area and city. Every profile cites its sources, and any sponsored placement is clearly labeled, so you always know what you\'re looking at.', 'counsel' ); ?></p>
				</li>
				<li class="counsel-steps__item">
					<span class="counsel-steps__num">3</span>
					<h2 class="counsel-steps__title"><?php esc_html_e( 'Reach out with confidence', 'counsel' ); ?></h2>
					<p><?php esc_html_e( 'Contact firms directly, armed with the right questions. Counsel never takes a referral fee from consumers and is not a party to your decision.', 'counsel' ); ?></p>
				</li>
			</ol>
		</section>

		<section class="counsel-how-cta">
			<a class="counsel-btn counsel-btn--primary" href="<?php echo esc_url( get_post_type_archive_link( 'firm' ) ); ?>">
				<?php esc_html_e( 'Find a Lawyer', 'counsel' ); ?>
			</a>
		</section>

		<?php counsel_render_disclaimer( 'not_legal_advice', 'block' ); ?>
	</div>

</main>
<?php
get_footer();
