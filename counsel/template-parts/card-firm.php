<?php
/**
 * The repeating firm result card.
 *
 * Expects to run inside the loop for a 'firm' post.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

$counsel_best_for = counsel_get_firm_meta( 'firm_best_for', null, '' );
$counsel_size     = counsel_get_firm_meta( 'firm_size', null, '' );
$counsel_cities   = counsel_firm_cities();
$counsel_is_spon  = counsel_is_sponsored();
?>
<article id="firm-<?php the_ID(); ?>" <?php post_class( 'counsel-card' . ( $counsel_is_spon ? ' counsel-card--sponsored' : '' ) ); ?>>

	<?php if ( has_post_thumbnail() ) : ?>
		<a class="counsel-card__media" href="<?php the_permalink(); ?>" tabindex="-1" aria-hidden="true">
			<?php the_post_thumbnail( 'counsel-firm-card', array( 'loading' => 'lazy', 'alt' => esc_attr( get_the_title() ) ) ); ?>
		</a>
	<?php endif; ?>

	<div class="counsel-card__body">

		<?php if ( $counsel_is_spon ) : ?>
			<div class="counsel-card__flag">
				<?php counsel_sponsored_badge( array( 'size' => 'sm' ) ); ?>
			</div>
		<?php endif; ?>

		<h3 class="counsel-card__title">
			<a href="<?php the_permalink(); ?>"><?php the_title(); ?></a>
		</h3>

		<?php if ( '' !== $counsel_best_for ) : ?>
			<p class="counsel-card__summary"><?php echo esc_html( $counsel_best_for ); ?></p>
		<?php else : ?>
			<p class="counsel-card__summary"><?php echo esc_html( wp_trim_words( get_the_excerpt(), 22 ) ); ?></p>
		<?php endif; ?>

		<?php counsel_practice_area_tags( null, 3 ); ?>

		<div class="counsel-card__meta">
			<?php if ( '' !== $counsel_cities ) : ?>
				<span class="counsel-card__city"><?php echo wp_kses_post( $counsel_cities ); ?></span>
			<?php endif; ?>
			<?php if ( '' !== $counsel_size ) : ?>
				<span class="counsel-card__size"><?php echo esc_html( $counsel_size ); ?></span>
			<?php endif; ?>
		</div>

		<a class="counsel-card__link" href="<?php the_permalink(); ?>">
			<?php
			/* translators: %s: firm name */
			printf( esc_html__( 'Read the %s profile', 'counsel' ), esc_html( get_the_title() ) );
			?>
			<span aria-hidden="true">&rarr;</span>
		</a>

	</div>
</article>
