/**
 * Kamino Website - Main JavaScript Entry Point
 * Modern vanilla JavaScript implementation
 */

import { initClipboard } from './modules/clipboard.js';
import { initScrollAnimations } from './modules/scroll.js';
import { initVideoControls } from './modules/video.js';
import { initNavigation } from './modules/navigation.js';

/**
 * Initialize all modules when DOM is ready
 */
function init() {
  console.log('Kamino website initializing...');

  try {
    // Initialize clipboard functionality
    initClipboard();
    console.log('✓ Clipboard module initialized');

    // Initialize scroll animations
    initScrollAnimations();
    console.log('✓ Scroll animations initialized');

    // Initialize video controls
    initVideoControls();
    console.log('✓ Video controls initialized');

    // Initialize navigation
    initNavigation();
    console.log('✓ Navigation initialized');
    console.log('Kamino website ready!');
  } catch (error) {
    console.error('Error initializing website:', error);
  }
}

/**
 * Wait for DOM to be fully loaded
 */
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  // DOM is already loaded
  init();
}

/**
 * Optional: Log performance metrics
 */
window.addEventListener('load', () => {
  if ('performance' in window) {
    const perfData = window.performance.timing;
    const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
    console.log(`Page load time: ${pageLoadTime}ms`);
  }
});
