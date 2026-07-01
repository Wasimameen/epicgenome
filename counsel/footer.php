<?php
/**
 * The footer: columns, footer menu, social links, and the global disclaimer.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

$counsel_socials = function_exists( 'counsel_get_social_links' ) ? counsel_get_social_links() : array();
?>
</div><!-- #content -->

<footer id="colophon" class="site-footer" role="contentinfo">
	<div class="counsel-container site-footer__inner">

		<div class="site-footer__brand">
			<a class="site-footer__wordmark" href="<?php echo esc_url( home_url( '/' ) ); ?>" rel="home">
				<?php esc_html_e( 'COUNSEL', 'counsel' ); ?>
			</a>
			<p class="site-footer__tagline">
				<?php echo esc_html( function_exists( 'counsel_mod' ) ? counsel_mod( 'counsel_footer_tagline' ) : __( 'An independent guide to hiring a lawyer.', 'counsel' ) ); ?>
			</p>

			<?php if ( ! empty( $counsel_socials ) ) : ?>
				<ul class="site-footer__social" aria-label="<?php esc_attr_e( 'Social links', 'counsel' ); ?>">
					<?php foreach ( $counsel_socials as $label => $url ) : ?>
						<li>
							<a href="<?php echo esc_url( $url ); ?>" rel="noopener" target="_blank">
								<?php echo esc_html( $label ); ?>
							</a>
						</li>
					<?php endforeach; ?>
				</ul>
			<?php endif; ?>
		</div>

		<nav class="site-footer__nav" aria-label="<?php esc_attr_e( 'Footer', 'counsel' ); ?>">
			<?php
			if ( has_nav_menu( 'footer' ) ) {
				wp_nav_menu(
					array(
						'theme_location' => 'footer',
						'menu_class'     => 'footer-menu',
						'container'      => false,
						'depth'          => 1,
					)
				);
			} else {
				echo '<ul class="footer-menu">';
				printf( '<li><a href="%1$s">%2$s</a></li>', esc_url( home_url( '/about/' ) ), esc_html__( 'About', 'counsel' ) );
				printf( '<li><a href="%1$s">%2$s</a></li>', esc_url( home_url( '/how-it-works/' ) ), esc_html__( 'How It Works', 'counsel' ) );
				printf( '<li><a href="%1$s">%2$s</a></li>', esc_url( home_url( '/for-attorneys/' ) ), esc_html__( 'For Attorneys', 'counsel' ) );
				printf( '<li><a href="%1$s">%2$s</a></li>', esc_url( home_url( '/contact/' ) ), esc_html__( 'Contact', 'counsel' ) );
				echo '</ul>';
			}
			?>
		</nav>

		<?php if ( is_active_sidebar( 'footer-widgets' ) ) : ?>
			<div class="site-footer__widgets">
				<?php dynamic_sidebar( 'footer-widgets' ); ?>
			</div>
		<?php endif; ?>

	</div><!-- .site-footer__inner -->

	<?php if ( get_theme_mod( 'counsel_show_footer_disclaimer', true ) ) : ?>
		<div class="counsel-container">
			<p class="counsel-footer__disclaimer">
				<?php echo esc_html( counsel_disclaimer_footer() ); ?>
			</p>
			<p class="counsel-footer__disclaimer counsel-footer__disclaimer--ad">
				<?php echo esc_html( counsel_disclaimer_advertising() ); ?>
			</p>
		</div>
	<?php endif; ?>

	<div class="site-footer__legal">
		<div class="counsel-container">
			<p class="site-footer__copyright">
				<?php
				printf(
					/* translators: 1: year, 2: site name */
					esc_html__( '© %1$s %2$s. All rights reserved.', 'counsel' ),
					esc_html( gmdate( 'Y' ) ),
					esc_html( get_bloginfo( 'name' ) )
				);
				?>
			</p>
		</div>
	</div>
</footer><!-- #colophon -->

<?php wp_footer(); ?>
</body>
</html>
