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

    // mouseenter/mouseleave are deliberately NOT here: they do not
    // propagate (no capture, no bubble), so a document listener can
    // never receive them — components detect enter/leave from the
    // bubbling mouseover/mouseout pair via the related_key payload.
    var DELEGATED_EVENTS = [
        "click", "dblclick", "input", "change", "submit",
        "keydown", "keyup", "focus", "blur", "contextmenu",
        "mouseover", "mouseout", "mousedown", "mouseup",
        "pointermove",
        "transitionend", "animationstart", "animationend",
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

    // Smooth horizontal scroll for data-neony-wheel-x zones.  Wheel deltas
    // accumulate into a target position; one rAF loop per element eases
    // scrollLeft toward it (~20% of the remaining distance per frame), so a
    // fast wheel stream glides instead of stuttering one hard step per event.
    // A weak Map keeps the target + active rAF handle per element.
    var wheelXState = new WeakMap();
    function smoothScrollX(el, delta) {
        var state = wheelXState.get(el);
        if (!state) {
            state = { target: el.scrollLeft, raf: 0 };
            wheelXState.set(el, state);
        }
        var max = el.scrollWidth - el.clientWidth;
        state.target = Math.max(0, Math.min(max, state.target + delta));
        if (state.raf) return; // a loop is already easing toward the target
        function step() {
            var current = el.scrollLeft;
            var remaining = state.target - current;
            if (Math.abs(remaining) < 1) {
                el.scrollLeft = state.target;
                state.raf = 0;
                return;
            }
            el.scrollLeft = current + remaining * 0.2;
            state.raf = requestAnimationFrame(step);
        }
        state.raf = requestAnimationFrame(step);
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

        // Horizontal-scroll zones (data-neony-wheel-x): translate a
        // vertical wheel into a sideways scroll.  WebKitGTK does not turn
        // a vertical wheel into horizontal scroll on its own, so JS must
        // drive it — but a direct scrollLeft += dy per event is jittery
        // next to native Shift+wheel.  Instead the wheel adds to a
        // target position and a single rAF loop eases scrollLeft toward
        // it, giving the smooth, compositor-like feel of native scroll.
        if (event.type === "wheel") {
            var wheelBar = event.target.closest
                ? event.target.closest('[data-neony-wheel-x="true"]')
                : null;
            if (wheelBar) {
                var dy = event.deltaY;
                if (event.deltaMode === 1) dy *= 40;
                else if (event.deltaMode === 2) dy *= wheelBar.clientWidth;
                smoothScrollX(wheelBar, dy);
                event.preventDefault();
                return;
            }
        }

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

        // Hover pair (mouseover/mouseout): the keyed element the
        // pointer moved from/to.  Components use it to detect real
        // boundary crossings — enter when related_target is outside
        // their subtree, leave when it is — instead of the child-to-
        // child hops these bubbling events fire on every inner element.
        if (event.type === "mouseover" || event.type === "mouseout") {
            var relatedEl =
                event.relatedTarget && event.relatedTarget.closest
                    ? event.relatedTarget.closest("[data-neony-key]")
                    : null;
            payload.related_key = relatedEl ? relatedEl.getAttribute("data-neony-key") : null;
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

        // CSS transition end — which property finished and how long it
        // took.  Gate on `propertyName` (only TransitionEvent has it).
        if (event.propertyName !== undefined) {
            payload.transition_property = event.propertyName;
            payload.elapsed_time = event.elapsedTime;
        }
        // CSS animation start / end — carries the animation name.
        if (event.animationName !== undefined) {
            payload.animation_name = event.animationName;
            payload.elapsed_time = event.elapsedTime;
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

    // Synthetic `outsideclick`: every element marked with
    // data-neony-outside="true" (an open overlay wrapper — trigger +
    // panel) receives one event per click that lands OUTSIDE its
    // subtree, so overlays can close on click-away.  Bubble phase on
    // document: the capture-phase handler above early-returns for
    // clicks with no keyed ancestor (blank page space) — precisely the
    // outside case this listener exists for.
    document.addEventListener(
        "click",
        function (event) {
            var roots = document.querySelectorAll('[data-neony-outside="true"]');
            for (var i = 0; i < roots.length; i++) {
                var root = roots[i];
                if (root.contains(event.target)) continue;
                var key = root.getAttribute("data-neony-key");
                if (!key) continue;
                window.lumiview
                    .invoke("neony.event", { key: key, event_type: "outsideclick", value: null })
                    .catch(function () {
                        // Fire-and-forget — ignore delivery failures
                    });
            }
        },
        false
    );

    // ---- Scroll indicator (data-neony-scroll) ----
    //
    // Replaces the hidden native scrollbar.  Each [data-neony-scroll]
    // container gets a JS-built overlay (track + thumb) appended as its
    // LAST child.  The overlay carries NO data-neony-key, so the Python
    // patch engine never touches it (engine.js resolves every op by
    // registry key — an unkeyed node is invisible to it).  Drag and
    // track-click use plain addEventListener on the overlay, outside
    // the delegated event pipeline, so a drag involves ZERO Python IPC
    // round-trips (every delegated pointermove is one full round-trip
    // today — the lag source — so the thumb must avoid that path).
    //
    // The thumb is also the single owner of the edge-fade mask: it
    // writes maskImage/webkitMaskImage on the container dynamically
    // (fade disappears at the scrolled end).  Containers with a
    // backdrop-filter (glass/popup) get the THUMB ONLY — mask-image +
    // backdrop-filter conflict in WebKitGTK.
    var SI_FADE_PX = 36; // matches the former static fade zone
    var SI_IDLE_MS = 1000; // scroll-stop before the thumb dims back
    var SI_THUMB_MIN = 24; // never let the thumb vanish on long lists
    var SI_GUTTER = 12; // overlay thickness (px)
    var SI_THIN = 4; // idle thumb thickness
    var SI_WIDE = 8; // active thumb thickness
    // Presets — the rest/active thumb look:
    //   silent  → hidden at rest, thin-but-solid on hover/scroll
    //   lighten → faint thin at rest, solid thin on hover/scroll
    //   normal  → faint thin at rest, solid wide on hover/scroll
    //   active  → solid wide always (once shown, never dims)
    var SI_PRESETS = {
        silent: { restOpacity: 0, activeOpacity: 0.8, activeWidth: SI_THIN },
        lighten: { restOpacity: 0.2, activeOpacity: 0.8, activeWidth: SI_THIN },
        normal: { restOpacity: 0.2, activeOpacity: 0.8, activeWidth: SI_WIDE },
        active: { restOpacity: 0.8, activeOpacity: 0.8, activeWidth: SI_WIDE },
    };
    var siInstances = new WeakMap(); // container -> state
    var siRafPending = new WeakSet(); // containers with a geometry rAF queued

    function siResolveAxis(container, attrValue) {
        // Preset suffix: "-silent" | "-lighten" | "-active" (absent =
        // "normal").  The preset selects the rest/active thumb look; the
        // suffix is stripped and the preset rides in state.
        var preset = "normal";
        var parts = attrValue.split("-");
        if (parts.length > 1) {
            var tail = parts[parts.length - 1];
            if (tail === "silent" || tail === "lighten" || tail === "active") {
                preset = tail;
                parts.pop();
            }
        }
        attrValue = parts.join("-");
        if (attrValue === "x") return { axis: "x", preset: preset };
        if (attrValue === "y") return { axis: "y", preset: preset };
        // "true" (both axes scrollable) — pick the axis that currently
        // overflows, re-evaluated per geometry update so it can flip.
        var cs = getComputedStyle(container);
        var ovY = cs.overflowY;
        var ovX = cs.overflowX;
        var scrollsY = (ovY === "auto" || ovY === "scroll") && container.scrollHeight > container.clientHeight + 1;
        var scrollsX = (ovX === "auto" || ovX === "scroll") && container.scrollWidth > container.clientWidth + 1;
        if (scrollsY) return { axis: "y", preset: preset };
        if (scrollsX) return { axis: "x", preset: preset };
        return {
            axis: (ovX === "auto" || ovX === "scroll") && (ovY === "hidden") ? "x" : "y",
            preset: preset,
        };
    }

    function siScheduleGeometry(container) {
        if (siRafPending.has(container)) return;
        siRafPending.add(container);
        requestAnimationFrame(function () {
            siRafPending.delete(container);
            var state = siInstances.get(container);
            if (state) siUpdateGeometry(state);
        });
    }

    function siUpdateGeometry(state) {
        var c = state.container;
        var vertical = state.axis === "y";
        var visible = vertical ? c.clientHeight : c.clientWidth;
        var full = vertical ? c.scrollHeight : c.scrollWidth;
        var pos = vertical ? c.scrollTop : c.scrollLeft;
        var maxScroll = full - visible;
        // Keep the sibling overlay pinned to the container's box —
        // the container may move within its parent (layout shifts).
        siPlaceOverlay(state);
        // Nothing to scroll → hide the indicator entirely.
        if (full <= visible + 1) {
            state.overlay.style.display = "none";
            siWriteMask(state, 0, 0, true);
            return;
        }
        state.overlay.style.display = "block";
        var trackLen = vertical ? state.track.clientHeight : state.track.clientWidth;
        var ratio = visible / full;
        var thumbLen = Math.max(SI_THUMB_MIN, Math.round(ratio * trackLen));
        var travel = trackLen - thumbLen;
        var pct = maxScroll > 0 ? pos / maxScroll : 0;
        var thumbOffset = Math.round(pct * travel);
        if (vertical) {
            state.thumb.style.top = thumbOffset + "px";
            state.thumb.style.height = thumbLen + "px";
        } else {
            state.thumb.style.left = thumbOffset + "px";
            state.thumb.style.width = thumbLen + "px";
        }
        siWriteMask(state, pct, maxScroll, false);
    }

    // Dynamic edge fade — only for containers WITHOUT backdrop-filter.
    // The fade collapses to nothing at whichever end is flush with the
    // content (top at scrollTop=0, bottom at scrollTop=max), so anchored
    // content at rest is never dimmed.
    function siWriteMask(state, pct, maxScroll, hide) {
        if (hide || !state.fadeEnabled) {
            state.container.style.maskImage = "";
            state.container.style.webkitMaskImage = "";
            return;
        }
        var vertical = state.axis === "y";
        // At the flush end, the gradient starts solid (no transparent
        // rim).  Mid-scroll, both ends carry the full fade.
        var topFade = pct <= 0
            ? "black 0px"
            : "transparent, rgba(0,0,0,0.5) " + (SI_FADE_PX - 10) + "px, black " + SI_FADE_PX + "px";
        var bottomFade = pct >= 1 && maxScroll > 0
            ? "black 100%"
            : "black calc(100% - " + SI_FADE_PX + "px), rgba(0,0,0,0.5) calc(100% - " + (SI_FADE_PX - 10) + "px), transparent";
        var dir = vertical ? "to bottom" : "to right";
        var grad = "linear-gradient(" + dir + ", " + topFade + ", " + bottomFade + ")";
        state.container.style.maskImage = grad;
        state.container.style.webkitMaskImage = grad;
    }

    function siPreset(state) {
        return SI_PRESETS[state.preset] || SI_PRESETS.normal;
    }

    function siEnterActive(state) {
        if (state.active) return;
        state.active = true;
        var p = siPreset(state);
        state.thumb.style.opacity = String(p.activeOpacity);
        siSetThumbExtent(state, p.activeWidth);
    }

    function siScheduleIdle(state) {
        if (state.preset === "active") return; // active preset never dims
        clearTimeout(state.idleTimer);
        state.idleTimer = setTimeout(function () {
            state.active = false;
            var p = siPreset(state);
            state.thumb.style.opacity = String(p.restOpacity);
            siSetThumbExtent(state, SI_THIN);
        }, SI_IDLE_MS);
    }

    function siSetThumbExtent(state, px) {
        // Thumb sits centered in the gutter; its cross-axis extent
        // grows/shrinks symmetrically about the center.
        if (state.axis === "y") state.thumb.style.width = px + "px";
        else state.thumb.style.height = px + "px";
    }

    function siPlaceOverlay(state) {
        var c = state.container;
        var vertical = state.axis === "y";
        // The overlay is a SIBLING of the container (see siAttach), so it
        // must be re-pinned whenever the container moves or resizes.
        if (vertical) {
            state.overlay.style.top = c.offsetTop + "px";
            state.overlay.style.height = c.offsetHeight + "px";
            state.overlay.style.left = (c.offsetLeft + c.offsetWidth - SI_GUTTER) + "px";
            state.overlay.style.width = SI_GUTTER + "px";
        } else {
            state.overlay.style.left = c.offsetLeft + "px";
            state.overlay.style.width = c.offsetWidth + "px";
            state.overlay.style.top = (c.offsetTop + c.offsetHeight - SI_GUTTER) + "px";
            state.overlay.style.height = SI_GUTTER + "px";
        }
    }

    function siAttach(container) {
        if (siInstances.has(container)) return; // idempotent
        var attrValue = container.getAttribute("data-neony-scroll") || "true";
        var resolved = siResolveAxis(container, attrValue);
        var axis = resolved.axis;
        var preset = resolved.preset;
        var vertical = axis === "y";
        // CRITICAL: the overlay must NOT be a child of the scroll
        // container — an absolutely-positioned child of an overflow
        // container scrolls away WITH the content (the containing block
        // is the content box).  Instead the overlay is a sibling, pinned
        // absolutely against the container's box within the parent
        // (which we make a positioning context).  This also makes it
        // invisible to the Python patch engine: it is not a child, so no
        // keyed insert/reorder can ever cross it.
        var parent = container.parentNode;
        if (parent && getComputedStyle(parent).position === "static") {
            parent.style.position = "relative";
        }
        // backdrop-filter on the SAME element breaks mask-image in
        // WebKitGTK — detect once and skip the fade for those surfaces
        // (glass sidebar, popups).  They still get the thumb.  Prefer
        // the inline style (always set by Styles.backdrop_filter); fall
        // back to the computed value.  jsdom returns undefined for both
        // computed backdrop props, so the inline read is what makes the
        // detection reliable across environments.
        var cs = getComputedStyle(container);
        var inlineBd = container.style.backdropFilter || container.style.webkitBackdropFilter;
        var computedBd = cs.backdropFilter || cs.webkitBackdropFilter;
        var bd = inlineBd || computedBd;
        var fadeEnabled = !bd || bd === "none";

        var overlay = document.createElement("div");
        Object.assign(overlay.style, {
            position: "absolute",
            zIndex: "5",
            // Default pass-through so the overlay never blocks wheel/
            // clicks on content; the track + thumb re-enable pointer
            // events on themselves.
            pointerEvents: "none",
            display: "none",
        });

        var track = document.createElement("div");
        Object.assign(track.style, {
            position: "absolute",
            inset: "0",
            pointerEvents: "auto",
            cursor: "pointer",
        });

        var thumb = document.createElement("div");
        thumb.className = "neony-scroll-thumb";
        Object.assign(thumb.style, {
            position: "absolute",
            pointerEvents: "auto",
            cursor: "grab",
            // Rest look from the preset: silent hides, lighten/normal
            // show faint, active shows strong.
            opacity: String(SI_PRESETS[preset].restOpacity),
            transition: "opacity 0.2s ease, width 0.2s ease, height 0.2s ease",
        });
        if (vertical) {
            // Centered in the gutter; width is the active extent.
            thumb.style.right = ((SI_GUTTER - SI_THIN) / 2) + "px";
            thumb.style.width = SI_THIN + "px";
        } else {
            thumb.style.bottom = ((SI_GUTTER - SI_THIN) / 2) + "px";
            thumb.style.height = SI_THIN + "px";
        }

        overlay.appendChild(track);
        overlay.appendChild(thumb);
        siPlaceOverlay({ container: container, axis: axis, overlay: overlay });
        parent.appendChild(overlay); // sibling, not a child of the scroller

        var state = {
            container: container,
            axis: axis,
            attrValue: attrValue,
            overlay: overlay,
            track: track,
            thumb: thumb,
            fadeEnabled: fadeEnabled,
            preset: preset,
            idleTimer: 0,
            active: false,
            dragging: false,
            dragStart: 0,
            dragStartScroll: 0,
        };
        siInstances.set(container, state);

        // Geometry refresh on container resize (window/relayout).
        // ResizeObserver is absent in jsdom (test env) — guard so the
        // indicator still works there; real WebViews always have it.
        if (typeof ResizeObserver !== "undefined") {
            var ro = new ResizeObserver(function () { siScheduleGeometry(container); });
            ro.observe(container);
            state.ro = ro;
        }
        // Geometry refresh on content change (Python adds/removes rows).
        var cmo = new MutationObserver(function () { siScheduleGeometry(container); });
        cmo.observe(container, { childList: true, subtree: true });
        state.cmo = cmo;

        function onScroll() {
            siEnterActive(state);
            siScheduleIdle(state);
            siScheduleGeometry(container);
        }
        function onEnter() { siEnterActive(state); }
        function onLeave() {
            // Keep it strong while dragging; otherwise let it idle-dim.
            if (!state.dragging) siScheduleIdle(state);
        }
        container.addEventListener("scroll", onScroll, { passive: true });
        container.addEventListener("mouseenter", onEnter);
        container.addEventListener("mouseleave", onLeave);
        state.onScroll = onScroll;
        state.onEnter = onEnter;
        state.onLeave = onLeave;

        // Track click → page one viewport toward the click position.
        track.addEventListener("click", function (event) {
            var vertical = state.axis === "y";
            var thumbPos = vertical ? (parseFloat(thumb.style.top) || 0) : (parseFloat(thumb.style.left) || 0);
            var clickPos = vertical ? event.offsetY : event.offsetX;
            var page = vertical ? container.clientHeight : container.clientWidth;
            if (vertical) {
                container.scrollTop += clickPos < thumbPos ? -page : page;
            } else {
                container.scrollLeft += clickPos < thumbPos ? -page : page;
            }
        });

        // Drag — plain listeners on the thumb, OUTSIDE the delegated
        // pipeline.  setPointerCapture routes all subsequent move/up to
        // the thumb.  No lumiview.invoke anywhere on this path.
        function onMove(event) {
            var vertical = state.axis === "y";
            var delta = (vertical ? event.clientY : event.clientX) - state.dragStart;
            var vis = vertical ? container.clientHeight : container.clientWidth;
            var full = vertical ? container.scrollHeight : container.scrollWidth;
            var maxScroll = full - vis;
            var trackLen = vertical ? track.clientHeight : track.clientWidth;
            var thumbLen = Math.max(SI_THUMB_MIN, Math.round(vis / full * trackLen));
            var travel = trackLen - thumbLen;
            var scrollPerPx = travel > 0 ? maxScroll / travel : 0;
            if (vertical) container.scrollTop = state.dragStartScroll + delta * scrollPerPx;
            else container.scrollLeft = state.dragStartScroll + delta * scrollPerPx;
            // The container's scroll listener fires geometry refresh.
        }
        function onUp(event) {
            state.dragging = false;
            thumb.style.cursor = "grab";
            thumb.removeEventListener("pointermove", onMove);
            thumb.removeEventListener("pointerup", onUp);
            thumb.removeEventListener("pointercancel", onUp);
            try { thumb.releasePointerCapture(event.pointerId); } catch (e) {}
            siScheduleIdle(state);
        }
        function onDown(event) {
            event.preventDefault();
            event.stopPropagation();
            state.dragging = true;
            state.dragStart = state.axis === "y" ? event.clientY : event.clientX;
            state.dragStartScroll = state.axis === "y" ? container.scrollTop : container.scrollLeft;
            try { thumb.setPointerCapture(event.pointerId); } catch (e) {}
            thumb.style.cursor = "grabbing";
            siEnterActive(state);
            thumb.addEventListener("pointermove", onMove);
            thumb.addEventListener("pointerup", onUp);
            thumb.addEventListener("pointercancel", onUp);
        }
        thumb.addEventListener("pointerdown", onDown);
        state.onDown = onDown;

        siScheduleGeometry(container);
    }

    function siDetach(container) {
        var state = siInstances.get(container);
        if (!state) return;
        clearTimeout(state.idleTimer);
        if (state.ro) state.ro.disconnect();
        if (state.cmo) state.cmo.disconnect();
        container.removeEventListener("scroll", state.onScroll);
        container.removeEventListener("mouseenter", state.onEnter);
        container.removeEventListener("mouseleave", state.onLeave);
        state.thumb.removeEventListener("pointerdown", state.onDown);
        state.overlay.remove();
        // Clear any mask we owned (restores the container to bare state).
        container.style.maskImage = "";
        container.style.webkitMaskImage = "";
        siInstances.delete(container);
    }

    function siScanAll(root) {
        var nodes = root.querySelectorAll("[data-neony-scroll]");
        for (var i = 0; i < nodes.length; i++) siAttach(nodes[i]);
    }
    siScanAll(document);

    // Catch containers added later by Python patches (lazy panels,
    // future components) and clean up removed ones.
    var siObserver = new MutationObserver(function (records) {
        for (var r = 0; r < records.length; r++) {
            var rec = records[r];
            for (var a = 0; a < rec.addedNodes.length; a++) {
                var node = rec.addedNodes[a];
                if (node.nodeType !== 1) continue;
                if (node.matches && node.matches("[data-neony-scroll]")) siAttach(node);
                if (node.querySelectorAll) siScanAll(node);
            }
            for (var d = 0; d < rec.removedNodes.length; d++) {
                var gone = rec.removedNodes[d];
                if (gone.nodeType !== 1) continue;
                if (siInstances.has(gone)) siDetach(gone);
                if (gone.querySelectorAll) {
                    var inner = gone.querySelectorAll("[data-neony-scroll]");
                    for (var g = 0; g < inner.length; g++) siDetach(inner[g]);
                }
            }
        }
    });
    // The engine's initialization script runs BEFORE the page body
    // exists (index.js registers capture-phase listeners on `document`
    // for the same reason — see the comment at the top of this file).
    // Attach the observer once a body is available; until then, wait
    // for DOMContentLoaded.  The initial scan above ran against an empty
    // document in that case, so re-scan when the DOM arrives — the
    // observer only reports changes AFTER it is attached, never the
    // pre-existing tree.  (jsdom always has a body, which is why the
    // tests never hit this path.)
    function siStartObserver() {
        if (document.body) {
            siScanAll(document);
            siObserver.observe(document.body, { childList: true, subtree: true });
        } else {
            document.addEventListener("DOMContentLoaded", siStartObserver, { once: true });
        }
    }
    siStartObserver();
})();
