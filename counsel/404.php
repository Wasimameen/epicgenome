<?php
/**
 * The 404 (not found) template — friendly, with routes back into the site.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

get_header();
?>
<main id="primary" class="site-main counsel-container" role="main">

	<section class="counsel-404">
		<p class="counsel-kicker"><?php esc_html_e( 'Error 404', 'counsel' ); ?></p>
		<h1 class="counsel-404__title"><?php esc_html_e( 'We couldn\'t find that page.', 'counsel' ); ?></h1>
		<p class="counsel-404__lede">
			<?php esc_html_e( 'The page may have moved, or the link may be out of date. Here are a few good places to pick back up:', 'counsel' ); ?>
		</p>

		<div class="counsel-404__search">
			<?php get_search_form(); ?>
		</div>

		<ul class="counsel-404__routes">
			<li>
				<a class="counsel-arrow-link" href="<?php echo esc_url( get_post_type_archive_link( 'firm' ) ); ?>">
					<?php esc_html_e( 'Find a Lawyer', 'counsel' ); ?>
					<span aria-hidden="true">&rarr;</span>
				</a>
			</li>
			<li>
				<a class="counsel-arrow-link" href="<?php echo esc_url( home_url( '/advice/' ) ); ?>">
					<?php esc_html_e( 'Ask Counsel', 'counsel' ); ?>
					<span aria-hidden="true">&rarr;</span>
				</a>
			</li>
			<li>
				<a class="counsel-arrow-link" href="<?php echo esc_url( home_url( '/guides/' ) ); ?>">
					<?php esc_html_e( 'Guides', 'counsel' ); ?>
					<span aria-hidden="true">&rarr;</span>
				</a>
			</li>
			<li>
				<a class="counsel-arrow-link" href="<?php echo esc_url( home_url( '/' ) ); ?>">
					<?php esc_html_e( 'Back to home', 'counsel' ); ?>
					<span aria-hidden="true">&rarr;</span>
				</a>
			</li>
		</ul>
	</section>

</main>
<?php
get_footer();
