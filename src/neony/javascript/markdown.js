/**
 * Markdown rendering (frontend).
 *
 * Attached to `window.neony.markdown` after index.js creates the neony
 * object.  A Markdown component's live DOM is owned by these functions,
 * not by the Python diff: the component root carries
 * `data-neony-markdown` and is a managed subtree (the bridge freezes its
 * snapshot), so Python ships only raw source text.
 *
 * Two update paths:
 * - `set(key, source)` — scheduled JS commands from Python (streaming
 *   appends, programmatic writes); re-renders the whole source.
 * - `renderMarkdown(el)` — called by the engine after it builds a node
 *   whose raw markdown source arrived as its text content (first mount,
 *   resync re-mounts, replaces).  Python keeps the current source, so a
 *   rebuild always carries the full text.
 *
 * markdown-it runs with `html: false` (raw HTML in the source is
 * escaped — LLM output is untrusted); fenced code blocks are highlighted
 * with highlight.js.  Anchors open in the system browser through the
 * `neony.open_external` bridge command (webview navigation is denied by
 * the default policy).
 */
(() => {
    if (!window.neony) return;

    const engine = window.neony.engine;
    // The "default" preset enables tables and strikethrough; `html: false`
    // escapes raw HTML instead of rendering it.
    const md = window.markdownit({ html: false, linkify: true });
    const hl = window.hljs || null;

    if (hl) {
        md.set({
            highlight: (source, lang) => {
                if (lang && hl.getLanguage(lang)) {
                    try {
                        return (
                            '<pre><code class="hljs language-' +
                            lang +
                            '">' +
                            hl.highlight(source, { language: lang, ignoreIllegals: true }).value +
                            "</code></pre>"
                        );
                    } catch (err) {
                        // Fall through to the escaped plain block.
                    }
                }
                return '<pre><code class="hljs">' + md.utils.escapeHtml(source) + "</code></pre>";
            },
        });
    }

    function elForKey(key) {
        return engine.registry.get(key);
    }

    function renderInto(el, source) {
        el.innerHTML = md.render(String(source));
    }

    /**
     * Convert every `[data-neony-markdown]` element inside `el` (or `el`
     * itself) from raw-source text content to rendered HTML.
     * @param {Node} el - freshly built subtree root
     */
    function convertTree(el) {
        if (!el || el.nodeType !== 1) return;
        if (el.matches("[data-neony-markdown]")) {
            renderInto(el, el.textContent);
            return;
        }
        const roots = el.querySelectorAll("[data-neony-markdown]");
        for (let i = 0; i < roots.length; i++) renderInto(roots[i], roots[i].textContent);
    }

    window.neony.renderMarkdown = convertTree;

    window.neony.markdown = {
        /** Re-render `key`'s content from the full markdown `source`.
         *  While a stream runs on the element, the newest block fades in
         *  on every update — each append gets its own entrance. */
        set: (key, source) => {
            const el = elForKey(key);
            if (!el) return false;
            renderInto(el, source);
            if (el.hasAttribute("data-neony-streaming")) {
                const last = el.lastElementChild;
                if (last) {
                    last.classList.remove("neony-stream-chunk");
                    void last.offsetWidth; // restart the entrance animation
                    last.classList.add("neony-stream-chunk");
                }
            }
            return true;
        },
        /** Re-render `key` from its own text content (resync paths). */
        reset: (key) => {
            const el = elForKey(key);
            if (!el) return false;
            renderInto(el, el.textContent);
            return true;
        },
    };

    // Markdown links open in the system browser: the webview navigation
    // policy denies in-page navigation, so in-app content routes here.
    document.addEventListener(
        "click",
        (event) => {
            const target = event.target;
            const anchor = target && target.closest ? target.closest("[data-neony-markdown] a") : null;
            if (!anchor) return;
            event.preventDefault();
            event.stopPropagation();
            if (window.lumiview && window.lumiview.invoke) {
                window.lumiview.invoke("neony.open_external", { url: anchor.href }).catch(() => {});
            }
        },
        true
    );
})();
