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
        "pointermove",
        "wheel", "paste", "copy", "cut",
        "dragover", "dragleave", "drop",
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
        var el = event.target.closest ? event.target.closest("[data-neony-key]") : null;
        // Keys typed while no element is focused land on <body> — no
        // data-neony-key ancestor to trace to.  Window-level key
        // listeners (Page.on_keydown / on_keyup, shortcuts) must still
        // fire, so route keyboard events through the engine root.
        if (!el && (event.type === "keydown" || event.type === "keyup")) {
            el = engine.root;
        }
        if (!el) return;

        // Drag-and-drop: the browser refuses to drop onto a page that
        // never calls preventDefault on dragover.  The drop itself must
        // also be prevented, or the browser navigates to the dropped file.
        if (event.type === "dragover" || event.type === "drop") {
            event.preventDefault();
        }

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

        // Pointer movement delta (PointerEvent).  Gated on pointerId —
        // the one property only PointerEvents have: movementX exists on
        // plain MouseEvents too (0), and gating on it would pollute
        // every click/mousedown payload.  movementX/Y are the change in
        // coordinates since the last pointermove event.
        if (event.pointerId !== undefined) {
            if (event.movementX !== undefined) {
                payload.movement_x = event.movementX;
                payload.movement_y = event.movementY;
            }
            // Pointer type: "mouse", "pen", or "touch".
            if (event.pointerType !== undefined) {
                payload.pointer_type = event.pointerType;
            }
        }

        // Wheel delta (WheelEvent only).  delta_mode tells the units:
        // 0 = pixels, 1 = lines, 2 = pages — WebKitGTK wheels deliver
        // one event per notch in pixel mode (mode=0, constant ±delta),
        // trackpads deliver continuous fractional deltas.
        if (event.deltaX !== undefined) {
            payload.delta_x = event.deltaX;
            payload.delta_y = event.deltaY;
            payload.delta_mode = event.deltaMode;
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

        // Dropped files — one entry per file: name, local filesystem
        // path, size, MIME.  File.path exists on WebView2 but is empty
        // on WKWebView and REMOVED in recent WebKitGTK (≥2.52) — parse
        // the drag's text/uri-list as the fallback path source, matched
        // to each file by base name.
        if (event.type === "drop" && event.dataTransfer && event.dataTransfer.files) {
            var uriPaths = [];
            try {
                var uriList = event.dataTransfer.getData("text/uri-list");
                if (uriList) {
                    var lines = uriList.split(/\r?\n/);
                    for (var u = 0; u < lines.length; u++) {
                        var uri = lines[u].trim();
                        if (uri.indexOf("file://") === 0) {
                            try {
                                uriPaths.push(decodeURIComponent(uri.slice(7)));
                            } catch (e2) {}
                        }
                    }
                }
            } catch (e1) {}

            var files = [];
            var fileList = event.dataTransfer.files;
            for (var f = 0; f < fileList.length; f++) {
                var file = fileList[f];
                var path = file.path || "";
                if (!path) {
                    for (var p = 0; p < uriPaths.length; p++) {
                        if (uriPaths[p].split("/").pop() === file.name) {
                            path = uriPaths[p];
                            break;
                        }
                    }
                }
                files.push({
                    name: file.name,
                    path: path,
                    size: file.size,
                    type: file.type,
                });
            }
            if (files.length > 0) payload.drop_files = files;
        }

        window.lumiview.invoke("neony.event", payload).catch(function () {
            // Fire-and-forget — ignore delivery failures
        });
    }

    for (var i = 0; i < DELEGATED_EVENTS.length; i++) {
        document.addEventListener(DELEGATED_EVENTS[i], eventHandler, true);
    }
})();
