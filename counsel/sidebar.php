<?php
/**
 * The optional sidebar, used on guides/advice where helpful.
 *
 * Only renders if the 'sidebar-1' widget area has widgets.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

if ( ! is_active_sidebar( 'sidebar-1' ) ) {
	return;
}
?>
<aside id="secondary" class="counsel-sidebar widget-area" role="complementary" aria-label="<?php esc_attr_e( 'Sidebar', 'counsel' ); ?>">
	<?php dynamic_sidebar( 'sidebar-1' ); ?>
</aside>
