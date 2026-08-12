import { describe, expect, it, vi, beforeEach } from "vitest";
import { loadRuntime } from "./load.js";

describe("wrap-grid vertical reorder (same board, cross-row)", () => {
  let invoke;
  beforeEach(() => {
    invoke = vi.fn(() => Promise.resolve());
    window.lumiview = { listen: vi.fn(), invoke, window: { minimize: vi.fn(), toggleMaximize: vi.fn(), close: vi.fn() } };
    if (globalThis.__neonyDndReset) globalThis.__neonyDndReset();
  });

  function mouse(type, x, y, target) {
    const e = new window.MouseEvent(type, { bubbles: true, cancelable: true });
    Object.defineProperty(e, "clientX", { value: x });
    Object.defineProperty(e, "clientY", { value: y });
    Object.defineProperty(e, "button", { value: 0 });
    target.dispatchEvent(e);
  }

  it("keeps the card when dragged from row 1 onto row 2", () => {
    const rt = loadRuntime(["builder.js", "engine.js", "index.js"]);
    const grid = document.createElement("div");
    grid.setAttribute("data-neony-key", "grid");
    grid.style.display = "flex";
    grid.style.flexDirection = "row";
    grid.style.flexWrap = "wrap";
    grid.style.gap = "4px";
    document.body.appendChild(grid);

    // 2 rows x 3 cols of 80px cards (wrap layout)
    const rects = [
      { left: 0, top: 100, width: 80, height: 80 },    // c1
      { left: 84, top: 100, width: 80, height: 80 },   // c2
      { left: 168, top: 100, width: 80, height: 80 },  // c3
      { left: 0, top: 184, width: 80, height: 80 },    // c4
      { left: 84, top: 184, width: 80, height: 80 },   // c5
      { left: 168, top: 184, width: 80, height: 80 },  // c6
    ];
    const cards = [];
    for (let i = 0; i < 6; i++) {
      const c = document.createElement("div");
      c.setAttribute("data-neony-key", "c" + (i + 1));
      c.setAttribute("data-neony-drag", "c" + (i + 1));
      c.getBoundingClientRect = () => rects[i];
      grid.appendChild(c);
      cards.push(c);
    }
    grid.getBoundingClientRect = () => ({ left: 0, top: 100, width: 260, height: 264 });

    const c1 = cards[0], c5 = cards[4];
    const realFromPoint = document.elementFromPoint;
    let over = c1;
    document.elementFromPoint = () => over;
    try {
      mouse("mousedown", 10, 110, c1);
      mouse("mousemove", 10, 110, c1); // below threshold
      over = c5;
      mouse("mousemove", 100, 200, c1); // past threshold — over c5, LEFT half (mid 124)
      const ph = document.querySelector("[data-neony-dnd-placeholder]");
      expect(ph).not.toBeNull();
      expect(ph.parentNode).toBe(grid);
      expect(ph.nextSibling).toBe(c5); // committed before c5

      mouse("mouseup", 100, 200, c1);

      // drop encoded on c5, before (offset_x = 0)
      const drop = invoke.mock.calls
        .filter(([name]) => name === "neony.event")
        .map(([, p]) => p)
        .find((p) => p.event_type === "drop");
      expect(drop.key).toBe("c5");
      expect(drop.offset_x).toBe(0);

      // settle: c1 back in the flow before c5 — same node, no placeholder
      expect(document.querySelector("[data-neony-dnd-placeholder]")).toBeNull();
      expect(c1.parentNode).toBe(grid);
      expect(c1.style.position).not.toBe("fixed");
      expect(c1.style.transform).toBe("");
      const order = Array.from(grid.children).map((el) => el.getAttribute("data-neony-key"));
      expect(order).toEqual(["c2", "c3", "c4", "c1", "c5", "c6"]);
      expect(grid.children.length).toBe(6); // no card lost

      // Python emits the same-board ReorderPatch — no-op on the settled DOM
      rt.neony.applyMessage({ rev: 2, ops: [{ op: "reorder", parent: "grid", ordered_keys: ["c2", "c3", "c4", "c1", "c5", "c6"] }] });
      const after = Array.from(grid.children).map((el) => el.getAttribute("data-neony-key"));
      expect(after).toEqual(["c2", "c3", "c4", "c1", "c5", "c6"]);
      expect(grid.children.length).toBe(6);
    } finally {
      document.elementFromPoint = realFromPoint;
    }
  });
});
