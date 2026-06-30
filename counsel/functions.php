<?php
/**
 * Counsel theme functions and definitions.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

if ( ! defined( 'COUNSEL_VERSION' ) ) {
	define( 'COUNSEL_VERSION', '1.0.0' );
}
if ( ! defined( 'COUNSEL_DIR' ) ) {
	define( 'COUNSEL_DIR', get_template_directory() );
}
if ( ! defined( 'COUNSEL_URI' ) ) {
	define( 'COUNSEL_URI', get_template_directory_uri() );
}

/**
 * Theme setup: supports, menus, image sizes, text domain.
 *
 * @return void
 */
function counsel_setup() {
	// Translation-ready.
	load_theme_textdomain( 'counsel', COUNSEL_DIR . '/languages' );

	add_theme_support( 'automatic-feed-links' );
	add_theme_support( 'title-tag' );
	add_theme_support( 'post-thumbnails' );
	add_theme_support( 'responsive-embeds' );
	add_theme_support( 'customize-selective-refresh-widgets' );

	add_theme_support(
		'html5',
		array(
			'search-form',
			'comment-form',
			'comment-list',
			'gallery',
			'caption',
			'style',
			'script',
		)
	);

	// Let WordPress manage the document title.
	add_theme_support(
		'custom-logo',
		array(
			'height'      => 48,
			'width'       => 200,
			'flex-width'  => true,
			'flex-height' => true,
		)
	);

	// Editor styles so the block editor reflects the front end.
	add_theme_support( 'editor-styles' );
	add_editor_style( 'assets/css/editor-style.css' );
	add_theme_support( 'wp-block-styles' );
	add_theme_support( 'align-wide' );

	// Image sizes.
	add_image_size( 'counsel-firm-card', 720, 480, true );   // Directory cards.
	add_image_size( 'counsel-profile-hero', 1600, 720, true ); // Profile hero.

	// Navigation menus.
	register_nav_menus(
		array(
			'primary' => __( 'Primary (Header)', 'counsel' ),
			'footer'  => __( 'Footer', 'counsel' ),
		)
	);

	// Editor color palette mirrors the brand tokens.
	add_theme_support(
		'editor-color-palette',
		array(
			array(
				'name'  => __( 'Oxblood', 'counsel' ),
				'slug'  => 'oxblood',
				'color' => '#8A2326',
			),
			array(
				'name'  => __( 'Brass', 'counsel' ),
				'slug'  => 'brass',
				'color' => '#B68A4E',
			),
			array(
				'name'  => __( 'Parchment', 'counsel' ),
				'slug'  => 'parchment',
				'color' => '#F1E8D8',
			),
			array(
				'name'  => __( 'Ink', 'counsel' ),
				'slug'  => 'ink',
				'color' => '#14110F',
			),
			array(
				'name'  => __( 'Paper', 'counsel' ),
				'slug'  => 'paper',
				'color' => '#FBF9F5',
			),
		)
	);
}
add_action( 'after_setup_theme', 'counsel_setup' );

/**
 * Set the content width.
 *
 * @return void
 */
function counsel_content_width() {
	$GLOBALS['content_width'] = apply_filters( 'counsel_content_width', 760 );
}
add_action( 'after_setup_theme', 'counsel_content_width', 0 );

/**
 * Register widget areas.
 *
 * @return void
 */
function counsel_widgets_init() {
	register_sidebar(
		array(
			'name'          => __( 'Article Sidebar', 'counsel' ),
			'id'            => 'sidebar-1',
			'description'   => __( 'Shown alongside guides and advice articles.', 'counsel' ),
			'before_widget' => '<section id="%1$s" class="widget %2$s">',
			'after_widget'  => '</section>',
			'before_title'  => '<h2 class="widget-title">',
			'after_title'   => '</h2>',
		)
	);

	register_sidebar(
		array(
			'name'          => __( 'Footer Columns', 'counsel' ),
			'id'            => 'footer-widgets',
			'description'   => __( 'Optional widgets shown in the footer (in addition to the footer menu).', 'counsel' ),
			'before_widget' => '<div id="%1$s" class="widget %2$s">',
			'after_widget'  => '</div>',
			'before_title'  => '<h2 class="widget-title">',
			'after_title'   => '</h2>',
		)
	);
}
add_action( 'widgets_init', 'counsel_widgets_init' );

/**
 * Enqueue styles and scripts.
 *
 * @return void
 */
function counsel_enqueue_assets() {
	// Google Fonts: Fraunces (display/headings) + Inter (body/UI), display=swap.
	wp_enqueue_style(
		'counsel-fonts',
		'https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&display=swap',
		array(),
		null // No version for external font URL.
	);

	// Required theme stylesheet (header block).
	wp_enqueue_style(
		'counsel-style',
		get_stylesheet_uri(),
		array(),
		COUNSEL_VERSION
	);

	// Main compiled stylesheet (cache-busted with filemtime).
	$main_css = COUNSEL_DIR . '/assets/css/main.css';
	wp_enqueue_style(
		'counsel-main',
		COUNSEL_URI . '/assets/css/main.css',
		array( 'counsel-fonts', 'counsel-style' ),
		file_exists( $main_css ) ? filemtime( $main_css ) : COUNSEL_VERSION
	);

	// Main JS in the footer, no jQuery dependency.
	$main_js = COUNSEL_DIR . '/assets/js/main.js';
	wp_enqueue_script(
		'counsel-main',
		COUNSEL_URI . '/assets/js/main.js',
		array(),
		file_exists( $main_js ) ? filemtime( $main_js ) : COUNSEL_VERSION,
		true
	);

	// Threaded comments support.
	if ( is_singular() && comments_open() && get_option( 'thread_comments' ) ) {
		wp_enqueue_script( 'comment-reply' );
	}
}
add_action( 'wp_enqueue_scripts', 'counsel_enqueue_assets' );

/**
 * Preconnect to Google Fonts hosts for faster font loading.
 *
 * @param array  $urls          URLs to print for resource hints.
 * @param string $relation_type The relation type the URLs are printed for.
 * @return array
 */
function counsel_resource_hints( $urls, $relation_type ) {
	if ( wp_style_is( 'counsel-fonts', 'queue' ) && 'preconnect' === $relation_type ) {
		$urls[] = array(
			'href' => 'https://fonts.googleapis.com',
		);
		$urls[] = array(
			'href'        => 'https://fonts.gstatic.com',
			'crossorigin' => 'anonymous',
		);
	}
	return $urls;
}
add_filter( 'wp_resource_hints', 'counsel_resource_hints', 10, 2 );

/**
 * Include theme component files.
 */
require COUNSEL_DIR . '/inc/disclaimers.php';
require COUNSEL_DIR . '/inc/post-types.php';
require COUNSEL_DIR . '/inc/taxonomies.php';
require COUNSEL_DIR . '/inc/meta-boxes.php';
require COUNSEL_DIR . '/inc/template-tags.php';
require COUNSEL_DIR . '/inc/customizer.php';

/**
 * On theme activation: seed starter terms and flush rewrite rules.
 *
 * Registering the CPT/taxonomies happens on `init`; here we just make sure
 * the rules are flushed so /attorneys/ works immediately, and the starter
 * terms exist.
 *
 * @return void
 */
function counsel_after_switch_theme() {
	// Ensure CPT + taxonomies are registered before seeding/flushing.
	counsel_register_firm_post_type();
	counsel_register_taxonomies();

	counsel_seed_taxonomy_terms();

	flush_rewrite_rules();
}
add_action( 'after_switch_theme', 'counsel_after_switch_theme' );

/**
 * Flush rewrite rules on deactivation too, to keep things clean.
 *
 * @return void
 */
function counsel_switch_theme() {
	flush_rewrite_rules();
}
add_action( 'switch_theme', 'counsel_switch_theme' );

/**
 * Allow the firm archive (Find a Lawyer) to be filtered by query args coming
 * from the search form: ?practice_area=slug&city=slug&firm_size=...
 *
 * @param WP_Query $query The query.
 * @return void
 */
function counsel_filter_firm_archive( $query ) {
	if ( is_admin() || ! $query->is_main_query() ) {
		return;
	}

	if ( ! $query->is_post_type_archive( 'firm' ) && ! $query->is_tax( array( 'practice_area', 'city' ) ) ) {
		return;
	}

	$tax_query = array();

	// Practice area from the search form (slug).
	$pa = isset( $_GET['practice_area'] ) ? sanitize_title( wp_unslash( $_GET['practice_area'] ) ) : ''; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Read-only public filter.
	if ( $pa && $query->is_post_type_archive( 'firm' ) ) {
		$tax_query[] = array(
			'taxonomy' => 'practice_area',
			'field'    => 'slug',
			'terms'    => $pa,
		);
	}

	// City from the search form (slug).
	$city = isset( $_GET['city'] ) ? sanitize_title( wp_unslash( $_GET['city'] ) ) : ''; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Read-only public filter.
	if ( $city && $query->is_post_type_archive( 'firm' ) ) {
		$tax_query[] = array(
			'taxonomy' => 'city',
			'field'    => 'slug',
			'terms'    => $city,
		);
	}

	if ( count( $tax_query ) > 1 ) {
		$tax_query['relation'] = 'AND';
	}

	if ( ! empty( $tax_query ) ) {
		$query->set( 'tax_query', $tax_query );
	}

	// Firm size meta filter (matches the stored string loosely).
	$size = isset( $_GET['firm_size'] ) ? sanitize_text_field( wp_unslash( $_GET['firm_size'] ) ) : ''; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Read-only public filter.
	if ( $size ) {
		$query->set(
			'meta_query',
			array(
				array(
					'key'     => 'firm_size',
					'value'   => $size,
					'compare' => 'LIKE',
				),
			)
		);
	}

	// Sponsored firms surface first, then by title — editorial ordering.
	if ( $query->is_post_type_archive( 'firm' ) || $query->is_tax( array( 'practice_area', 'city' ) ) ) {
		$query->set( 'posts_per_page', 12 );
	}
}
add_action( 'pre_get_posts', 'counsel_filter_firm_archive' );

/**
 * Handle the "For Attorneys" availability inquiry form submission.
 *
 * Plugin-free: posts back to the same page, validates a nonce, emails the
 * attorney-inquiry address, and stores a transient flag for the success notice.
 *
 * @return void
 */
function counsel_handle_attorney_inquiry() {
	if ( empty( $_POST['counsel_attorney_inquiry'] ) ) {
		return;
	}

	if ( ! isset( $_POST['counsel_inquiry_nonce'] )
		|| ! wp_verify_nonce( sanitize_key( wp_unslash( $_POST['counsel_inquiry_nonce'] ) ), 'counsel_attorney_inquiry' ) ) {
		return;
	}

	// Honeypot — bots fill hidden fields.
	if ( ! empty( $_POST['counsel_hp'] ) ) {
		return;
	}

	$name     = isset( $_POST['inq_name'] ) ? sanitize_text_field( wp_unslash( $_POST['inq_name'] ) ) : '';
	$firm     = isset( $_POST['inq_firm'] ) ? sanitize_text_field( wp_unslash( $_POST['inq_firm'] ) ) : '';
	$city     = isset( $_POST['inq_city'] ) ? sanitize_text_field( wp_unslash( $_POST['inq_city'] ) ) : '';
	$practice = isset( $_POST['inq_practice'] ) ? sanitize_text_field( wp_unslash( $_POST['inq_practice'] ) ) : '';
	$email    = isset( $_POST['inq_email'] ) ? sanitize_email( wp_unslash( $_POST['inq_email'] ) ) : '';
	$phone    = isset( $_POST['inq_phone'] ) ? sanitize_text_field( wp_unslash( $_POST['inq_phone'] ) ) : '';

	$redirect = wp_get_referer() ? wp_get_referer() : home_url( '/' );

	if ( '' === $name || ! is_email( $email ) ) {
		wp_safe_redirect( add_query_arg( 'inquiry', 'error', $redirect ) );
		exit;
	}

	$to      = counsel_get_attorney_email();
	$subject = sprintf(
		/* translators: %s: firm name */
		__( 'New attorney inquiry from %s', 'counsel' ),
		'' !== $firm ? $firm : $name
	);

	$body = array(
		__( 'A new attorney availability inquiry was submitted on Counsel.', 'counsel' ),
		'',
		sprintf( '%s %s', __( 'Name:', 'counsel' ), $name ),
		sprintf( '%s %s', __( 'Firm:', 'counsel' ), $firm ),
		sprintf( '%s %s', __( 'City:', 'counsel' ), $city ),
		sprintf( '%s %s', __( 'Practice area:', 'counsel' ), $practice ),
		sprintf( '%s %s', __( 'Email:', 'counsel' ), $email ),
		sprintf( '%s %s', __( 'Phone:', 'counsel' ), $phone ),
	);

	$headers = array( 'Reply-To: ' . $name . ' <' . $email . '>' );

	wp_mail( $to, $subject, implode( "\n", $body ), $headers );

	wp_safe_redirect( add_query_arg( 'inquiry', 'sent', $redirect ) );
	exit;
}
add_action( 'template_redirect', 'counsel_handle_attorney_inquiry' );

/**
 * Add a body class describing the current template context.
 *
 * @param string[] $classes Body classes.
 * @return string[]
 */
function counsel_body_classes( $classes ) {
	if ( is_singular( 'firm' ) && counsel_is_sponsored() ) {
		$classes[] = 'is-sponsored-firm';
	}
	if ( ! is_singular() ) {
		$classes[] = 'hfeed';
	}
	return $classes;
}
add_filter( 'body_class', 'counsel_body_classes' );

/**
 * Use the firm-card image size for excerpts, and a gentle excerpt length.
 *
 * @param int $length Default length.
 * @return int
 */
function counsel_excerpt_length( $length ) {
	return 28;
}
add_filter( 'excerpt_length', 'counsel_excerpt_length' );

/**
 * Editorial "read more" ellipsis.
 *
 * @param string $more Default more string.
 * @return string
 */
function counsel_excerpt_more( $more ) {
	return '&hellip;';
}
add_filter( 'excerpt_more', 'counsel_excerpt_more' );

/**
 * Optional, disable-able LegalService / Organization microdata hook.
 *
 * We intentionally do NOT hard-code JSON-LD that would conflict with an SEO
 * plugin. Instead we expose a filter so site owners can opt in. Returning false
 * from `counsel_enable_microdata` (the default until an SEO plugin is absent and
 * the owner opts in) prevents output.
 *
 * @return void
 */
function counsel_maybe_output_microdata() {
	/**
	 * Enable Counsel's built-in Organization microdata.
	 *
	 * Off by default to avoid clashing with SEO plugins. Enable via:
	 *   add_filter( 'counsel_enable_microdata', '__return_true' );
	 *
	 * @param bool $enabled Whether to output microdata.
	 */
	if ( ! apply_filters( 'counsel_enable_microdata', false ) ) {
		return;
	}

	if ( ! is_front_page() ) {
		return;
	}

	$data = array(
		'@context' => 'https://schema.org',
		'@type'    => 'Organization',
		'name'     => get_bloginfo( 'name' ),
		'url'      => home_url( '/' ),
		'description' => get_bloginfo( 'description' ),
	);

	$socials = array_values( counsel_get_social_links() );
	if ( ! empty( $socials ) ) {
		$data['sameAs'] = $socials;
	}

	printf(
		'<script type="application/ld+json">%s</script>' . "\n",
		wp_json_encode( $data ) // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- wp_json_encode escapes for JSON context.
	);
}
add_action( 'wp_head', 'counsel_maybe_output_microdata' );
