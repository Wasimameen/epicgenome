/**
 * Counsel — front-end enhancements.
 *
 * Vanilla JS, no jQuery. Progressive enhancement only: everything works
 * without JS; this just improves the experience.
 *
 * - Mobile menu toggle (accessible, keyboard- and Escape-friendly).
 * - Submenu toggles for keyboard/touch.
 * - Search form: prevent empty submits from doing nothing useful.
 *
 * @package Counsel
 */
( function () {
	'use strict';

	document.addEventListener( 'DOMContentLoaded', function () {
		initMenuToggle();
		initSubmenus();
		initSearchEnhancements();
	} );

	/**
	 * Mobile menu toggle.
	 */
	function initMenuToggle() {
		var toggle = document.querySelector( '.menu-toggle' );
		var nav = document.getElementById( 'site-navigation' );

		if ( ! toggle || ! nav ) {
			return;
		}

		toggle.addEventListener( 'click', function () {
			var isOpen = toggle.getAttribute( 'aria-expanded' ) === 'true';
			setMenu( ! isOpen );
		} );

		// Close on Escape.
		document.addEventListener( 'keydown', function ( e ) {
			if ( e.key === 'Escape' && toggle.getAttribute( 'aria-expanded' ) === 'true' ) {
				setMenu( false );
				toggle.focus();
			}
		} );

		// Close when a link is followed (mobile).
		nav.addEventListener( 'click', function ( e ) {
			if ( e.target.closest( 'a' ) && window.matchMedia( '(max-width: 860px)' ).matches ) {
				setMenu( false );
			}
		} );

		function setMenu( open ) {
			toggle.setAttribute( 'aria-expanded', open ? 'true' : 'false' );
			toggle.setAttribute(
				'aria-label',
				open ? counselLabel( 'Close menu' ) : counselLabel( 'Open menu' )
			);
			document.body.classList.toggle( 'menu-open', open );
			nav.classList.toggle( 'is-open', open );
		}
	}

	/**
	 * Submenu expand/collapse for keyboard and touch users.
	 */
	function initSubmenus() {
		var parents = document.querySelectorAll( '.main-navigation .menu-item-has-children' );

		Array.prototype.forEach.call( parents, function ( parent ) {
			var link = parent.querySelector( 'a' );
			var submenu = parent.querySelector( '.sub-menu' );

			if ( ! link || ! submenu ) {
				return;
			}

			var btn = document.createElement( 'button' );
			btn.className = 'submenu-toggle';
			btn.setAttribute( 'aria-expanded', 'false' );
			btn.setAttribute( 'aria-label', counselLabel( 'Expand submenu' ) );
			btn.innerHTML = '<span aria-hidden="true">+</span>';

			btn.addEventListener( 'click', function () {
				var open = btn.getAttribute( 'aria-expanded' ) === 'true';
				btn.setAttribute( 'aria-expanded', open ? 'false' : 'true' );
				parent.classList.toggle( 'submenu-open', ! open );
			} );

			link.parentNode.insertBefore( btn, link.nextSibling );
		} );
	}

	/**
	 * Light search-form UX: trim and avoid pointless navigation.
	 */
	function initSearchEnhancements() {
		var forms = document.querySelectorAll( '.counsel-search' );

		Array.prototype.forEach.call( forms, function ( form ) {
			form.addEventListener( 'submit', function () {
				// Remove empty selects so the results URL stays clean.
				Array.prototype.forEach.call( form.querySelectorAll( 'select' ), function ( sel ) {
					if ( sel.value === '' ) {
						sel.disabled = true;
					}
				} );
			} );
		} );
	}

	/**
	 * Tiny i18n shim — returns the string as-is (placeholder for wp_localize).
	 *
	 * @param {string} str String.
	 * @return {string} String.
	 */
	function counselLabel( str ) {
		return str;
	}
} )();
