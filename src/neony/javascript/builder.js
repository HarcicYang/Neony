/**
 * DOM builder — creates real DOM nodes from Neony NodeDescriptor JSON.
 *
 * Every created element is registered in the provided *registry* Map
 * (key → Element) so the engine can look up elements by key later.
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
    }

    // Apply HTML attributes (empty string = boolean presence)
    const attrs = desc.attrs || {};
    for (const [name, value] of Object.entries(attrs)) {
        el.setAttribute(name, value);
    }

    // Text content
    if (desc.text !== null && desc.text !== undefined) {
        el.textContent = desc.text;
    }

    // Recurse into children
    const children = desc.children || [];
    for (const child of children) {
        el.appendChild(buildNode(child, registry));
    }

    // Register for later patch lookups
    registry.set(desc.key, el);
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
