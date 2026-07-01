<?php
/**
 * Single Firm Profile — the ten-section editorial layout.
 *
 * Sections in order:
 *   1. At-a-glance fact box (from custom fields, via counsel_fact_box()).
 *   2. Origins
 *   3. Practice areas (linked to taxonomy terms)
 *   4. Size / reach / team
 *   5. What clients say
 *   6. Notable results (firm-reported) + the results disclaimer
 *   7. Community & presence
 *   8. How they compare (links up to a matching Best Of roundup)
 *   9. FAQs
 *  10. Sources
 *
 * Sections 2–9 are authored in the post content/fields. To make the editorial
 * sections explicit and well-styled, author the body using H2 headings — the
 * theme styles them within the .counsel-prose measure. The fact box, the
 * results block, the compare link, and the sources block are rendered from
 * custom fields here. The profile-level disclaimer is appended at the bottom.
 *
 * Comments are disabled on firm profiles (see the bottom of this file).
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

get_header();

// If Elementor Pro has a single template assigned for firm profiles, use it.
if ( function_exists( 'counsel_do_elementor_location' ) && counsel_do_elementor_location( 'single' ) ) {
	get_footer();
	return;
}

while ( have_posts() ) :
	the_post();

	$counsel_best_for = counsel_get_firm_meta( 'firm_best_for', null, '' );
	$counsel_results  = counsel_get_firm_meta( 'firm_results', null, '' );
	$counsel_sources  = counsel_get_firm_meta( 'firm_sources', null, '' );
	$counsel_is_spon  = counsel_is_sponsored();
	?>
	<main id="primary" class="site-main counsel-firm" role="main"
		<?php echo apply_filters( 'counsel_enable_microdata', false ) ? 'itemscope itemtype="https://schema.org/LegalService"' : ''; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Static attribute string. ?>>

		<div class="counsel-container">
			<?php counsel_breadcrumbs(); ?>
		</div>

		<header class="counsel-firm__header">
			<div class="counsel-container">
				<?php if ( $counsel_is_spon ) : ?>
					<div class="counsel-firm__flag">
						<?php counsel_sponsored_badge(); ?>
					</div>
				<?php endif; ?>

				<h1 class="counsel-firm__title" <?php echo apply_filters( 'counsel_enable_microdata', false ) ? 'itemprop="name"' : ''; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>>
					<?php the_title(); ?>
				</h1>

				<?php if ( '' !== $counsel_best_for ) : ?>
					<p class="counsel-firm__bestfor"><?php echo esc_html( $counsel_best_for ); ?></p>
				<?php endif; ?>

				<div class="counsel-firm__meta">
					<?php
					$counsel_cities = counsel_firm_cities();
					if ( '' !== $counsel_cities ) {
						echo '<span class="counsel-firm__city">' . wp_kses_post( $counsel_cities ) . '</span>';
					}
					?>
				</div>
			</div>
		</header>

		<?php if ( has_post_thumbnail() ) : ?>
			<figure class="counsel-firm__hero">
				<?php the_post_thumbnail( 'counsel-profile-hero', array( 'loading' => 'eager' ) ); ?>
			</figure>
		<?php endif; ?>

		<div class="counsel-container counsel-firm__layout">

			<div class="counsel-firm__main">

				<?php // SECTION 1 — At a glance fact box. ?>
				<?php counsel_fact_box(); ?>

				<?php // SECTIONS 2–9 — authored editorial content (Origins, Practice areas, Size/reach/team, What clients say, Community & presence, FAQs, etc.). ?>
				<div class="counsel-prose counsel-firm__body entry-content">
					<?php
					the_content();

					wp_link_pages(
						array(
							'before' => '<nav class="page-links">' . esc_html__( 'Pages:', 'counsel' ),
							'after'  => '</nav>',
						)
					);
					?>
				</div>

				<?php // SECTION 3 (structured) — Practice areas linked to taxonomy terms. ?>
				<?php
				$counsel_pa_terms = get_the_terms( get_the_ID(), 'practice_area' );
				if ( ! empty( $counsel_pa_terms ) && ! is_wp_error( $counsel_pa_terms ) ) :
					?>
					<section class="counsel-firm__section counsel-firm__practice">
						<?php counsel_section_heading( __( 'Practice areas', 'counsel' ), 'h2' ); ?>
						<?php counsel_practice_area_tags(); ?>
					</section>
				<?php endif; ?>

				<?php // SECTION 6 — Notable results + mandatory results disclaimer. ?>
				<?php if ( '' !== $counsel_results ) : ?>
					<section class="counsel-firm__section counsel-firm__results">
						<?php counsel_section_heading( __( 'Notable results', 'counsel' ), 'h2', __( 'Firm-reported', 'counsel' ) ); ?>
						<ul class="counsel-firm__results-list">
							<?php
							$counsel_result_lines = preg_split( '/\r\n|\r|\n/', $counsel_results );
							foreach ( $counsel_result_lines as $counsel_line ) {
								$counsel_line = trim( $counsel_line );
								if ( '' === $counsel_line ) {
									continue;
								}
								echo '<li>' . esc_html( $counsel_line ) . '</li>';
							}
							?>
						</ul>
						<?php // Disclaimer immediately follows the results, per requirements. ?>
						<?php counsel_render_disclaimer( 'results', 'inline' ); ?>
					</section>
				<?php endif; ?>

				<?php // SECTION 8 — How they compare (link up to a matching Best Of roundup). ?>
				<?php
				$counsel_roundup_url = counsel_get_firm_meta( 'firm_roundup_url', null, '' );
				if ( '' !== $counsel_roundup_url ) :
					?>
					<section class="counsel-firm__section counsel-firm__compare">
						<?php counsel_section_heading( __( 'How they compare', 'counsel' ), 'h2' ); ?>
						<p>
							<?php esc_html_e( 'See where this firm stands against others we\'ve reviewed in the same area:', 'counsel' ); ?>
						</p>
						<a class="counsel-arrow-link" href="<?php echo esc_url( $counsel_roundup_url ); ?>">
							<?php esc_html_e( 'Read the related Best Of roundup', 'counsel' ); ?>
							<span aria-hidden="true">&rarr;</span>
						</a>
					</section>
				<?php endif; ?>

				<?php // SECTION 10 — Sources. ?>
				<?php if ( '' !== $counsel_sources ) : ?>
					<section class="counsel-firm__section counsel-firm__sources">
						<?php counsel_section_heading( __( 'Sources', 'counsel' ), 'h2' ); ?>
						<div class="counsel-firm__sources-body">
							<?php echo wp_kses_post( wpautop( make_clickable( $counsel_sources ) ) ); ?>
						</div>
					</section>
				<?php endif; ?>

				<?php // Profile-level disclaimer. ?>
				<?php counsel_render_disclaimer( 'profile', 'block' ); ?>

			</div><!-- .counsel-firm__main -->

			<aside class="counsel-firm__aside" aria-label="<?php esc_attr_e( 'Quick actions', 'counsel' ); ?>">
				<div class="counsel-firm__sticky">
					<?php
					$counsel_phone   = counsel_get_firm_meta( 'firm_phone', null, '' );
					$counsel_website = counsel_get_firm_meta( 'firm_website', null, '' );
					?>
					<?php if ( '' !== $counsel_phone || '' !== $counsel_website ) : ?>
						<div class="counsel-firm__contact-card">
							<h2 class="counsel-firm__contact-title"><?php esc_html_e( 'Contact this firm', 'counsel' ); ?></h2>
							<?php if ( '' !== $counsel_phone ) : ?>
								<a class="counsel-btn counsel-btn--primary counsel-firm__contact-btn" href="<?php echo esc_url( 'tel:' . preg_replace( '/[^0-9+]/', '', $counsel_phone ) ); ?>">
									<?php echo esc_html( $counsel_phone ); ?>
								</a>
							<?php endif; ?>
							<?php if ( '' !== $counsel_website ) : ?>
								<a class="counsel-btn counsel-btn--ghost counsel-firm__contact-btn" href="<?php echo esc_url( $counsel_website ); ?>" rel="nofollow noopener" target="_blank">
									<?php esc_html_e( 'Visit website', 'counsel' ); ?>
								</a>
							<?php endif; ?>
							<p class="counsel-firm__contact-note">
								<?php esc_html_e( 'Counsel is independent and is not the firm. Contacting the firm does not create an attorney–client relationship.', 'counsel' ); ?>
							</p>
						</div>
					<?php endif; ?>

					<a class="counsel-arrow-link" href="<?php echo esc_url( get_post_type_archive_link( 'firm' ) ); ?>">
						<?php esc_html_e( 'Back to the directory', 'counsel' ); ?>
						<span aria-hidden="true">&rarr;</span>
					</a>
				</div>
			</aside>

		</div><!-- .counsel-firm__layout -->

	</main>
	<?php
endwhile;

get_footer();
