/**
 * Unit tests for engine.js — the NeonyEngine patch application engine.
 *
 * Covers: mount, applyMessage revision tracking (stale drop, gap
 * resync), and every patch op (create, remove, replace, reorder,
 * update_attrs, update_styles, set_text, move).
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import { loadRuntime } from "./load.js";

let rt;

beforeEach(() => {
  rt = loadRuntime(["builder.js", "engine.js"]);
});

/** Build a PatchMessage-shaped object. */
function makeMsg(rev, ops) {
  return { rev, ops };
}

/** Mount a minimal root so the engine has a live tree. */
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
    // jsdom's CSSStyleDeclaration drops unknown properties entirely, so
    // assert the writes/removes themselves: both the standard and the
    // -webkit- prefixed variant must be touched.
    const setProperty = vi.spyOn(a.style, "setProperty");
    const removeProperty = vi.spyOn(a.style, "removeProperty");
    engine.applyOps([{ op: "update_styles", key: "a", set: { "backdrop-filter": "blur(8px)" }, remove: [] }]);
    expect(setProperty).toHaveBeenCalledWith("backdrop-filter", "blur(8px)");
    expect(setProperty).toHaveBeenCalledWith("-webkit-backdrop-filter", "blur(8px)");
    engine.applyOps([{ op: "update_styles", key: "a", set: {}, remove: ["backdrop-filter"] }]);
    expect(removeProperty).toHaveBeenCalledWith("backdrop-filter");
    expect(removeProperty).toHaveBeenCalledWith("-webkit-backdrop-filter");
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
