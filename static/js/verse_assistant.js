/**
 * VERSE — Full UI Automation Voice Assistant for StudyVerse
 * ==========================================================
 * Controls the entire app by voice. On every page, Verse can:
 * - Click buttons  - Type into inputs  - Fill forms  - Open modals
 * - Navigate pages - Read data aloud   - Execute real backend actions
 *
 * DOM Actions are executed client-side after Gemini returns intents.
 */

(function () {
    'use strict';

    /* ─── STATE ──────────────────────────────────────────── */
    let recognition = null;
    let isListening = false;
    let isSpeaking = false;
    let bubbleHideTimer = null;

    /* ─── DOM REFS ───────────────────────────────────────── */
    let micBtn, micLabel, bubble, bubbleHeader,
        bubbleText, bubbleUser, welcomeOverlay;

    /* ─── PAGE ELEMENT MAP ───────────────────────────────────
     * Maps every Verse action to exact DOM element IDs/selectors
     * so the DOM engine knows exactly what to interact with.
     * ──────────────────────────────────────────────────────── */
    const PAGE_MAP = {
        // ── BATTLE (/battle) ──────────────────────────────
        '/battle': {
            create_room: { op: 'click', id: 'btn-create' },
            join_room: { op: 'click', id: 'btn-join' },
            type_room_code: { op: 'type', id: 'join-code' },
            submit_code: { op: 'click', id: 'btn-join' },
            submit_solution: { op: 'click', id: 'btn-submit' },
            vote_yes: { op: 'click', id: 'btn-vote-yes' },
            vote_no: { op: 'click', id: 'btn-vote-no' },
            accept_request: { op: 'click', id: 'btn-accept' },
            reject_request: { op: 'click', id: 'btn-reject' },
        },

        // ── POMODORO (/pomodoro) ──────────────────────────
        '/pomodoro': {
            start_timer: { op: 'click', id: 'start-btn' },
            pause_timer: { op: 'click', id: 'start-btn' },
            reset_timer: { op: 'click', id: 'reset-btn' },
            focus_mode: { op: 'click', id: 'focusMode' },
            short_break: { op: 'click', id: 'shortBreakMode' },
            stopwatch: { op: 'click', id: 'stopwatchMode' },
            go_live: { op: 'click', id: 'goLiveBtn' },
            add_goal: { op: 'click', id: 'add-goal-btn' },
            type_goal: { op: 'type', id: 'new-goal-input' },
            brain_dump: { op: 'focus', id: 'brain-dump-area' },
        },

        // ── QUIZ (/quiz) ──────────────────────────────────
        // Options are .quiz-option divs injected by JS — use clickNth with correct selector
        // Settings are .btn-select buttons — use clickByText
        '/quiz': {
            start_quiz: { op: 'click', id: 'start-quiz-btn' },
            next_question: { op: 'click', id: 'next-question-btn' },
            answer_a: { op: 'clickNth', selector: '#options-container .quiz-option', index: 0 },
            answer_b: { op: 'clickNth', selector: '#options-container .quiz-option', index: 1 },
            answer_c: { op: 'clickNth', selector: '#options-container .quiz-option', index: 2 },
            answer_d: { op: 'clickNth', selector: '#options-container .quiz-option', index: 3 },
            count_5: { op: 'clickByText', selector: '.btn-select', text: '5' },
            count_10: { op: 'clickByText', selector: '.btn-select', text: '10' },
            count_15: { op: 'clickByText', selector: '.btn-select', text: '15' },
            count_20: { op: 'clickByText', selector: '.btn-select', text: '20' },
            difficulty_easy: { op: 'clickByText', selector: '.btn-select', text: 'Easy' },
            difficulty_medium: { op: 'clickByText', selector: '.btn-select', text: 'Medium' },
            difficulty_hard: { op: 'clickByText', selector: '.btn-select', text: 'Hard' },
        },

        // ── TODOS (/todos) ────────────────────────────────
        '/todos': {
            open_add_modal: { op: 'click', id: 'addTaskModal', fallback: '[onclick*="addTaskModal"]' },
            add_task: { op: 'click', id: 'btnDone' },
            type_task_title: { op: 'type', id: 'taskTitle' },
            set_priority_high: { op: 'selectOption', id: 'taskPriority', value: 'high' },
            set_priority_medium: { op: 'selectOption', id: 'taskPriority', value: 'medium' },
            set_priority_low: { op: 'selectOption', id: 'taskPriority', value: 'low' },
        },

        // ── CHAT (/chat) ──────────────────────────────────
        '/chat': {
            type_message: { op: 'type', id: 'chatInput' },
            send_message: { op: 'click', id: 'sendButton' },
            submit_chat: { op: 'submit', id: 'chatForm' },
        },

        // ── FRIENDS (/friends) ────────────────────────────
        '/friends': {
            search_friend: { op: 'type', id: 'user-search' },
        },

        // ── CALENDAR (/calendar) ──────────────────────────
        '/calendar': {
            add_event: { op: 'click', selector: '[onclick*="quickAddModal"], .add-event-btn, button[data-modal]' },
            type_event_title: { op: 'type', id: 'quick-add-title' },
        },

        // ── SHOP (/shop) ──────────────────────────────────
        '/shop': {
            search_shop: { op: 'type', id: 'shop-search' },
        },

        // ── SYLLABUS (/syllabus) ──────────────────────────
        '/syllabus': {
            upload_pdf: { op: 'click', id: 'uploadPdf' },
        },

        // ── GLOBAL (any page, layout.html elements) ───────
        'global': {
            toggle_theme: { op: 'click', id: 'theme-toggle' },
            toggle_sidebar: { op: 'click', id: 'sidebar-toggle' },
            zen_mode: { op: 'click', id: 'zen-mode-nav-btn' },
            open_feedback: { op: 'click', id: 'feedbackBtn' },
            type_distraction: { op: 'type', id: 'distraction-input' },
        }
    };

    /* ─── DOM AUTOMATION ENGINE ──────────────────────────────
     * Smart element finder and manipulator.
     * ──────────────────────────────────────────────────────── */

    /**
     * Find an element using multiple strategies in priority order.
     * @param {string} id - element ID to try first
     * @param {string} selector - CSS selector to try second
     * @param {string} text - text content to search for
     * @param {string} placeholder - placeholder text
     * @returns {Element|null}
     */
    function findElement({ id, selector, text, placeholder, ariaLabel } = {}) {
        // 1. By ID (fastest, most reliable)
        if (id) {
            const el = document.getElementById(id);
            if (el) return el;
        }

        // 2. By CSS selector
        if (selector) {
            const els = document.querySelectorAll(selector);
            if (els.length > 0) return els[0];
        }

        // 3. By button/link text content (case insensitive)
        if (text) {
            const candidates = document.querySelectorAll('button, a, [role="button"], input[type="submit"], input[type="button"]');
            const lowerText = text.toLowerCase();
            for (const el of candidates) {
                if (el.textContent.trim().toLowerCase().includes(lowerText)) return el;
            }
        }

        // 4. By placeholder
        if (placeholder) {
            const el = document.querySelector(`[placeholder*="${placeholder}"]`);
            if (el) return el;
        }

        // 5. By aria-label
        if (ariaLabel) {
            const el = document.querySelector(`[aria-label*="${ariaLabel}"]`);
            if (el) return el;
        }

        return null;
    }

    /**
     * Execute a single DOM action descriptor.
     * @param {{op, id, selector, value, index, text}} action
     */
    async function executeDomAction(action) {
        const { op, id, selector, value, index, text, placeholder, fn, args } = action;

        switch (op) {
            case 'click': {
                const el = findElement({ id, selector, text, placeholder });
                if (el) {
                    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    await wait(200);
                    el.click();
                    return true;
                }
                console.warn('[Verse DOM] Could not find element to click:', action);
                return false;
            }

            case 'clickNth': {
                const els = document.querySelectorAll(selector);
                const el = els[index ?? 0];
                if (el) {
                    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    await wait(150);
                    el.click();
                    return true;
                }
                console.warn('[Verse DOM] clickNth: no element at index', index, 'for', selector);
                return false;
            }

            case 'clickByText': {
                // Click a button/element whose text matches exactly (case-insensitive)
                const candidates = document.querySelectorAll(selector || 'button, a, [role="button"]');
                const target = text?.trim().toLowerCase();
                for (const el of candidates) {
                    if (el.textContent.trim().toLowerCase() === target) {
                        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        await wait(150);
                        el.click();
                        return true;
                    }
                }
                console.warn('[Verse DOM] clickByText: no element matching text', text);
                return false;
            }

            case 'type': {
                const el = findElement({ id, selector, placeholder });
                if (el) {
                    el.focus();
                    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    // Clear and type
                    el.value = '';
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    await wait(100);
                    // Type character by character for natural feel
                    for (const char of value || '') {
                        el.value += char;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        await wait(18);
                    }
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    return true;
                }
                return false;
            }

            case 'focus': {
                const el = findElement({ id, selector });
                if (el) { el.focus(); el.scrollIntoView({ behavior: 'smooth' }); return true; }
                return false;
            }

            case 'submit': {
                const el = findElement({ id, selector });
                if (el) {
                    if (el.tagName === 'FORM') { el.submit(); }
                    else { el.dispatchEvent(new Event('submit', { bubbles: true })); }
                    return true;
                }
                return false;
            }

            case 'selectOption': {
                const el = findElement({ id, selector });
                if (el && el.tagName === 'SELECT') {
                    el.value = value;
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    return true;
                }
                // Also try radio buttons / checkbox buttons
                const radio = document.querySelector(`[value="${value}"]`);
                if (radio) { radio.click(); return true; }
                return false;
            }

            case 'navigate': {
                setTimeout(() => { window.location.href = value; }, 400);
                return true;
            }

            case 'callFunction': {
                // Call a global helper function, e.g. for complex UI like Habit Matrix.
                const fnName = fn || value;
                if (!fnName) return false;

                try {
                    // Support nested paths like "App.helpers.doThing"
                    const parts = fnName.split('.');
                    let ctx = window;
                    for (const p of parts) {
                        if (!ctx[p]) { ctx = null; break; }
                        ctx = ctx[p];
                    }
                    if (typeof ctx === 'function') {
                        ctx(args);
                        return true;
                    }
                } catch (e) {
                    console.warn('[Verse DOM] callFunction failed for', fnName, e);
                }
                return false;
            }

            default:
                return false;
        }
    }

    /**
     * Execute a sequence of DOM actions (with navigation awareness).
     * @param {Array} actions - list of action descriptors from Gemini
     */
    async function executeDomActions(actions) {
        if (!actions || !actions.length) return;

        // Check if we need to navigate first
        const navAction = actions.find(a => a.op === 'navigate');
        const currentPath = window.location.pathname;

        if (navAction && navAction.value !== currentPath) {
            // Store pending actions in sessionStorage, navigate, re-execute on arrival
            sessionStorage.setItem('verse_pending_actions', JSON.stringify(
                actions.filter(a => a.op !== 'navigate')
            ));
            sessionStorage.setItem('verse_pending_reply', '');
            await wait(1200); // Let speech start
            window.location.href = navAction.value;
            return;
        }

        // Execute all non-navigate actions sequentially
        for (const action of actions.filter(a => a.op !== 'navigate')) {
            await executeDomAction(action);
            await wait(action.delay || 300);
        }
    }

    /**
     * On page load — check if there are pending actions to execute.
     */
    function checkPendingActions() {
        const pending = sessionStorage.getItem('verse_pending_actions');
        if (!pending) return;
        sessionStorage.removeItem('verse_pending_actions');

        try {
            const actions = JSON.parse(pending);
            if (actions && actions.length) {
                // Small delay to let page JS initialize
                setTimeout(() => executeDomActions(actions), 1200);
            }
        } catch (e) { /* ignore */ }
    }


    /* ─── SPEECH SYNTHESIS ────────────────────────────────── */
    function speak(text, onEnd) {
        if (!window.speechSynthesis) return onEnd?.();
        window.speechSynthesis.cancel();

        const utter = new SpeechSynthesisUtterance(text);
        utter.lang = 'en-US';
        utter.rate = 1.05;
        utter.pitch = 1.0;
        utter.volume = 1.0;

        // Pick a good voice
        const voices = window.speechSynthesis.getVoices();
        const preferred = voices.find(v =>
            /google us english|samantha|karen|zira|microsoft zira/i.test(v.name)
        ) || voices.find(v => v.lang === 'en-US') || voices[0];
        if (preferred) utter.voice = preferred;

        utter.onend = () => { isSpeaking = false; onEnd?.(); };
        utter.onerror = () => { isSpeaking = false; onEnd?.(); };

        isSpeaking = true;
        window.speechSynthesis.speak(utter);
    }

    function stopSpeaking() {
        window.speechSynthesis?.cancel();
        isSpeaking = false;
    }


    /* ─── SPEECH RECOGNITION ──────────────────────────────── */
    function initRecognition() {
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR) return null;

        const r = new SR();
        r.lang = 'en-US';
        r.continuous = false;
        r.interimResults = true;
        r.maxAlternatives = 1;
        r._lastFinal = '';

        r.onstart = () => {
            isListening = true;
            micBtn.classList.add('verse-listening');
            micBtn.classList.remove('verse-thinking');
            micBtn.innerHTML = '<i class="fa-solid fa-stop"></i>';
            showBubble('listening');
        };

        r.onresult = (event) => {
            const interim = Array.from(event.results).map(r => r[0].transcript).join('');
            updateBubbleTranscript(interim);
            for (const res of event.results) {
                if (res.isFinal) r._lastFinal = res[0].transcript;
            }
        };

        r.onend = () => {
            if (!isListening) return;
            isListening = false;
            const final = r._lastFinal?.trim();
            if (final && final.length > 1) {
                processUserSpeech(final);
            } else {
                setBubbleIdle();
                resetMicBtn();
            }
        };

        r.onerror = (e) => {
            isListening = false;
            resetMicBtn();
            if (e.error !== 'aborted' && e.error !== 'no-speech') {
                showToast('⚠️ ' + e.error);
            }
            setBubbleIdle();
        };

        return r;
    }

    function startListening() {
        if (isSpeaking) stopSpeaking();
        if (!recognition) {
            showToast('🚫 Voice not supported. Use Chrome or Edge.');
            return;
        }
        recognition._lastFinal = '';
        try { recognition.start(); }
        catch (e) { recognition.stop(); setTimeout(startListening, 300); }
    }

    function stopListening() {
        if (!isListening) return;
        isListening = false;
        recognition?.stop();
        resetMicBtn();
    }


    /* ─── CORE: SPEECH → AI → ACTION ────────────────────────
     * Full pipeline from spoken words to app interaction.
     * ──────────────────────────────────────────────────────── */
    async function processUserSpeech(transcript) {
        micBtn.classList.remove('verse-listening');
        micBtn.classList.add('verse-thinking');
        micBtn.innerHTML = '<i class="fa-solid fa-spinner"></i>';
        showBubble('thinking', transcript);

        try {
            const resp = await fetch('/api/voice-assistant', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({
                    text: transcript,
                    page: window.location.pathname
                })
            });

            // Always read the raw text so we can debug non-JSON responses (e.g. 500 HTML, login redirects)
            const rawText = await resp.text();
            let data = null;

            try {
                data = rawText ? JSON.parse(rawText) : null;
            } catch (parseErr) {
                console.error('[Verse] Failed to parse JSON from /api/voice-assistant:', parseErr, rawText);
            }

            // Handle HTTP errors or non-JSON responses gracefully instead of throwing,
            // so the user gets a helpful explanation instead of a generic "snag" message.
            if (!resp.ok || !data) {
                let friendly = 'Something went wrong talking to the AI on the server.';

                // If the backend sent a JSON error-like object, surface its message
                if (data && typeof data.reply === 'string') {
                    friendly = data.reply;
                } else if (resp.status === 401 || resp.status === 302) {
                    friendly = 'Your session might have expired. Please refresh the page and sign in again.';
                } else if (resp.status >= 500) {
                    friendly = 'The server hit an error while processing that. Check your Render logs.';
                }

                console.error('[Verse] /api/voice-assistant HTTP error:', resp.status, rawText);
                showBubble('reply', transcript, friendly);
                speak(friendly);
                return;
            }

            // At this point we have a valid JSON payload from the backend
            // Show reply in bubble
            showBubble('reply', transcript, data.reply);

            // Speak reply
            speak(data.reply, () => scheduleBubbleHide(7000));

            // Execute action — dom_actions are handled INSIDE executeBackendAction.
            // DO NOT execute dom_actions a second time here — it causes double-clicks (toggle flicker).
            if (data.action && data.action !== 'none' && data.action !== 'conversation') {
                await executeBackendAction(data.action, data.params || {}, data.dom_actions || []);
            }

        } catch (err) {
            console.error('[Verse] Network or unexpected error:', err?.message || err);
            const errMsg = 'Sorry, I hit a snag. Please check your internet connection and try again.';
            showBubble('reply', transcript, errMsg);
            speak(errMsg);
        } finally {
            resetMicBtn();
        }
    }


    /* ─── BACKEND ACTION EXECUTOR ────────────────────────────
     * Calls /api/verse/action, then triggers DOM interactions.
     * ──────────────────────────────────────────────────────── */
    async function executeBackendAction(action, params, extraDomActions) {
        await wait(300);

        // ── Pure navigation (no backend call needed) ──────
        const navMap = {
            navigate_dashboard: '/dashboard',
            navigate_pomodoro: '/pomodoro',
            navigate_todos: '/todos',
            navigate_quiz: '/quiz',
            navigate_syllabus: '/syllabus',
            navigate_leaderboard: '/leaderboard',
            navigate_friends: '/friends',
            navigate_shop: '/shop',
            navigate_progress: '/progress',
            navigate_chat: '/chat',
            navigate_battle: '/battle',
            navigate_profile: '/profile',
            navigate_settings: '/settings',
            navigate_calendar: '/calendar',
            navigate_topic_resolver: '/topic-resolver',
            navigate_photo_solver: '/photo-solver',
            navigate_support: '/support',
            navigate_live: '/live',
        };
        if (navMap[action]) {
            const target = navMap[action];
            if (window.location.pathname === target) {
                // Already here — execute any DOM actions instead
                if (extraDomActions.length) await executeDomActions(extraDomActions);
            } else {
                if (extraDomActions.length) {
                    sessionStorage.setItem('verse_pending_actions', JSON.stringify(extraDomActions));
                }
                setTimeout(() => { window.location.href = target; }, 1500);
            }
            return;
        }

        // ── wb_draw_ai — Voice-controlled whiteboard drawing ─
        if (action === 'wb_draw_ai') {
            const shape = (params.shape || 'line').toLowerCase();
            const color = (params.color || '').toLowerCase();
            const drawCmd = color ? `${color} ${shape}` : shape;

            const doDrawing = () => {
                // Switch to whiteboard tab
                if (typeof switchTab === 'function') switchTab('whiteboard');
                // Wait a bit for canvas to resize, then draw
                setTimeout(() => {
                    if (typeof window.verseDrawOnWhiteboard === 'function') {
                        window.verseDrawOnWhiteboard(drawCmd);
                    } else {
                        showToast('✏️ Whiteboard not loaded yet — try again!');
                    }
                }, 400);
            };

            if (window.location.pathname === '/group') {
                doDrawing();
            } else {
                // Navigate to /group, then draw after load
                sessionStorage.setItem('verse_wb_draw_pending', drawCmd);
                setTimeout(() => { window.location.href = '/group'; }, 1200);
            }
            return;
        }

        // ── Real server-side actions ──────────────────────
        const serverActions = [
            'add_todo', 'read_pending_todos', 'send_friend_request',
            'start_quiz', 'start_battle',
            'get_stats', 'get_streak', 'get_xp',
            'get_leaderboard', 'get_friends',
            'shop_item', 'navigate_user_profile',
            'dom_interact'
        ];
        if (!serverActions.includes(action)) return;

        // dom_interact = only DOM no server call
        if (action === 'dom_interact') {
            if (extraDomActions.length) await executeDomActions(extraDomActions);
            return;
        }

        try {
            const resp = await fetch('/api/verse/action', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action, params })
            });
            const result = await resp.json();

            if (!result.success) {
                const errMsg = result.message || "I couldn't do that.";
                showBubble('reply', null, errMsg);
                stopSpeaking();
                setTimeout(() => speak(errMsg), 200);
                return;
            }

            if (action === 'add_todo') {
                showToast('✅ ' + result.message);
                // If on todos page, trigger modal auto-fill
                if (window.location.pathname === '/todos') {
                    await executeDomActions([
                        { op: 'click', selector: '[onclick*="addTaskModal"], .btn-add-task, button:has(.fa-plus)', text: 'Add Task', delay: 300 },
                        { op: 'type', id: 'taskTitle', value: params.title, delay: 400 },
                        { op: 'selectOption', id: 'taskPriority', value: params.priority || 'medium', delay: 200 },
                    ]);
                }

            } else if (action === 'read_pending_todos') {
                const todos = result.todos || [];
                if (!todos.length) {
                    const msg = "You have no pending tasks — all clear!";
                    showBubble('reply', null, msg);
                    stopSpeaking(); speak(msg);
                } else {
                    const listHTML = todos.map(t =>
                        `<div style="padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.05)">
                            <span style="font-size:0.8rem">${t.priority === 'high' ? '🔴' :
                            t.priority === 'medium' ? '🟡' : '🟢'
                        } ${t.title}</span>
                         </div>`
                    ).join('');
                    if (bubbleText) bubbleText.innerHTML = listHTML;
                    if (bubbleHeader) bubbleHeader.innerHTML = '📋 Pending Tasks';
                    stopSpeaking();
                    setTimeout(() => speak(result.message), 200);
                }

            } else if (action === 'send_friend_request') {
                showToast('👋 ' + result.message);
                showBubble('reply', null, result.message);
                stopSpeaking();
                setTimeout(() => speak(result.message), 200);

            } else if (action === 'start_quiz') {
                sessionStorage.setItem('verse_quiz_autostart', result.difficulty || 'medium');
                const path = result.navigate || '/quiz';
                if (window.location.pathname === path) {
                    await executeDomActions([{ op: 'click', id: 'start-quiz-btn', delay: 400 }]);
                } else {
                    sessionStorage.setItem('verse_pending_actions', JSON.stringify([
                        { op: 'click', id: 'start-quiz-btn', delay: 800 }
                    ]));
                    setTimeout(() => { window.location.href = path; }, 1500);
                }

            } else if (action === 'start_battle') {
                const path = result.navigate || '/battle';
                if (window.location.pathname === path) {
                    await executeDomActions([{ op: 'click', id: 'btn-create', delay: 400 }]);
                } else {
                    sessionStorage.setItem('verse_pending_actions', JSON.stringify([
                        { op: 'click', id: 'btn-create', delay: 800 }
                    ]));
                    setTimeout(() => { window.location.href = path; }, 1500);
                }

            } else if (action === 'get_leaderboard' || action === 'get_friends' ||
                action === 'get_stats' || action === 'get_streak' || action === 'get_xp') {
                // These return a spoken message — just speak it
                const msg = result.message || 'Here are your stats!';
                showBubble('reply', null, msg);
                stopSpeaking();
                setTimeout(() => speak(msg), 200);

            } else if (action === 'shop_item') {
                const msg = result.message || data.reply;
                showToast((result.success ? '\uD83D\uDECD\uFE0F ' : '\u274C ') + msg);
                showBubble('reply', null, msg);
                stopSpeaking();
                setTimeout(() => speak(msg), 200);
                // ALWAYS reload after shop action so theme CSS (body class) gets re-applied by Flask
                if (result.success) {
                    setTimeout(() => { window.location.reload(); }, 2500);
                }

            } else if (action === 'navigate_user_profile') {
                const msg = result.message || data.reply;
                showBubble('reply', null, msg);
                stopSpeaking();
                setTimeout(() => speak(msg), 200);
                if (result.navigate) {
                    setTimeout(() => { window.location.href = result.navigate; }, 1500);
                }
            }

        } catch (err) {
            console.error('[Verse] Backend action error:', err);
        }
    }


    /* ─── WELCOME ANIMATION ───────────────────────────────── */
    function showWelcome(welcomeText) {
        if (!welcomeOverlay) return;
        welcomeOverlay.classList.add('verse-show');
        const sub = welcomeOverlay.querySelector('.verse-welcome-subtitle');
        if (sub) sub.textContent = welcomeText;
        setTimeout(() => speak(welcomeText), 800);
        const dismiss = () => dismissWelcome();
        welcomeOverlay.addEventListener('click', dismiss, { once: true });
        setTimeout(dismiss, 9000);
    }

    function dismissWelcome() {
        if (!welcomeOverlay) return;
        welcomeOverlay.classList.remove('verse-show');
        welcomeOverlay.classList.add('verse-hide');
        setTimeout(() => welcomeOverlay.remove(), 700);
    }


    /* ─── BUBBLE UI ───────────────────────────────────────── */
    function showBubble(state, userText, verseText) {
        clearTimeout(bubbleHideTimer);
        if (!bubble) return;
        bubble.classList.add('verse-bubble-show');
        bubbleUser.style.display = 'none';

        if (state === 'listening') {
            bubbleHeader.innerHTML = '<span class="verse-bubble-dot"></span> Listening...';
            bubbleText.innerHTML = `<div class="verse-mini-wave">
                <div class="verse-mini-bar"></div><div class="verse-mini-bar"></div>
                <div class="verse-mini-bar"></div><div class="verse-mini-bar"></div>
                <div class="verse-mini-bar"></div></div>`;
        } else if (state === 'thinking') {
            bubbleHeader.innerHTML = '<span class="verse-bubble-dot"></span> Verse is thinking...';
            bubbleText.textContent = userText || '';
        } else if (state === 'reply') {
            bubbleHeader.innerHTML = '🎙️ Verse';
            bubbleText.textContent = verseText || '';
            if (userText) {
                bubbleUser.style.display = 'block';
                bubbleUser.textContent = 'You: ' + userText;
            }
        }
    }

    function updateBubbleTranscript(text) {
        if (!bubble) return;
        bubbleHeader.innerHTML = '<span class="verse-bubble-dot"></span> Listening...';
        bubbleText.textContent = text;
    }

    function setBubbleIdle() { scheduleBubbleHide(2000); }

    function scheduleBubbleHide(ms) {
        clearTimeout(bubbleHideTimer);
        bubbleHideTimer = setTimeout(() => {
            bubble?.classList.remove('verse-bubble-show');
        }, ms);
    }


    /* ─── MIC BUTTON STATE ───────────────────────────────── */
    function resetMicBtn() {
        if (!micBtn) return;
        micBtn.classList.remove('verse-listening', 'verse-thinking');
        micBtn.innerHTML = '<i class="fa-solid fa-microphone"></i>';
        isListening = false;
    }


    /* ─── TOAST ───────────────────────────────────────────── */
    function showToast(msg) {
        const t = document.createElement('div');
        t.className = 'verse-toast';
        t.textContent = msg;
        document.body.appendChild(t);
        requestAnimationFrame(() => {
            t.classList.add('verse-toast-show');
            setTimeout(() => {
                t.classList.remove('verse-toast-show');
                setTimeout(() => t.remove(), 400);
            }, 3500);
        });
    }


    /* ─── UTILS ───────────────────────────────────────────── */
    function wait(ms) { return new Promise(r => setTimeout(r, ms)); }


    /* ─── INIT ────────────────────────────────────────────── */
    function init() {
        micBtn = document.getElementById('verse-mic-btn');
        micLabel = document.getElementById('verse-mic-label');
        bubble = document.getElementById('verse-bubble');
        bubbleHeader = document.getElementById('verse-bubble-header');
        bubbleText = document.getElementById('verse-bubble-text');
        bubbleUser = document.getElementById('verse-bubble-user');
        welcomeOverlay = document.getElementById('verse-welcome-overlay');

        if (!micBtn) return;

        // Pre-load voices
        window.speechSynthesis?.getVoices();
        if (window.speechSynthesis) {
            window.speechSynthesis.onvoiceschanged = () => { };
        }

        recognition = initRecognition();

        // Mic button
        micBtn.addEventListener('click', () => {
            isListening ? stopListening() : startListening();
        });

        // Alt+V shortcut
        document.addEventListener('keydown', (e) => {
            if (e.altKey && e.key.toLowerCase() === 'v') {
                e.preventDefault();
                isListening ? stopListening() : startListening();
            }
        });

        // Handle pending actions from previous page navigation
        checkPendingActions();

        // Handle pending whiteboard draw (after navigating to /group)
        const wbPendingCmd = sessionStorage.getItem('verse_wb_draw_pending');
        if (wbPendingCmd && window.location.pathname === '/group') {
            sessionStorage.removeItem('verse_wb_draw_pending');
            setTimeout(() => {
                if (typeof switchTab === 'function') switchTab('whiteboard');
                setTimeout(() => {
                    if (typeof window.verseDrawOnWhiteboard === 'function') {
                        window.verseDrawOnWhiteboard(wbPendingCmd);
                    }
                }, 600);
            }, 1500);
        }
    }


    /* ─── PUBLIC API ──────────────────────────────────────── */
    window.Verse = {
        showWelcome,
        dismissWelcome,
        speak,
        showToast,
        executeDomActions,  // exposed for page-specific scripts
        executeDomAction,
    };


    /* ─── BOOT ────────────────────────────────────────────── */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
