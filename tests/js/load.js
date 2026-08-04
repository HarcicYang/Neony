/**
 * Load the Neony JS runtime sources into the jsdom window.
 *
 * A class declaration (`NeonyEngine`) is a lexical binding, not a window
 * property, so an exposure line is appended in the same eval scope:
 * `window.__neony__ = { buildNode, unregisterSubtree, NeonyEngine, neony: window.neony }`
 * (`window.neony` is a real property set by the index.js IIFE).
 */

import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SRC_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../src/neony/javascript");
const FILES = ["builder.js", "engine.js", "index.js"];

function sourceFor(names) {
  return names.map((n) => readFileSync(path.join(SRC_DIR, n), "utf-8")).join("\n");
}

/**
 * Evaluate the given runtime files in the window context.
 *
 * @param {string[]} names - subset of FILES to load, in dependency order
 * @returns {{buildNode: Function, unregisterSubtree: Function, NeonyEngine: Function, neony: object}}
 */
export function loadRuntime(names = FILES) {
  // typeof guards: a subset load (e.g. ["builder.js"]) must not fail on
  // bindings that belong to files not loaded in this eval.
  const exposure =
    "\n;window.__neony__ = { " +
    "buildNode: typeof buildNode !== 'undefined' ? buildNode : undefined, " +
    "unregisterSubtree: typeof unregisterSubtree !== 'undefined' ? unregisterSubtree : undefined, " +
    "NeonyEngine: typeof NeonyEngine !== 'undefined' ? NeonyEngine : undefined, " +
    "neony: window.neony };";
  window.eval(sourceFor(names) + exposure);
  return window.__neony__;
}
