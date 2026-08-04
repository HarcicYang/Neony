/**
 * Bootstrap and event delegation. Injected once per page by the bridge
 * plugin; creates the global ``window.neony`` API.
 */
(() => {
    // Guard against double-injection
    if (window.neony) return;

    const engine = new NeonyEngine();

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

    window.lumiview.listen("neony:patch", (msg) => {
        engine.applyMessage(msg);
    });

    // Event delegation: listen on `document` (capture phase —
    // `document.body` may not exist yet), trace each event to the
    // nearest data-neony-key ancestor, forward via lumiview.invoke.

    var DELEGATED_EVENTS = [
        "click", "dblclick", "input", "change", "submit",
        "keydown", "keyup", "focus", "blur", "contextmenu",
        "mouseover", "mouseout", "mousedown", "mouseup",
        "wheel", "paste", "copy", "cut",
    ];

    function captureValue(el, event) {
        // Keyboard events carry the pressed key, not the element's value.
        if (event.key !== undefined) return event.key;
        // Checkboxes use `checked` — `value` is always "on".
        if (el.type === "checkbox" || el.type === "radio") {
            return el.checked;
        }
        // A button's `value` IDL property defaults to "" — not user data,
        // so it must not shadow the null fallback below.
        if (el.value !== undefined && el.tagName !== "BUTTON") return el.value;
        return null;
    }

    function eventHandler(event) {
        var el = event.target.closest("[data-neony-key]");
        if (!el) return;

        // Window-control buttons: on *click* only, run the native
        // `lumiview.window.*` action (a plain hover must never close a
        // window), then still forward the normal Neony event.
        var winAction = el.getAttribute("data-window-action");
        if (winAction && event.type === "click" && window.lumiview.window) {
            var action = window.lumiview.window[winAction];
            if (action) action();
        }

        var key = el.getAttribute("data-neony-key");
        var value = captureValue(el, event);

        var payload = {
            key: key,
            event_type: event.type,
            value: value,
        };

        // Modifier keys — present on KeyboardEvent, MouseEvent, ...
        if (event.ctrlKey) payload.ctrl_key = true;
        if (event.shiftKey) payload.shift_key = true;
        if (event.altKey) payload.alt_key = true;
        if (event.metaKey) payload.meta_key = true;

        // Mouse coordinates (MouseEvent / WheelEvent only — undefined
        // elsewhere, so the guard keeps keydown payloads lean).
        if (event.clientX !== undefined) {
            payload.x = event.clientX;
            payload.y = event.clientY;
            payload.offset_x = event.offsetX;
            payload.offset_y = event.offsetY;
        }

        // Wheel delta (WheelEvent only)
        if (event.deltaX !== undefined) {
            payload.delta_x = event.deltaX;
            payload.delta_y = event.deltaY;
        }

        // Clipboard data — paste only.  getData() works only during the
        // synchronous dispatch, which this capture-phase handler is.
        // copy / cut have already written the selection by now, so they
        // fire as notifications without payload.
        if (event.type === "paste" && event.clipboardData) {
            try {
                payload.clipboard_text = event.clipboardData.getData("text/plain");
            } catch (e) {}
            try {
                payload.clipboard_html = event.clipboardData.getData("text/html");
            } catch (e) {}
        }

        window.lumiview.invoke("neony.event", payload).catch(function () {
            // Fire-and-forget — ignore delivery failures
        });
    }

    for (var i = 0; i < DELEGATED_EVENTS.length; i++) {
        document.addEventListener(DELEGATED_EVENTS[i], eventHandler, true);
    }
})();
