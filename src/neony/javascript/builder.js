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

    // WebKitGTK's media pipeline does not resolve custom URI schemes. Keep
    // the declared source in a private property; the runtime hydrates it to
    // a Blob URL after the node is mounted.
    if ((desc.tag === "audio" || desc.tag === "video") && attrs.src) {
        el._neonyMediaSource = attrs.src;
        el._neonyMediaSourceToken = 0;
    }

    if (desc.text !== null && desc.text !== undefined) {
        el.textContent = desc.text;
    }

    const children = desc.children || [];
    for (const child of children) {
        el.appendChild(buildNode(child, registry));
    }

    // Register for later patch lookups. Media hydration is called here so
    // initial mounts and nested create patches share the same path.
    registry.set(desc.key, el);
    if ((desc.tag === "audio" || desc.tag === "video") && window.neony && window.neony.hydrateMedia) {
        window.neony.hydrateMedia(el);
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
