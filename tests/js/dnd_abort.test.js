import { describe, expect, it, vi, beforeEach } from "vitest";
import { loadRuntime } from "./load.js";

describe("dnd abort on window blur (lost mouseup)", () => {
  let invoke;
  beforeEach(() => {
    invoke = vi.fn(() => Promise.resolve());
    window.lumiview = { listen: vi.fn(), invoke, window: { minimize: vi.fn(), toggleMaximize: vi.fn(), close: vi.fn() } };
    if (globalThis.__neonyDndReset) globalThis.__neonyDndReset();
  });

  function load() {
    return loadRuntime(["builder.js", "engine.js", "index.js"]);
  }

  it("leaves the placeholder behind when mouseup is lost (BUG)", () => {
    const rt = load();
    rt.neony.mount({ rev: 1, ops: [{ op: "create", key: "page", node: { key: "page", tag: "div", children: [
      { key: "row", tag: "div", styles: { "flex-direction": "row" }, children: [
        { key: "a", tag: "span", attrs: { "data-neony-drag": "a" } },
        { key: "b", tag: "span", attrs: { "data-neony-drag": "b" } },
      ]},
    ]}}] });
    const a = document.querySelector("[data-neony-key='a']");
    a.getBoundingClientRect = () => ({ left: 0, top: 100, width: 60, height: 40 });
    document.elementFromPoint = () => a;

    // arm + begin the drag
    const md = new window.MouseEvent("mousedown", { bubbles: true, cancelable: true });
    Object.defineProperty(md, "clientX", { value: 5 });
    Object.defineProperty(md, "clientY", { value: 110 });
    Object.defineProperty(md, "button", { value: 0 });
    a.dispatchEvent(md);
    const mm = new window.MouseEvent("mousemove", { bubbles: true, cancelable: true });
    Object.defineProperty(mm, "clientX", { value: 50 });
    Object.defineProperty(mm, "clientY", { value: 160 });
    a.dispatchEvent(mm);
    expect(document.querySelector("[data-neony-dnd-placeholder]")).not.toBeNull();

    // user drags out of the window and releases there: mouseup never
    // reaches us — only a blur does.
    window.dispatchEvent(new window.Event("blur"));

    // placeholder must be gone (no blank slot stuck in the DOM)
    expect(document.querySelector("[data-neony-dnd-placeholder]")).toBeNull();
    expect(a.style.position).not.toBe("fixed");
  });
});
