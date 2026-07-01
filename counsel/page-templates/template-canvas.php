<?php
/**
 * Template Name: Blank Canvas (page builder)
 *
 * A completely blank canvas — NO theme header, footer, container, or styling
 * chrome — for landing pages built entirely in Elementor (or another builder).
 * Only wp_head() and wp_footer() are output, so the builder controls 100% of
 * the page. Equivalent to "Elementor Canvas".
 *
 * The theme's main.css (with your Customizer colours/fonts) is still enqueued,
 * so brand tokens remain available to builder widgets.
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
	<link rel="icon" href="<?php echo esc_url( COUNSEL_URI . '/assets/img/favicon.svg' ); ?>" type="image/svg+xml" />
	<?php wp_head(); ?>
</head>
<body <?php body_class( 'counsel-canvas-page' ); ?>>
<?php wp_body_open(); ?>

<main id="primary" class="site-main site-main--canvas" role="main">
	<?php
	while ( have_posts() ) :
		the_post();
		the_content();
	endwhile;
	?>
</main>

<?php wp_footer(); ?>
</body>
</html>
