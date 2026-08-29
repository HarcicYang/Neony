/**
 * Tests for markdown.js — frontend markdown rendering glue.
 *
 * Loads the vendored markdown-it / highlight.js bundles plus the full
 * runtime (index.js creates window.neony; markdown.js attaches the
 * glue).  The managed markdown root ships its raw source as text
 * content; the engine's mount conversion renders it.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import { loadRuntime } from "./load.js";

const FILES = [
  "vendor/markdown-it.min.js",
  "vendor/highlight.min.js",
  "builder.js",
  "engine.js",
  "index.js",
  "markdown.js",
];

let neony;
let invoke;

beforeEach(() => {
  // window.lumiview MUST be set before the runtime eval — the IIFE
  // early-returns (never registering its document listeners) otherwise.
  invoke = vi.fn(() => Promise.resolve());
  window.lumiview = { listen: vi.fn(), invoke, window: { minimize: vi.fn(), toggleMaximize: vi.fn(), close: vi.fn() } };
  neony = loadRuntime(FILES).neony;
});

function mountMarkdown(key, source) {
  neony.mount({
    rev: 1,
    ops: [{ op: "create", key, node: { key, tag: "div", attrs: { "data-neony-markdown": "true" }, text: source } }],
  });
  return document.querySelector(`[data-neony-key='${key}']`);
}

describe("markdown rendering (mount conversion)", () => {
  it("renders headings, emphasis, inline code and lists", () => {
    const el = mountMarkdown("md1", "# Title\n\n**bold** and *italic*\n\n`code`\n\n- one\n- two\n");
    expect(el.querySelector("h1").textContent).toBe("Title");
    expect(el.querySelector("strong").textContent).toBe("bold");
    expect(el.querySelector("em").textContent).toBe("italic");
    expect(el.querySelector("code").textContent).toBe("code");
    expect(el.querySelectorAll("li").length).toBe(2);
  });

  it("escapes raw HTML in the source (html: false)", () => {
    const el = mountMarkdown("md2", 'hello <img src=x onerror="alert(1)"> <b>bold</b>');
    expect(el.querySelector("img")).toBeNull();
    expect(el.querySelector("b")).toBeNull();
    expect(el.textContent).toContain("<b>bold</b>");
  });

  it("renders GFM tables", () => {
    const el = mountMarkdown("md3", "| a | b |\n| --- | --- |\n| 1 | 2 |\n");
    expect(el.querySelector("table")).not.toBeNull();
    expect(el.querySelectorAll("th").length).toBe(2);
    expect(el.querySelectorAll("td").length).toBe(2);
  });

  it("highlights fenced code blocks with hljs", () => {
    const el = mountMarkdown("md4", "```python\nprint('hi')\n```\n");
    const code = el.querySelector("pre code");
    expect(code).not.toBeNull();
    expect(code.className).toContain("hljs");
    expect(code.className).toContain("language-python");
    // Real tokens: the string content is wrapped in a highlight span.
    expect(code.querySelector("span.hljs-string, span.hljs-built_in, span")).not.toBeNull();
  });

  it("escapes unknown-language code blocks without highlighting", () => {
    const el = mountMarkdown("md5", "```\n<b>raw & stuff</b>\n```\n");
    const code = el.querySelector("pre code");
    expect(code.className).toContain("hljs");
    expect(code.querySelector("b")).toBeNull();
    expect(code.textContent).toContain("<b>raw & stuff</b>");
  });
});

describe("markdown.set (streaming updates)", () => {
  it("re-renders the whole source idempotently", () => {
    const el = mountMarkdown("md6", "# One");
    expect(el.querySelector("h1").textContent).toBe("One");

    expect(neony.markdown.set("md6", "# Two\n\nparagraph")).toBe(true);
    expect(el.querySelector("h1").textContent).toBe("Two");
    expect(el.querySelector("p").textContent).toBe("paragraph");

    // Same source again — stable output, no throw.
    expect(neony.markdown.set("md6", "# Two\n\nparagraph")).toBe(true);
    expect(el.querySelector("h1").textContent).toBe("Two");
  });

  it("fades the newest block on every streaming update", () => {
    const el = mountMarkdown("md9", "# One");
    el.setAttribute("data-neony-streaming", "true");

    neony.markdown.set("md9", "# One\n\nfirst paragraph");
    const p1 = el.querySelector("p");
    expect(p1.classList.contains("neony-stream-chunk")).toBe(true);

    // Each update re-fades whatever block is newest now.
    neony.markdown.set("md9", "# One\n\nfirst paragraph\n\nsecond paragraph");
    const blocks = el.querySelectorAll(".neony-stream-chunk");
    expect(blocks.length).toBe(1);
    expect(blocks[0].textContent).toBe("second paragraph");
  });

  it("does not tag blocks when no stream is running", () => {
    const el = mountMarkdown("md10", "# One");
    neony.markdown.set("md10", "# One\n\nparagraph");
    expect(el.querySelectorAll(".neony-stream-chunk").length).toBe(0);
  });

  it("returns false for unknown keys", () => {
    expect(neony.markdown.set("ghost", "# nope")).toBe(false);
  });

  it("reset re-renders from the element's text content", () => {
    const el = mountMarkdown("md7", "# Source");
    // Simulate a resync re-mount: the engine rebuilt the element with the
    // raw source as its text content.
    el.textContent = "# Rebuilt";
    expect(neony.markdown.reset("md7")).toBe(true);
    expect(el.querySelector("h1").textContent).toBe("Rebuilt");
  });
});

describe("markdown links", () => {
  it("routes link clicks through the open_external command", () => {
    const el = mountMarkdown("md8", "[site](https://example.com/page)\n");
    const anchor = el.querySelector("a");
    const event = new window.MouseEvent("click", { bubbles: true, cancelable: true });
    anchor.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
    expect(invoke).toHaveBeenCalledWith("neony.open_external", { url: "https://example.com/page" });
  });

  it("ignores clicks outside markdown roots", () => {
    const outside = document.createElement("a");
    outside.href = "https://example.com/other";
    // preventDefault: jsdom would otherwise attempt a navigation on the
    // default click (which the app's native policy blocks for real).
    outside.addEventListener("click", (e) => e.preventDefault());
    document.body.appendChild(outside);
    outside.dispatchEvent(new window.MouseEvent("click", { bubbles: true, cancelable: true }));
    expect(invoke).not.toHaveBeenCalled();
  });
});
