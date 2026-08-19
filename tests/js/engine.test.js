/**
 * Unit tests for engine.js — mount, revision tracking, and patch ops.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import { loadRuntime } from "./load.js";

let rt;

beforeEach(() => {
  rt = loadRuntime(["builder.js", "engine.js"]);
});

function makeMsg(rev, ops) {
  return { rev, ops };
}

function mountEngine(engine, rev = 1, node = { key: "root", tag: "div" }) {
  engine.mount(makeMsg(rev, [{ op: "create", key: node.key, node }]));
  return engine;
}

describe("NeonyEngine.mount", () => {
  it("builds the tree into the container and acks", () => {
    const engine = new rt.NeonyEngine();
    const msg = makeMsg(1, [
      {
        op: "create",
        key: "root",
        node: { key: "root", tag: "div", children: [{ key: "a", tag: "span", text: "hi" }] },
      },
    ]);
    const ack = engine.mount(msg);

    expect(JSON.parse(ack)).toEqual({ ok: true, rev: 1 });
    expect(engine.lastRev).toBe(1);
    expect(engine.root).not.toBeNull();
    expect(engine.container.contains(engine.root)).toBe(true);
    expect(engine.container.querySelector("[data-neony-key='a']").textContent).toBe("hi");
    expect(engine.registry.get("root")).toBe(engine.root);
  });

  it("clears the container before mounting", () => {
    const engine = mountEngine(new rt.NeonyEngine());
    engine.mount(makeMsg(2, [{ op: "create", key: "fresh", node: { key: "fresh", tag: "div" } }]));
    expect(engine.registry.has("root")).toBe(false);
    expect(engine.container.querySelector("[data-neony-key='fresh']")).not.toBeNull();
  });

  it("resets body margin and padding", () => {
    document.body.style.margin = "10px";
    document.body.style.padding = "5px";
    mountEngine(new rt.NeonyEngine());
    expect(document.body.style.margin).toBe("0px");
    expect(document.body.style.padding).toBe("0px");
  });

  it("falls back to document.body when #neony-root is absent", () => {
    const engine = new rt.NeonyEngine();
    engine.mount(makeMsg(1, [{ op: "create", key: "root", node: { key: "root", tag: "div" } }]));
    expect(engine.container).toBe(document.body);
  });

  it("uses #neony-root when present", () => {
    const host = document.createElement("div");
    host.id = "neony-root";
    document.body.appendChild(host);
    const engine = new rt.NeonyEngine();
    engine.mount(makeMsg(1, [{ op: "create", key: "root", node: { key: "root", tag: "div" } }]));
    expect(engine.container).toBe(host);
  });

  it("invokes neony.ready with the mounted rev", () => {
    const invoke = vi.fn(() => Promise.resolve());
    window.lumiview = { invoke };
    mountEngine(new rt.NeonyEngine(), 7);
    expect(invoke).toHaveBeenCalledWith("neony.ready", { rev: 7 });
  });
});

describe("revision tracking (applyMessage)", () => {
  it("drops stale messages (rev <= lastRev)", () => {
    const engine = mountEngine(new rt.NeonyEngine(), 5);
    engine.applyMessage(makeMsg(3, [{ op: "set_text", key: "root", text: "stale" }]));
    engine.applyMessage(makeMsg(5, [{ op: "set_text", key: "root", text: "equal" }]));
    expect(engine.root.textContent).toBe("");
    expect(engine.lastRev).toBe(5);
  });

  it("applies messages in order and advances lastRev", () => {
    const engine = mountEngine(new rt.NeonyEngine(), 1);
    engine.applyMessage(makeMsg(2, [{ op: "set_text", key: "root", text: "hi" }]));
    expect(engine.lastRev).toBe(2);
    expect(engine.root.textContent).toBe("hi");
  });

  it("streams children after a large shallow mount", () => {
    const engine = new rt.NeonyEngine();
    engine.mount(makeMsg(1, [
      { op: "create", key: "root", node: { key: "root", tag: "div" } },
    ]));
    const a = makeMsg(2, [
      { op: "create", key: "a", parent: "root", index: 0, node: { key: "a", tag: "span", text: "A" } },
    ]);
    const b = makeMsg(2, [
      { op: "create", key: "b", parent: "root", index: 1, node: { key: "b", tag: "span", text: "B" } },
    ]);
    a.batch = "r2"; a.chunk = 0; a.chunks = 2;
    b.batch = "r2"; b.chunk = 1; b.chunks = 2;

    engine.applyMessage(a);
    engine.applyMessage(b);

    expect(engine.registry.get("root").children.length).toBe(2);
    expect(engine.registry.get("a").textContent).toBe("A");
    expect(engine.registry.get("b").textContent).toBe("B");
    expect(engine.lastRev).toBe(2);
  });

  it("applies multi-chunk batches atomically once complete", () => {
    const engine = mountEngine(new rt.NeonyEngine(), 1);
    const a = makeMsg(2, [{ op: "set_text", key: "root", text: "part-a" }]);
    const b = makeMsg(2, [{ op: "set_text", key: "root", text: "part-b" }]);
    a.batch = "r2"; a.chunk = 0; a.chunks = 2;
    b.batch = "r2"; b.chunk = 1; b.chunks = 2;

    engine.applyMessage(a);
    expect(engine.lastRev).toBe(1);
    expect(engine.root.textContent).toBe(""); // buffered, not applied

    engine.applyMessage(b);
    expect(engine.lastRev).toBe(2);
    expect(engine.root.textContent).toBe("part-b"); // chunks applied in order
  });

  it("ignores duplicate chunks inside a pending batch", () => {
    const engine = mountEngine(new rt.NeonyEngine(), 1);
    const a = makeMsg(2, [{ op: "set_text", key: "root", text: "a" }]);
    const b = makeMsg(2, [{ op: "set_text", key: "root", text: "b" }]);
    a.batch = "r2"; a.chunk = 0; a.chunks = 2;
    b.batch = "r2"; b.chunk = 1; b.chunks = 2;

    engine.applyMessage(a);
    engine.applyMessage(a); // duplicate ignored
    engine.applyMessage(b);
    expect(engine.lastRev).toBe(2);
    expect(engine.root.textContent).toBe("b");
  });

  it("requests a resync when a batch starts on a rev gap", () => {
    const invoke = vi.fn(() => Promise.resolve());
    window.lumiview = { invoke };
    const engine = mountEngine(new rt.NeonyEngine(), 1);
    const a = makeMsg(3, [{ op: "set_text", key: "root", text: "a" }]);
    a.batch = "r3"; a.chunk = 0; a.chunks = 2;

    engine.applyMessage(a);
    expect(invoke).toHaveBeenCalledWith("neony.resync", { rev: 1 });
    expect(engine.root.textContent).toBe("");
    expect(engine.lastRev).toBe(1);
  });
  it("requests a resync on a revision gap and skips the ops", () => {
    const invoke = vi.fn(() => Promise.resolve());
    window.lumiview = { invoke };
    const engine = mountEngine(new rt.NeonyEngine(), 1);
    engine.applyMessage(makeMsg(3, [{ op: "set_text", key: "root", text: "skipped" }]));
    expect(invoke).toHaveBeenCalledWith("neony.resync", { rev: 1 });
    expect(engine.root.textContent).toBe("");
    expect(engine.lastRev).toBe(1);
  });
});

describe("patch ops", () => {
  function baseEngine() {
    return mountEngine(new rt.NeonyEngine(), 1, {
      key: "root",
      tag: "div",
      children: [
        { key: "a", tag: "span", text: "A" },
        { key: "b", tag: "span", text: "B" },
      ],
    });
  }

  it("create: appends a new child and registers it", () => {
    const engine = baseEngine();
    engine.applyOps([{ op: "create", key: "c", node: { key: "c", tag: "span", text: "C" }, parent: "root", index: 2 }]);
    expect(engine.root.children.length).toBe(3);
    expect(engine.registry.get("c").textContent).toBe("C");
  });

  it("create: inserts at the given index", () => {
    const engine = baseEngine();
    engine.applyOps([{ op: "create", key: "x", node: { key: "x", tag: "span", text: "X" }, parent: "root", index: 0 }]);
    expect(engine.root.children[0]).toBe(engine.registry.get("x"));
    expect(engine.root.children[1]).toBe(engine.registry.get("a"));
  });

  it("create: reusing an existing key cleans up the old subtree first", () => {
    const engine = baseEngine();
    engine.applyOps([{ op: "create", key: "a", node: { key: "a", tag: "span", text: "new A" }, parent: "root", index: 0 }]);
    expect(engine.root.children.length).toBe(2); // replaced, not duplicated
    expect(engine.registry.get("a").textContent).toBe("new A");
  });

  it("remove: detaches and unregisters the subtree", () => {
    const engine = baseEngine();
    engine.applyOps([{ op: "remove", key: "a" }]);
    expect(engine.root.children.length).toBe(1);
    expect(engine.registry.has("a")).toBe(false);
  });

  it("remove: unknown key is a silent no-op", () => {
    const engine = baseEngine();
    expect(() => engine.applyOps([{ op: "remove", key: "nope" }])).not.toThrow();
  });

  it("move: re-parents the SAME element across containers", () => {
    const engine = mountEngine(new rt.NeonyEngine(), 1, {
      key: "root",
      tag: "div",
      children: [
        { key: "grid", tag: "div", children: [{ key: "g1", tag: "span" }] },
        { key: "tray", tag: "div", children: [{ key: "t1", tag: "span", text: "T" }] },
      ],
    });
    const t1 = engine.registry.get("t1");
    engine.applyOps([{ op: "move", key: "t1", to_parent: "grid", to_index: 0 }]);
    expect(engine.registry.get("t1")).toBe(t1); // same node, still registered
    expect(engine.registry.get("grid").children[0]).toBe(t1);
    expect(engine.registry.get("tray").children.length).toBe(0);
  });

  it("replace: swaps the node in place with the same key", () => {
    const engine = baseEngine();
    engine.applyOps([{ op: "replace", key: "a", node: { key: "a", tag: "strong", text: "bold" } }]);
    expect(engine.root.children[0].tagName).toBe("STRONG");
    expect(engine.root.children[0].textContent).toBe("bold");
    expect(engine.registry.get("a")).toBe(engine.root.children[0]);
  });

  it("reorder: reorders children to the given key order", () => {
    const engine = baseEngine();
    engine.applyOps([{ op: "reorder", parent: "root", ordered_keys: ["b", "a"] }]);
    expect(engine.root.children[0]).toBe(engine.registry.get("b"));
    expect(engine.root.children[1]).toBe(engine.registry.get("a"));
  });


  it("reorder: skips DOM moves when children already match", () => {
    const engine = baseEngine();
    const insertBefore = vi.spyOn(engine.root, "insertBefore");
    engine.applyOps([{ op: "reorder", parent: "root", ordered_keys: ["a", "b"] }]);
    expect(insertBefore).not.toHaveBeenCalled();
  });

  it("update_attrs: skips an identical attribute write", () => {
    const engine = baseEngine();
    const a = engine.registry.get("a");
    a.setAttribute("title", "same");
    const setAttribute = vi.spyOn(a, "setAttribute");
    engine.applyOps([{ op: "update_attrs", key: "a", set: { title: "same" }, remove: [] }]);
    expect(setAttribute).not.toHaveBeenCalled();
  });

  it("update_styles: skips an identical style write", () => {
    const engine = baseEngine();
    const a = engine.registry.get("a");
    a.style.setProperty("color", "red");
    const setProperty = vi.spyOn(a.style, "setProperty");
    engine.applyOps([{ op: "update_styles", key: "a", set: { color: "red" }, remove: [] }]);
    expect(setProperty).not.toHaveBeenCalled();
  });

  it("update_attrs: sets attributes", () => {
    const engine = baseEngine();
    engine.applyOps([{ op: "update_attrs", key: "a", set: { title: "hello" }, remove: [] }]);
    expect(engine.registry.get("a").getAttribute("title")).toBe("hello");
  });

  it("update_attrs: removes attributes", () => {
    const engine = baseEngine();
    engine.applyOps([{ op: "update_attrs", key: "a", set: { title: "hello" }, remove: [] }]);
    engine.applyOps([{ op: "update_attrs", key: "a", set: {}, remove: ["title"] }]);
    expect(engine.registry.get("a").hasAttribute("title")).toBe(false);
  });

  it("update_attrs: sets checkbox checked via IDL property", () => {
    const engine = mountEngine(new rt.NeonyEngine(), 1, {
      key: "root",
      tag: "div",
      children: [{ key: "cb", tag: "input", attrs: { type: "checkbox" } }],
    });
    engine.applyOps([{ op: "update_attrs", key: "cb", set: { checked: "" }, remove: [] }]);
    expect(engine.registry.get("cb").checked).toBe(true);
    engine.applyOps([{ op: "update_attrs", key: "cb", set: {}, remove: ["checked"] }]);
    expect(engine.registry.get("cb").checked).toBe(false);
  });

  it("update_attrs: sets input value via IDL property, skips identical writes", () => {
    const engine = mountEngine(new rt.NeonyEngine(), 1, {
      key: "root",
      tag: "div",
      children: [{ key: "inp", tag: "input", attrs: { type: "text" } }],
    });
    const inp = engine.registry.get("inp");
    inp.value = "existing";
    engine.applyOps([{ op: "update_attrs", key: "inp", set: { value: "existing" }, remove: [] }]);
    expect(inp.value).toBe("existing");
    engine.applyOps([{ op: "update_attrs", key: "inp", set: { value: "new" }, remove: [] }]);
    expect(inp.value).toBe("new");
  });

  it("update_styles: sets and removes CSS properties", () => {
    const engine = baseEngine();
    engine.applyOps([{ op: "update_styles", key: "a", set: { color: "red" }, remove: [] }]);
    expect(engine.registry.get("a").style.color).toBe("red");
    engine.applyOps([{ op: "update_styles", key: "a", set: {}, remove: ["color"] }]);
    expect(engine.registry.get("a").style.color).toBe("");
  });

  it("update_styles: mirrors -webkit- prefix for backdrop-filter", () => {
    const engine = baseEngine();
    const a = engine.registry.get("a");
    // jsdom drops unknown CSS properties — assert the writes/removes themselves.
    const setProperty = vi.spyOn(a.style, "setProperty");
    const removeProperty = vi.spyOn(a.style, "removeProperty");
    engine.applyOps([{ op: "update_styles", key: "a", set: { "backdrop-filter": "blur(8px)" }, remove: [] }]);
    expect(setProperty).toHaveBeenCalledWith("backdrop-filter", "blur(8px)");
    expect(setProperty).toHaveBeenCalledWith("-webkit-backdrop-filter", "blur(8px)");
    engine.applyOps([{ op: "update_styles", key: "a", set: {}, remove: ["backdrop-filter"] }]);
    expect(removeProperty).toHaveBeenCalledWith("backdrop-filter");
    expect(removeProperty).toHaveBeenCalledWith("-webkit-backdrop-filter");
  });

  it("update_styles: mirrors -webkit- and -moz- prefixes for user-select", () => {
    const engine = baseEngine();
    const a = engine.registry.get("a");
    const setProperty = vi.spyOn(a.style, "setProperty");
    const removeProperty = vi.spyOn(a.style, "removeProperty");
    engine.applyOps([{ op: "update_styles", key: "a", set: { "user-select": "none" }, remove: [] }]);
    expect(setProperty).toHaveBeenCalledWith("user-select", "none");
    expect(setProperty).toHaveBeenCalledWith("-webkit-user-select", "none");
    expect(setProperty).toHaveBeenCalledWith("-moz-user-select", "none");
    engine.applyOps([{ op: "update_styles", key: "a", set: {}, remove: ["user-select"] }]);
    expect(removeProperty).toHaveBeenCalledWith("user-select");
    expect(removeProperty).toHaveBeenCalledWith("-webkit-user-select");
    expect(removeProperty).toHaveBeenCalledWith("-moz-user-select");
  });

  it("set_text: replaces text content", () => {
    const engine = baseEngine();
    engine.applyOps([{ op: "set_text", key: "a", text: "changed" }]);
    expect(engine.registry.get("a").textContent).toBe("changed");
  });

  it("move: relocates an element to another parent", () => {
    const engine = mountEngine(new rt.NeonyEngine(), 1, {
      key: "root",
      tag: "div",
      children: [
        { key: "a", tag: "span", text: "A" },
        { key: "box", tag: "div", children: [{ key: "b", tag: "span", text: "B" }] },
      ],
    });
    engine.applyOps([{ op: "move", key: "a", to_parent: "box", to_index: 0 }]);
    expect(engine.registry.get("box").children[0]).toBe(engine.registry.get("a"));
    expect(engine.root.children.length).toBe(1);
  });

  it("ops for unknown keys are silent no-ops", () => {
    const engine = baseEngine();
    expect(() =>
      engine.applyOps([
        { op: "set_text", key: "nope", text: "x" },
        { op: "update_styles", key: "nope", set: { color: "red" }, remove: [] },
        { op: "update_attrs", key: "nope", set: { a: "b" }, remove: [] },
        { op: "reorder", parent: "nope", ordered_keys: [] },
        { op: "move", key: "nope", to_parent: "root", to_index: 0 },
      ]),
    ).not.toThrow();
  });
});

describe("cross-board drop pipeline (settle + MovePatch)", () => {
  it("re-parents the settle-moved element without a blank slot", () => {
    const engine = mountEngine(new rt.NeonyEngine(), 1, {
      key: "page",
      tag: "div",
      children: [
        { key: "grid", tag: "div", children: [{ key: "g1", tag: "span" }, { key: "g2", tag: "span" }] },
        { key: "tray", tag: "div", children: [{ key: "t1", tag: "span", text: "T" }] },
      ],
    });
    const t1 = engine.registry.get("t1");

    // Step 1: the settle glides the source into the target board's slot
    // (JS dndSettle moves the DOM node directly).
    const grid = engine.registry.get("grid");
    grid.insertBefore(t1, grid.children[0]);

    // Step 2: the Python handler moves the model; the diff emits a
    // MovePatch that re-parents the SAME element at the SAME place —
    // must be a no-op (no flash, no blank slot).
    engine.applyOps([{ op: "move", key: "t1", to_parent: "grid", to_index: 0 }]);
    expect(engine.registry.get("t1")).toBe(t1);
    expect(grid.children[0]).toBe(t1);
    expect(engine.registry.get("tray").children.length).toBe(0);
  });
});

describe("cross-board drop end-to-end (index.js dnd + MovePatch)", () => {
  it("settle glides the source into the target board; MovePatch re-parents the same element", async () => {
    // window.lumiview MUST be set before the runtime eval — the IIFE
    // early-returns (never registering its document listeners) otherwise.
    const invoke = vi.fn(() => Promise.resolve());
    window.lumiview = { listen: vi.fn(), invoke, window: { minimize: vi.fn(), toggleMaximize: vi.fn(), close: vi.fn() } };
    const rt = loadRuntime(["builder.js", "engine.js", "index.js"]);
    if (globalThis.__neonyDndReset) globalThis.__neonyDndReset();

    // Mount: page > (grid: g1, g2) + (tray: t1)
    rt.neony.mount({ rev: 1, ops: [{ op: "create", key: "page", node: { key: "page", tag: "div", children: [
      { key: "grid", tag: "div", styles: { "flex-direction": "row" }, attrs: { "data-neony-drag": "grid" }, children: [
        { key: "g1", tag: "span", attrs: { "data-neony-drag": "g1" } },
        { key: "g2", tag: "span", attrs: { "data-neony-drag": "g2" } },
      ]},
      { key: "tray", tag: "div", styles: { "flex-direction": "row" }, attrs: { "data-neony-drag": "tray" }, children: [
        { key: "t1", tag: "span", attrs: { "data-neony-drag": "t1" } },
      ]},
    ]}}] });

    const g1 = document.querySelector("[data-neony-key='g1']");
    const g2 = document.querySelector("[data-neony-key='g2']");
    const tray = document.querySelector("[data-neony-key='tray']");
    const t1 = document.querySelector("[data-neony-key='t1']");
    const grid = document.querySelector("[data-neony-key='grid']");

    // Drag t1 onto g2's upper half, release — settle moves t1 into the grid.
    let over = t1;
    const realFromPoint = document.elementFromPoint;
    document.elementFromPoint = () => over;
    const rects = new Map();
    for (const [el, r] of [[g1,{left:0,top:100,width:60,height:40}],[g2,{left:68,top:100,width:60,height:40}],[t1,{left:0,top:160,width:60,height:40}],[grid,{left:0,top:100,width:300,height:40}],[tray,{left:0,top:160,width:300,height:40}]]) {
      const orig = el.getBoundingClientRect;
      el.getBoundingClientRect = () => r;
      rects.set(el, orig);
    }
    try {
      const e = new window.MouseEvent("mousedown", { bubbles: true, cancelable: true });
      Object.defineProperty(e, "clientX", { value: 5 });
      Object.defineProperty(e, "clientY", { value: 170 });
      Object.defineProperty(e, "button", { value: 0 });
      t1.dispatchEvent(e);
      const m = new window.MouseEvent("mousemove", { bubbles: true, cancelable: true });
      Object.defineProperty(m, "clientX", { value: 5 });
      Object.defineProperty(m, "clientY", { value: 170 });
      t1.dispatchEvent(m);
      over = g2;
      const m2 = new window.MouseEvent("mousemove", { bubbles: true, cancelable: true });
      Object.defineProperty(m2, "clientX", { value: 9 });
      Object.defineProperty(m2, "clientY", { value: 135 });
      t1.dispatchEvent(m2);
      expect(t1.style.position).toBe("fixed"); // drag began
      const ph = document.querySelector("[data-neony-dnd-placeholder]");
      expect(ph.parentNode).toBe(grid); // slot re-homed into the grid
      over = g2;
      const u = new window.MouseEvent("mouseup", { bubbles: true, cancelable: true });
      Object.defineProperty(u, "clientX", { value: 9 });
      Object.defineProperty(u, "clientY", { value: 135 });
      t1.dispatchEvent(u);

      // Settle moved t1 INTO the grid, before g2 (same DOM node), and
      // cleared the ghost transform (no leftover translate offset).
      expect(t1.parentNode).toBe(grid);
      expect(t1.parentNode.children[1]).toBe(t1);
      expect(t1.parentNode.children[0]).toBe(g1);
      expect(t1.style.transform).toBe("");

      // The Python-side MovePatch re-parents the SAME element — no-op.
      rt.neony.applyMessage({ rev: 2, ops: [{ op: "move", key: "t1", to_parent: "grid", to_index: 1 }] });
      expect(t1.parentNode).toBe(grid);
      expect(rt.neony.engine.registry.get("t1")).toBe(t1);
    } finally {
      document.elementFromPoint = realFromPoint;
      for (const [el, orig] of rects) el.getBoundingClientRect = orig;
    }
  });
});
