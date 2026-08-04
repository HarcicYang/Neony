/**
 * Neony JavaScript runtime — bootstrap and event delegation.
 *
 * Injected once per page by the Neony bridge plugin.
 * Creates the global ``window.neony`` API and subscribes to
 * Python-emitted patch events.
 */
(() => {
    // Guard against double-injection
    if (window.neony) return;

    const engine = new NeonyEngine();

    // Public API
    window.neony = {
        engine,
        mount: (msg) => engine.mount(msg),
        applyMessage: (msg) => engine.applyMessage(msg),
    };

    // Require the LumiView bridge for Python communication
    if (!window.lumiview || !window.lumiview.listen) {
        console.warn(
            "[neony] window.lumiview is not available. " +
            "Reactive mode requires a LumiView Bridge. " +
            "Make sure to pass Bridge(includes=[neony]) to Window.create()."
        );
        return;
    }

    // Listen for patch messages from Python
    window.lumiview.listen("neony:patch", (msg) => {
        engine.applyMessage(msg);
    });

    // ── event delegation ────────────────────────────────────────
    //
    // Listen on `document` (capture phase) — `document.body` may not
    // exist yet when the init script runs.  Each event is traced back
    // to the nearest ancestor with a data-neony-key attribute and
    // forwarded to Python via lumiview.invoke("neony.event", ...).

    var DELEGATED_EVENTS = [
        "click", "dblclick", "input", "change", "submit",
        "keydown", "keyup", "focus", "blur", "contextmenu",
        "mouseover", "mouseout", "mousedown", "mouseup",
    ];

    function captureValue(el, event) {
        // Keyboard events: the pressed key is the payload — the element's
        // value (e.g. what's already typed in an input) is irrelevant.
        if (event.key !== undefined) return event.key;
        // Checkboxes / radio: use `checked` property (not `value`, which
        // is always "on" for unchecked checkboxes).
        if (el.type === "checkbox" || el.type === "radio") {
            return el.checked;
        }
        // Buttons expose a `value` IDL property that defaults to "" —
        // not user data, so it must not shadow the null fallback below.
        if (el.value !== undefined && el.tagName !== "BUTTON") return el.value;
        return null;
    }

    function eventHandler(event) {
        var el = event.target.closest("[data-neony-key]");
        if (!el) return;

        // Window-control buttons (e.g. TitleBar): on *click* only, route
        // the action through the WindowControls bridge scope so
        // `lumiview.window.*` executes the native operation, then still
        // dispatch the normal Neony event so user callbacks run too.
        // Restricted to clicks — this handler receives every delegated
        // event type, and a plain hover must never close a window.
        var winAction = el.getAttribute("data-window-action");
        if (winAction && event.type === "click" && window.lumiview.window) {
            var action = window.lumiview.window[winAction];
            if (action) action();
        }

        var key = el.getAttribute("data-neony-key");
        var value = captureValue(el, event);

        window.lumiview.invoke("neony.event", {
            key: key,
            event_type: event.type,
            value: value,
        }).catch(function () {
            // Fire-and-forget — ignore delivery failures
        });
    }

    for (var i = 0; i < DELEGATED_EVENTS.length; i++) {
        document.addEventListener(DELEGATED_EVENTS[i], eventHandler, true);
    }
})();
