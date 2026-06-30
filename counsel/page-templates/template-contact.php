<?php
/**
 * Template Name: Contact
 *
 * Offers two clear paths: consumers and attorneys. Pulls any editor content
 * above the two-path chooser.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

get_header();

$counsel_contact_email  = function_exists( 'counsel_get_contact_email' ) ? counsel_get_contact_email() : get_option( 'admin_email' );
$counsel_attorney_email = function_exists( 'counsel_get_attorney_email' ) ? counsel_get_attorney_email() : get_option( 'admin_email' );
$counsel_phone          = get_theme_mod( 'counsel_contact_phone', '' );
$counsel_topic          = isset( $_GET['topic'] ) ? sanitize_key( wp_unslash( $_GET['topic'] ) ) : ''; // phpcs:ignore WordPress.Security.NonceVerification.Recommended
?>
<main id="primary" class="site-main page-contact" role="main">

	<div class="counsel-container">
		<?php counsel_breadcrumbs(); ?>

		<header class="counsel-page__header">
			<p class="counsel-kicker"><?php esc_html_e( 'Contact', 'counsel' ); ?></p>
			<?php
			while ( have_posts() ) :
				the_post();
				?>
				<h1 class="counsel-page__title"><?php the_title(); ?></h1>
				<?php
				if ( '' !== trim( wp_strip_all_tags( get_the_content() ) ) ) :
					?>
					<div class="counsel-prose entry-content"><?php the_content(); ?></div>
					<?php
				else :
					?>
					<p class="counsel-page__lede"><?php esc_html_e( 'Tell us which best describes you and we\'ll point you the right way.', 'counsel' ); ?></p>
					<?php
				endif;
			endwhile;
			?>
		</header>

		<?php if ( 'suggest-a-city' === $counsel_topic ) : ?>
			<div class="counsel-notice" role="status">
				<?php esc_html_e( 'Want Counsel in your city? Email us using the consumer path below with your city in the subject — we prioritize coverage by demand.', 'counsel' ); ?>
			</div>
		<?php endif; ?>

		<div class="counsel-contact-paths">

			<section class="counsel-contact-card">
				<h2 class="counsel-contact-card__title"><?php esc_html_e( 'I\'m looking for a lawyer', 'counsel' ); ?></h2>
				<p><?php esc_html_e( 'Questions about a profile, our guides, or how to use the directory? We\'re glad to help — though remember Counsel is independent and can\'t give legal advice or make referrals.', 'counsel' ); ?></p>
				<?php if ( $counsel_contact_email ) : ?>
					<a class="counsel-btn counsel-btn--primary" href="<?php echo esc_url( 'mailto:' . antispambot( $counsel_contact_email ) ); ?>">
						<?php esc_html_e( 'Email Counsel', 'counsel' ); ?>
					</a>
				<?php endif; ?>
				<?php if ( $counsel_phone ) : ?>
					<p class="counsel-contact-card__alt">
						<?php
						/* translators: %s: phone number */
						printf( esc_html__( 'Or call %s', 'counsel' ), '<a href="' . esc_url( 'tel:' . preg_replace( '/[^0-9+]/', '', $counsel_phone ) ) . '">' . esc_html( $counsel_phone ) . '</a>' );
						?>
					</p>
				<?php endif; ?>
			</section>

			<section class="counsel-contact-card counsel-contact-card--attorneys">
				<h2 class="counsel-contact-card__title"><?php esc_html_e( 'I\'m an attorney', 'counsel' ); ?></h2>
				<p><?php esc_html_e( 'Interested in an exclusive, clearly labeled sponsorship? Start on our For Attorneys page to check availability in your practice area and city.', 'counsel' ); ?></p>
				<a class="counsel-btn counsel-btn--ghost" href="<?php echo esc_url( home_url( '/for-attorneys/' ) ); ?>">
					<?php esc_html_e( 'For Attorneys', 'counsel' ); ?>
				</a>
				<?php if ( $counsel_attorney_email ) : ?>
					<p class="counsel-contact-card__alt">
						<?php
						/* translators: %s: email address */
						printf( esc_html__( 'Or email %s', 'counsel' ), '<a href="' . esc_url( 'mailto:' . antispambot( $counsel_attorney_email ) ) . '">' . esc_html( $counsel_attorney_email ) . '</a>' );
						?>
					</p>
				<?php endif; ?>
			</section>

		</div>

		<?php counsel_render_disclaimer( 'not_legal_advice', 'block' ); ?>
	</div>

</main>
<?php
get_footer();
