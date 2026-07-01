<?php
/**
 * The header: <head>, skip link, and the site header + primary nav.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;
?>
<!DOCTYPE html>
<html <?php language_attributes(); ?>>
<head>
	<meta charset="<?php bloginfo( 'charset' ); ?>" />
	<meta name="viewport" content="width=device-width, initial-scale=1" />
	<link rel="profile" href="https://gmpg.org/xfn/11" />
	<link rel="icon" href="<?php echo esc_url( COUNSEL_URI . '/assets/img/favicon.svg' ); ?>" type="image/svg+xml" />
	<?php wp_head(); ?>
</head>

<body <?php body_class(); ?>>
<?php wp_body_open(); ?>

<a class="skip-link screen-reader-text" href="#content"><?php esc_html_e( 'Skip to content', 'counsel' ); ?></a>

<?php
// If Elementor Pro has a header assigned, let it render and skip the theme's
// header entirely. Otherwise the theme header below is the fallback.
if ( ! function_exists( 'counsel_do_elementor_location' ) || ! counsel_do_elementor_location( 'header' ) ) :
	?>
<header id="masthead" class="site-header" role="banner">
	<div class="site-header__inner counsel-container">

		<div class="site-branding">
			<?php if ( has_custom_logo() ) : ?>
				<?php the_custom_logo(); ?>
			<?php else : ?>
				<a class="site-branding__wordmark" href="<?php echo esc_url( home_url( '/' ) ); ?>" rel="home" aria-label="<?php echo esc_attr( get_bloginfo( 'name' ) ); ?>">
					<?php
					// Inline the wordmark SVG so it inherits brand color; fall back to text.
					$wordmark = COUNSEL_DIR . '/assets/img/wordmark.svg';
					if ( file_exists( $wordmark ) ) {
						// SVG is local and trusted (shipped with the theme).
						echo file_get_contents( $wordmark ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents, WordPress.Security.EscapeOutput.OutputNotEscaped
					} else {
						echo '<span class="site-branding__text">' . esc_html__( 'COUNSEL', 'counsel' ) . '</span>';
					}
					?>
				</a>
			<?php endif; ?>
		</div>

		<button
			class="menu-toggle"
			aria-controls="primary-menu"
			aria-expanded="false"
			aria-label="<?php esc_attr_e( 'Open menu', 'counsel' ); ?>"
		>
			<span class="menu-toggle__bars" aria-hidden="true"></span>
			<span class="screen-reader-text"><?php esc_html_e( 'Menu', 'counsel' ); ?></span>
		</button>

		<nav id="site-navigation" class="main-navigation" role="navigation" aria-label="<?php esc_attr_e( 'Primary', 'counsel' ); ?>">
			<?php
			if ( has_nav_menu( 'primary' ) ) {
				wp_nav_menu(
					array(
						'theme_location' => 'primary',
						'menu_id'        => 'primary-menu',
						'menu_class'     => 'primary-menu',
						'container'      => false,
						'depth'          => 2,
					)
				);
			} else {
				// Sensible default nav so the header is never empty on a fresh install.
				echo '<ul id="primary-menu" class="primary-menu">';
				printf(
					'<li><a href="%1$s">%2$s</a></li>',
					esc_url( get_post_type_archive_link( 'firm' ) ),
					esc_html__( 'Find a Lawyer', 'counsel' )
				);
				printf(
					'<li><a href="%1$s">%2$s</a></li>',
					esc_url( home_url( '/how-it-works/' ) ),
					esc_html__( 'How It Works', 'counsel' )
				);
				printf(
					'<li><a href="%1$s">%2$s</a></li>',
					esc_url( home_url( '/about/' ) ),
					esc_html__( 'About', 'counsel' )
				);
				printf(
					'<li class="menu-item--attorneys"><a href="%1$s">%2$s</a></li>',
					esc_url( home_url( '/for-attorneys/' ) ),
					esc_html__( 'For Attorneys', 'counsel' )
				);
				echo '</ul>';
			}
			?>
		</nav>

		<?php if ( ! function_exists( 'counsel_mod' ) || counsel_mod( 'counsel_show_header_cta' ) ) : ?>
			<div class="site-header__cta">
				<a class="counsel-btn counsel-btn--primary" href="<?php echo esc_url( function_exists( 'counsel_header_cta_url' ) ? counsel_header_cta_url() : get_post_type_archive_link( 'firm' ) ); ?>">
					<?php echo esc_html( function_exists( 'counsel_mod' ) ? counsel_mod( 'counsel_header_cta_label' ) : __( 'Find a Lawyer', 'counsel' ) ); ?>
				</a>
			</div>
		<?php endif; ?>

	</div><!-- .site-header__inner -->
</header><!-- #masthead -->
<?php endif; // End Elementor header fallback. ?>

<div id="content" class="site-content">
