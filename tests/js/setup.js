/**
 * After each test: wipe the body and drop Neony globals.  The runtime
 * globals (buildNode / NeonyEngine) are intentionally NOT deleted —
 * eval'd declarations live in the shared variable environment and
 * class methods resolve them at call time.
 */

import { afterEach } from "vitest";

// jsdom's rAF (when present) is async via setTimeout — run callbacks
// synchronously instead so scroll-indicator paths that schedule rAF are
// deterministic in tests.  Tests that need control spy on the global
// before use (see the scroll-indicator drag test).
globalThis.requestAnimationFrame = (cb) => {
  cb();
  return 1;
};
globalThis.cancelAnimationFrame = () => {};

afterEach(() => {
  document.body.innerHTML = "";
  delete window.neony;
  delete window.lumiview;
  delete window.__neony__;
});
