<?php
/**
 * Central home for every legal disclaimer string used across Counsel.
 *
 * Disclosure is a brand and legal requirement. Keeping these strings in one
 * place means compliance can review and update them without hunting through
 * templates. Default text is filterable and several strings can be overridden
 * from the Customizer (see inc/customizer.php).
 *
 * NOTE: These are sensible starting points, not a substitute for a compliance
 * review. See README.md.
 *
 * @package Counsel
 */

defined( 'ABSPATH' ) || exit;

/**
 * "Not legal advice" — for advice columns and educational guides.
 *
 * @return string
 */
function counsel_disclaimer_not_legal_advice() {
	$default = __( 'This is general educational information, not legal advice, and reading it doesn\'t create an attorney–client relationship. Laws and deadlines vary by state and change over time. For advice about your specific situation, talk to a licensed attorney in your state.', 'counsel' );

	/**
	 * Filter the "not legal advice" disclaimer text.
	 *
	 * @param string $default The default disclaimer text.
	 */
	return apply_filters( 'counsel_disclaimer_not_legal_advice', $default );
}

/**
 * Results disclaimer — placed immediately under any reported case results.
 *
 * @return string
 */
function counsel_disclaimer_results() {
	$default = __( 'Past results do not guarantee future outcomes. Each case is different.', 'counsel' );

	/** This filter is documented in inc/disclaimers.php */
	return apply_filters( 'counsel_disclaimer_results', $default );
}

/**
 * Advertising / sponsored disclosure.
 *
 * @return string
 */
function counsel_disclaimer_advertising() {
	$default = __( 'Some content on Counsel is sponsored and is clearly labeled. Sponsorship does not influence our independent profiles, reviews, or "best of" selections. Featured attorney content is attorney advertising; the featured firm shares responsibility for the accuracy and compliance of claims about its own services.', 'counsel' );

	/** This filter is documented in inc/disclaimers.php */
	return apply_filters( 'counsel_disclaimer_advertising', $default );
}

/**
 * Firm-profile-level disclaimer, appended to the bottom of every profile.
 *
 * @return string
 */
function counsel_disclaimer_profile() {
	$default = __( 'This profile is an independent editorial overview compiled by Counsel and is not legal advice, an endorsement, or a referral. Counsel is not a law firm. Details such as fees, languages, and consultation policies are provided by the firm or gathered from public sources and may change; confirm directly with the firm. Some profiles are sponsored and are clearly labeled as such.', 'counsel' );

	/** This filter is documented in inc/disclaimers.php */
	return apply_filters( 'counsel_disclaimer_profile', $default );
}

/**
 * Roundup ("Best Of") disclaimer.
 *
 * @return string
 */
function counsel_disclaimer_roundup() {
	$default = __( 'Counsel\'s "Best Of" selections are made independently by our editorial team using the methodology described above. Placement on this list cannot be purchased and is never influenced by sponsorship. Sponsored firms, where present, are clearly labeled.', 'counsel' );

	/** This filter is documented in inc/disclaimers.php */
	return apply_filters( 'counsel_disclaimer_roundup', $default );
}

/**
 * Global footer disclaimer line.
 *
 * Can be overridden from the Customizer (Counsel Settings → Footer disclaimer).
 *
 * @return string
 */
function counsel_disclaimer_footer() {
	$default = __( 'Counsel is an independent legal-information and directory service. It is not a law firm and does not provide legal advice or referrals in exchange for fees from consumers. Information on this site is for general educational purposes and is not a substitute for advice from a licensed attorney in your state.', 'counsel' );

	$custom = get_theme_mod( 'counsel_footer_disclaimer', '' );
	$text   = ( is_string( $custom ) && '' !== trim( $custom ) ) ? $custom : $default;

	/** This filter is documented in inc/disclaimers.php */
	return apply_filters( 'counsel_disclaimer_footer', $text );
}

/**
 * The editor's note explaining that Ask Counsel questions are composites.
 *
 * @return string
 */
function counsel_disclaimer_composite() {
	$default = __( 'Editor\'s note: Ask Counsel questions are composites drawn from common situations readers write to us about. They are not the words of any single individual, and no detail identifies a real person.', 'counsel' );

	/** This filter is documented in inc/disclaimers.php */
	return apply_filters( 'counsel_disclaimer_composite', $default );
}
