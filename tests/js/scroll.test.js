/**
 * Unit tests for the internal scroll commands and StickToBottom autostick.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import { loadRuntime } from "./load.js";

window.lumiview = { listen: vi.fn(), invoke: vi.fn(() => Promise.resolve()), window: {} };

const { neony } = loadRuntime();

function mountNode(node) {
  neony.engine.mount({ rev: 1, ops: [{ op: "create", key: node.key, node }] });
  return document.querySelector(`[data-neony-key='${node.key}']`);
}

describe("scroll commands", () => {
  beforeEach(() => {
    window.lumiview = { listen: vi.fn(), invoke: vi.fn(() => Promise.resolve()), window: {} };
  });

  it("scrollToBottom scrolls to scrollHeight - clientHeight", () => {
    const el = mountNode({ key: "list", tag: "div" });
    el.scrollTo = vi.fn();
    Object.defineProperty(el, "scrollHeight", { value: 500, configurable: true });
    Object.defineProperty(el, "clientHeight", { value: 200, configurable: true });
    expect(neony.scrollToBottom("list", "smooth")).toBe(true);
    expect(el.scrollTo).toHaveBeenCalledWith({ top: 300, behavior: "smooth" });
  });

  it("scrollToTop scrolls to 0", () => {
    const el = mountNode({ key: "list", tag: "div" });
    el.scrollTo = vi.fn();
    expect(neony.scrollToTop("list", "smooth")).toBe(true);
    expect(el.scrollTo).toHaveBeenCalledWith({ top: 0, behavior: "smooth" });
  });
});

describe("autostick", () => {
  beforeEach(() => {
    window.lumiview = { listen: vi.fn(), invoke: vi.fn(() => Promise.resolve()), window: {} };
  });

  it("keeps a pinned container at the bottom when children arrive", async () => {
    const el = mountNode({ key: "list", tag: "div", attrs: { "data-neony-autostick": "true" } });
    await new Promise((resolve) => setTimeout(resolve, 0));

    Object.defineProperty(el, "scrollHeight", { value: 500, configurable: true });
    Object.defineProperty(el, "clientHeight", { value: 200, configurable: true });
    Object.defineProperty(el, "scrollTop", { value: 400, writable: true, configurable: true });

    el.appendChild(document.createElement("div"));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(el.scrollTop).toBe(500);
  });
});
