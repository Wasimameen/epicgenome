<?php
/**
 * Minimal comments template.
 *
 * Comments are disabled on firm profiles (single-firm.php never calls
 * comments_template(), and this file bails on the 'firm' post type as a
 * belt-and-suspenders guard). Used lightly on advice/guide posts if enabled.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

// Never render comments on firm profiles.
if ( 'firm' === get_post_type() ) {
	return;
}

// If the post is password protected and the visitor hasn't entered it, bail.
if ( post_password_required() ) {
	return;
}
?>
<section id="comments" class="counsel-comments">

	<?php if ( have_comments() ) : ?>
		<h2 class="counsel-comments__title">
			<?php
			$counsel_count = get_comments_number();
			printf(
				/* translators: %s: comment count */
				esc_html( _n( '%s response', '%s responses', $counsel_count, 'counsel' ) ),
				esc_html( number_format_i18n( $counsel_count ) )
			);
			?>
		</h2>

		<ol class="counsel-comments__list">
			<?php
			wp_list_comments(
				array(
					'style'      => 'ol',
					'short_ping' => true,
					'avatar_size' => 48,
				)
			);
			?>
		</ol>

		<?php
		the_comments_pagination(
			array(
				'prev_text' => __( '&larr; Older comments', 'counsel' ),
				'next_text' => __( 'Newer comments &rarr;', 'counsel' ),
			)
		);
		?>

	<?php endif; ?>

	<?php if ( ! comments_open() && get_comments_number() && post_type_supports( get_post_type(), 'comments' ) ) : ?>
		<p class="counsel-comments__closed"><?php esc_html_e( 'Comments are closed.', 'counsel' ); ?></p>
	<?php endif; ?>

	<?php
	comment_form(
		array(
			'title_reply'        => __( 'Leave a response', 'counsel' ),
			'class_submit'       => 'counsel-btn counsel-btn--primary',
		)
	);
	?>

</section>
