<?php
/**
 * Template Name: For Attorneys
 *
 * The one advertiser-facing page. Value props, a "what you get" list, the
 * independence/disclosure commitment, and a "check availability" inquiry form
 * (handled plugin-free by counsel_handle_attorney_inquiry() in functions.php).
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

get_header();

// Inquiry status from the redirect after submission.
$counsel_inquiry = isset( $_GET['inquiry'] ) ? sanitize_key( wp_unslash( $_GET['inquiry'] ) ) : ''; // phpcs:ignore WordPress.Security.NonceVerification.Recommended

$counsel_practice_terms = get_terms( array( 'taxonomy' => 'practice_area', 'hide_empty' => false ) );
?>
<main id="primary" class="site-main page-attorneys" role="main">

	<section class="counsel-attorneys-hero">
		<div class="counsel-container">
			<p class="counsel-kicker"><?php esc_html_e( 'For Attorneys', 'counsel' ); ?></p>
			<h1 class="counsel-attorneys-hero__title">
				<?php esc_html_e( 'Be the firm clients trust before they call.', 'counsel' ); ?>
			</h1>
			<p class="counsel-attorneys-hero__lede">
				<?php esc_html_e( 'Counsel is read by people actively deciding who to hire. A sponsorship puts your firm in front of them inside calm, credible editorial — never a race-to-the-bottom lead list. Sponsorships are exclusive and clearly labeled.', 'counsel' ); ?>
			</p>
			<a class="counsel-btn counsel-btn--primary" href="#check-availability">
				<?php esc_html_e( 'Check availability', 'counsel' ); ?>
			</a>
		</div>
	</section>

	<?php
	// Editor-owned content, if the page has any.
	while ( have_posts() ) :
		the_post();
		if ( '' !== trim( wp_strip_all_tags( get_the_content() ) ) ) :
			?>
			<section class="counsel-attorneys-intro">
				<div class="counsel-container counsel-prose"><?php the_content(); ?></div>
			</section>
			<?php
		endif;
	endwhile;
	?>

	<section class="counsel-attorneys-value">
		<div class="counsel-container">
			<?php counsel_section_heading( __( 'Why firms sponsor Counsel', 'counsel' ), 'h2', __( 'Value', 'counsel' ) ); ?>
			<div class="counsel-attorneys-value__grid">
				<?php
				$counsel_values = array(
					array(
						'title' => __( 'Intent, not noise', 'counsel' ),
						'desc'  => __( 'Our readers are mid-decision — researching, comparing, and ready to act. You reach them in context, not in a banner.', 'counsel' ),
					),
					array(
						'title' => __( 'Borrowed credibility', 'counsel' ),
						'desc'  => __( 'Appearing within independent editorial signals seriousness. Your firm benefits from the trust the publication earns.', 'counsel' ),
					),
					array(
						'title' => __( 'Exclusive placement', 'counsel' ),
						'desc'  => __( 'We limit sponsorships per practice area and city, so you\'re not lost in a crowded list of competitors.', 'counsel' ),
					),
				);
				foreach ( $counsel_values as $counsel_v ) {
					echo '<div class="counsel-attorneys-value__item">';
					echo '<h3>' . esc_html( $counsel_v['title'] ) . '</h3>';
					echo '<p>' . esc_html( $counsel_v['desc'] ) . '</p>';
					echo '</div>';
				}
				?>
			</div>
		</div>
	</section>

	<section class="counsel-attorneys-get">
		<div class="counsel-container counsel-attorneys-get__inner">
			<div class="counsel-attorneys-get__col">
				<?php counsel_section_heading( __( 'What you get', 'counsel' ), 'h2' ); ?>
				<ul class="counsel-checklist">
					<li><?php esc_html_e( 'An exclusive sponsored placement in your practice area and city', 'counsel' ); ?></li>
					<li><?php esc_html_e( 'A clearly labeled, professionally written featured profile', 'counsel' ); ?></li>
					<li><?php esc_html_e( 'Placement within relevant guides and roundups where appropriate', 'counsel' ); ?></li>
					<li><?php esc_html_e( 'A direct contact path for ready-to-hire readers', 'counsel' ); ?></li>
					<li><?php esc_html_e( 'Transparent reporting on how your placement performs', 'counsel' ); ?></li>
				</ul>
			</div>
			<div class="counsel-attorneys-get__col">
				<?php counsel_section_heading( __( 'Our independence commitment', 'counsel' ), 'h2' ); ?>
				<div class="counsel-prose">
					<p><?php esc_html_e( 'Sponsorship buys visibility, never editorial favor. It does not influence our independent profiles, reviews, or "Best Of" selections, and placement on a roundup can never be purchased.', 'counsel' ); ?></p>
					<p><?php esc_html_e( 'Every sponsored placement is clearly labeled as such. Featured attorney content is attorney advertising, and the featured firm shares responsibility for the accuracy and compliance of claims about its own services.', 'counsel' ); ?></p>
				</div>
			</div>
		</div>
	</section>

	<section id="check-availability" class="counsel-attorneys-form">
		<div class="counsel-container">
			<?php counsel_section_heading( __( 'Check availability', 'counsel' ), 'h2', __( 'Get started', 'counsel' ) ); ?>

			<?php if ( 'sent' === $counsel_inquiry ) : ?>
				<div class="counsel-notice counsel-notice--success" role="status">
					<?php esc_html_e( 'Thank you — your inquiry is in. We\'ll be in touch shortly about availability in your area.', 'counsel' ); ?>
				</div>
			<?php elseif ( 'error' === $counsel_inquiry ) : ?>
				<div class="counsel-notice counsel-notice--error" role="alert">
					<?php esc_html_e( 'Please add your name and a valid email address, then try again.', 'counsel' ); ?>
				</div>
			<?php endif; ?>

			<form class="counsel-form" method="post" action="<?php echo esc_url( get_permalink() ); ?>">
				<?php wp_nonce_field( 'counsel_attorney_inquiry', 'counsel_inquiry_nonce' ); ?>
				<input type="hidden" name="counsel_attorney_inquiry" value="1" />
				<p class="counsel-form__hp" aria-hidden="true">
					<label><?php esc_html_e( 'Leave this field empty', 'counsel' ); ?>
						<input type="text" name="counsel_hp" tabindex="-1" autocomplete="off" />
					</label>
				</p>

				<div class="counsel-form__row">
					<div class="counsel-form__field">
						<label for="inq_name"><?php esc_html_e( 'Your name', 'counsel' ); ?> <span class="counsel-req">*</span></label>
						<input type="text" id="inq_name" name="inq_name" required />
					</div>
					<div class="counsel-form__field">
						<label for="inq_firm"><?php esc_html_e( 'Firm', 'counsel' ); ?></label>
						<input type="text" id="inq_firm" name="inq_firm" />
					</div>
				</div>

				<div class="counsel-form__row">
					<div class="counsel-form__field">
						<label for="inq_city"><?php esc_html_e( 'City', 'counsel' ); ?></label>
						<input type="text" id="inq_city" name="inq_city" />
					</div>
					<div class="counsel-form__field">
						<label for="inq_practice"><?php esc_html_e( 'Practice area', 'counsel' ); ?></label>
						<select id="inq_practice" name="inq_practice">
							<option value=""><?php esc_html_e( 'Select…', 'counsel' ); ?></option>
							<?php
							if ( ! is_wp_error( $counsel_practice_terms ) ) {
								foreach ( $counsel_practice_terms as $counsel_t ) {
									printf( '<option value="%1$s">%1$s</option>', esc_attr( $counsel_t->name ) );
								}
							}
							?>
						</select>
					</div>
				</div>

				<div class="counsel-form__row">
					<div class="counsel-form__field">
						<label for="inq_email"><?php esc_html_e( 'Email', 'counsel' ); ?> <span class="counsel-req">*</span></label>
						<input type="email" id="inq_email" name="inq_email" required />
					</div>
					<div class="counsel-form__field">
						<label for="inq_phone"><?php esc_html_e( 'Phone', 'counsel' ); ?></label>
						<input type="tel" id="inq_phone" name="inq_phone" />
					</div>
				</div>

				<div class="counsel-form__actions">
					<button type="submit" class="counsel-btn counsel-btn--primary"><?php esc_html_e( 'Check availability', 'counsel' ); ?></button>
				</div>
			</form>
		</div>
	</section>

</main>
<?php
get_footer();
