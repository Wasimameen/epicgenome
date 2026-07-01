<?php
/**
 * Template Name: Full Width (page builder)
 *
 * A clean, edge-to-edge canvas that keeps the theme header and footer but
 * imposes NO container width, sidebar, page title, or prose measure — ideal for
 * pages designed in Elementor (or any page builder / full-width blocks).
 *
 * Elementor's own "Elementor Full Width" template does the same thing; this is
 * provided so the option exists even before Elementor registers its templates,
 * and so it works with other builders too.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

get_header();
?>
<main id="primary" class="site-main site-main--full" role="main">
	<?php
	while ( have_posts() ) :
		the_post();
		the_content();

		wp_link_pages(
			array(
				'before' => '<nav class="page-links">' . esc_html__( 'Pages:', 'counsel' ),
				'after'  => '</nav>',
			)
		);

		if ( comments_open() || get_comments_number() ) {
			comments_template();
		}
	endwhile;
	?>
</main>
<?php
get_footer();
