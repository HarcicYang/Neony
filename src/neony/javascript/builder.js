/**
 * Creates real DOM nodes from NodeDescriptor JSON, registering every
 * element in the *registry* Map (key → Element).
 */

/**
 * Build a DOM subtree from a NodeDescriptor object.
 *
 * @param {object} desc - NodeDescriptor dict (key, tag, attrs, styles, text, children)
 * @param {Map<string, Element>} registry - key → Element map
 * @returns {Element}
 */
function buildNode(desc, registry) {
    const el = document.createElement(desc.tag);

    // Identity attribute — used by event delegation and patch lookups
    el.setAttribute("data-neony-key", desc.key);

    // Apply inline styles via CSSOM (safe, no injection risk)
    const styles = desc.styles || {};
    for (const [prop, value] of Object.entries(styles)) {
        el.style.setProperty(prop, value);
        // WebKitGTK needs the prefixed variant of backdrop-filter
        if (prop === "backdrop-filter") {
            el.style.setProperty("-webkit-backdrop-filter", value);
        }
        // user-select also needs -webkit- and -moz- prefixes.
        if (prop === "user-select") {
            el.style.setProperty("-webkit-user-select", value);
            el.style.setProperty("-moz-user-select", value);
        }
    }

    // Apply HTML attributes (empty string = boolean presence)
    const attrs = desc.attrs || {};
    for (const [name, value] of Object.entries(attrs)) {
        el.setAttribute(name, value);
    }

    // Managed media (neony Video/Audio components): the source travels
    // in data-neony-media-src and NEVER lands in the DOM src attribute —
    // WebKitGTK's media pipeline cannot resolve custom URI schemes, and
    // swapping src mid-flight leaves it stuck on the interrupted load.
    // The attribute stays in the DOM as diff state; hydration runs after
    // mount from this clean, sourceless state.
    const mediaSrc = attrs["data-neony-media-src"];
    if (mediaSrc !== undefined) {
        el._neonyMediaSource = mediaSrc;
        el._neonyMediaSourceToken = 0;
    }

    if (desc.text !== null && desc.text !== undefined) {
        el.textContent = desc.text;
    }

    const children = desc.children || [];
    for (const child of children) {
        el.appendChild(buildNode(child, registry));
    }

    // Register for later patch lookups. Direct-event wiring may happen
    // immediately, but initial media hydration must wait until the
    // surrounding create operation has appended this node to the live
    // document. WebKitGTK can leave a Blob-backed <video> at HAVE_NOTHING
    // forever when resource selection starts on a detached node (Flaza
    // message videos are created with their MP4 source already present;
    // Gallery normally changes source only after mount).
    registry.set(desc.key, el);
    if (mediaSrc !== undefined && window.neony && window.neony.hydrateMedia) {
        const hydrateAfterMount = function () {
            // A later patch may have removed/replaced this node before
            // this microtask runs; never hydrate detached stale nodes.
            if (el.isConnected && registry.get(desc.key) === el) {
                window.neony.hydrateMedia(el);
            }
        };
        if (typeof queueMicrotask === "function") {
            queueMicrotask(hydrateAfterMount);
        } else {
            Promise.resolve().then(hydrateAfterMount);
        }
    }
    if (attrs["data-neony-direct-events"] && window.neony && window.neony.wireDirectEvents) {
        window.neony.wireDirectEvents(el);
    }
    return el;
}

/**
 * Walk a subtree and unregister every element from the registry.
 *
 * @param {Element} el - root of the subtree to unregister
 * @param {Map<string, Element>} registry
 */
function unregisterSubtree(el, registry) {
    const key = el.getAttribute("data-neony-key");
    if (key) registry.delete(key);
    for (const child of el.children) {
        unregisterSubtree(child, registry);
    }
}
