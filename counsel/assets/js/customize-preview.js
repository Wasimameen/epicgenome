/**
 * Counsel — Customizer live preview.
 *
 * Binds postMessage settings so colour and text edits update instantly in the
 * preview without a full refresh. Structural settings (fonts, layout, toggles)
 * use 'refresh' transport and are handled server-side.
 *
 * @package Counsel
 */
( function ( $ ) {
	'use strict';

	if ( typeof wp === 'undefined' || ! wp.customize ) {
		return;
	}

	var root = document.documentElement;

	/**
	 * Bind a colour setting to a CSS custom property.
	 *
	 * @param {string} settingId Setting id.
	 * @param {string} cssVar    CSS variable name.
	 */
	function bindColor( settingId, cssVar ) {
		wp.customize( settingId, function ( value ) {
			value.bind( function ( to ) {
				if ( to ) {
					root.style.setProperty( cssVar, to );
				}
			} );
		} );
	}

	/**
	 * Bind a text setting to an element's text content.
	 *
	 * @param {string} settingId Setting id.
	 * @param {string} selector  CSS selector.
	 */
	function bindText( settingId, selector ) {
		wp.customize( settingId, function ( value ) {
			value.bind( function ( to ) {
				document.querySelectorAll( selector ).forEach( function ( el ) {
					el.textContent = to;
				} );
			} );
		} );
	}

	// Colours.
	bindColor( 'counsel_color_oxblood', '--oxblood' );
	bindColor( 'counsel_color_brass', '--brass' );
	bindColor( 'counsel_color_parchment', '--parchment' );
	bindColor( 'counsel_color_ink', '--ink' );
	bindColor( 'counsel_color_paper', '--paper' );
	bindColor( 'counsel_color_muted', '--muted' );
	bindColor( 'counsel_color_line', '--line' );
	bindColor( 'counsel_color_sponsored', '--sponsored' );

	// Hero + homepage + footer text.
	bindText( 'counsel_hero_kicker', '.counsel-hero__kicker' );
	bindText( 'counsel_hero_title', '.counsel-hero__title' );
	bindText( 'counsel_hero_lede', '.counsel-hero__lede' );
	bindText( 'counsel_hero_trust', '.counsel-hero__trust' );
	bindText( 'counsel_closing_title', '.counsel-closing-cta__title' );
	bindText( 'counsel_closing_lede', '.counsel-closing-cta__lede' );
	bindText( 'counsel_footer_tagline', '.site-footer__tagline' );
	bindText( 'counsel_header_cta_label', '.site-header__cta .counsel-btn' );

} )( window.jQuery );
