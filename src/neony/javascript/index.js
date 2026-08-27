/**
 * Bootstrap and event delegation. Injected once per page by the bridge
 * plugin; creates the global ``window.neony`` API.
 */
(() => {
    // Guard against double-injection
    if (window.neony) return;

    const engine = new NeonyEngine();

    function releaseMedia(el) {
        if (!el) return;
        var key = el.getAttribute && el.getAttribute("data-neony-key");
        if (key && webAudio.states.has(key)) waRelease(key);
        if (el._neonyMediaObjectUrl) {
            URL.revokeObjectURL(el._neonyMediaObjectUrl);
            el._neonyMediaObjectUrl = null;
        }
        el._neonyMediaSourceToken = (el._neonyMediaSourceToken || 0) + 1;
        for (const child of el.children || []) releaseMedia(child);
    }

    // ── WebAudio transport (managed <audio> only) ─────────────────────
    // WebKitGTK funnels every HTMLMediaElement in a page through one
    // shared audio chain.  The FIRST lifecycle prerolls cleanly, but any
    // later source change fights that chain: decoder misalignment
    // (fixed separately by node replacement) and — still unsolved at
    // pipeline level — a corked shared stream that stays silent for
    // tens of seconds.  Decoding into an AudioBuffer and driving
    // BufferSourceNodes sidesteps HTMLMediaElement pipelines entirely:
    // switching sources becomes swapping buffer nodes, instantly.
    var webAudio = {
        ctx: null,
        states: new Map(),
        ensureCtx: function () {
            if (!this.ctx) {
                var AC = window.AudioContext || window.webkitAudioContext;
                if (!AC) return null;
                this.ctx = new AC();
            }
            return this.ctx;
        },
    };

    function waStateOf(key, el) {
        var st = webAudio.states.get(key);
        if (!st) {
            st = {
                key: key,
                el: el,
                buffer: null,
                gain: null,
                srcNode: null,
                volume: typeof el.volume === "number" ? el.volume : 1,
                muted: !!el.muted,
                playing: false,
                offset: 0,
                startCtx: 0,
                loadToken: 0,
                pendingPlay: false,
                duration: 0,
                endedSent: false,
            };
            webAudio.states.set(key, st);
        }
        return st;
    }

    function waGain(st) {
        if (!st.gain && webAudio.ctx) {
            st.gain = webAudio.ctx.createGain();
            st.gain.gain.value = st.muted ? 0 : st.volume;
            st.gain.connect(webAudio.ctx.destination);
        }
        return st.gain;
    }

    function waApplyGain(st) {
        if (st.gain) st.gain.gain.value = st.muted ? 0 : st.volume;
    }

    function waEmit(key, type, fields) {
        var st = webAudio.states.get(key);
        if (!window.lumiview || !window.lumiview.invoke || !st) return;
        var payload = { key: key, event_type: type, value: null };
        payload.media_time = waTime(st);
        payload.media_duration = st.duration;
        payload.media_volume = st.volume;
        payload.media_muted = st.muted;
        payload.media_paused = !st.playing;
        if (fields) for (var k in fields) payload[k] = fields[k];
        window.lumiview.invoke("neony.event", payload).catch(function () {});
    }

    function waTime(st) {
        if (!webAudio.ctx) return st.offset;
        var t = st.playing ? webAudio.ctx.currentTime - st.startCtx + st.offset : st.offset;
        if (st.duration > 0 && t > st.duration) t = st.duration;
        return t;
    }

    function waStopSource(st) {
        if (st.srcNode) {
            try {
                st.srcNode.onended = null;
                st.srcNode.stop();
            } catch (_) { /* already stopped */ }
            try { st.srcNode.disconnect(); } catch (_) {}
            st.srcNode = null;
        }
    }

    function waStart(st, offset) {
        var ctx = webAudio.ensureCtx();
        if (!ctx || !st.buffer) return;
        waStopSource(st);
        var node = ctx.createBufferSource();
        node.buffer = st.buffer;
        node.connect(waGain(st));
        node.onended = function () {
            if (st.srcNode === node && st.playing) waFinish(st);
        };
        st.srcNode = node;
        st.offset = Math.max(0, Math.min(offset, st.duration));
        st.startCtx = ctx.currentTime;
        st.playing = true;
        st.endedSent = false;
        waEnsureTimer();
        try { node.start(0, st.offset); } catch (_) {}
        waEmit(st.key, "play");
    }

    function waFinish(st) {
        // Natural end: park at the final sample and report like native.
        waStopSource(st);
        st.playing = false;
        st.offset = st.duration;
        waEmit(st.key, "ended");
        waEmit(st.key, "pause");
    }

    function waPause(st) {
        if (st.playing) {
            st.offset = waTime(st);
            waStopSource(st);
            st.playing = false;
            waEmit(st.key, "pause");
        }
        waEmit(st.key, "timeupdate");
    }

    function waSeek(st, time) {
        var target = Math.max(0, Math.min(time, st.duration));
        var wasPlaying = st.playing;
        waStopSource(st);
        st.playing = false;
        st.offset = target;
        if (wasPlaying) {
            waStart(st, target); // emits play
        } else {
            waEmit(st.key, "seeked");
        }
        waEmit(st.key, "timeupdate");
    }

    // Production clock driver: native <media> elements emit their own
    // timeupdate events, decoded-buffer playback has no such source, so
    // the engine pumps synthesized updates itself.
    var waTimer = null;
    function waEnsureTimer() {
        if (waTimer === null && typeof setInterval === "function") {
            waTimer = setInterval(function () {
                try { waTick(); } catch (_) { /* one bad state must not kill the clock */ }
            }, 250);
        }
    }

    function waTick() {
        webAudio.states.forEach(function (st) {
            if (!st.playing || !st.buffer) return;
            var t = waTime(st);
            if (st.duration > 0 && t >= st.duration - 0.02) {
                waFinish(st);
                return;
            }
            waEmit(st.key, "timeupdate");
        });
    }

    async function webAudioLoad(el, source) {
        var key = el.getAttribute("data-neony-key");
        if (!key) return;
        var st = waStateOf(key, el);
        var token = st.loadToken + 1;
        st.loadToken = token;
        // The shared byte reader validates against the element token as
        // well — keep both counters in lockstep.
        el._neonyMediaSourceToken = token;
        st.source = source;
        // Drop the previous decode immediately: buffers are the whole
        // file in PCM, so holding two during a switch doubles memory.
        st.buffer = null;
        waHardReset(st);

        el._neonyHydrating = true;
        notifyLoading(el, true);
        try {
            var read = await readProtocolBytes(el, source, token);
            if (!read || st.loadToken !== token || st.source !== source) return;
            var ctx = webAudio.ensureCtx();
            if (!ctx) throw new Error("WebAudio unavailable");
            var arrayBuf = read.bytes.slice().buffer;
            var buffer = await new Promise(function (resolve, reject) {
                var p = ctx.decodeAudioData(arrayBuf, resolve, reject);
                if (p && typeof p.then === "function") p.then(resolve, reject);
            });
            if (st.loadToken !== token || st.source !== source) return;
            st.buffer = buffer;
            st.duration = buffer.duration;
            st.offset = 0;
            st.endedSent = false;
            waEmit(key, "loadedmetadata", { media_duration: buffer.duration });
            waEmit(key, "durationchange", { media_duration: buffer.duration });
            if (st.pendingPlay) {
                st.pendingPlay = false;
                waStart(st, 0);
            }
        } catch (error) {
            if (st.loadToken === token) {
                console.error("[neony] audio decode failed:", error);
                waEmit(key, "error", { media_error: 4 }); // MEDIA_ERR_SRC_NOT_SUPPORTED
            }
        } finally {
            if (st.loadToken === token) {
                el._neonyHydrating = false;
                notifyLoading(el, false);
            }
        }
    }

    function waHardReset(st) {
        waStopSource(st);
        st.playing = false;
        st.offset = 0;
        st.duration = 0;
        st.pendingPlay = false;
        if (st.gain) {
            try { st.gain.disconnect(); } catch (_) {}
            st.gain = null;
        }
    }

    function waRelease(key) {
        var st = webAudio.states.get(key);
        if (!st) return;
        waHardReset(st);
        webAudio.states.delete(key);
    }

    function isWebAudioBacked(el) {
        return (
            !!el &&
            el.getAttribute &&
            el.getAttribute("data-neony-media-engine") === "webaudio" &&
            el.getAttribute("data-neony-key")
        );
    }

    function notifyLoading(el, active) {
        // Surface the hydration phase to the component so its transport
        // row can show a loading sweep where the position slider sits.
        if (!window.lumiview || !window.lumiview.invoke) return;
        var key = el.getAttribute && el.getAttribute("data-neony-key");
        if (!key) return;
        window.lumiview
            .invoke("neony.event", { key: key, event_type: "media_loading", value: active })
            .catch(function () {});
    }

    function base64ToBytes(b64) {
        var bin = atob(b64);
        var bytes = new Uint8Array(bin.length);
        for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
        return bytes;
    }

    function base64ToBlob(b64, type) {
        return new Blob([base64ToBytes(b64)], { type: type || "application/octet-stream" });
    }

    // Piecewise protocol read shared by both playback transports.  One
    // giant base64 reply would stall the asyncio loop (json.dumps) and
    // the WebView main thread (eval_js parse) for seconds on large
    // files.  Returns null when the hydration was superseded mid-read.
    async function readProtocolBytes(el, source, token) {
        const CHUNK = 1 << 20; // 1 MiB per round trip
        const parts = [];
        let offset = 0;
        let contentType = "application/octet-stream";
        for (;;) {
            if (el._neonyMediaSourceToken !== token || el._neonyMediaSource !== source) return null;
            const res = await window.lumiview.invoke("neony.media_read", {
                url: source,
                offset: offset,
                chunk: CHUNK,
            });
            if (res.status >= 400) throw new Error("protocol media request failed: " + res.status);
            const bytes = base64ToBytes(res.data_b64);
            parts.push(bytes);
            offset += bytes.length;
            if (res.content_type) contentType = res.content_type;
            if (res.complete || (res.total !== null && offset >= res.total)) break;
        }
        let total = 0;
        for (const part of parts) total += part.length;
        const out = new Uint8Array(total);
        let at = 0;
        for (const part of parts) {
            out.set(part, at);
            at += part.length;
        }
        return { bytes: out, contentType };
    }

    async function hydrateMedia(el) {
        if (!el) return;
        // Managed media only: the desired source arrives via the
        // data-neony-media-src contract (neony Video/Audio components).
        const source = el._neonyMediaSource || null;
        if (!source || !source.startsWith("neony://")) return;
        // WebAudio-backed elements never touch HTMLMediaElement src at
        // all — their bytes decode into buffer nodes instead (see the
        // engine block below for why the native path is not viable).
        // Without any AudioContext implementation we degrade to the
        // native pipeline rather than refusing to play.
        if (isWebAudioBacked(el) && webAudio.ensureCtx()) {
            await webAudioLoad(el, source);
            return;
        }
        // Drop any previously hydrated Blob first — this also covers
        // switching to a non-protocol source (https:/data:) that the
        // browser's own media pipeline loads natively.
        if (el._neonyMediaObjectUrl) {
            URL.revokeObjectURL(el._neonyMediaObjectUrl);
            el._neonyMediaObjectUrl = null;
        }
        const token = (el._neonyMediaSourceToken || 0) + 1;
        const key = el.getAttribute && el.getAttribute("data-neony-key");
        // WebKitGTK pipeline-reuse defect: loading a SECOND blob into an
        // already-hydrated <audio>/<video> makes the reused GStreamer
        // pipeline feed misaligned AAC frames to the decoder ("Audio
        // decoding error" / decode_pce warnings) and playback stays
        // silent for ~10 s until it resyncs.  A freshly built element
        // always decodes cleanly, so a re-hydration swaps in a clone:
        // dropping the old node destroys its media player outright and
        // the replacement builds a pristine pipeline.
        if (
            key &&
            engine.registry &&
            typeof engine.registry.set === "function" &&
            el.parentNode &&
            (el.getAttribute("src") || el._neonyMediaObjectUrl)
        ) {
            var freshNode = el.cloneNode(false);
            if (typeof el.volume === "number") {
                try { freshNode.volume = el.volume; } catch (_) { /* jsdom */ }
            }
            freshNode.muted = !!el.muted;
            // Engine bookkeeping lives in expando props, not attributes:
            // carry the desired source across so in-flight checks in THIS
            // hydration keep passing against the replacement.
            freshNode._neonyMediaSource = source;
            if (el._neonyPendingPlay) freshNode._neonyPendingPlay = true;
            freshNode._neonyDirectWired = false;
            wireDirectEvents(freshNode);
            var parent = el.parentNode;
            parent.replaceChild(freshNode, el);
            engine.registry.set(key, freshNode);
            releaseMedia(el); // revoke the outgoing Blob; dead node only
            el = freshNode;
        }
        el._neonyMediaSourceToken = token;
        // Detach the element from the OLD resource right away: reading a
        // large file through the bridge takes a while, and playback on
        // the stale blob (a silent tail, or the wrong file entirely)
        // must not survive the switch.  A play() arriving mid-hydration
        // is parked and resumed once the new source is attached.
        if (el.getAttribute("src")) {
            el.removeAttribute("src");
            if (typeof el.load === "function") {
                try { el.load(); } catch (_) { /* non-browser DOM */ }
            }
        }
        el._neonyHydrating = true;
        notifyLoading(el, true);
        try {
            let blob;
            if (window.lumiview && window.lumiview.invoke) {
                const read = await readProtocolBytes(el, source, token);
                if (!read) return; // superseded mid-read
                blob = new Blob([read.bytes], { type: read.contentType });
            } else {
                const response = await fetch(source, { credentials: "omit" });
                if (!response.ok) throw new Error("protocol media request failed: " + response.status);
                blob = await response.blob();
            }
            if (el._neonyMediaSourceToken !== token || el._neonyMediaSource !== source) return;
            const objectUrl = URL.createObjectURL(blob);
            el._neonyMediaObjectUrl = objectUrl;
            // Swapping src while the element's previous load is still in
            // flight does not restart resource selection on WebKitGTK —
            // the media pipeline stays stuck on the interrupted request
            // forever (readyState 0, no error).  An explicit load()
            // restarts it; jsdom has no usable HTMLMediaElement.load.
            el.setAttribute("src", objectUrl);
            if (typeof el.load === "function") {
                try { el.load(); } catch (_) { /* non-browser DOM */ }
            }
            if (el._neonyPendingPlay) {
                el._neonyPendingPlay = false;
                if (el.play) el.play().catch(function () {});
            }
        } catch (error) {
            if (el._neonyMediaSourceToken === token) {
                console.error("[neony] failed to hydrate media source", source, error);
            }
        } finally {
            if (el._neonyMediaSourceToken === token) {
                el._neonyHydrating = false;
                notifyLoading(el, false);
            }
        }
    }

    // ---- direct media events ----
    //
    // Media events (timeupdate, loadedmetadata, ...) do not bubble, so
    // document-level delegation can never see them.  Elements carrying
    // data-neony-direct-events="a,b,c" get real addEventListener hooks;
    // each firing is forwarded through the standard neony.event channel
    // with media state riding in dedicated payload fields.

    function wireDirectEvents(el) {
        if (!el || el._neonyDirectWired) return;
        var spec = el.getAttribute && el.getAttribute("data-neony-direct-events");
        if (!spec) return;
        el._neonyDirectWired = true;
        var types = spec.split(",");
        var onDirect = function (event) {
            if (!window.lumiview || !window.lumiview.invoke) return;
            var key = el.getAttribute("data-neony-key");
            if (!key) return;
            var payload = { key: key, event_type: event.type, value: null };
            if (el.currentTime !== undefined) payload.media_time = el.currentTime;
            if (el.duration !== undefined && !isNaN(el.duration)) payload.media_duration = el.duration;
            if (el.volume !== undefined) payload.media_volume = el.volume;
            payload.media_muted = !!el.muted;
            payload.media_paused = !!el.paused;
            if (event.type === "error" && el.error) payload.media_error = el.error.code;
            window.lumiview.invoke("neony.event", payload).catch(function (err) {
                // Visible, not silent: a rejected event payload means the
                // bridge command signature and JS drifted apart.
                console.error("[neony] media event dispatch failed:", err);
            });
        };
        for (var i = 0; i < types.length; i++) {
            var t = types[i].trim();
            if (t) el.addEventListener(t, onDirect);
        }
    }

    function mediaEl(key) {
        return engine.registry.get(key) || null;
    }

    window.neony = {
        engine,
        mount: (msg) => engine.mount(msg),
        applyMessage: (msg) => engine.applyMessage(msg),
        hydrateMedia,
        releaseMedia,
        wireDirectEvents,
        // Managed-media playback commands (neony Video/Audio components).
        mediaPlay: (key) => {
            var el = mediaEl(key);
            if (isWebAudioBacked(el)) {
                var st0 = waStateOf(key, el);
                if (!st0.buffer || el._neonyHydrating) {
                    st0.pendingPlay = true; // decode in flight — resume on arrival
                    return;
                }
                waStart(st0, st0.playing ? st0.offset : st0.offset);
                return;
            }
            if (!el || !el.play) {
                if (window.__NEONY_DIAG) console.error("[neony-diag] mediaPlay: no element for", key);
                return;
            }
            if (el._neonyHydrating) {
                // Source still being read through the bridge — resume as
                // soon as the new Blob is attached instead of failing on
                // the detached element.
                el._neonyPendingPlay = true;
                return;
            }
            el.play().catch(function () {});
        },
        mediaPause: (key) => {
            var el = mediaEl(key);
            if (isWebAudioBacked(el)) {
                waStateOf(key, el).pendingPlay = false;
                waPause(waStateOf(key, el));
                return;
            }
            el._neonyPendingPlay = false;
            if (el && el.pause) el.pause();
        },
        mediaSeek: (key, time) => {
            var el = mediaEl(key);
            if (isWebAudioBacked(el)) {
                if (isFinite(time)) waSeek(waStateOf(key, el), time);
                return;
            }
            if (el && isFinite(time)) el.currentTime = time;
        },
        mediaSetMuted: (key, muted) => {
            var el = mediaEl(key);
            if (isWebAudioBacked(el)) {
                var stM = waStateOf(key, el);
                stM.muted = !!muted;
                waApplyGain(stM);
                waEmit(key, "volumechange");
                return;
            }
            if (el) el.muted = !!muted;
        },
        mediaSetVolume: (key, volume) => {
            var el = mediaEl(key);
            if (isWebAudioBacked(el)) {
                var stV = waStateOf(key, el);
                if (isFinite(volume)) stV.volume = Math.min(1, Math.max(0, volume));
                waApplyGain(stV);
                waEmit(key, "volumechange");
                return;
            }
            if (el && isFinite(volume)) el.volume = Math.min(1, Math.max(0, volume));
        },
        // Internal: drives WebAudio timeupdate/ended synthesis.  Exposed
        // so tests (and embedders without rAF loops) can pump the clock.
        mediaEngineTick: () => waTick(),
        // Internal: drops the shared AudioContext and all per-element
        // state.  Tests reset between cases; embedders can use it on
        // page teardown to release the audio device immediately.
        mediaEngineReset: () => {
            webAudio.states.forEach(waHardReset);
            webAudio.states.clear();
            if (webAudio.ctx) {
                try { webAudio.ctx.close(); } catch (_) {}
                webAudio.ctx = null;
            }
        },
        // Internal scroll commands.  Keyed lookup only; the smooth/auto
        // behavior maps directly to the native Element.scrollTo options
        // (jsdom falls back to a plain scrollTop assignment).
        scrollTo: (key, top, behavior) => {
            const el = engine.registry.get(key);
            if (!el) return false;
            const opts = { top: top, behavior: behavior || "auto" };
            if (typeof el.scrollTo === "function") {
                el.scrollTo(opts);
            } else {
                el.scrollTop = top;
            }
            return true;
        },
        scrollToBottom: (key, behavior) => {
            const el = engine.registry.get(key);
            if (!el) return false;
            const top = el.scrollHeight - el.clientHeight;
            const opts = { top: top > 0 ? top : 0, behavior: behavior || "auto" };
            if (typeof el.scrollTo === "function") {
                el.scrollTo(opts);
            } else {
                el.scrollTop = opts.top;
            }
            return true;
        },
        scrollToTop: (key, behavior) => {
            const el = engine.registry.get(key);
            if (!el) return false;
            const opts = { top: 0, behavior: behavior || "auto" };
            if (typeof el.scrollTo === "function") {
                el.scrollTo(opts);
            } else {
                el.scrollTop = 0;
            }
            return true;
        },
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

    // ---- StickToBottom auto-stick (data-neony-autostick) ----
    //
    // Chat-stream scroll model: pinned while the user is near the bottom;
    // new content is appended by the patch engine and the observer keeps
    // the view pinned.  Scrolling up un-pins; scrolling back near the
    // bottom re-pins.  This is internal JS — Python sees only the
    // StickToBottom component and its scroll_to_bottom(force=True) API.
    var autostickStates = new WeakMap();

    function autostickAttach(el) {
        if (autostickStates.has(el)) return;
        var state = { el: el, pinned: true, mo: null, onScroll: null };

        function update() {
            var distance = el.scrollHeight - el.scrollTop - el.clientHeight;
            state.pinned = distance < 80;
        }
        function onScroll() { update(); }
        el.addEventListener("scroll", onScroll, { passive: true });

        var mo = new MutationObserver(function () {
            update();
            if (state.pinned) {
                el.scrollTop = el.scrollHeight;
            }
        });
        mo.observe(el, { childList: true, subtree: true, characterData: true });
        state.mo = mo;
        state.onScroll = onScroll;
        autostickStates.set(el, state);
        update();
        el.scrollTop = el.scrollHeight;
    }

    function autostickDetach(el) {
        var state = autostickStates.get(el);
        if (!state) return;
        if (state.mo) state.mo.disconnect();
        if (state.onScroll) el.removeEventListener("scroll", state.onScroll);
        autostickStates.delete(el);
    }

    function autostickScanAll(root) {
        var nodes = root.querySelectorAll("[data-neony-autostick]");
        for (var i = 0; i < nodes.length; i++) autostickAttach(nodes[i]);
    }
    autostickScanAll(document);

    var autostickObserver = new MutationObserver(function (records) {
        for (var r = 0; r < records.length; r++) {
            var rec = records[r];
            for (var a = 0; a < rec.addedNodes.length; a++) {
                var node = rec.addedNodes[a];
                if (node.nodeType !== 1) continue;
                if (node.matches && node.matches("[data-neony-autostick]")) autostickAttach(node);
                if (node.querySelectorAll) autostickScanAll(node);
            }
            for (var d = 0; d < rec.removedNodes.length; d++) {
                var gone = rec.removedNodes[d];
                if (gone.nodeType !== 1) continue;
                if (autostickStates.has(gone)) autostickDetach(gone);
                if (gone.querySelectorAll) {
                    var inner = gone.querySelectorAll("[data-neony-autostick]");
                    for (var g = 0; g < inner.length; g++) autostickDetach(inner[g]);
                }
            }
        }
    });
    function autostickStartObserver() {
        if (document.body) {
            autostickScanAll(document);
            autostickObserver.observe(document.body, { childList: true, subtree: true });
        } else {
            document.addEventListener("DOMContentLoaded", autostickStartObserver, { once: true });
        }
    }
    autostickStartObserver();

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
        "pointermove", "scroll",
        "transitionend", "animationstart", "animationend",
        "wheel", "paste", "copy", "cut",
        "dragstart", "dragenter", "dragover", "dragleave", "drop", "dragend",
        "compositionstart", "compositionupdate", "compositionend",
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
        // contenteditable hosts have no `value`; their user data is text.
        if (el.isContentEditable) return el.innerText;
        return null;
    }

    // ---- pointer-driven in-app drags ----
    //
    // HTML5 drag-and-drop is unreliable on WebKitGTK/Wayland: the native
    // drag image positions randomly (sometimes grab-relative, sometimes
    // absolute) and dragstart-time DOM mutations / canvas setDragImage
    // abort the drag entirely.  The drop hit-test uses the REAL pointer
    // while the user aims at the (wrongly-placed) image — so reorder
    // fires only sometimes.
    //
    // Elements with data-neony-drag therefore skip HTML5 DnD entirely:
    // a mousedown arms the drag, and once the pointer moves ~4px the
    // element gets a synthetic dragstart (synchronous setData via a
    // synthetic DataTransfer, exactly like the native flow), a self-drawn
    // ghost tracks the pointer locally (one rAF per frame, zero IPC),
    // dragover is dispatched to the element under the cursor via
    // elementFromPoint, and drop/dragend fire at release.  The synthetic
    // events flow through the SAME eventHandler pipeline, so the Python
    // API (drag_payload / on_dragstart / on_dragover / on_drop) is
    // unchanged.  Draggable attributes are stripped from the DOM so the
    // browser never starts its own (misbehaving) drag.
    var dndState = null; // active pointer-drag, or null
    var lastDragover = {};

    function dndActive() {
        return dndState !== null;
    }

    // Restore the ghost-targeted styles on the source and clear any
    // FLIP transforms/transitions the drag left on its siblings.  The
    // source itself keeps its restored transition (it may be the target
    // of a settle FLIP right after).
    function dndRestoreSource() {
        if (!dndState) return;
        var src = dndState.source;
        var container = dndState.srcParent;
        if (container) {
            var kids = container.children;
            for (var j = 0; j < kids.length; j++) {
                var el = kids[j];
                if (el === src) continue;
                el.style.transform = "";
                el.style.transition = "";
            }
        }
        if (src) {
            var ghostProps = dndState.ghostProps;
            for (var p in ghostProps) src.style[p] = ghostProps[p];
        }
    }

    function dndClear() {
        if (!dndState) return;
        // The placeholder is a raw JS div — the Python diff knows nothing
        // about it.  Every abort path (blur mid-drag, cancelled mouseup)
        // must remove it, or the dashed slot sticks in the DOM as a blank
        // box.
        var ph = dndState.placeholder;
        if (ph && ph.parentNode) ph.parentNode.removeChild(ph);
        dndRestoreSource();
        dndState = null;
    }

    // Synthetic DataTransfer carrying the payload across the synthetic
    // drag lifecycle (setData in dragstart, getData on drop).
    function makeDndTransfer(payload) {
        var store = payload ? { "application/x-neony": payload } : {};
        return {
            setData: function (type, value) {
                store[type] = value;
            },
            getData: function (type) {
                return store[type] || "";
            },
            files: [],
            effectAllowed: "none",
        };
    }

    function dndDispatch(target, type, transfer, x, y) {
        var evt = new Event(type, { bubbles: true, cancelable: true });
        // Native offsetX/offsetY are relative to the TARGET element (the
        // reorder demo splits a 40px card at its own 0..40 range); page
        // coordinates here made every drop look like the card's lower
        // half, so upward reorders always inserted AFTER the target.
        var rect = target.getBoundingClientRect();
        Object.defineProperty(evt, "dataTransfer", { value: transfer });
        Object.defineProperty(evt, "clientX", { value: x });
        Object.defineProperty(evt, "clientY", { value: y });
        Object.defineProperty(evt, "offsetX", { value: x - rect.left });
        Object.defineProperty(evt, "offsetY", { value: y - rect.top });
        target.dispatchEvent(evt);
    }

    // Real HTML5 drag events for data-neony-drag elements are swallowed
    // (preventDefault on dragstart cancels the browser's own drag; the
    // pointer-driven path owns the lifecycle).
    function dndOnDragStart(event) {
        var src = event.target.closest ? event.target.closest("[data-neony-drag]") : null;
        if (!src) return;
        event.preventDefault();
    }

    function dndOnMouseDown(event) {
        if (event.button !== 0) return;
        var src = event.target.closest ? event.target.closest("[data-neony-drag]") : null;
        if (!src) return;
        // Neutralize the element's draggable attribute so the browser can
        // never start its own (misbehaving) HTML5 drag — the pointer path
        // owns the lifecycle from here.  Keep the payload marker.
        src.removeAttribute("draggable");
        dndState = {
            source: src,
            payload: src.getAttribute("data-neony-drag"),
            transfer: makeDndTransfer(src.getAttribute("data-neony-drag")),
            x: event.clientX,
            y: event.clientY,
            offsetX: event.clientX,
            offsetY: event.clientY,
            ghost: null,
            rafId: 0,
            started: false,
            insertion: null,
            srcParent: null,
            sourceParent: null,
            ghostProps: {},
        };
        document.addEventListener("mousemove", dndOnMouseMove, true);
        document.addEventListener("mouseup", dndOnMouseUp, true);
        // Dragging OUT of the window and releasing there loses the mouseup
        // (Wayland/GTK: the pointer leaves, the release never reaches us)
        // — only a blur arrives.  Abort the drag so the ghost and the
        // dashed landing slot don't stick in the DOM as a blank box.
        window.addEventListener("blur", dndOnBlur, true);
    }

    function dndOnBlur() {
        if (!dndState) return;
        document.removeEventListener("mousemove", dndOnMouseMove, true);
        document.removeEventListener("mouseup", dndOnMouseUp, true);
        window.removeEventListener("blur", dndOnBlur, true);
        dndClear();
    }

    function dndOnMouseMove(event) {
        if (!dndState || !dndState.source) return;
        if (!dndState.started) {
            var dx = event.clientX - dndState.offsetX;
            var dy = event.clientY - dndState.offsetY;
            if (dx * dx + dy * dy < 16) return; // 4px threshold
            dndBegin(event);
        }
        dndMove(event);
    }

    function dndBegin(event) {
        dndState.started = true;
        // Synthetic dragstart on the source (sync setData, like native).
        var src = dndState.source;
        var transfer = dndState.transfer;
        var de = new Event("dragstart", { bubbles: true, cancelable: true });
        Object.defineProperty(de, "dataTransfer", { value: transfer });
        src.dispatchEvent(de);

        // Save the ghost-targeted props so dndClear can restore them —
        // the source's OTHER inline styles (background, border, padding
        // injected by Neony) must survive.
        var ghostProps = dndState.ghostProps;
        var rect = src.getBoundingClientRect();
        ghostProps.position = src.style.position;
        ghostProps.left = src.style.left;
        ghostProps.top = src.style.top;
        ghostProps.width = src.style.width;
        ghostProps.height = src.style.height;
        ghostProps.margin = src.style.margin;
        ghostProps.zIndex = src.style.zIndex;
        ghostProps.pointerEvents = src.style.pointerEvents;
        ghostProps.transition = src.style.transition;
        ghostProps.boxShadow = src.style.boxShadow;
        ghostProps.opacity = src.style.opacity;

        // The source card leaves the flow and becomes the ghost itself.
        // Anchored at 0,0 — the translate transform (from dndGhostFollow)
        // does ALL the positioning, so the ghost sits exactly under the
        // cursor's grab offset.  (Fixing it at rect.left/rect.top would
        // double-offset it by the card's own position, so the ghost floats
        // away from the cursor — aim and drop then disagree.)
        src.style.position = "fixed";
        src.style.left = "0px";
        src.style.top = "0px";
        src.style.width = rect.width + "px";
        src.style.height = rect.height + "px";
        src.style.margin = "0";
        src.style.zIndex = "2147483647";
        src.style.pointerEvents = "none";
        src.style.transition = "none";
        src.style.boxShadow = "0 10px 28px rgba(0,0,0,0.35)";
        src.style.opacity = "0.9";
        dndState.srcParent = src.parentNode;
        dndState.sourceParent = src.parentNode;
        dndState.axis = dndAxisOf(src.parentNode);
        var ph = document.createElement("div");
        // A visible "landing slot": the card's footprint as a dashed
        // outline, shown only while the cursor is over an insertion point
        // (hidden at the source slot).  Makes the drop target obvious
        // instead of an invisible gap.  Sized along the container's main
        // axis (height for a column, width for a row).
        ph.setAttribute("data-neony-dnd-placeholder", "");
        ph.style.cssText =
            "pointer-events:none;flex-shrink:0;box-sizing:border-box;align-self:stretch;" +
            (dndState.axis === "horizontal"
                ? "width:" + rect.width + "px;"
                : "height:" + rect.height + "px;") +
            "border:2px dashed rgba(108,140,255,0.9);border-radius:8px;" +
            "background:rgba(108,140,255,0.08);visibility:hidden;";
        src.parentNode.insertBefore(ph, src.nextSibling);
        dndState.placeholder = ph;
        dndState.ghost = src;
        dndState.offsetX = event.clientX - rect.left;
        dndState.offsetY = event.clientY - rect.top;
        // Park the ghost at its layout slot synchronously — the translate
        // (rect.left, rect.top) matches the grab point, and it can't paint
        // a stray frame at the page origin before the first rAF.
        src.style.transform =
            "translate3d(" + (event.clientX - dndState.offsetX) + "px," +
            (event.clientY - dndState.offsetY) + "px,0)";
    }

    // Which axis the drag's container lays out along — decides the
    // before/after cursor test (clientY for a column, clientX for a row)
    // and the placeholder's size.  Defaults to vertical.
    function dndAxisOf(container) {
        if (!container) return "vertical";
        var dir = "";
        try {
            var cs = window.getComputedStyle(container);
            if (cs) dir = cs.flexDirection || "";
        } catch (e) {}
        if (!dir) dir = container.style.flexDirection || "";
        return dir.indexOf("row") === 0 ? "horizontal" : "vertical";
    }

    // Resize the placeholder along the CURRENT container's axis (the
    // re-home path can move the drag into a differently-oriented board).
    // The footprint matches the passed *rect* (the hovered card of the
    // re-homed board), defaulting to the source's own size.
    function dndResizePlaceholder(rect) {
        if (!dndState || !dndState.placeholder) return;
        var ph = dndState.placeholder;
        if (!rect) rect = dndState.source.getBoundingClientRect();
        if (dndState.axis === "horizontal") {
            ph.style.width = rect.width + "px";
            ph.style.height = "";
        } else {
            ph.style.height = rect.height + "px";
            ph.style.width = "";
        }
    }

    function dndMove(event) {
        if (!dndState || !dndState.started) return;
        dndState.x = event.clientX;
        dndState.y = event.clientY;
        dndGhostFollow();
        var over = document.elementFromPoint(event.clientX, event.clientY);
        var overKeyed = over && over.closest ? over.closest("[data-neony-key]") : null;
        if (overKeyed && overKeyed !== dndState.source) {
            dndDispatch(overKeyed, "dragover", dndState.transfer, event.clientX, event.clientY);
            dndPreviewInsertion(overKeyed, event.clientX, event.clientY);
        } else {
            dndPreviewInsertion(null, 0, 0);
        }
    }

    // Position-only drop preview: the invisible placeholder (which keeps
    // the source slot open) travels to the insertion point, so the list
    // shows a single gap where the card will land.  No element is ever
    // resized — siblings only shift position, FLIP-animated.
    function dndPreviewInsertion(target, clientX, clientY) {
        if (!dndState || !dndState.srcParent || !dndState.placeholder) return;
        var ph = dndState.placeholder;
        var container = dndState.srcParent;
        var horizontal = dndState.axis === "horizontal";
        // Cross-container: hovering a card in ANOTHER board re-homes the
        // placeholder there, so the landing slot shows in the target board
        // (the source board closes up).  Gated on data-neony-drag so plain
        // keyed ancestors never trigger a re-home.
        if (
            target &&
            target.hasAttribute &&
            target.hasAttribute("data-neony-drag") &&
            target !== dndState.source &&
            target.parentNode &&
            target.parentNode !== container
        ) {
            container = target.parentNode;
            dndState.srcParent = container;
            dndState.axis = dndAxisOf(container);
            horizontal = dndState.axis === "horizontal";
            dndResizePlaceholder(target.getBoundingClientRect());
        }
        if (target && target.parentNode === container) {
            // Judge the cursor against the hovered card along the
            // container's axis: the first half inserts before it, the
            // second half after it.
            var rect = target.getBoundingClientRect();
            var mid = horizontal ? rect.left + rect.width / 2 : rect.top + rect.height / 2;
            var cursor = horizontal ? clientX : clientY;
            var before = cursor < mid;
            var key = (target.getAttribute("data-neony-key") || "") + (before ? ":before" : ":after");
            if (dndState.insertion === key) return;
            // Tiny hysteresis (~2px): flip crisply at the midline without
            // oscillating exactly on it (each flip re-runs the FLIP).
            if (dndState.insertion && dndState.insertion.indexOf((target.getAttribute("data-neony-key") || "") + ":") === 0) {
                var dead = Math.min(2, (horizontal ? rect.width : rect.height) / 2);
                if (Math.abs(cursor - mid) < dead) return;
            }
            dndState.insertion = key;
            ph.style.visibility = "visible";
            var where = before ? target : target.nextSibling;
            if (where === ph) return;
            dndFlipMove(container, function () {
                container.insertBefore(ph, where);
            });
            return;
        }
        // Not a card: keep the committed insertion while the cursor stays
        // inside this container (the visible slot must not vanish when the
        // cursor reaches for it); clear it only when the cursor leaves the
        // container entirely.
        if (target && container.contains(target)) return;
        if (dndState.insertion === "none") return;
        dndState.insertion = "none";
        ph.style.visibility = "hidden";
        // The placeholder's home is the SOURCE's original container — after
        // a re-home the drag may live in another board.
        dndState.srcParent = dndState.sourceParent;
        dndState.axis = dndAxisOf(dndState.sourceParent);
        dndResizePlaceholder();
        container = dndState.srcParent;
        var revert = dndState.source.nextSibling;
        if (revert === ph) return;
        dndFlipMove(container, function () {
            container.insertBefore(ph, revert);
        });
    }

    // FLIP: record every sibling's position FIRST, apply the caller's DOM
    // move, then offset each moved sibling back to its old spot and animate
    // it to the new one on the next frame.  The source ghost is excluded —
    // its transform belongs to dndGhostFollow.
    function dndFlipMove(container, doMove) {
        var kids = [];
        for (var i = 0; i < container.children.length; i++) kids.push(container.children[i]);
        var firsts = [];
        for (var j = 0; j < kids.length; j++) {
            var r = kids[j].getBoundingClientRect();
            firsts.push({ top: r.top, left: r.left });
        }
        doMove();
        void container.offsetHeight; // flush, so deltas are vs the NEW layout
        var moved = [];
        for (var k = 0; k < kids.length; k++) {
            var el = kids[k];
            if (el === dndState.source) continue;
            var f = firsts[k];
            var r2 = el.getBoundingClientRect();
            var dx = f.left - r2.left;
            var dy = f.top - r2.top;
            if (dx || dy) {
                // Snap to the hold position — a leftover transform
                // transition from a previous flip would otherwise animate
                // this first step and double-move the element.
                el.style.transition = "none";
                el.style.transform = "translate(" + dx + "px," + dy + "px)";
                moved.push(el);
            }
        }
        if (!moved.length) return;
        requestAnimationFrame(function () {
            for (var m = 0; m < moved.length; m++) {
                var e2 = moved[m];
                e2.style.transition = "transform 120ms ease";
                e2.style.transform = "";
            }
        });
    }

    function dndGhostFollow() {
        if (!dndState || !dndState.ghost) return;
        if (dndState.rafId) return;
        var s = dndState;
        s.rafId = 1;
        requestAnimationFrame(function () {
            s.rafId = 0;
            if (!dndState || !s.ghost) return;
            s.ghost.style.transform =
                "translate3d(" + (s.x - s.offsetX) + "px," + (s.y - s.offsetY) + "px,0)";
        });
    }

    function dndOnMouseUp(event) {
        document.removeEventListener("mousemove", dndOnMouseMove, true);
        document.removeEventListener("mouseup", dndOnMouseUp, true);
        window.removeEventListener("blur", dndOnBlur, true);
        if (!dndState || !dndState.started) {
            dndClear();
            return;
        }
        var transfer = dndState.transfer;
        var target = dndState.source;
        var before = false;
        var x = event.clientX;
        var y = event.clientY;
        // Honor the committed insertion: the drop lands EXACTLY where the
        // placeholder showed it.  Using the raw cursor offset here would
        // drift from the preview near a card's midline (hysteresis dead
        // zone) or on a fast release — the preview and the result then
        // disagree.
        var ins = dndState.insertion;
        if (ins && ins !== "none") {
            var colon = ins.lastIndexOf(":");
            var targetKey = ins.slice(0, colon);
            before = ins.slice(colon + 1) === "before";
            var kids = dndState.srcParent ? dndState.srcParent.children : null;
            if (kids) {
                for (var i = 0; i < kids.length; i++) {
                    if (kids[i].getAttribute("data-neony-key") === targetKey) {
                        target = kids[i];
                        var tr = target.getBoundingClientRect();
                        // Encode the side on the container's axis so the
                        // handler's "< mid" test yields the committed
                        // insertion (offset_y for a column, offset_x for a
                        // row).
                        if (dndState.axis === "horizontal") {
                            x = before ? tr.left : tr.left + tr.width;
                        } else {
                            y = before ? tr.top : tr.top + tr.height;
                        }
                        break;
                    }
                }
            }
        } else {
            var over = document.elementFromPoint(event.clientX, event.clientY);
            var overKeyed = over && over.closest ? over.closest("[data-neony-key]") : null;
            if (overKeyed) target = overKeyed;
        }
        dndDispatch(target, "drop", transfer, x, y);
        dndDispatch(dndState.source, "dragend", transfer, event.clientX, event.clientY);
        // Animate the reorder into its final layout: the source glides
        // from the cursor into the committed slot and the rest shift into
        // place — the "end" animation to match the "start" pickup.
        dndSettle(target, before);
    }

    // Drop settle: FLIP everything (including the source ghost) from its
    // current spot into the final layout.  The source is reinserted into
    // the flow at the committed insertion, so the Python patch that
    // follows the drop is a no-op for it — no double animation.
    function dndSettle(target, before) {
        if (!dndState || !dndState.srcParent) return;
        var src = dndState.source;
        var container = dndState.srcParent;
        var ph = dndState.placeholder;
        var kids = [];
        for (var i = 0; i < container.children.length; i++) kids.push(container.children[i]);
        var firsts = [];
        for (var j = 0; j < kids.length; j++) {
            var r = kids[j].getBoundingClientRect();
            firsts.push({ top: r.top, left: r.left });
        }
        // The source's ghost position BEFORE restore — after restore it is
        // static again (back at its original slot), and the FLIP must glide
        // it from the CURSOR into the committed slot.
        var srcFirst = src.getBoundingClientRect();
        if (ph && ph.parentNode) ph.parentNode.removeChild(ph);
        dndRestoreSource();
        // The source glides into the committed slot — WITHIN this board,
        // or across boards: the Python handler moves the card model and
        // the diff emits a MovePatch (cross-parent move), which re-parents
        // THIS SAME element — no flash, no blank slot.
        if (target && target.parentNode === container) {
            container.insertBefore(src, before ? target : target.nextSibling);
        }
        var moved = [];
        var origTrans = {};
        for (var k = 0; k < kids.length; k++) {
            var el = kids[k];
            if (el === ph || el === src) continue;
            var f = firsts[k];
            var r2 = el.getBoundingClientRect();
            var dx = f.left - r2.left;
            var dy = f.top - r2.top;
            if (dx || dy) {
                origTrans[el] = el.style.transition;
                el.style.transition = "none";
                el.style.transform = "translate(" + dx + "px," + dy + "px)";
                moved.push(el);
            }
        }
        // The source leaves the flow as a ghost (its transform follows the
        // cursor), so it is NOT in `kids`' recorded flow position — the FLIP
        // loop above skips it.  FLIP it from the CURSOR into the committed
        // slot, or its ghost transform survives and the card hangs offset
        // at the slot (looks like it vanished — worse across a wrap row,
        // where the offset is a full row).
        if (src.parentNode === container) {
            var r3 = src.getBoundingClientRect();
            var sdx = srcFirst.left - r3.left;
            var sdy = srcFirst.top - r3.top;
            if (sdx || sdy) {
                origTrans[src] = src.style.transition;
                src.style.transition = "none";
                src.style.transform = "translate(" + sdx + "px," + sdy + "px)";
                moved.push(src);
            } else {
                src.style.transform = "";
            }
        }
        if (!moved.length) {
            dndState = null;
            return;
        }
        requestAnimationFrame(function () {
            for (var m = 0; m < moved.length; m++) {
                var e2 = moved[m];
                e2.style.transition = "transform 220ms cubic-bezier(.2,.8,.2,1)";
                e2.style.transform = "";
            }
            setTimeout(function () {
                for (var n = 0; n < moved.length; n++) {
                    moved[n].style.transition = origTrans[moved[n]];
                }
            }, 260);
        });
        dndState = null;
    }

    // Test-only reset hook: clears any in-flight pointer drag.
    window.__neonyDndReset = dndClear;

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

    function readClipboardFiles(key, fileList) {
        // FileReader is async, so pasted file bytes cannot ride on the
        // synchronous paste event.  Read each file as a data URL and
        // deliver a synthetic ``neony.paste_files`` command when done.
        var delivered = [];
        var remaining = fileList.length;
        if (remaining === 0) return;
        for (var i = 0; i < fileList.length; i++) {
            (function (file) {
                var reader = new FileReader();
                reader.onload = function () {
                    delivered.push({
                        name: file.name,
                        size: file.size,
                        type: file.type,
                        data_url: reader.result,
                    });
                    remaining -= 1;
                    if (remaining === 0) {
                        window.lumiview
                            .invoke("neony.paste_files", { key: key, files: delivered })
                            .catch(function () {});
                    }
                };
                reader.onerror = function () {
                    remaining -= 1;
                    if (remaining === 0 && delivered.length > 0) {
                        window.lumiview
                            .invoke("neony.paste_files", { key: key, files: delivered })
                            .catch(function () {});
                    }
                };
                reader.readAsDataURL(file);
            })(fileList[i]);
        }
    }

    function positionCascadeSubmenu(event) {
        if (event.type !== "mouseover" || !event.target.closest) return;
        var row = event.target.closest('[data-neony-cascade-row="true"]');
        if (!row) return;
        var submenu = null;
        for (var i = 0; i < row.children.length; i++) {
            var child = row.children[i];
            if (child.matches && child.matches('[role="menu"]')) {
                submenu = child;
                break;
            }
        }
        // Menu panels are generic divs today; use the second keyed child as
        // the submenu while keeping the role lookup ready for richer ARIA.
        if (!submenu && row.children.length > 1) submenu = row.children[1];
        if (!submenu || !submenu.getBoundingClientRect) return;

        // Measure the hidden panel without flashing it. Its normal open state
        // is applied by Python immediately after this delegated hover event.
        var oldDisplay = submenu.style.display;
        var oldVisibility = submenu.style.visibility;
        submenu.style.display = "flex";
        submenu.style.visibility = "hidden";
        submenu.style.left = "calc(100% + 4px)";
        submenu.style.right = "auto";
        submenu.style.top = "0px";
        var rowRect = row.getBoundingClientRect();
        var menuRect = submenu.getBoundingClientRect();
        var gap = 4;
        var roomRight = window.innerWidth - rowRect.right;
        var roomLeft = rowRect.left;
        if (roomRight < menuRect.width + gap && roomLeft >= menuRect.width + gap) {
            submenu.style.left = "auto";
            submenu.style.right = "calc(100% + 4px)";
        }
        var projectedBottom = rowRect.top + menuRect.height;
        if (projectedBottom > window.innerHeight - gap) {
            submenu.style.top = Math.min(0, window.innerHeight - gap - projectedBottom) + "px";
        }
        submenu.style.visibility = oldVisibility;
        submenu.style.display = oldDisplay;
    }

    // ---- narrow overlay coordination ----
    //
    // These are deliberately two component-specific policies, not a global
    // "one overlay" rule: Dialog, Tooltip, Select and ordinary dropdowns
    // retain their existing independent lifecycles.
    var messageActionsOwner = null;
    var messageActionsHideTimer = null;
    var MESSAGE_ACTIONS_HIDE_DELAY_MS = 160;

    function cancelMessageActionsHide() {
        if (messageActionsHideTimer !== null) {
            clearTimeout(messageActionsHideTimer);
            messageActionsHideTimer = null;
        }
    }

    function setMessageActionsVisible(root, visible) {
        if (!root || !root.isConnected) return;
        var key = root.getAttribute("data-neony-message-actions");
        var row = key ? engine.registry.get(key) : null;
        if (row) row.style.display = visible ? "flex" : "none";
    }

    function coordinateMessageActions(event) {
        if (event.type !== "mouseover" && event.type !== "mouseout") return;
        var root = event.target.closest ? event.target.closest("[data-neony-message-actions]") : null;
        if (!root) return;
        var related = event.relatedTarget;
        if (related && root.contains(related)) return; // internal bubble/action-row hop
        if (event.type === "mouseover") {
            cancelMessageActionsHide();
            if (messageActionsOwner && messageActionsOwner !== root) {
                setMessageActionsVisible(messageActionsOwner, false);
            }
            messageActionsOwner = root;
            setMessageActionsVisible(root, true);
        } else if (messageActionsOwner === root) {
            cancelMessageActionsHide();
            var owner = root;
            messageActionsHideTimer = setTimeout(function () {
                if (messageActionsOwner === owner) {
                    setMessageActionsVisible(owner, false);
                    messageActionsOwner = null;
                }
                messageActionsHideTimer = null;
            }, MESSAGE_ACTIONS_HIDE_DELAY_MS);
        }
    }

    function closeSupersededContextMenus(current) {
        var menus = document.querySelectorAll('[data-neony-overlay-group="context-menu"][data-neony-overlay-open="true"]');
        for (var i = 0; i < menus.length; i++) {
            var menu = menus[i];
            if (menu === current) continue;
            menu.style.display = "none"; // remove the visual residue before IPC returns
            var key = menu.getAttribute("data-neony-key");
            if (key) {
                window.lumiview.invoke("neony.event", { key: key, event_type: "outsideclick", value: null }).catch(function () {});
            }
        }
    }

    // Attribute patches are the authoritative indication that Python opened a
    // cursor menu.  Observe them instead of treating every Menu instance (or
    // every data-neony-outside node) as mutually exclusive.
    var overlayObserver = new MutationObserver(function (records) {
        for (var i = 0; i < records.length; i++) {
            var menu = records[i].target;
            if (
                menu.getAttribute("data-neony-overlay-group") === "context-menu" &&
                menu.getAttribute("data-neony-overlay-open") === "true"
            ) {
                closeSupersededContextMenus(menu);
            }
        }
        if (messageActionsOwner && !messageActionsOwner.isConnected) messageActionsOwner = null;
    });
    overlayObserver.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["data-neony-overlay-group", "data-neony-overlay-open"],
        childList: true,
        subtree: true,
    });

    function eventHandler(event) {
        positionCascadeSubmenu(event);
        if (event.type === "contextmenu") {
            closeSupersededContextMenus(null);
        }
        coordinateMessageActions(event);
        // Interactive scopes own their decorated descendants.  Font/glyph
        // icons often receive the physical hit; resolving them straight to
        // the enclosing button keeps click/hover/press semantics at the
        // accessible control instead of depending on per-child Python
        // bubbling workarounds.
        var eventScope = event.target.closest ? event.target.closest("[data-neony-event-scope]") : null;
        var el = eventScope || (event.target.closest ? event.target.closest("[data-neony-key]") : null);
        // Keys typed while no element is focused land on <body> — no
        // data-neony-key ancestor to trace to.  Window-level key
        // listeners (Page.on_keydown / on_keyup, shortcuts) must still
        // fire, so route keyboard events through the engine root.  The
        // document's own scroll (a plain <body>/<html> scroll, target is
        // `document` — which has no closest) routes the same way so a
        // window-level scroll listener sees it.
        if (!el && (event.type === "keydown" || event.type === "keyup" || event.type === "scroll")) {
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

        // In-app drags: an element with data-neony-drag (from
        // DOMElement.drag_payload) is draggable.  setData MUST run
        // synchronously inside the dragstart event, so the payload is
        // read from the element's attribute — a Python round-trip would
        // be far too late.  effectAllowed "move" signals a reorder.
        if (event.type === "dragstart" && event.dataTransfer) {
            var dragPayload = el.getAttribute("data-neony-drag");
            if (dragPayload !== null) {
                event.dataTransfer.setData("application/x-neony", dragPayload);
                event.dataTransfer.effectAllowed = "move";
            }
        }

        // Dragover throttle: dragover fires for EVERY pointer motion
        // during a drag.  Forwarding each one is a full Python round-trip
        // and the events queue up BEHIND the drop, delaying it — the
        // "reorder animation lags, drag feels broken" symptom.  The drop
        // itself carries everything a handler needs (drag_payload,
        // coordinates), so per-dragover traffic only matters for drop-zone
        // highlighting — throttled to ~8/s keeps that alive without the
        // flood.  The map is cleared on drop/dragend so keys don't pile up.
        var elKey = el.getAttribute("data-neony-key");
        if (event.type === "dragover") {
            event.preventDefault();
            var now = Date.now();
            if (lastDragover[elKey] !== undefined && now - lastDragover[elKey] < 120) {
                return;
            }
            lastDragover[elKey] = now;
        } else if (event.type === "drop" || event.type === "dragend") {
            lastDragover = {};
        }

        // Window-control buttons: on *click* only, run the native
        // `lumiview.window.*` action (a plain hover must never close a
        // window), then still forward the normal Neony event.
        var winAction = el.getAttribute("data-window-action");
        if (winAction && event.type === "click" && window.lumiview.window) {
            var action = window.lumiview.window[winAction];
            if (action) action();
        }

        var value = captureValue(el, event);

        var payload = {
            key: elKey,
            event_type: event.type,
            value: value,
        };

        // RichText internals: expose caret/image info for contenteditable
        // editors and keep Enter from inserting newlines (chat send).
        var richRoot = event.target && event.target.closest
            ? event.target.closest("[data-neony-rich-text]")
            : null;
        if (richRoot) {
            var richCaretEvents = {
                input: true,
                click: true,
                keydown: true,
                keyup: true,
                compositionstart: true,
                compositionupdate: true,
                compositionend: true,
                focus: true,
                blur: true,
            };
            if (richCaretEvents[event.type] && window.neony && window.neony.richText) {
                var richSelection = window.neony.richText.selectionFromEvent(event);
                if (richSelection) {
                    payload.caret_position = richSelection.start;
                    payload.selection_end = richSelection.end;
                }
                var richImage = window.neony.richText.imageFromEvent(event);
                if (richImage) {
                    payload.image_src = richImage.src;
                    payload.image_alt = richImage.alt;
                    payload.image_index = richImage.index;
                }
            }
            if (event.type === "keydown" && event.key === "Enter" && !event.isComposing) {
                event.preventDefault();
            }
        }

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

        // IME composition (compositionstart / compositionupdate /
        // compositionend).  ``data`` is the new text on update and the
        // committed text on end; ``isComposing`` also rides on input
        // events so Python can ignore intermediate composition edits.
        if (event.type === "compositionstart" || event.type === "compositionupdate" || event.type === "compositionend") {
            payload.composition_data = event.data || "";
        }
        // Only send truthy isComposing: KeyboardEvent.isComposing exists
        // (false) in every browser, and a constant false would bloat every
        // keydown payload while carrying no information.
        if (event.isComposing) {
            payload.is_composing = true;
        }

        // Scroll position (scroll event only).  Read from the ACTUAL
        // scroller (event.target) rather than the keyed ancestor `el` —
        // the scroller may be an unkeyed wrapper inside a keyed element.
        // A document-level scroll's target is `document` (no scrollTop of
        // its own; the viewport is the documentElement).
        if (event.type === "scroll") {
            var scroller = event.target === document ? document.documentElement : event.target;
            payload.scroll_top = (scroller && scroller.scrollTop) || 0;
            payload.scroll_left = (scroller && scroller.scrollLeft) || 0;
            payload.scroll_height = (scroller && scroller.scrollHeight) || 0;
            payload.client_height = (scroller && scroller.clientHeight) || 0;
            payload.scroll_width = (scroller && scroller.scrollWidth) || 0;
            payload.client_width = (scroller && scroller.clientWidth) || 0;
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
            // File contents are read asynchronously and delivered as a
            // synthetic ``neony.paste_files`` command (see
            // readClipboardFiles); the synchronous payload only carries
            // metadata so handlers know a file paste happened.
            var pasteFileList = event.clipboardData.files;
            if (pasteFileList && pasteFileList.length > 0) {
                var pasteFiles = [];
                for (var pf = 0; pf < pasteFileList.length; pf++) {
                    pasteFiles.push({
                        name: pasteFileList[pf].name,
                        size: pasteFileList[pf].size,
                        type: pasteFileList[pf].type,
                    });
                }
                payload.paste_files = pasteFiles;
                readClipboardFiles(elKey, pasteFileList);
            }
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

        // In-app drag payload: forwarded on dragstart (from the element's
        // data-neony-drag) and read back on drop (getData works during
        // drop, unlike dragover) so the drop handler can identify what
        // was dragged.
        if (event.type === "dragstart") {
            var dp0 = el.getAttribute("data-neony-drag");
            if (dp0 !== null) payload.drag_payload = dp0;
        } else if (event.type === "drop" && event.dataTransfer) {
            var dp1 = event.dataTransfer.getData("application/x-neony");
            if (dp1) payload.drag_payload = dp1;
        }

        window.lumiview.invoke("neony.event", payload).catch(function () {
            // Fire-and-forget — ignore delivery failures
        });
    }

    for (var i = 0; i < DELEGATED_EVENTS.length; i++) {
        document.addEventListener(DELEGATED_EVENTS[i], eventHandler, true);
    }

    // Pointer-driven in-app drags: mousedown arms the drag; the
    // synthetic lifecycle is owned by the pointer handlers above.  The
    // delegated dragstart listener stops the browser from starting its
    // own (misbehaving) HTML5 drag on data-neony-drag elements.
    document.addEventListener("dragstart", dndOnDragStart, true);
    document.addEventListener("mousedown", dndOnMouseDown, true);

    // Synthetic `outsideclick`: every element marked with
    // data-neony-outside="true" (an open overlay wrapper — trigger +
    // panel) receives one event per click that lands OUTSIDE its
    // subtree, so overlays can close on click-away.  Capture phase is
    // deliberate: a blank-area target (or a native/third-party listener)
    // may stop propagation before document bubble phase, which otherwise
    // leaves an open popup stranded.
    function dispatchOutsideClick(event) {
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
    }

    document.addEventListener("click", dispatchOutsideClick, true);

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
