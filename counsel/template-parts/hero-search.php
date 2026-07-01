<?php
/**
 * Home hero with the headline and the practice-area + city search form.
 *
 * All copy and the search toggle are editable from
 * Appearance → Customize → Counsel Theme → Homepage Hero.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

$counsel_kicker = counsel_mod( 'counsel_hero_kicker' );
$counsel_title  = counsel_mod( 'counsel_hero_title' );
$counsel_lede   = counsel_mod( 'counsel_hero_lede' );
$counsel_trust  = counsel_mod( 'counsel_hero_trust' );
?>
<section class="counsel-hero" aria-labelledby="counsel-hero-title">
	<div class="counsel-container counsel-hero__inner">

		<?php if ( '' !== $counsel_kicker ) : ?>
			<p class="counsel-kicker counsel-hero__kicker"><?php echo esc_html( $counsel_kicker ); ?></p>
		<?php endif; ?>

		<h1 id="counsel-hero-title" class="counsel-hero__title">
			<?php echo esc_html( $counsel_title ); ?>
		</h1>

		<?php if ( '' !== $counsel_lede ) : ?>
			<p class="counsel-hero__lede"><?php echo esc_html( $counsel_lede ); ?></p>
		<?php endif; ?>

		<?php if ( counsel_mod( 'counsel_show_hero_search' ) ) : ?>
			<div class="counsel-hero__search">
				<?php get_search_form( array( 'counsel_search_variant' => 'hero' ) ); ?>
			</div>
		<?php endif; ?>

		<?php if ( '' !== $counsel_trust ) : ?>
			<p class="counsel-hero__trust"><?php echo esc_html( $counsel_trust ); ?></p>
		<?php endif; ?>

	</div>
</section>
