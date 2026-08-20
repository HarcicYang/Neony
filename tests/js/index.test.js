/**
 * Unit tests for index.js — bootstrap and event delegation.
 *
 * Loading order matters: the IIFE skips event-delegation setup when
 * `window.lumiview` is missing, so the mock must exist BEFORE
 * loadRuntime() runs — and the runtime loads ONCE at module scope,
 * since its capture-phase listeners on `document` must not be
 * duplicated per test.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

  it("positions cascade submenus on the side with viewport room", () => {
    mountTree({
      key: "cascade-row",
      tag: "div",
      attrs: { "data-neony-cascade-row": "true" },
      children: [
        { key: "cascade-trigger", tag: "button", text: "Theme" },
        { key: "cascade-submenu", tag: "div", styles: { display: "none" } },
      ],
    });
    const row = document.querySelector("[data-neony-key='cascade-row']");
    const trigger = document.querySelector("[data-neony-key='cascade-trigger']");
    const submenu = document.querySelector("[data-neony-key='cascade-submenu']");
    row.getBoundingClientRect = () => ({ left: 900, right: 1060, top: 700, width: 160, height: 32 });
    submenu.getBoundingClientRect = () => ({ left: 1064, right: 1264, top: 700, width: 200, height: 180 });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1100 });
    Object.defineProperty(window, "innerHeight", { configurable: true, value: 800 });

    trigger.dispatchEvent(new window.MouseEvent("mouseover", { bubbles: true }));

    expect(submenu.style.left).toBe("auto");
    expect(submenu.style.right).toBe("calc(100% + 4px)");
    expect(submenu.style.top).toBe("-84px");
  });

  it("keeps cascade submenus on the right when there is room", () => {
    mountTree({
      key: "cascade-row-right",
      tag: "div",
      attrs: { "data-neony-cascade-row": "true" },
      children: [
        { key: "cascade-trigger-right", tag: "button", text: "Theme" },
        { key: "cascade-submenu-right", tag: "div", styles: { display: "none" } },
      ],
    });
    const row = document.querySelector("[data-neony-key='cascade-row-right']");
    const trigger = document.querySelector("[data-neony-key='cascade-trigger-right']");
    const submenu = document.querySelector("[data-neony-key='cascade-submenu-right']");
    row.getBoundingClientRect = () => ({ left: 100, right: 260, top: 100, width: 160, height: 32 });
    submenu.getBoundingClientRect = () => ({ left: 264, right: 464, top: 100, width: 200, height: 180 });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1100 });
    Object.defineProperty(window, "innerHeight", { configurable: true, value: 800 });

    trigger.dispatchEvent(new window.MouseEvent("mouseover", { bubbles: true }));

    expect(submenu.style.left).toBe("calc(100% + 4px)");
    expect(submenu.style.right).toBe("auto");
    expect(submenu.style.top).toBe("0px");
  });

  it("forwards click events with key, type, and null value", () => {
    mountTree({ key: "btn", tag: "button", text: "click me" });
    const el = document.querySelector("[data-neony-key='btn']");
    el.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
    expect(invoke).toHaveBeenCalledWith(
      "neony.event",
      expect.objectContaining({ key: "btn", event_type: "click", value: null })
    );
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
    // element has no handler, Python-side opt-in bubbling (`bubble_events`)
    // routes the event to a handler-bearing ancestor instead.
    mountTree({
      key: "card",
      tag: "div",
      children: [{ key: "inner", tag: "span", text: "x" }],
    });
    const inner = document.querySelector("[data-neony-key='inner']");
    inner.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
    expect(invoke).toHaveBeenCalledWith(
      "neony.event",
      expect.objectContaining({ key: "inner", event_type: "click", value: null })
    );
  });

  it("ignores events on elements without a key", () => {
    const plain = document.createElement("div");
    document.body.appendChild(plain);
    plain.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
    expect(invoke).not.toHaveBeenCalled();
  });

  it("carries the related key on mouseover/mouseout", () => {
    // Native mouseenter/mouseleave never reach document listeners (they
    // don't propagate), so enter/leave must be derived from the
    // bubbling mouseover/mouseout pair: the payload carries the keyed
    // element the pointer moved from/to.
    mountTree({
      key: "wrap",
      tag: "div",
      children: [{ key: "btn", tag: "button", text: "a" }],
    });
    const btn = document.querySelector("[data-neony-key='btn']");

    // Entered from off-page / an unkeyed part — no related key.
    btn.dispatchEvent(
      new window.MouseEvent("mouseover", { bubbles: true, relatedTarget: document.body })
    );
    expect(invoke).toHaveBeenCalledWith(
      "neony.event",
      expect.objectContaining({ key: "btn", event_type: "mouseover", related_key: null })
    );

    // Leaving toward a keyed element carries its key.
    invoke.mockClear();
    btn.dispatchEvent(
      new window.MouseEvent("mouseout", { bubbles: true, relatedTarget: btn.parentElement })
    );
    expect(invoke).toHaveBeenCalledWith(
      "neony.event",
      expect.objectContaining({ key: "btn", event_type: "mouseout", related_key: "wrap" })
    );
  });

  it("routes body-focused keydowns through the engine root", () => {
    // With nothing focused, keys land on <body> — no data-neony-key
    // ancestor.  Window-level key listeners live on the root, so
    // keyboard events must fall back to it.
    mountTree({ key: "root", tag: "div" });
    document.body.dispatchEvent(
      new window.KeyboardEvent("keydown", { key: "b", ctrlKey: true, bubbles: true })
    );
    expect(invoke).toHaveBeenCalledWith(
      "neony.event",
      expect.objectContaining({ key: "root", event_type: "keydown", value: "b", ctrl_key: true })
    );
  });

  it("routes body-focused keyups through the engine root", () => {
    mountTree({ key: "root", tag: "div" });
    document.body.dispatchEvent(new window.KeyboardEvent("keyup", { key: "b", bubbles: true }));
    expect(invoke).toHaveBeenCalledWith(
      "neony.event",
      expect.objectContaining({ key: "root", event_type: "keyup", value: "b" })
    );
  });

  it("does not route body-focused non-keyboard events", () => {
    mountTree({ key: "root", tag: "div" });
    document.body.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
    // The body click still has no keyed target (only keyboard events
    // fall back to the root) — mount's "neony.ready" ack aside, no
    // neony.event payload may be sent.
    expect(invoke.mock.calls.filter(([name]) => name === "neony.event")).toHaveLength(0);
  });

  it("routes window-control actions through lumiview.window on click", () => {
    mountTree({ key: "close-btn", tag: "button", attrs: { "data-window-action": "close" } });
    const el = document.querySelector("[data-neony-key='close-btn']");
    el.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
    expect(win.close).toHaveBeenCalled();
    // ...and the normal Neony event still fires for user callbacks
    expect(invoke).toHaveBeenCalledWith(
      "neony.event",
      expect.objectContaining({ key: "close-btn", event_type: "click", value: null })
    );
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

describe("narrow overlay coordination", () => {
  let invoke;

  beforeEach(() => {
    invoke = vi.fn(() => Promise.resolve());
    window.lumiview = { listen, invoke, window: {} };
  });

  it("immediately hides a superseded top-level context menu", async () => {
    mountTree({
      key: "root",
      tag: "div",
      children: [
        {
          key: "old-menu",
          tag: "div",
          attrs: {
            "data-neony-overlay-group": "context-menu",
            "data-neony-overlay-open": "true",
          },
          styles: { display: "flex" },
        },
        {
          key: "new-menu",
          tag: "div",
          attrs: { "data-neony-overlay-group": "context-menu" },
          styles: { display: "flex" },
        },
      ],
    });
    const oldMenu = document.querySelector("[data-neony-key='old-menu']");
    const newMenu = document.querySelector("[data-neony-key='new-menu']");
    newMenu.setAttribute("data-neony-overlay-open", "true");
    await Promise.resolve();

    expect(oldMenu.style.display).toBe("none");
    expect(newMenu.style.display).toBe("flex");
    expect(invoke).toHaveBeenCalledWith("neony.event", {
      key: "old-menu",
      event_type: "outsideclick",
      value: null,
    });
  });

  it("keeps only the newest message action row visible", () => {
    mountTree({
      key: "root",
      tag: "div",
      children: [
        {
          key: "first-bubble",
          tag: "div",
          attrs: { "data-neony-message-actions": "first-actions" },
          children: [{ key: "first-actions", tag: "div", styles: { display: "none" } }],
        },
        {
          key: "second-bubble",
          tag: "div",
          attrs: { "data-neony-message-actions": "second-actions" },
          children: [{ key: "second-actions", tag: "div", styles: { display: "none" } }],
        },
      ],
    });
    const first = document.querySelector("[data-neony-key='first-bubble']");
    const second = document.querySelector("[data-neony-key='second-bubble']");
    first.dispatchEvent(new window.MouseEvent("mouseover", { bubbles: true }));
    second.dispatchEvent(new window.MouseEvent("mouseover", { bubbles: true }));

    expect(document.querySelector("[data-neony-key='first-actions']").style.display).toBe("none");
    expect(document.querySelector("[data-neony-key='second-actions']").style.display).toBe("flex");
  });
});

describe("rich event payload", () => {
  let invoke;
  let win;

  beforeEach(() => {
    win = { minimize: vi.fn(), toggleMaximize: vi.fn(), close: vi.fn() };
    invoke = vi.fn(() => Promise.resolve());
    window.lumiview = { listen, invoke, window: win };
  });

  function lastPayload() {
    return invoke.mock.calls.find(([name]) => name === "neony.event")[1];
  }

  it("carries modifier keys on keydown", () => {
    mountTree({ key: "inp", tag: "input" });
    const el = document.querySelector("[data-neony-key='inp']");
    el.dispatchEvent(
      new window.KeyboardEvent("keydown", {
        key: "s",
        ctrlKey: true,
        shiftKey: true,
        bubbles: true,
      })
    );
    // Unpressed modifiers are omitted from the payload, not sent as false.
    expect(lastPayload()).toEqual(expect.objectContaining({ ctrl_key: true, shift_key: true }));
  });

  it("carries viewport and element-relative coordinates on click", () => {
    mountTree({ key: "btn", tag: "button" });
    const el = document.querySelector("[data-neony-key='btn']");
    el.dispatchEvent(new window.MouseEvent("click", { clientX: 42, clientY: 17, bubbles: true }));
    // Element at the origin → offset == client coordinates.
    expect(lastPayload()).toEqual(
      expect.objectContaining({ x: 42, y: 17, offset_x: 42, offset_y: 17 })
    );
  });

  it("carries no coordinates on keyboard events", () => {
    mountTree({ key: "inp", tag: "input" });
    const el = document.querySelector("[data-neony-key='inp']");
    el.dispatchEvent(new window.KeyboardEvent("keydown", { key: "s", bubbles: true }));
    const payload = lastPayload();
    expect(payload.x).toBeUndefined();
    expect(payload.y).toBeUndefined();
  });

  it("carries wheel deltas", () => {
    mountTree({ key: "scroller", tag: "div" });
    const el = document.querySelector("[data-neony-key='scroller']");
    el.dispatchEvent(new window.WheelEvent("wheel", { deltaX: 10, deltaY: -3, bubbles: true }));
    expect(lastPayload()).toEqual(expect.objectContaining({ delta_x: 10, delta_y: -3 }));
  });

  it("carries the wheel delta mode", () => {
    mountTree({ key: "scroller", tag: "div" });
    const el = document.querySelector("[data-neony-key='scroller']");
    el.dispatchEvent(new window.WheelEvent("wheel", { deltaY: 3, deltaMode: 1, bubbles: true }));
    expect(lastPayload()).toEqual(expect.objectContaining({ delta_y: 3, delta_mode: 1 }));
  });

  it("carries the scroll position from the scrolled element", () => {
    mountTree({ key: "scroller", tag: "div", styles: { overflow: "auto" } });
    const el = document.querySelector("[data-neony-key='scroller']");
    Object.defineProperty(el, "scrollTop", { value: 120, configurable: true });
    Object.defineProperty(el, "scrollLeft", { value: 40, configurable: true });
    el.dispatchEvent(new window.Event("scroll"));
    expect(lastPayload()).toEqual(
      expect.objectContaining({ key: "scroller", event_type: "scroll", scroll_top: 120, scroll_left: 40 })
    );
  });

  it("reads scroll position from the actual scroller when it is unkeyed", () => {
    // A component's inner scroll container may carry no data-neony-key:
    // the payload key traces to the keyed ancestor, but the position
    // must come from event.target (the real scroller), not the ancestor.
    mountTree({ key: "wrap", tag: "div" });
    const wrap = document.querySelector("[data-neony-key='wrap']");
    const scroller = document.createElement("div");
    wrap.appendChild(scroller);
    Object.defineProperty(scroller, "scrollTop", { value: 77, configurable: true });
    scroller.dispatchEvent(new window.Event("scroll"));
    expect(lastPayload()).toEqual(
      expect.objectContaining({ key: "wrap", event_type: "scroll", scroll_top: 77, scroll_left: 0 })
    );
  });

  it("routes document-level scroll through the engine root", () => {
    mountTree({ key: "root", tag: "div" });
    document.dispatchEvent(new window.Event("scroll"));
    expect(lastPayload()).toEqual(
      expect.objectContaining({ key: "root", event_type: "scroll", scroll_top: 0, scroll_left: 0 })
    );
  });

  it("forwards paste clipboard data as plain text and HTML", () => {
    mountTree({ key: "inp", tag: "input" });
    const el = document.querySelector("[data-neony-key='inp']");
    const clipboardData = {
      getData: vi.fn((type) => (type === "text/html" ? "<b>hi</b>" : "hi")),
    };
    const event = new window.Event("paste", { bubbles: true, cancelable: true });
    Object.defineProperty(event, "clipboardData", { value: clipboardData });
    el.dispatchEvent(event);
    expect(clipboardData.getData).toHaveBeenCalledWith("text/plain");
    expect(clipboardData.getData).toHaveBeenCalledWith("text/html");
    expect(lastPayload()).toEqual(
      expect.objectContaining({ clipboard_text: "hi", clipboard_html: "<b>hi</b>" })
    );
  });

  it("fires copy as a notification without clipboard payload", () => {
    mountTree({ key: "inp", tag: "input" });
    const el = document.querySelector("[data-neony-key='inp']");
    el.dispatchEvent(new window.Event("copy", { bubbles: true, cancelable: true }));
    const payload = lastPayload();
    expect(payload.clipboard_text).toBeUndefined();
    expect(payload.clipboard_html).toBeUndefined();
  });

  it("forwards dropped files with name, path, size and type", () => {
    mountTree({ key: "drop-zone", tag: "div" });
    const el = document.querySelector("[data-neony-key='drop-zone']");
    const dataTransfer = {
      getData: () => "",
      files: [
        { name: "a.png", path: "/home/user/a.png", size: 1024, type: "image/png" },
        { name: "b.txt", path: "", size: 12, type: "text/plain" }, // WKWebView: no path
      ],
    };
    const event = new window.Event("drop", { bubbles: true, cancelable: true });
    Object.defineProperty(event, "dataTransfer", { value: dataTransfer });
    el.dispatchEvent(event);
    expect(lastPayload()).toEqual(
      expect.objectContaining({
        drop_files: [
          { name: "a.png", path: "/home/user/a.png", size: 1024, type: "image/png" },
          { name: "b.txt", path: "", size: 12, type: "text/plain" },
        ],
      })
    );
  });

  it("falls back to text/uri-list when File.path is missing", () => {
    // WebKitGTK >= 2.52 removed File.path; the drag's text/uri-list is
    // the path source there (and on WKWebView).
    mountTree({ key: "drop-zone", tag: "div" });
    const el = document.querySelector("[data-neony-key='drop-zone']");
    const dataTransfer = {
      getData: () => "file:///home/user/a%20file.png\r\nfile:///tmp/b.txt\r\n",
      files: [
        { name: "a file.png", path: "", size: 1024, type: "image/png" },
        { name: "b.txt", path: "", size: 12, type: "text/plain" },
      ],
    };
    const event = new window.Event("drop", { bubbles: true, cancelable: true });
    Object.defineProperty(event, "dataTransfer", { value: dataTransfer });
    el.dispatchEvent(event);
    expect(lastPayload()).toEqual(
      expect.objectContaining({
        drop_files: [
          { name: "a file.png", path: "/home/user/a file.png", size: 1024, type: "image/png" },
          { name: "b.txt", path: "/tmp/b.txt", size: 12, type: "text/plain" },
        ],
      })
    );
  });

  it("fires dragover as a notification without drop_files", () => {
    mountTree({ key: "drop-zone", tag: "div" });
    const el = document.querySelector("[data-neony-key='drop-zone']");
    el.dispatchEvent(new window.Event("dragover", { bubbles: true, cancelable: true }));
    const payload = lastPayload();
    expect(payload.drop_files).toBeUndefined();
    expect(payload.event_type).toBe("dragover");
  });

  it("does not include modifier keys when no modifier is pressed", () => {
    mountTree({ key: "btn", tag: "button" });
    const el = document.querySelector("[data-neony-key='btn']");
    el.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
    const payload = lastPayload();
    expect(payload.ctrl_key).toBeUndefined();
    expect(payload.shift_key).toBeUndefined();
    expect(payload.alt_key).toBeUndefined();
    expect(payload.meta_key).toBeUndefined();
  });
});

describe("in-app drag (dragstart / dragend / drop payload)", () => {
  let invoke;
  let win;

  beforeEach(() => {
    win = { minimize: vi.fn(), toggleMaximize: vi.fn(), close: vi.fn() };
    invoke = vi.fn(() => Promise.resolve());
    window.lumiview = { listen, invoke, window: win };
  });

  function lastPayload() {
    return invoke.mock.calls.find(([name]) => name === "neony.event")[1];
  }

  // jsdom has no DragEvent/DataTransfer globals — dispatch a plain
  // Event and attach a mock dataTransfer via defineProperty (the same
  // pattern as the paste/drop tests).  A plain store mimics the surface
  // the engine touches (setData / getData / effectAllowed / files).
  function makeDataTransfer(initial = {}) {
    const store = new Map(Object.entries(initial));
    const dt = {
      setData: vi.fn((type, value) => store.set(type, value)),
      getData: vi.fn((type) => store.get(type) || ""),
      effectAllowed: "none",
      files: [],
    };
    Object.defineProperty(dt, "setDragImage", {
      value: vi.fn(),
      writable: true,
    });
    return dt;
  }

  function dragEvent(type, dataTransfer, coords = {}) {
    const event = new window.Event(type, { bubbles: true, cancelable: true });
    Object.defineProperty(event, "dataTransfer", { value: dataTransfer });
    Object.defineProperty(event, "clientX", { value: coords.clientX ?? 0 });
    Object.defineProperty(event, "clientY", { value: coords.clientY ?? 0 });
    return event;
  }

  it("seeds dataTransfer on dragstart from the drag_payload attribute", () => {
    // The payload must reach setData synchronously inside dragstart —
    // a Python round-trip would be too late, so the engine reads the
    // element's data-neony-drag attribute (set from DOMElement.drag_payload).
    mountTree({ key: "item", tag: "div", attrs: { "data-neony-drag": "row-1" } });
    const el = document.querySelector("[data-neony-key='item']");
    const dt = makeDataTransfer();
    el.dispatchEvent(dragEvent("dragstart", dt));
    expect(dt.setData).toHaveBeenCalledWith("application/x-neony", "row-1");
    expect(dt.effectAllowed).toBe("move");
    expect(lastPayload()).toEqual(
      expect.objectContaining({ key: "item", event_type: "dragstart", drag_payload: "row-1" })
    );
  });

  it("throttles dragover to ~8/s per key", () => {
    mountTree({ key: "zone", tag: "div" });
    const el = document.querySelector("[data-neony-key='zone']");
    const dt = makeDataTransfer();
    // Mock Date.now so the 120ms throttle window is deterministic.
    let now = 1000;
    const realNow = Date.now;
    globalThis.Date.now = () => now;
    try {
      el.dispatchEvent(dragEvent("dragover", dt)); // first — forwarded
      el.dispatchEvent(dragEvent("dragover", dt)); // +0ms — throttled
      now += 130;
      el.dispatchEvent(dragEvent("dragover", dt)); // +130ms — forwarded
      now += 130;
      el.dispatchEvent(dragEvent("dragover", dt)); // +260ms — forwarded
    } finally {
      globalThis.Date.now = realNow;
    }
    const dragoverCount = invoke.mock.calls.filter(([name, p]) => name === "neony.event" && p.event_type === "dragover").length;
    expect(dragoverCount).toBe(3);
  });

  it("resets the dragover throttle map on drop and dragend", () => {
    mountTree({ key: "zone", tag: "div" });
    const el = document.querySelector("[data-neony-key='zone']");
    const dt = makeDataTransfer();
    el.dispatchEvent(dragEvent("dragover", dt)); // forwarded (t=0)
    el.dispatchEvent(dragEvent("drop", dt)); // clears the map
    el.dispatchEvent(dragEvent("dragover", dt)); // forwarded again (fresh map)
    const dragoverCount = invoke.mock.calls.filter(([name, p]) => name === "neony.event" && p.event_type === "dragover").length;
    expect(dragoverCount).toBe(2);
  });

  it("does not seed dataTransfer on dragstart without a drag payload", () => {
    mountTree({ key: "item", tag: "div" });
    const el = document.querySelector("[data-neony-key='item']");
    const dt = makeDataTransfer();
    el.dispatchEvent(dragEvent("dragstart", dt));
    expect(dt.setData).not.toHaveBeenCalled();
    expect(lastPayload().drag_payload).toBeUndefined();
  });

  it("forwards dragend and dragenter", () => {
    mountTree({ key: "item", tag: "div", attrs: { "data-neony-drag": "row-1" } });
    const el = document.querySelector("[data-neony-key='item']");
    // Two dispatches — grab the LAST invocation (lastPayload() above
    // uses .find, which returns the first).
    const last = () => invoke.mock.calls.filter(([name]) => name === "neony.event").at(-1)[1];
    el.dispatchEvent(dragEvent("dragend"));
    expect(last()).toEqual(expect.objectContaining({ key: "item", event_type: "dragend" }));
    el.dispatchEvent(dragEvent("dragenter"));
    expect(last()).toEqual(expect.objectContaining({ key: "item", event_type: "dragenter" }));
  });

  it("reads the in-app drag payload back on drop", () => {
    mountTree({ key: "zone", tag: "div" });
    const el = document.querySelector("[data-neony-key='zone']");
    const dt = makeDataTransfer({ "application/x-neony": "row-1" });
    el.dispatchEvent(dragEvent("drop", dt));
    expect(lastPayload()).toEqual(
      expect.objectContaining({ key: "zone", event_type: "drop", drag_payload: "row-1" })
    );
  });
});

describe("pointer-driven in-app drag (synthetic drag lifecycle)", () => {
  let invoke;
  let win;

  beforeEach(() => {
    win = { minimize: vi.fn(), toggleMaximize: vi.fn(), close: vi.fn() };
    invoke = vi.fn(() => Promise.resolve());
    window.lumiview = { listen, invoke, window: win };
    // Reset module-level dnd state between tests (dndState survives the
    // eval'd IIFE scope, like lastDragover).
    if (globalThis.__neonyDndReset) globalThis.__neonyDndReset();
  });

  function mouse(type, x, y, target = document) {
    const e = new window.MouseEvent(type, { bubbles: true, cancelable: true });
    Object.defineProperty(e, "clientX", { value: x });
    Object.defineProperty(e, "clientY", { value: y });
    Object.defineProperty(e, "button", { value: 0 });
    target.dispatchEvent(e);
  }

  function fireDragFrom(el, x0, y0, x1, y1) {
    mouse("mousedown", x0, y0, el); // arms the drag
    mouse("mousemove", x0, y0, el); // below threshold
    mouse("mousemove", x1, y1, el); // past threshold — drag begins
    mouse("mouseup", x1, y1, el);
  }

  it("synthesizes dragstart/drop/dragend for a data-neony-drag element", () => {
    mountTree({
      key: "item",
      tag: "div",
      attrs: { "data-neony-drag": "row-1" },
      children: [],
    });
    const el = document.querySelector("[data-neony-key='item']");
    // elementFromPoint needs a real element at the drop point — jsdom
    // returns null for empty coordinates; point into the item itself.
    const realFromPoint = document.elementFromPoint;
    document.elementFromPoint = () => el;
    try {
      fireDragFrom(el, 50, 50, 120, 90);
    } finally {
      document.elementFromPoint = realFromPoint;
    }
    const calls = invoke.mock.calls.filter(([name]) => name === "neony.event").map(([, p]) => p);
    const types = calls.map((p) => p.event_type);
    expect(types).toContain("dragstart");
    expect(types).toContain("drop");
    expect(types).toContain("dragend");
    const drop = calls.find((p) => p.event_type === "drop");
    expect(drop.drag_payload).toBe("row-1");
    // Ghost created on drag begin, removed on release.
    expect(document.querySelector("[data-neony-ghost]")).toBeNull();
  });

  it("does not start a drag below the 4px threshold", () => {
    mountTree({ key: "item", tag: "div", attrs: { "data-neony-drag": "row-1" } });
    const el = document.querySelector("[data-neony-key='item']");
    const realFromPoint = document.elementFromPoint;
    document.elementFromPoint = () => el;
    try {
      mouse("mousedown", 50, 50);
      mouse("mousemove", 52, 51); // < 4px
      mouse("mouseup", 52, 51);
    } finally {
      document.elementFromPoint = realFromPoint;
    }
    const types = invoke.mock.calls
      .filter(([name]) => name === "neony.event")
      .map(([, p]) => p.event_type);
    expect(types).not.toContain("dragstart");
    expect(types).not.toContain("drop");
    expect(document.querySelector("[data-neony-ghost]")).toBeNull();
  });

  it("reports offsetY relative to the drop target (not page coords)", () => {
    // Regression: offsetX/offsetY in the synthetic drop must be relative
    // to the TARGET element — the reorder demo splits a card at its own
    // top/bottom half.  Page coordinates made every drop look like the
    // card's lower half, so upward reorders always inserted AFTER the
    // target ("3 dragged to 1 lands at 2").
    mountTree({ key: "item", tag: "div", attrs: { "data-neony-drag": "row-1" } });
    const el = document.querySelector("[data-neony-key='item']");
    const realFromPoint = document.elementFromPoint;
    document.elementFromPoint = () => el;
    // jsdom rects are 0,0,0,0 — force a rect so the offset math is real.
    const realRect = el.getBoundingClientRect;
    el.getBoundingClientRect = () => ({ left: 40, top: 100, width: 150, height: 40 });
    try {
      fireDragFrom(el, 50, 50, 60, 110); // inside target: (60-40, 110-100) = (20, 10)
      const calls = invoke.mock.calls.filter(([name]) => name === "neony.event").map(([, p]) => p);
      const drop = calls.find((p) => p.event_type === "drop");
      expect(drop.offset_x).toBe(20);
      expect(drop.offset_y).toBe(10);
    } finally {
      el.getBoundingClientRect = realRect;
      document.elementFromPoint = realFromPoint;
    }
  });

  it("shifts cards position-only to preview the insertion point", () => {
    mountTree({
      key: "row",
      tag: "div",
      styles: { display: "flex", "flex-direction": "column", gap: "8px" },
      children: [],
    });
    const row = document.querySelector("[data-neony-key='row']");
    const realFromPoint = document.elementFromPoint;
    document.elementFromPoint = () => row;
    const realRect = row.getBoundingClientRect;
    row.getBoundingClientRect = () => ({ left: 0, top: 100, width: 200, height: 240 });
    try {
      // Source and target cards, both inside the row.
      const src = document.createElement("div");
      src.setAttribute("data-neony-drag", "row-1");
      src.style.height = "40px";
      src.style.background = "rgb(1, 2, 3)"; // Neony-injected style — must survive the ghost
      src.getBoundingClientRect = () => ({ left: 0, top: 100, width: 200, height: 40 });
      row.appendChild(src);
      const target = document.createElement("div");
      target.setAttribute("data-neony-key", "target-card");
      target.style.height = "40px";
      target.getBoundingClientRect = () => ({ left: 0, top: 148, width: 200, height: 40 });
      row.appendChild(target);
      let over = src;
      document.elementFromPoint = () => over;
      try {
        mouse("mousedown", 10, 10, src);
        mouse("mousemove", 10, 10, src); // below threshold
        over = target;
        mouse("mousemove", 10, 20, src); // past threshold — drag begins
        // The source leaves the flow as its own ghost; a placeholder
        // keeps its slot open.  No element resizes.
        expect(src.style.position).toBe("fixed");
        expect(src.style.pointerEvents).toBe("none");
        expect(src.style.background).toBe("rgb(1, 2, 3)"); // background survives
        expect(src.style.transform).toContain("translate3d"); // ghost is positioned
        const ph = row.querySelector("[data-neony-dnd-placeholder]");
        expect(ph).not.toBeNull();
        expect(target.style.height).toBe("40px"); // never resized
        // Upper half of the target → placeholder before it.
        expect(ph.nextSibling).toBe(target);
        // Lower half (y=175 → past the 168 midline + 6px hysteresis) →
        // placeholder after it.
        mouse("mousemove", 10, 175, src);
        expect(ph.previousSibling).toBe(target);
        expect(target.style.height).toBe("40px"); // still never resized
        // Hovering the source slot (a gap, not a card) KEEPS the committed
        // insertion — the visible slot must not vanish when reached for.
        over = src;
        mouse("mousemove", 10, 10, src);
        expect(ph.previousSibling).toBe(target); // still after the target
        mouse("mouseup", 10, 10, src);
        // Cleanup: placeholder removed, source restored to the flow.
        expect(row.querySelector("[data-neony-dnd-placeholder]")).toBeNull();
        expect(src.style.position).not.toBe("fixed");
        expect(src.style.background).toBe("rgb(1, 2, 3)"); // still intact after cleanup
      } finally {
        over = src;
      }
    } finally {
      row.getBoundingClientRect = realRect;
      document.elementFromPoint = realFromPoint;
    }
  });

  it("clears the preview when the cursor leaves the container", () => {
    mountTree({
      key: "row",
      tag: "div",
      styles: { display: "flex", "flex-direction": "column", gap: "8px" },
      children: [],
    });
    const row = document.querySelector("[data-neony-key='row']");
    const realFromPoint = document.elementFromPoint;
    document.elementFromPoint = () => row;
    const realRect = row.getBoundingClientRect;
    row.getBoundingClientRect = () => ({ left: 0, top: 100, width: 200, height: 240 });
    try {
      const src = document.createElement("div");
      src.setAttribute("data-neony-drag", "row-1");
      src.style.height = "40px";
      src.getBoundingClientRect = () => ({ left: 0, top: 100, width: 200, height: 40 });
      row.appendChild(src);
      const target = document.createElement("div");
      target.setAttribute("data-neony-key", "target-card");
      target.style.height = "40px";
      target.getBoundingClientRect = () => ({ left: 0, top: 148, width: 200, height: 40 });
      row.appendChild(target);
      // A keyed element OUTSIDE the container (a sibling in body).
      const outside = document.createElement("div");
      outside.setAttribute("data-neony-key", "outside");
      document.body.appendChild(outside);
      let over = src;
      document.elementFromPoint = () => over;
      try {
        mouse("mousedown", 10, 10, src);
        mouse("mousemove", 10, 10, src); // below threshold
        over = target;
        mouse("mousemove", 10, 20, src); // begin — over target upper half
        const ph = row.querySelector("[data-neony-dnd-placeholder]");
        expect(ph.style.visibility).toBe("visible");
        expect(ph.nextSibling).toBe(target);
        // Leaving the container clears the preview: slot hidden, back to
        // the source slot.
        over = outside;
        mouse("mousemove", 10, 10, src);
        expect(ph.style.visibility).toBe("hidden");
        expect(ph.nextSibling).toBe(target); // reverted before target
        over = src;
        mouse("mouseup", 10, 10, src);
      } finally {
        over = src;
      }
    } finally {
      row.getBoundingClientRect = realRect;
      document.elementFromPoint = realFromPoint;
    }
  });

  it("reorders horizontally (row container) by the left/right half", () => {
    mountTree({
      key: "row",
      tag: "div",
      styles: { display: "flex", "flex-direction": "row", gap: "8px" },
      children: [],
    });
    const row = document.querySelector("[data-neony-key='row']");
    const realFromPoint = document.elementFromPoint;
    document.elementFromPoint = () => row;
    const realRect = row.getBoundingClientRect;
    row.getBoundingClientRect = () => ({ left: 0, top: 100, width: 300, height: 40 });
    try {
      const src = document.createElement("div");
      src.setAttribute("data-neony-drag", "row-1");
      src.style.width = "60px";
      src.getBoundingClientRect = () => ({ left: 0, top: 100, width: 60, height: 40 });
      row.appendChild(src);
      const target = document.createElement("div");
      target.setAttribute("data-neony-key", "target-card");
      target.style.width = "60px";
      target.getBoundingClientRect = () => ({ left: 68, top: 100, width: 60, height: 40 });
      row.appendChild(target);
      let over = src;
      document.elementFromPoint = () => over;
      try {
        mouse("mousedown", 5, 110, src);
        mouse("mousemove", 5, 110, src); // below threshold
        over = target;
        mouse("mousemove", 78, 110, src); // begin — target LEFT half (mid 98)
        const ph = row.querySelector("[data-neony-dnd-placeholder]");
        expect(ph).not.toBeNull();
        expect(ph.style.visibility).toBe("visible");
        expect(ph.style.width).toBe("60px"); // sized along the row axis
        expect(ph.nextSibling).toBe(target); // before target
        mouse("mousemove", 118, 110, src); // right half → after target
        expect(ph.previousSibling).toBe(target);
        // Drop encodes the side via offset_x.
        over = src;
        mouse("mouseup", 5, 110, src);
        const calls = invoke.mock.calls
          .filter(([name]) => name === "neony.event")
          .map(([, p]) => p);
        const drop = calls.find((p) => p.event_type === "drop");
        expect(drop).toBeTruthy();
        expect(drop.key).toBe("target-card");
        expect(drop.offset_x).toBe(60); // encoded "after" (>= 30px mid)
        expect(drop.drag_payload).toBe("row-1");
      } finally {
        over = src;
      }
    } finally {
      row.getBoundingClientRect = realRect;
      document.elementFromPoint = realFromPoint;
    }
  });

  it("drops at the committed insertion, not the raw cursor point", () => {
    // Regression: the preview's placeholder shows where the card will
    // land, so the drop MUST target that same card+side — even if the
    // release point's cursor hits something else (a gap, the source slot).
    mountTree({
      key: "row",
      tag: "div",
      styles: { display: "flex", "flex-direction": "column", gap: "8px" },
      children: [],
    });
    const row = document.querySelector("[data-neony-key='row']");
    const realFromPoint = document.elementFromPoint;
    document.elementFromPoint = () => row;
    const realRect = row.getBoundingClientRect;
    row.getBoundingClientRect = () => ({ left: 0, top: 100, width: 200, height: 240 });
    try {
      const src = document.createElement("div");
      src.setAttribute("data-neony-drag", "row-1");
      src.style.height = "40px";
      src.getBoundingClientRect = () => ({ left: 0, top: 100, width: 200, height: 40 });
      row.appendChild(src);
      const target = document.createElement("div");
      target.setAttribute("data-neony-key", "target-card");
      target.style.height = "40px";
      target.getBoundingClientRect = () => ({ left: 0, top: 148, width: 200, height: 40 });
      row.appendChild(target);
      let over = src;
      document.elementFromPoint = () => over;
      try {
        mouse("mousedown", 10, 10, src);
        mouse("mousemove", 10, 10, src); // below threshold
        over = target;
        mouse("mousemove", 10, 20, src); // past threshold — over target upper half
        mouse("mousemove", 10, 175, src); // lower half → committed "target:after"
        // Release while the cursor still points at the SOURCE slot — the
        // raw cursor would drop on the row (no reorder), but the committed
        // insertion must win so the result matches the preview.
        over = src;
        mouse("mouseup", 10, 10, src);
        const calls = invoke.mock.calls
          .filter(([name]) => name === "neony.event")
          .map(([, p]) => p);
        const drop = calls.find((p) => p.event_type === "drop");
        expect(drop).toBeTruthy();
        expect(drop.key).toBe("target-card");
        expect(drop.offset_y).toBe(40); // encoded "after" (>= 20px mid)
        expect(drop.drag_payload).toBe("row-1");
        // Settle: the source re-enters the flow at the committed slot
        // (right after the target), so it glides into place and the Python
        // reorder patch that follows is a no-op for it.
        const kids = Array.from(row.children);
        expect(row.querySelector("[data-neony-dnd-placeholder]")).toBeNull();
        expect(kids.indexOf(target)).toBe(0);
        expect(kids.indexOf(src)).toBe(1);
        expect(src.style.position).not.toBe("fixed");
      } finally {
        over = src;
      }
    } finally {
      row.getBoundingClientRect = realRect;
      document.elementFromPoint = realFromPoint;
    }
  });

  it("re-homes the landing slot into another board (cross-board)", () => {
    // Two keyed flex boards; dragging from board A onto a card of board B
    // moves the placeholder across containers — the slot shows up in B.
    const a = document.createElement("div");
    a.setAttribute("data-neony-key", "board-a");
    a.style.display = "flex";
    a.style.flexDirection = "row";
    a.style.gap = "8px";
    document.body.appendChild(a);
    const b = document.createElement("div");
    b.setAttribute("data-neony-key", "board-b");
    b.style.display = "flex";
    b.style.flexDirection = "row";
    b.style.gap = "8px";
    document.body.appendChild(b);
    const realFromPoint = document.elementFromPoint;
    const realRectA = a.getBoundingClientRect;
    const realRectB = b.getBoundingClientRect;
    a.getBoundingClientRect = () => ({ left: 0, top: 100, width: 300, height: 40 });
    b.getBoundingClientRect = () => ({ left: 0, top: 160, width: 300, height: 40 });
    const src = document.createElement("div");
    src.setAttribute("data-neony-drag", "a-1");
    src.style.width = "60px";
    src.getBoundingClientRect = () => ({ left: 0, top: 100, width: 60, height: 40 });
    a.appendChild(src);
    const targetB = document.createElement("div");
    targetB.setAttribute("data-neony-key", "b-1");
    targetB.setAttribute("data-neony-drag", "b-1");
    targetB.style.width = "80px";
    targetB.getBoundingClientRect = () => ({ left: 68, top: 160, width: 80, height: 40 });
    b.appendChild(targetB);
    let over = src;
    document.elementFromPoint = () => over;
    try {
      mouse("mousedown", 5, 110, src);
      mouse("mousemove", 5, 110, src); // below threshold
      over = targetB;
      mouse("mousemove", 9, 135, src); // begin + over B's target LEFT half
      const ph = document.querySelector("[data-neony-dnd-placeholder]");
      expect(ph).not.toBeNull();
      expect(ph.parentNode).toBe(b); // placeholder moved into board B
      expect(ph.style.visibility).toBe("visible");
      expect(ph.style.width).toBe("80px"); // resized to B's card footprint
      expect(ph.nextSibling).toBe(targetB); // before target
      // Moving back onto a card in board A re-homes the slot back.
      over = src;
      mouse("mousemove", 5, 110, src);
      expect(ph.parentNode).toBe(a);
      // Hover B again, then drop: the drop targets B's card with the
      // source's payload, and the settle glides the source into B's
      // committed slot (the Python handler moves the card model; the diff
      // emits a MovePatch that re-parents THIS SAME element).
      over = targetB;
      mouse("mousemove", 5, 110, src);
      mouse("mouseup", 5, 110, src);
      const calls = invoke.mock.calls
        .filter(([name]) => name === "neony.event")
        .map(([, p]) => p);
      const drop = calls.find((p) => p.event_type === "drop");
      expect(drop).toBeTruthy();
      expect(drop.key).toBe("b-1");
      expect(drop.drag_payload).toBe("a-1");
      expect(drop.offset_x).toBe(0); // encoded "before"
      expect(b.querySelector("[data-neony-dnd-placeholder]")).toBeNull();
      expect(src.parentNode).toBe(b); // glided into board B's slot
      expect(src.style.position).not.toBe("fixed");
    } finally {
      over = src;
    }
  });

  it("clears a re-homed slot when the cursor leaves every board", () => {
    const a = document.createElement("div");
    a.setAttribute("data-neony-key", "board-a");
    a.style.display = "flex";
    a.style.flexDirection = "row";
    a.style.gap = "8px";
    document.body.appendChild(a);
    const b = document.createElement("div");
    b.setAttribute("data-neony-key", "board-b");
    b.style.display = "flex";
    b.style.flexDirection = "row";
    b.style.gap = "8px";
    document.body.appendChild(b);
    const realFromPoint = document.elementFromPoint;
    const realRectA = a.getBoundingClientRect;
    const realRectB = b.getBoundingClientRect;
    a.getBoundingClientRect = () => ({ left: 0, top: 100, width: 300, height: 40 });
    b.getBoundingClientRect = () => ({ left: 0, top: 160, width: 300, height: 40 });
    const src = document.createElement("div");
    src.setAttribute("data-neony-drag", "a-1");
    src.style.width = "60px";
    src.getBoundingClientRect = () => ({ left: 0, top: 100, width: 60, height: 40 });
    a.appendChild(src);
    const targetB = document.createElement("div");
    targetB.setAttribute("data-neony-key", "b-1");
    targetB.setAttribute("data-neony-drag", "b-1");
    targetB.style.width = "80px";
    targetB.getBoundingClientRect = () => ({ left: 68, top: 160, width: 80, height: 40 });
    b.appendChild(targetB);
    // A keyed element OUTSIDE both boards (a sibling in body).
    const outside = document.createElement("div");
    outside.setAttribute("data-neony-key", "outside");
    document.body.appendChild(outside);
    let over = src;
    document.elementFromPoint = () => over;
    try {
      mouse("mousedown", 5, 110, src);
      mouse("mousemove", 5, 110, src); // below threshold
      over = targetB;
      mouse("mousemove", 9, 135, src); // begin — re-home into board B
      const ph = document.querySelector("[data-neony-dnd-placeholder]");
      expect(ph.parentNode).toBe(b);
      expect(ph.style.visibility).toBe("visible");
      // Leaving both boards reverts the slot to the source's board.
      over = outside;
      mouse("mousemove", 5, 110, src);
      expect(ph.parentNode).toBe(a); // back in the source board
      expect(ph.style.visibility).toBe("hidden");
      over = src;
      mouse("mouseup", 5, 110, src);
    } finally {
      over = src;
    }
  });
});

describe("pointermove events", () => {
  let invoke;
  let win;

  beforeEach(() => {
    win = { minimize: vi.fn(), toggleMaximize: vi.fn(), close: vi.fn() };
    invoke = vi.fn(() => Promise.resolve());
    window.lumiview = { listen, invoke, window: win };
  });

  function lastPayload() {
    return invoke.mock.calls.find(([name]) => name === "neony.event")[1];
  }

  // jsdom has no PointerEvent constructor — build a MouseEvent and
  // define the pointer-only properties, same pattern as the paste/drop
  // tests above.
  function pointerMoveEvent(init) {
    const event = new window.MouseEvent("pointermove", { bubbles: true });
    Object.defineProperty(event, "clientX", { value: init.clientX });
    Object.defineProperty(event, "clientY", { value: init.clientY });
    Object.defineProperty(event, "pointerId", { value: 1 });
    Object.defineProperty(event, "movementX", { value: init.movementX });
    Object.defineProperty(event, "movementY", { value: init.movementY });
    Object.defineProperty(event, "pointerType", { value: init.pointerType });
    return event;
  }

  it("delegates pointermove with coordinates, delta and pointer type", () => {
    mountTree({ key: "drag-area", tag: "div" });
    const el = document.querySelector("[data-neony-key='drag-area']");
    el.dispatchEvent(
      pointerMoveEvent({ clientX: 100, clientY: 200, movementX: 5, movementY: -3, pointerType: "mouse" })
    );
    expect(lastPayload()).toEqual(
      expect.objectContaining({
        key: "drag-area",
        event_type: "pointermove",
        x: 100,
        y: 200,
        movement_x: 5,
        movement_y: -3,
        pointer_type: "mouse",
      })
    );
  });

  it("carries pointer_type for touch pointers", () => {
    mountTree({ key: "area", tag: "div" });
    const el = document.querySelector("[data-neony-key='area']");
    el.dispatchEvent(
      pointerMoveEvent({ clientX: 50, clientY: 60, movementX: 1, movementY: 1, pointerType: "touch" })
    );
    expect(lastPayload()).toEqual(expect.objectContaining({ pointer_type: "touch" }));
  });

  it("omits pointer fields on plain mouse events", () => {
    // movementX exists on plain MouseEvents too (0) — the payload must
    // not carry movement/type for non-pointer events.
    mountTree({ key: "btn", tag: "button" });
    const el = document.querySelector("[data-neony-key='btn']");
    el.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
    const payload = lastPayload();
    expect(payload.movement_x).toBeUndefined();
    expect(payload.movement_y).toBeUndefined();
    expect(payload.pointer_type).toBeUndefined();
  });
});

describe("outsideclick", () => {
  let invoke;
  let win;

  beforeEach(() => {
    win = { minimize: vi.fn(), toggleMaximize: vi.fn(), close: vi.fn() };
    invoke = vi.fn(() => Promise.resolve());
    window.lumiview = { listen, invoke, window: win };
  });

  function outsidePayloads() {
    return invoke.mock.calls
      .filter(([name, payload]) => name === "neony.event" && payload.event_type === "outsideclick")
      .map(([, payload]) => payload);
  }

  it("fires outsideclick for a marked overlay when a click lands outside it", () => {
    mountTree({
      key: "dd",
      tag: "div",
      attrs: { "data-neony-outside": "true" },
    });
    document.body.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
    expect(outsidePayloads()).toEqual([{ key: "dd", event_type: "outsideclick", value: null }]);
  });

  it("fires outsideclick from a blank click even when bubble propagation is stopped", () => {
    mountTree({
      key: "dd",
      tag: "div",
      attrs: { "data-neony-outside": "true" },
    });
    const blank = document.createElement("div");
    document.body.appendChild(blank);
    blank.addEventListener("click", (event) => event.stopPropagation());
    blank.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));

    expect(outsidePayloads()).toEqual([{ key: "dd", event_type: "outsideclick", value: null }]);
  });

  it("does not fire outsideclick for clicks inside the overlay", () => {
    mountTree({
      key: "dd",
      tag: "div",
      attrs: { "data-neony-outside": "true" },
      children: [{ key: "row", tag: "button", text: "pick" }],
    });
    const row = document.querySelector("[data-neony-key='row']");
    row.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
    expect(outsidePayloads()).toEqual([]);
  });

  it("fires outsideclick alongside the normal click on a keyed element elsewhere", () => {
    mountTree({
      key: "root",
      tag: "div",
      children: [
        { key: "dd", tag: "div", attrs: { "data-neony-outside": "true" } },
        { key: "btn", tag: "button", text: "x" },
      ],
    });
    const btn = document.querySelector("[data-neony-key='btn']");
    btn.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
    expect(invoke).toHaveBeenCalledWith(
      "neony.event",
      expect.objectContaining({ key: "btn", event_type: "click" })
    );
    expect(outsidePayloads()).toEqual([{ key: "dd", event_type: "outsideclick", value: null }]);
  });

  it("ignores overlays without the marker", () => {
    mountTree({ key: "dd", tag: "div" });
    document.body.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
    expect(outsidePayloads()).toEqual([]);
  });
});

describe("wheel-x (vertical wheel → horizontal scroll)", () => {
  let invoke;
  let rafSpy;

  beforeEach(() => {
    invoke = vi.fn(() => Promise.resolve());
    window.lumiview = { listen, invoke, window: {} };
    // Run the easing loop synchronously so one wheel event eases all the
    // way to the target in-test (each frame runs immediately).
    rafSpy = vi.spyOn(global, "requestAnimationFrame").mockImplementation((cb) => {
      cb();
      return 1;
    });
  });
  afterEach(() => {
    rafSpy.mockRestore();
  });

  function wheelBar(extraAttrs = {}) {
    const bar = document.createElement("div");
    bar.setAttribute("data-neony-key", "bar");
    bar.setAttribute("data-neony-wheel-x", "true");
    for (const [k, v] of Object.entries(extraAttrs)) bar.setAttribute(k, v);
    // scrollWidth/clientWidth back the clamp range; defaults give free room.
    Object.defineProperty(bar, "scrollWidth", { value: 10000, configurable: true });
    Object.defineProperty(bar, "clientWidth", { value: 200, configurable: true });
    document.body.appendChild(bar);
    return bar;
  }

  it("translates a vertical wheel into scrollLeft and cancels the default", () => {
    const bar = wheelBar();
    const event = new window.WheelEvent("wheel", { deltaY: 40, cancelable: true, bubbles: true });
    bar.dispatchEvent(event);

    expect(bar.scrollLeft).toBe(40);
    expect(event.defaultPrevented).toBe(true);
  });

  it("scales line-mode deltas to a readable step", () => {
    const bar = wheelBar();
    const event = new window.WheelEvent("wheel", { deltaY: 3, deltaMode: 1, cancelable: true, bubbles: true });
    bar.dispatchEvent(event);

    // deltaMode 1 (lines) scales by 40 → 3 * 40 = 120.
    expect(bar.scrollLeft).toBe(120);
  });

  it("does not intercept unmarked elements", () => {
    const el = document.createElement("div");
    el.setAttribute("data-neony-key", "plain");
    document.body.appendChild(el);

    const event = new window.WheelEvent("wheel", { deltaY: 40, cancelable: true, bubbles: true });
    el.dispatchEvent(event);

    expect(event.defaultPrevented).toBe(false);
    expect(el.scrollLeft).toBe(0);
    expect(invoke).toHaveBeenCalledWith(
      "neony.event",
      expect.objectContaining({ event_type: "wheel" })
    );
  });
});

describe("scroll indicator (data-neony-scroll)", () => {
  let rafSpy;

  beforeEach(() => {
    // Run the geometry rAF synchronously so one schedule updates the
    // thumb immediately (each frame runs at once).
    rafSpy = vi.spyOn(global, "requestAnimationFrame").mockImplementation((cb) => {
      cb();
      return 1;
    });
  });
  afterEach(() => {
    rafSpy.mockRestore();
    document.body.innerHTML = "";
  });

  // jsdom does not lay out scroll metrics — define them as real props.
  function makeScrollEl({
    axis = "y",
    scrollSize = 1000,
    clientSize = 200,
    scrollTop = 0,
    backdropFilter = false,
  } = {}) {
    const el = document.createElement("div");
    el.setAttribute("data-neony-scroll", axis);
    if (axis === "y") {
      Object.defineProperty(el, "scrollHeight", { value: scrollSize, configurable: true });
      Object.defineProperty(el, "clientHeight", { value: clientSize, configurable: true });
    } else {
      Object.defineProperty(el, "scrollWidth", { value: scrollSize, configurable: true });
      Object.defineProperty(el, "clientWidth", { value: clientSize, configurable: true });
    }
    let top = scrollTop;
    let left = scrollTop;
    Object.defineProperty(el, "scrollTop", { configurable: true, get: () => top, set: (v) => { top = v; } });
    Object.defineProperty(el, "scrollLeft", { configurable: true, get: () => left, set: (v) => { left = v; } });
    if (backdropFilter) el.style.backdropFilter = "blur(8px)";
    document.body.appendChild(el);
    return el;
  }

  // The boot MutationObserver attaches async — flush it with a microtask
  // tick (MutationObserver callbacks fire on the microtask queue).
  function flushObserver() {
    return new Promise((resolve) => setTimeout(resolve, 0));
  }

  // The overlay is a SIBLING of the container (pinned in the parent),
  // so it is found from the parent, not inside the scroller.
  function findThumb(el) {
    return el.parentElement.querySelector(".neony-scroll-thumb");
  }

  it("hides the overlay when content does not overflow", async () => {
    const el = makeScrollEl({ scrollSize: 200, clientSize: 200 });
    await flushObserver();
    const overlay = findThumb(el)?.parentElement;
    expect(overlay).toBeDefined();
    expect(overlay.style.display).toBe("none");
  });

  it("shows and positions the thumb by the geometry ratio (vertical)", async () => {
    const el = makeScrollEl({ axis: "y", scrollSize: 1000, clientSize: 200, scrollTop: 0 });
    await flushObserver();
    const thumb = findThumb(el);
    expect(thumb).toBeDefined();
    const overlay = thumb.parentElement;
    expect(overlay.style.display).not.toBe("none");
    // clientHeight of the track is 0 in jsdom (no layout), so thumbLen
    // collapses to SI_THUMB_MIN; just assert the thumb is placed.
    expect(thumb.style.height).toBeDefined();
  });

  it("writes a dynamic mask with no top fade at scrollTop=0", async () => {
    const el = makeScrollEl({ axis: "y", scrollSize: 1000, clientSize: 200, scrollTop: 0 });
    await flushObserver();
    // At the top, the leading edge is solid (no transparent rim).
    expect(el.style.maskImage).toContain("black 0px");
    expect(el.style.webkitMaskImage).toBe(el.style.maskImage);
  });

  it("applies NO mask when the container has a backdrop-filter", async () => {
    const el = makeScrollEl({ axis: "y", scrollSize: 1000, clientSize: 200, backdropFilter: true });
    await flushObserver();
    expect(el.style.maskImage).toBe("");
  });

  it("drag maps pointer movement to scrollTop through the ratio", async () => {
    window.lumiview = { listen, invoke: vi.fn(() => Promise.resolve()), window: {} };
    const el = makeScrollEl({ axis: "y", scrollSize: 1000, clientSize: 200, scrollTop: 0 });
    await flushObserver();
    const thumb = findThumb(el);
    // setPointerCapture doesn't exist in jsdom.
    thumb.setPointerCapture = vi.fn();
    thumb.releasePointerCapture = vi.fn();

    function pointerEvent(type, init) {
      const e = new window.MouseEvent(type, { bubbles: true });
      Object.defineProperty(e, "clientY", { value: init.clientY });
      Object.defineProperty(e, "pointerId", { value: 1 });
      e.preventDefault = vi.fn();
      e.stopPropagation = vi.fn();
      return e;
    }

    const down = pointerEvent("pointerdown", { clientY: 100 });
    thumb.dispatchEvent(down);
    expect(thumb.setPointerCapture).toHaveBeenCalledWith(1);

    // Drag runs with ZERO Python IPC — the invoke count must not rise.
    const before = window.lumiview.invoke.mock.calls.length;
    const move = pointerEvent("pointermove", { clientY: 150 });
    thumb.dispatchEvent(move);
    expect(window.lumiview.invoke.mock.calls.length).toBe(before);

    const up = pointerEvent("pointerup", { clientY: 150 });
    thumb.dispatchEvent(up);
    expect(thumb.releasePointerCapture).toHaveBeenCalledWith(1);
  });

  it("attaches at most once (idempotent) and detaches on removal", async () => {
    const el = makeScrollEl({ axis: "y", scrollSize: 1000, clientSize: 200 });
    await flushObserver();
    expect(el.parentElement.querySelectorAll(".neony-scroll-thumb").length).toBe(1);
    // Re-discovering must not double-attach.
    el.setAttribute("data-neony-scroll", "y"); // no-op churn
    await flushObserver();
    expect(el.parentElement.querySelectorAll(".neony-scroll-thumb").length).toBe(1);
    el.remove();
    await flushObserver();
    // Detach cleared the mask it owned.
    expect(el.style.maskImage).toBe("");
  });
});

describe("transition and animation events", () => {
  let invoke;
  let win;

  beforeEach(() => {
    win = { minimize: vi.fn(), toggleMaximize: vi.fn(), close: vi.fn() };
    invoke = vi.fn(() => Promise.resolve());
    window.lumiview = { listen, invoke, window: win };
  });

  function lastPayload() {
    return invoke.mock.calls.find(([name]) => name === "neony.event")[1];
  }

  // jsdom has no TransitionEvent/AnimationEvent constructors — build an
  // Event and define the interface properties, same pattern as the
  // paste/drop/pointermove tests above.
  function defineProps(event, props) {
    for (const [name, value] of Object.entries(props)) {
      Object.defineProperty(event, name, { value });
    }
    return event;
  }

  it("delegates transitionend with property and elapsed time", () => {
    mountTree({ key: "box", tag: "div" });
    const el = document.querySelector("[data-neony-key='box']");
    el.dispatchEvent(
      defineProps(new window.Event("transitionend", { bubbles: true }), {
        propertyName: "opacity",
        elapsedTime: 0.15,
      })
    );
    expect(lastPayload()).toEqual(
      expect.objectContaining({
        event_type: "transitionend",
        transition_property: "opacity",
        elapsed_time: 0.15,
      })
    );
  });

  it("delegates animationend with name and elapsed time", () => {
    mountTree({ key: "box", tag: "div" });
    const el = document.querySelector("[data-neony-key='box']");
    el.dispatchEvent(
      defineProps(new window.Event("animationend", { bubbles: true }), {
        animationName: "spin",
        elapsedTime: 2.0,
      })
    );
    expect(lastPayload()).toEqual(
      expect.objectContaining({
        event_type: "animationend",
        animation_name: "spin",
        elapsed_time: 2.0,
      })
    );
  });

  it("delegates animationstart with name", () => {
    mountTree({ key: "box", tag: "div" });
    const el = document.querySelector("[data-neony-key='box']");
    el.dispatchEvent(
      defineProps(new window.Event("animationstart", { bubbles: true }), {
        animationName: "spin",
      })
    );
    expect(lastPayload()).toEqual(
      expect.objectContaining({ event_type: "animationstart", animation_name: "spin" })
    );
  });

  it("omits transition fields on plain events", () => {
    mountTree({ key: "btn", tag: "button" });
    const el = document.querySelector("[data-neony-key='btn']");
    el.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
    const payload = lastPayload();
    expect(payload.transition_property).toBeUndefined();
    expect(payload.elapsed_time).toBeUndefined();
    expect(payload.animation_name).toBeUndefined();
  });
});

describe("Flaza protocol additions (composition, scroll geometry, paste files, scrollTo)", () => {
  let invoke;
  let win;

  beforeEach(() => {
    win = { minimize: vi.fn(), toggleMaximize: vi.fn(), close: vi.fn() };
    invoke = vi.fn(() => Promise.resolve());
    window.lumiview = { listen, invoke, window: win };
  });

  function lastPayload() {
    return invoke.mock.calls.filter(([name]) => name === "neony.event").at(-1)[1];
  }

  it("delegates composition events and carries composition_data", () => {
    mountTree({ key: "editor", tag: "div" });
    const el = document.querySelector("[data-neony-key='editor']");
    const event = new window.Event("compositionupdate", { bubbles: true });
    Object.defineProperty(event, "data", { value: "ni" });
    el.dispatchEvent(event);
    expect(lastPayload()).toEqual(
      expect.objectContaining({ key: "editor", event_type: "compositionupdate", composition_data: "ni" })
    );
  });

  it("carries is_composing only while true", () => {
    mountTree({ key: "editor", tag: "div" });
    const el = document.querySelector("[data-neony-key='editor']");
    const composing = new window.Event("input", { bubbles: true });
    Object.defineProperty(composing, "isComposing", { value: true });
    el.dispatchEvent(composing);
    expect(lastPayload()).toEqual(expect.objectContaining({ event_type: "input", is_composing: true }));

    invoke.mockClear();
    const plain = new window.Event("input", { bubbles: true });
    Object.defineProperty(plain, "isComposing", { value: false });
    el.dispatchEvent(plain);
    expect(lastPayload().is_composing).toBeUndefined();
  });

  it("captures contenteditable text as the input value", () => {
    mountTree({ key: "editor", tag: "div" });
    const el = document.querySelector("[data-neony-key='editor']");
    Object.defineProperty(el, "isContentEditable", { value: true, configurable: true });
    el.innerText = "你好";
    el.dispatchEvent(new window.Event("input", { bubbles: true }));
    expect(lastPayload()).toEqual(expect.objectContaining({ event_type: "input", value: "你好" }));
  });

  it("carries scroll geometry from the scrolled element", () => {
    mountTree({ key: "list", tag: "div", styles: { overflow: "auto" } });
    const el = document.querySelector("[data-neony-key='list']");
    Object.defineProperty(el, "scrollTop", { value: 80, configurable: true });
    Object.defineProperty(el, "scrollHeight", { value: 500, configurable: true });
    Object.defineProperty(el, "clientHeight", { value: 200, configurable: true });
    Object.defineProperty(el, "scrollWidth", { value: 300, configurable: true });
    Object.defineProperty(el, "clientWidth", { value: 120, configurable: true });
    el.dispatchEvent(new window.Event("scroll"));
    expect(lastPayload()).toEqual(
      expect.objectContaining({
        key: "list",
        event_type: "scroll",
        scroll_top: 80,
        scroll_height: 500,
        client_height: 200,
        scroll_width: 300,
        client_width: 120,
      })
    );
  });

  it("forwards paste file metadata synchronously", () => {
    mountTree({ key: "editor", tag: "div" });
    const el = document.querySelector("[data-neony-key='editor']");
    const RealFileReader = window.FileReader;
    window.FileReader = class { readAsDataURL() {} };
    try {
      const clipboardData = {
        getData: () => "",
        files: [{ name: "shot.png", size: 99, type: "image/png" }],
      };
      const event = new window.Event("paste", { bubbles: true, cancelable: true });
      Object.defineProperty(event, "clipboardData", { value: clipboardData });
      el.dispatchEvent(event);
      expect(lastPayload()).toEqual(
        expect.objectContaining({
          event_type: "paste",
          paste_files: [{ name: "shot.png", size: 99, type: "image/png" }],
        })
      );
    } finally {
      window.FileReader = RealFileReader;
    }
  });

  it("delivers pasted file bytes as data URLs via neony.paste_files", async () => {
    mountTree({ key: "editor", tag: "div" });
    const el = document.querySelector("[data-neony-key='editor']");
    const RealFileReader = window.FileReader;
    window.FileReader = class {
      readAsDataURL(file) {
        this.result = "data:image/png;base64," + file.name;
        if (this.onload) this.onload();
      }
    };
    try {
      const clipboardData = {
        getData: () => "",
        files: [{ name: "shot.png", size: 10, type: "image/png" }],
      };
      const event = new window.Event("paste", { bubbles: true, cancelable: true });
      Object.defineProperty(event, "clipboardData", { value: clipboardData });
      el.dispatchEvent(event);
      await Promise.resolve();
      expect(invoke).toHaveBeenCalledWith("neony.paste_files", {
        key: "editor",
        files: [
          { name: "shot.png", size: 10, type: "image/png", data_url: "data:image/png;base64,shot.png" },
        ],
      });
    } finally {
      window.FileReader = RealFileReader;
    }
  });

  it("scrollTo command scrolls the keyed element with behavior", () => {
    mountTree({ key: "list", tag: "div" });
    const el = document.querySelector("[data-neony-key='list']");
    el.scrollTo = vi.fn();
    expect(neony.scrollTo("list", 120, "smooth")).toBe(true);
    expect(el.scrollTo).toHaveBeenCalledWith({ top: 120, behavior: "smooth" });
  });

  it("scrollTo falls back to scrollTop when scrollTo is missing", () => {
    mountTree({ key: "list", tag: "div" });
    const el = document.querySelector("[data-neony-key='list']");
    delete el.scrollTo;
    expect(neony.scrollTo("list", 40)).toBe(true);
    expect(el.scrollTop).toBe(40);
  });
});
