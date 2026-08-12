import { describe, expect, it, vi, beforeEach } from "vitest";
import { loadRuntime } from "./load.js";

describe("vertical drag in a wrapping grid", () => {
  let invoke;
  beforeEach(() => {
    invoke = vi.fn(() => Promise.resolve());
    window.lumiview = { listen: vi.fn(), invoke, window: { minimize: vi.fn(), toggleMaximize: vi.fn(), close: vi.fn() } };
    if (globalThis.__neonyDndReset) globalThis.__neonyDndReset();
  });

  function load() {
    return loadRuntime(["builder.js", "engine.js", "index.js"]);
  }

  // 4 per row, 76px cards + 8px gap; rows at y=100..176 and y=184..260
  const CARD_W = 76, GAP = 8, ROW_H = 76;
  function rowX(i) { return 4 + (i % 4) * (CARD_W + GAP); }
  function rowY(i) { return 100 + Math.floor(i / 4) * (CARD_W + GAP); }

  function mount() {
    const rt = load();
    const cards = [];
    for (let i = 1; i <= 8; i++) {
      cards.push({ key: `g${i}`, tag: "div", styles: { width: "76px", height: "76px" }, attrs: { "data-neony-drag": `g${i}` } });
    }
    rt.neony.mount({ rev: 1, ops: [{ op: "create", key: "page", node: { key: "page", tag: "div", children: [
      { key: "grid", tag: "div", styles: { display: "flex", "flex-direction": "row", "flex-wrap": "wrap", "max-width": "336px" }, children: cards },
    ]}}] });
    const els = {};
    for (let i = 1; i <= 8; i++) {
      const el = document.querySelector(`[data-neony-key='g${i}']`);
      el.getBoundingClientRect = () => ({ left: rowX(i), top: rowY(i), width: CARD_W, height: ROW_H });
      els[`g${i}`] = el;
    }
    const grid = document.querySelector("[data-neony-key='grid']");
    grid.getBoundingClientRect = () => ({ left: 0, top: 100, width: 336, height: 236 });
    return { rt, els, grid };
  }

  function mouse(type, x, y, target = document) {
    const e = new window.MouseEvent(type, { bubbles: true, cancelable: true });
    Object.defineProperty(e, "clientX", { value: x });
    Object.defineProperty(e, "clientY", { value: y });
    Object.defineProperty(e, "button", { value: 0 });
    target.dispatchEvent(e);
  }

  it("re-homes the slot to the row above when dragging vertically", () => {
    const { rt, els, grid } = mount();
    const g8 = els.g8; // row 2, col 4
    const g5 = els.g5; // row 2, col 1
    const g2 = els.g2; // row 1, col 2
    const g1 = els.g1; // row 1, col 1
    let over = g8;
    document.elementFromPoint = () => over;

    mouse("mousedown", 4 + 3 * (CARD_W + GAP) + 30, rowY(8) + 30, g8);
    mouse("mousemove", 4 + 3 * (CARD_W + GAP) + 30, rowY(8) + 30, g8); // below threshold
    // drag g8 (row 2) UP to hover g2 (row 1) — vertical motion
    over = g2;
    mouse("mousemove", rowX(2) + 10, rowY(2) + 10, g8);
    const ph = document.querySelector("[data-neony-dnd-placeholder]");
    expect(ph).not.toBeNull();
    expect(ph.parentNode).toBe(grid);
    // cursor at g2's TOP half → slot BEFORE g2 (row 1, col 2)
    expect(ph.previousSibling).toBe(g1 || null);
  });
});
