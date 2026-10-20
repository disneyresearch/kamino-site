/**
 * Syntax Highlighting Module
 * Applies highlight.js (loaded from CDN in index.html) to code blocks
 */

export function initHighlighting() {
  if (!window.hljs) {
    console.warn('highlight.js not available; code blocks are left unhighlighted');
    return;
  }

  document.querySelectorAll('pre code[class*="language-"]').forEach(block => {
    window.hljs.highlightElement(block);
  });
}
