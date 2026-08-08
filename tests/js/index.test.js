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
