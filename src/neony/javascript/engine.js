/**
 * Neony DOM engine — maintains a live DOM tree and applies JSON patches.
 *
 * Owns a registry (key → Element), the current root, and a revision
 * counter used to detect missed patch messages.
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
    }

    // ── mount (full initial render) ─────────────────────────────

    /**
     * Full initial render. Clears the container, builds the entire tree
     * from the first CREATE patch's node, and appends it.
     *
     * @param {object} msg - PatchMessage with rev and ops[0] = CreatePatch
     * @returns {string} JSON ack: {ok: true, rev: N}
     */
    mount(msg) {
        this.registry.clear();

        // Reset host-page defaults — the browser's 8px body margin would
        // otherwise leave a white ring around the themed root.
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

    // ── patch application ──────────────────────────────────────

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
     * Apply a PatchMessage with revision tracking.
     * Drops stale messages. Requests a resync on rev gaps.
     * @param {object} msg - {rev: number, ops: Array}
     */
    applyMessage(msg) {
        if (msg.rev <= this.lastRev) return;

        if (msg.rev > this.lastRev + 1) {
            // Gap detected — ask Python for a full resync
            if (window.lumiview && window.lumiview.invoke) {
                window.lumiview.invoke("neony.resync", { rev: this.lastRev })
                    .catch(function () {});
            }
            return;
        }

        this.applyOps(msg.ops);
        this.lastRev = msg.rev;
    }

    // ── individual op handlers ─────────────────────────────────

    _create(op) {
        // If key already exists (e.g. from a prior REMOVE+CREATE cycle),
        // clean up the old subtree first.
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

        for (const key of op.ordered_keys) {
            const child = this.registry.get(key);
            if (child && child.parentNode === parent) {
                // appendChild re-inserts an existing node at the end
                parent.appendChild(child);
            }
        }
    }

    _updateAttrs(op) {
        const el = this.registry.get(op.key);
        if (!el) return;

        const setAttrs = op.set || {};
        for (const [name, value] of Object.entries(setAttrs)) {
            // Direct property assignment for `checked` and `value` —
            // once an input has been interacted with, its IDL property
            // no longer tracks the content attribute reliably, and
            // setAttribute("value") can refire `input` in WebKitGTK.
            if (name === "checked" && (el.type === "checkbox" || el.type === "radio")) {
                el.checked = true;
            } else if (name === "value" && el.tagName === "INPUT") {
                if (el.value !== value) el.value = value;
            } else {
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
            el.style.setProperty(prop, value);
            // WebKitGTK needs the prefixed variant of backdrop-filter
            if (prop === "backdrop-filter") {
                el.style.setProperty("-webkit-backdrop-filter", value);
            }
        }
        const removeStyles = op.remove || [];
        for (const prop of removeStyles) {
            el.style.removeProperty(prop);
            if (prop === "backdrop-filter") {
                el.style.removeProperty("-webkit-backdrop-filter");
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
