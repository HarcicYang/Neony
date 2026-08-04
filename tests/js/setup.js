/**
 * Global test hygiene for the Neony JS runtime tests.
 *
 * After each test: wipe the body and drop the Neony state globals so
 * every test starts clean.
 *
 * NOTE: the runtime globals (buildNode / unregisterSubtree /
 * NeonyEngine) are intentionally NOT deleted.  eval'd function
 * declarations live in the shared global variable environment, and
 * class methods resolve them at CALL time — deleting them would break
 * engines created by a module-level load (see index.test.js).
 */

import { afterEach } from "vitest";

afterEach(() => {
  document.body.innerHTML = "";
  delete window.neony;
  delete window.lumiview;
  delete window.__neony__;
});
