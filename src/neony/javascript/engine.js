/**
 * Maintains the live DOM tree and applies JSON patches (registry,
 * root, and a revision counter for gap detection).
 */
class NeonyEngine {
    constructor() {
        /** @type {Map<string, Element>} key → live DOM node */
        this.registry = new Map();
        /** @type {Element|null} */
        this.root = null;
        /** @type {Element|null} */
        this.container = null;
        /** @type {number} monotonic revision of the last applied patch message */
        this.lastRev = 0;
        /** @type {object|null} buffered multi-chunk patch batch */
        this.pendingBatch = null;
    }

    /**
     * Full initial render: clear the container, build the tree from the
     * first CREATE patch, append it.
     * @param {object} msg - PatchMessage with rev and ops[0] = CreatePatch
     * @returns {string} JSON ack: {ok: true, rev: N}
     */
    mount(msg) {
        this.registry.clear();
        this.pendingBatch = null;

        // The browser's 8px body margin would leave a white ring around the root.
        document.body.style.margin = "0";
        document.body.style.padding = "0";

        this.container = document.querySelector("#neony-root") || document.body;
        this.container.innerHTML = "";

        const createOp = msg.ops[0];
        this.root = buildNode(createOp.node, this.registry);
        this.container.appendChild(this.root);
        this.lastRev = msg.rev;

        // Notify Python that the engine is ready
        if (window.lumiview && window.lumiview.invoke) {
            window.lumiview.invoke("neony.ready", { rev: msg.rev }).catch(() => {});
        }

        return JSON.stringify({ ok: true, rev: msg.rev });
    }

    /**
     * Apply a batch of patches to the live DOM.
     * @param {Array<object>} ops
     */
    applyOps(ops) {
        for (const op of ops) {
            switch (op.op) {
                case "create":
                    this._create(op);
                    break;
                case "remove":
                    this._remove(op);
                    break;
                case "replace":
                    this._replace(op);
                    break;
                case "reorder":
                    this._reorder(op);
                    break;
                case "update_attrs":
                    this._updateAttrs(op);
                    break;
                case "update_styles":
                    this._updateStyles(op);
                    break;
                case "set_text":
                    this._setText(op);
                    break;
                case "move":
                    this._move(op);
                    break;
            }
        }
    }

    /**
     * Apply a PatchMessage: drop stale messages, resync on rev gaps.
     * Multi-chunk batches are buffered and applied atomically once the
     * final chunk arrives.
     * @param {object} msg - {rev: number, ops: Array, chunks?: number}
     */
    applyMessage(msg) {
        if (msg.rev <= this.lastRev) return;

        const chunkCount = msg.chunks || 1;
        if (chunkCount > 1) {
            this._applyBatchChunk(msg, chunkCount);
            return;
        }

        if (this._hasRevGap(msg.rev)) return;

        this.applyOps(msg.ops);
        this.lastRev = msg.rev;
    }

    /**
     * Buffer one chunk of a split render.  The batch is applied only when
     * every chunk has arrived, so a partially delivered render can never
     * leave the DOM in a mixed state.
     */
    _applyBatchChunk(msg, chunkCount) {
        const batch = msg.batch || "";
        const chunk = msg.chunk || 0;

        if (!this.pendingBatch || this.pendingBatch.batch !== batch) {
            if (this._hasRevGap(msg.rev)) return;
            this.pendingBatch = {
                batch: batch,
                rev: msg.rev,
                chunks: chunkCount,
                ops: new Array(chunkCount),
                received: 0,
            };
        }

        const pending = this.pendingBatch;
        if (pending.rev !== msg.rev || pending.chunks !== chunkCount || chunk < 0 || chunk >= pending.chunks) {
            this.pendingBatch = null;
            this._requestResync();
            return;
        }
        if (pending.ops[chunk]) return; // duplicate chunk — ignore

        pending.ops[chunk] = msg.ops;
        pending.received += 1;
        if (pending.received < pending.chunks) return;

        this.pendingBatch = null;
        if (this._hasRevGap(pending.rev)) return;

        const ops = [];
        for (const part of pending.ops) {
            for (const op of part) ops.push(op);
        }
        this.applyOps(ops);
        this.lastRev = pending.rev;
    }

    _hasRevGap(rev) {
        if (rev <= this.lastRev + 1) return false;
        this._requestResync();
        return true;
    }

    _requestResync() {
        if (window.lumiview && window.lumiview.invoke) {
            window.lumiview.invoke("neony.resync", { rev: this.lastRev })
                .catch(function () {});
        }
    }

    _create(op) {
        // Clean up any prior subtree with this key first.
        const existing = this.registry.get(op.key);
        if (existing) {
            unregisterSubtree(existing, this.registry);
            if (existing.parentNode) existing.parentNode.removeChild(existing);
        }

        const newNode = buildNode(op.node, this.registry);

        if (op.parent) {
            const parent = this.registry.get(op.parent);
            if (parent) {
                if (op.index !== null && op.index !== undefined && op.index < parent.children.length) {
                    parent.insertBefore(newNode, parent.children[op.index]);
                } else {
                    parent.appendChild(newNode);
                }
            }
        }
    }

    _remove(op) {
        const el = this.registry.get(op.key);
        if (!el) return;
        unregisterSubtree(el, this.registry);
        if (el.parentNode) el.parentNode.removeChild(el);
    }

    _replace(op) {
        const oldEl = this.registry.get(op.key);
        if (!oldEl) return;
        unregisterSubtree(oldEl, this.registry);

        const newEl = buildNode(op.node, this.registry);
        if (oldEl.parentNode) {
            oldEl.parentNode.replaceChild(newEl, oldEl);
        }
    }

    _reorder(op) {
        const parent = this.registry.get(op.parent);
        if (!parent) return;

        // Walk from the end so each misplaced node is inserted before the
        // already-correct suffix. Nodes that are already in place are untouched.
        let anchor = null;
        for (let i = op.ordered_keys.length - 1; i >= 0; i--) {
            const child = this.registry.get(op.ordered_keys[i]);
            if (!child || child.parentNode !== parent) continue;
            if (child.nextElementSibling !== anchor) parent.insertBefore(child, anchor);
            anchor = child;
        }
    }

    _updateAttrs(op) {
        const el = this.registry.get(op.key);
        if (!el) return;

        const setAttrs = op.set || {};
        for (const [name, value] of Object.entries(setAttrs)) {
            // IDL property for `checked`/`value`: setAttribute("value")
            // can refire `input` in WebKitGTK.
            if (name === "checked" && (el.type === "checkbox" || el.type === "radio")) {
                el.checked = true;
            } else if (name === "value" && el.tagName === "INPUT") {
                if (el.value !== value) el.value = value;
            } else if (el.getAttribute(name) !== String(value)) {
                el.setAttribute(name, value);
            }
        }
        const removeAttrs = op.remove || [];
        for (const name of removeAttrs) {
            if (name === "checked" && (el.type === "checkbox" || el.type === "radio")) {
                el.checked = false;
            } else if (name === "value" && el.tagName === "INPUT") {
                el.value = "";
            } else {
                el.removeAttribute(name);
            }
        }
    }

    _updateStyles(op) {
        const el = this.registry.get(op.key);
        if (!el) return;

        const setStyles = op.set || {};
        for (const [prop, value] of Object.entries(setStyles)) {
            if (el.style.getPropertyValue(prop) !== String(value)) {
                el.style.setProperty(prop, value);
            }
            // WebKitGTK needs the prefixed variant of backdrop-filter
            if (prop === "backdrop-filter" && el.style.getPropertyValue("-webkit-backdrop-filter") !== String(value)) {
                el.style.setProperty("-webkit-backdrop-filter", value);
            }
            // user-select also needs -webkit- and -moz- prefixes.
            if (prop === "user-select") {
                if (el.style.getPropertyValue("-webkit-user-select") !== String(value)) {
                    el.style.setProperty("-webkit-user-select", value);
                }
                if (el.style.getPropertyValue("-moz-user-select") !== String(value)) {
                    el.style.setProperty("-moz-user-select", value);
                }
            }
        }
        const removeStyles = op.remove || [];
        for (const prop of removeStyles) {
            el.style.removeProperty(prop);
            if (prop === "backdrop-filter") {
                el.style.removeProperty("-webkit-backdrop-filter");
            }
            if (prop === "user-select") {
                el.style.removeProperty("-webkit-user-select");
                el.style.removeProperty("-moz-user-select");
            }
        }
    }

    _setText(op) {
        const el = this.registry.get(op.key);
        if (el) {
            el.textContent = op.text;
        }
    }

    _move(op) {
        const el = this.registry.get(op.key);
        if (!el) return;
        const toParent = this.registry.get(op.to_parent);
        if (!toParent) return;

        if (el.parentNode) el.parentNode.removeChild(el);

        if (op.to_index !== null && op.to_index !== undefined && op.to_index < toParent.children.length) {
            toParent.insertBefore(el, toParent.children[op.to_index]);
        } else {
            toParent.appendChild(el);
        }
    }
}
