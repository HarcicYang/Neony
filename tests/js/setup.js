/**
 * After each test: wipe the body and drop Neony globals.  The runtime
 * globals (buildNode / NeonyEngine) are intentionally NOT deleted —
 * eval'd declarations live in the shared variable environment and
 * class methods resolve them at call time.
 */

import { afterEach } from "vitest";

afterEach(() => {
  document.body.innerHTML = "";
  delete window.neony;
  delete window.lumiview;
  delete window.__neony__;
});
