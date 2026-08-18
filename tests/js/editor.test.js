/**
 * Unit tests for editor.js — the RichText contenteditable internals.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import { loadRuntime } from "./load.js";

// lumiview must exist before the runtime loads (see load.js).
window.lumiview = { listen: vi.fn(), invoke: vi.fn(() => Promise.resolve()), window: {} };

const { neony } = loadRuntime();

function mountEditor(html) {
  const node = {
    key: "editor",
    tag: "div",
    attrs: { contenteditable: "true", "data-neony-rich-text": "true" },
  };
  neony.engine.mount({ rev: 1, ops: [{ op: "create", key: node.key, node }] });
  const el = document.querySelector("[data-neony-key='editor']");
  if (html) el.innerHTML = html;
  return el;
}

describe("richText internals", () => {
  beforeEach(() => {
    window.lumiview = { listen: vi.fn(), invoke: vi.fn(() => Promise.resolve()), window: {} };
  });

  it("exports ordered text and image segments", () => {
    mountEditor('a<img src="x.png" alt="pic"><img src="y.png">b');
    expect(neony.richText.exportContent("editor")).toEqual([
      { kind: "text", text: "a" },
      { kind: "image", src: "x.png", alt: "pic" },
      { kind: "image", src: "y.png", alt: "" },
      { kind: "text", text: "b" },
    ]);
  });

  it("round-trips caret positions across text and images", () => {
    const el = mountEditor('ab<img src="x.png">cd');
    // Flat units: a=0, b=1, image=2, c=3, d=4. Position 3 is after the
    // image and before "c".
    neony.richText.setCaret("editor", 3);
    expect(neony.richText.getCaret("editor")).toBe(3);
    el.focus();
  });

  it("inserts an image at the caret and moves the caret after it", () => {
    mountEditor("ab");
    neony.richText.setCaret("editor", 1);
    expect(neony.richText.insertImage("editor", "x.png", "pic", 1)).toBe(true);
    expect(neony.richText.exportContent("editor")).toEqual([
      { kind: "text", text: "a" },
      { kind: "image", src: "x.png", alt: "pic" },
      { kind: "text", text: "b" },
    ]);
    expect(neony.richText.getCaret("editor")).toBe(2);
  });

  it("loads segments from the Python model", () => {
    mountEditor("old");
    expect(
      neony.richText.loadContent("editor", [
        { kind: "text", text: "你好" },
        { kind: "image", src: "x.png", alt: "" },
      ])
    ).toBe(true);
    expect(neony.richText.exportContent("editor")).toEqual([
      { kind: "text", text: "你好" },
      { kind: "image", src: "x.png", alt: "" },
    ]);
  });

  it("merges consecutive text nodes into one text segment", () => {
    const el = mountEditor();
    el.appendChild(document.createTextNode("你"));
    el.appendChild(document.createTextNode("好"));
    expect(neony.richText.exportContent("editor")).toEqual([{ kind: "text", text: "你好" }]);
  });
});
