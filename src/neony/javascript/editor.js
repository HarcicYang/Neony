/**
 * RichText editor internals.
 *
 * Attached to `window.neony.richText` after index.js creates the neony
 * object.  The editor root is a `contenteditable` element marked with
 * `data-neony-rich-text`; its live DOM is owned by these functions, not
 * by the Python diff (the bridge freezes managed subtrees).
 *
 * Flat-position model: every text character counts as 1, every inline
 * `<img>` counts as 1, every `<br>` counts as 1.  Python never sees DOM
 * nodes; it reads and writes positions in this coordinate system.
 */
(() => {
    if (!window.neony) return;

    const engine = window.neony.engine;

    function elForKey(key) {
        return engine.registry.get(key);
    }

    function isImage(node) {
        return node.nodeType === 1 && node.tagName === "IMG";
    }

    function isBreak(node) {
        return node.nodeType === 1 && node.tagName === "BR";
    }

    // Number of flat units inside `node` (excluding the node itself when
    // it is an image/break — those count as 1).
    function nodeLength(node) {
        if (node.nodeType === 3) return node.data.length;
        if (node.nodeType !== 1) return 0;
        if (isImage(node) || isBreak(node)) return 1;
        let total = 0;
        for (let i = 0; i < node.childNodes.length; i++) {
            total += nodeLength(node.childNodes[i]);
        }
        return total;
    }

    // Flat position of the start of `node` inside `root`.
    function nodeStartOffset(root, node) {
        if (node === root) return 0;
        let pos = 0;
        let found = false;
        (function walk(n) {
            if (found) return;
            if (n === node) {
                found = true;
                return;
            }
            if (n.nodeType === 3) {
                pos += n.data.length;
            } else if (n.nodeType === 1) {
                if (isImage(n) || isBreak(n)) {
                    pos += 1;
                } else {
                    for (let i = 0; i < n.childNodes.length; i++) {
                        walk(n.childNodes[i]);
                        if (found) return;
                    }
                }
            }
        })(root);
        return found ? pos : 0;
    }

    // Convert a DOM Range boundary to a flat position.
    function rangeOffset(root, container, offset) {
        const base = nodeStartOffset(root, container);
        if (container.nodeType === 3) {
            return base + Math.min(offset, container.data.length);
        }
        if (container.nodeType === 1) {
            let add = 0;
            for (let i = 0; i < offset && i < container.childNodes.length; i++) {
                add += nodeLength(container.childNodes[i]);
            }
            return base + add;
        }
        return base;
    }

    // Convert a flat position to a {parent, offset} Range boundary.
    function resolvePosition(root, pos) {
        if (pos <= 0) {
            const first = root.firstChild;
            if (first && first.nodeType === 3) return { parent: first, offset: 0 };
            return { parent: root, offset: 0 };
        }
        return findInElement(root, pos);
    }

    function findInElement(el, pos) {
        let current = 0;
        for (let i = 0; i < el.childNodes.length; i++) {
            const child = el.childNodes[i];
            const length = nodeLength(child);
            if (child.nodeType === 3) {
                if (pos <= current + length) {
                    return { parent: child, offset: pos - current };
                }
            } else if (child.nodeType === 1) {
                if (isImage(child) || isBreak(child)) {
                    if (pos === current) return { parent: el, offset: i };
                    if (pos === current + 1) return { parent: el, offset: i + 1 };
                } else if (length > 0) {
                    if (pos < current + length) {
                        return findInElement(child, pos - current);
                    }
                    if (pos === current + length) {
                        return { parent: el, offset: i + 1 };
                    }
                } else if (pos === current) {
                    return { parent: el, offset: i };
                }
            }
            current += length;
        }
        return { parent: el, offset: el.childNodes.length };
    }

    function flatten(root) {
        const units = [];
        (function walk(node) {
            if (node.nodeType === 3) {
                units.push({ kind: "text", text: node.data });
            } else if (node.nodeType === 1) {
                if (isImage(node)) {
                    units.push({
                        kind: "image",
                        src: node.getAttribute("src") || "",
                        alt: node.getAttribute("alt") || "",
                    });
                } else if (isBreak(node)) {
                    units.push({ kind: "text", text: "\n" });
                } else {
                    for (let i = 0; i < node.childNodes.length; i++) walk(node.childNodes[i]);
                }
            }
        })(root);
        return units;
    }

    // Merge consecutive text units into single segments.
    function exportContent(key) {
        const root = elForKey(key);
        if (!root) return null;
        const segments = [];
        let pending = "";
        const flush = () => {
            if (pending.length > 0) {
                segments.push({ kind: "text", text: pending });
                pending = "";
            }
        };
        const units = flatten(root);
        for (const unit of units) {
            if (unit.kind === "text") {
                pending += unit.text;
            } else {
                flush();
                segments.push(unit);
            }
        }
        flush();
        return segments;
    }

    function setCaret(key, pos, focus) {
        const root = elForKey(key);
        if (!root) return false;
        if (focus !== false && typeof root.focus === "function") {
            root.focus();
        }
        const boundary = resolvePosition(root, pos);
        const range = document.createRange();
        try {
            range.setStart(boundary.parent, boundary.offset);
        } catch (e) {
            range.selectNodeContents(root);
            range.collapse(false);
        }
        range.collapse(true);
        const sel = window.getSelection();
        if (sel) {
            sel.removeAllRanges();
            sel.addRange(range);
        }
        return true;
    }

    function caretFromEvent(event) {
        const target = event.target && event.target.closest ? event.target : null;
        if (!target) return null;
        const root = target.closest("[data-neony-rich-text]");
        if (!root) return null;
        const sel = window.getSelection();
        if (!sel || sel.rangeCount === 0) return null;
        const range = sel.getRangeAt(0);
        return rangeOffset(root, range.startContainer, range.startOffset);
    }

    function selectionFromEvent(event) {
        const target = event.target && event.target.closest ? event.target : null;
        if (!target) return null;
        const root = target.closest("[data-neony-rich-text]");
        if (!root) return null;
        const sel = window.getSelection();
        if (!sel || sel.rangeCount === 0) return null;
        const range = sel.getRangeAt(0);
        return {
            start: rangeOffset(root, range.startContainer, range.startOffset),
            end: rangeOffset(root, range.endContainer, range.endOffset),
        };
    }

    function imageFromEvent(event) {
        const target = event.target && event.target.closest ? event.target : null;
        if (!target) return null;
        const img = target.closest && target.closest("img[data-neony-rich-image]");
        if (!img) return null;
        const root = img.closest("[data-neony-rich-text]");
        if (!root) return null;
        return {
            index: nodeStartOffset(root, img),
            src: img.getAttribute("src") || "",
            alt: img.getAttribute("alt") || "",
        };
    }

    function insertImage(key, src, alt, pos) {
        const root = elForKey(key);
        if (!root) return false;

        let range = null;
        if (typeof pos === "number") {
            setCaret(key, pos, false);
        }
        const sel = window.getSelection();
        if (sel && sel.rangeCount > 0) {
            range = sel.getRangeAt(0);
        }
        if (!range) {
            range = document.createRange();
            range.selectNodeContents(root);
            range.collapse(false);
        }

        const img = document.createElement("img");
        img.setAttribute("src", src);
        if (alt) img.setAttribute("alt", alt);
        img.setAttribute("data-neony-rich-image", "true");
        img.setAttribute("draggable", "false");

        if (!range.collapsed) range.deleteContents();
        range.insertNode(img);

        range.setStartAfter(img);
        range.collapse(true);
        if (sel) {
            sel.removeAllRanges();
            sel.addRange(range);
        }
        if (typeof root.focus === "function") root.focus();
        return true;
    }

    function loadContent(key, segments) {
        const root = elForKey(key);
        if (!root) return false;
        root.innerHTML = "";
        for (const seg of segments) {
            if (seg.kind === "image") {
                const img = document.createElement("img");
                img.setAttribute("src", seg.src || "");
                if (seg.alt) img.setAttribute("alt", seg.alt);
                img.setAttribute("data-neony-rich-image", "true");
                img.setAttribute("draggable", "false");
                root.appendChild(img);
            } else {
                root.appendChild(document.createTextNode(seg.text || ""));
            }
        }
        return true;
    }

    // Lightweight pointer reorder for inline images.  Images stay inside
    // the contenteditable flow; dropping one before/after another image
    // changes DOM order and emits input so Python re-exports the model.
    let richDrag = null;
    document.addEventListener("pointerdown", (event) => {
        const target = event.target && event.target.closest ? event.target : null;
        const image = target && target.closest("img[data-neony-rich-image]");
        if (!image) return;
        const root = image.closest("[data-neony-rich-text]");
        if (!root) return;
        richDrag = { image, root, pointerId: event.pointerId };
        if (image.setPointerCapture && event.pointerId !== undefined) {
            image.setPointerCapture(event.pointerId);
        }
    }, true);

    document.addEventListener("pointerup", (event) => {
        if (!richDrag) return;
        const drag = richDrag;
        richDrag = null;
        const target = document.elementFromPoint
            ? document.elementFromPoint(event.clientX || 0, event.clientY || 0)
            : null;
        const image = target && target.closest ? target.closest("img[data-neony-rich-image]") : null;
        if (!image || image === drag.image || image.closest("[data-neony-rich-text]") !== drag.root) return;
        const rect = image.getBoundingClientRect ? image.getBoundingClientRect() : { left: 0, width: 0 };
        if ((event.clientX || 0) < rect.left + rect.width / 2) {
            image.parentNode.insertBefore(drag.image, image);
        } else {
            image.parentNode.insertBefore(drag.image, image.nextSibling);
        }
        drag.root.dispatchEvent(new Event("input", { bubbles: true }));
    }, true);

    window.neony.richText = {
        caretFromEvent,
        selectionFromEvent,
        imageFromEvent,
        exportContent,
        focus: (key) => {
            const root = elForKey(key);
            if (!root) return false;
            if (typeof root.focus === "function") root.focus();
            return true;
        },
        getCaret: (key) => {
            const root = elForKey(key);
            if (!root) return null;
            const sel = window.getSelection();
            if (!sel || sel.rangeCount === 0) return 0;
            const range = sel.getRangeAt(0);
            return rangeOffset(root, range.startContainer, range.startOffset);
        },
        setCaret,
        insertImage,
        loadContent,
    };
})();
