/**
 * Unit tests for builder.js — buildNode() and unregisterSubtree().
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import { loadRuntime } from "./load.js";

let rt;

beforeEach(() => {
  rt = loadRuntime(["builder.js"]);
});

describe("buildNode", () => {
  it("creates an element with the right tag and key attribute", () => {
    const registry = new Map();
    const el = rt.buildNode({ key: "a", tag: "div" }, registry);
    expect(el.tagName).toBe("DIV");
    expect(el.getAttribute("data-neony-key")).toBe("a");
    expect(registry.get("a")).toBe(el);
  });

  it("applies styles via CSSOM", () => {
    const el = rt.buildNode(
      { key: "s", tag: "div", styles: { color: "red", "font-size": "16px" } },
      new Map(),
    );
    expect(el.style.color).toBe("red");
    expect(el.style.fontSize).toBe("16px");
  });

  it("adds the -webkit- prefix for backdrop-filter", () => {
    // jsdom's CSSStyleDeclaration drops unknown properties entirely, so
    // assert the writes themselves (on the prototype — buildNode creates
    // its own element): the source must call setProperty for both the
    // standard and the -webkit- prefixed variant.
    const setProperty = vi.spyOn(CSSStyleDeclaration.prototype, "setProperty");
    rt.buildNode({ key: "b", tag: "div", styles: { "backdrop-filter": "blur(8px)" } }, new Map());
    expect(setProperty).toHaveBeenCalledWith("backdrop-filter", "blur(8px)");
    expect(setProperty).toHaveBeenCalledWith("-webkit-backdrop-filter", "blur(8px)");
  });

  it("adds -webkit- and -moz- prefixes for user-select", () => {
    const setProperty = vi.spyOn(CSSStyleDeclaration.prototype, "setProperty");
    rt.buildNode({ key: "u", tag: "div", styles: { "user-select": "none" } }, new Map());
    expect(setProperty).toHaveBeenCalledWith("user-select", "none");
    expect(setProperty).toHaveBeenCalledWith("-webkit-user-select", "none");
    expect(setProperty).toHaveBeenCalledWith("-moz-user-select", "none");
  });

  it("applies attributes (empty string = boolean presence)", () => {
    const el = rt.buildNode(
      { key: "a", tag: "input", attrs: { type: "checkbox", disabled: "" } },
      new Map(),
    );
    expect(el.getAttribute("type")).toBe("checkbox");
    expect(el.hasAttribute("disabled")).toBe(true);
  });

  it("sets text content when present", () => {
    const el = rt.buildNode({ key: "t", tag: "span", text: "hello" }, new Map());
    expect(el.textContent).toBe("hello");
  });

  it("leaves text content empty when absent", () => {
    const el = rt.buildNode({ key: "t", tag: "span" }, new Map());
    expect(el.textContent).toBe("");
  });

  it("builds children recursively and registers every key", () => {
    const registry = new Map();
    const el = rt.buildNode(
      {
        key: "root",
        tag: "div",
        children: [
          { key: "a", tag: "span", text: "A" },
          { key: "b", tag: "span", children: [{ key: "c", tag: "i" }] },
        ],
      },
      registry,
    );
    expect(el.children.length).toBe(2);
    expect(registry.has("a")).toBe(true);
    expect(registry.has("b")).toBe(true);
    expect(registry.has("c")).toBe(true);
    expect(registry.get("c").parentElement).toBe(registry.get("b"));
  });
});

describe("unregisterSubtree", () => {
  it("removes the whole subtree from the registry", () => {
    const registry = new Map();
    rt.buildNode(
      {
        key: "root",
        tag: "div",
        children: [{ key: "a", tag: "span", children: [{ key: "b", tag: "i" }] }],
      },
      registry,
    );
    expect(registry.size).toBe(3);
    rt.unregisterSubtree(registry.get("root"), registry);
    expect(registry.size).toBe(0);
  });

  it("is a no-op for elements without a key", () => {
    const registry = new Map();
    const el = document.createElement("div");
    rt.unregisterSubtree(el, registry);
    expect(registry.size).toBe(0);
  });
});
