/**
 * Unit tests for index.js — bootstrap and event delegation.
 *
 * Loading order matters: the IIFE skips event-delegation setup when
 * `window.lumiview` is missing, so the mock must exist BEFORE
 * loadRuntime() runs — and the runtime loads ONCE at module scope,
 * since its capture-phase listeners on `document` must not be
 * duplicated per test.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import { loadRuntime } from "./load.js";

// lumiview must exist before the runtime loads (see docstring).
const listen = vi.fn();
window.lumiview = { listen, invoke: vi.fn(), window: {} };

const { neony } = loadRuntime();

function mountTree(node) {
  neony.engine.mount({ rev: 1, ops: [{ op: "create", key: node.key, node }] });
  return neony.engine;
}

describe("bootstrap", () => {
  it("exposes window.neony with engine, mount, and applyMessage", () => {
    expect(neony).toBeDefined();
    expect(neony.engine).toBeDefined();
    expect(typeof neony.mount).toBe("function");
    expect(typeof neony.applyMessage).toBe("function");
  });

  it("subscribes to the neony:patch event", () => {
    expect(listen).toHaveBeenCalledWith("neony:patch", expect.any(Function));
  });

  it("applies patch messages received via lumiview.listen", () => {
    mountTree({ key: "root", tag: "div" });
    const handler = listen.mock.calls.find(([name]) => name === "neony:patch")[1];
    handler({ rev: 2, ops: [{ op: "set_text", key: "root", text: "via listen" }] });
    expect(document.querySelector("[data-neony-key='root']").textContent).toBe("via listen");
  });
});

describe("event delegation", () => {
  let invoke;
  let win;

  beforeEach(() => {
    win = { minimize: vi.fn(), toggleMaximize: vi.fn(), close: vi.fn() };
    invoke = vi.fn(() => Promise.resolve());
    window.lumiview = { listen, invoke, window: win };
  });

  it("forwards click events with key, type, and null value", () => {
    mountTree({ key: "btn", tag: "button", text: "click me" });
    const el = document.querySelector("[data-neony-key='btn']");
    el.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
    expect(invoke).toHaveBeenCalledWith("neony.event", { key: "btn", event_type: "click", value: null });
  });

  it("captures input element values", () => {
    mountTree({ key: "inp", tag: "input", attrs: { type: "text" } });
    const el = document.querySelector("[data-neony-key='inp']");
    el.value = "hello";
    el.dispatchEvent(new window.Event("input", { bubbles: true }));
    expect(invoke).toHaveBeenCalledWith("neony.event", { key: "inp", event_type: "input", value: "hello" });
  });

  it("captures checkbox checked state (not the 'on' value)", () => {
    mountTree({ key: "cb", tag: "input", attrs: { type: "checkbox" } });
    const el = document.querySelector("[data-neony-key='cb']");
    el.checked = true;
    el.dispatchEvent(new window.Event("change", { bubbles: true }));
    expect(invoke).toHaveBeenCalledWith("neony.event", { key: "cb", event_type: "change", value: true });
  });

  it("captures keydown key names", () => {
    mountTree({ key: "inp", tag: "input" });
    const el = document.querySelector("[data-neony-key='inp']");
    el.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    expect(invoke).toHaveBeenCalledWith("neony.event", { key: "inp", event_type: "keydown", value: "Enter" });
  });

  it("traces events to the nearest keyed ancestor", () => {
    // The JS deliberately forwards the INNERMOST keyed element. If that
    // element has no handler, Python-side opt-in bubbling (`_bubble_events`)
    // routes the event to a handler-bearing ancestor instead.
    mountTree({
      key: "card",
      tag: "div",
      children: [{ key: "inner", tag: "span", text: "x" }],
    });
    const inner = document.querySelector("[data-neony-key='inner']");
    inner.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
    expect(invoke).toHaveBeenCalledWith("neony.event", { key: "inner", event_type: "click", value: null });
  });

  it("ignores events on elements without a key", () => {
    const plain = document.createElement("div");
    document.body.appendChild(plain);
    plain.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
    expect(invoke).not.toHaveBeenCalled();
  });

  it("routes window-control actions through lumiview.window on click", () => {
    mountTree({ key: "close-btn", tag: "button", attrs: { "data-window-action": "close" } });
    const el = document.querySelector("[data-neony-key='close-btn']");
    el.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
    expect(win.close).toHaveBeenCalled();
    // ...and the normal Neony event still fires for user callbacks
    expect(invoke).toHaveBeenCalledWith("neony.event", { key: "close-btn", event_type: "click", value: null });
  });

  it("does NOT route window-control actions on non-click events", () => {
    mountTree({ key: "close-btn", tag: "button", attrs: { "data-window-action": "close" } });
    const el = document.querySelector("[data-neony-key='close-btn']");
    el.dispatchEvent(new window.MouseEvent("mouseover", { bubbles: true }));
    expect(win.close).not.toHaveBeenCalled();
  });

  it("does not throw when a window-control action is missing from lumiview.window", () => {
    mountTree({ key: "btn", tag: "button", attrs: { "data-window-action": "nonexistent" } });
    const el = document.querySelector("[data-neony-key='btn']");
    expect(() => el.dispatchEvent(new window.MouseEvent("click", { bubbles: true }))).not.toThrow();
  });
});
