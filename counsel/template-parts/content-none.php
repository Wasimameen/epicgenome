<?php
/**
 * Empty-state partial — shown when a query returns no results.
 *
 * Context-aware: the firm directory gets a "we're still building this area"
 * message with routes into guides and a "suggest a city" CTA; search gets the
 * search form back; everything else gets a friendly default.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;
?>
<section class="counsel-empty">
	<div class="counsel-empty__inner">

	<?php if ( is_post_type_archive( 'firm' ) || is_tax( array( 'practice_area', 'city' ) ) ) : ?>

		<h2 class="counsel-empty__title"><?php esc_html_e( 'We\'re still building out this area.', 'counsel' ); ?></h2>
		<p class="counsel-empty__lede">
			<?php esc_html_e( 'Counsel grows market by market, carefully. We don\'t list firms until we\'ve researched them, so this corner of the directory is still in progress. In the meantime, here\'s how to get your bearings:', 'counsel' ); ?>
		</p>

		<div class="counsel-empty__routes">
			<a class="counsel-arrow-link" href="<?php echo esc_url( home_url( '/guides/' ) ); ?>">
				<?php esc_html_e( 'Read our guides on cost and process', 'counsel' ); ?>
				<span aria-hidden="true">&rarr;</span>
			</a>
			<a class="counsel-arrow-link" href="<?php echo esc_url( home_url( '/advice/' ) ); ?>">
				<?php esc_html_e( 'Browse Ask Counsel', 'counsel' ); ?>
				<span aria-hidden="true">&rarr;</span>
			</a>
		</div>

		<div class="counsel-empty__cta">
			<p><?php esc_html_e( 'Want Counsel in your city sooner?', 'counsel' ); ?></p>
			<a class="counsel-btn counsel-btn--ghost" href="<?php echo esc_url( add_query_arg( 'topic', 'suggest-a-city', home_url( '/contact/' ) ) ); ?>">
				<?php esc_html_e( 'Suggest a city', 'counsel' ); ?>
			</a>
		</div>

	<?php elseif ( is_search() ) : ?>

		<h2 class="counsel-empty__title"><?php esc_html_e( 'Nothing matched that search.', 'counsel' ); ?></h2>
		<p class="counsel-empty__lede"><?php esc_html_e( 'Try different words, or search the directory by practice area and city.', 'counsel' ); ?></p>
		<?php get_search_form(); ?>

	<?php else : ?>

		<h2 class="counsel-empty__title"><?php esc_html_e( 'Nothing here yet.', 'counsel' ); ?></h2>
		<p class="counsel-empty__lede"><?php esc_html_e( 'There\'s no content to show on this page right now. Try the search below or head back home.', 'counsel' ); ?></p>
		<?php get_search_form(); ?>

	<?php endif; ?>

	</div>
</section>
