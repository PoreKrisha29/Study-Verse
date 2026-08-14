/**
 * calls.js — StudyVerse Call System
 * Handles Group Calls (Jitsi tab) and 1-to-1 DM Calls (popup → new tab)
 * Requires: socket.io, Jitsi External API (for group call tab only)
 */

(function () {
    'use strict';

    if (window.svCallsReady) return;

    // ── Ring Sound via Web Audio API ─────────────────────────────
    let ringInterval = null;
    let callTimeoutTimer = null;

    function playRing() {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            function beep() {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.frequency.value = 520;
                osc.type = 'sine';
                gain.gain.setValueAtTime(0.3, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
                osc.start(ctx.currentTime);
                osc.stop(ctx.currentTime + 0.6);
            }
            beep();
            ringInterval = setInterval(beep, 1800);
        } catch (e) { /* Audio not supported, silent */ }
    }

    function stopRing() {
        if (ringInterval) { clearInterval(ringInterval); ringInterval = null; }
    }

    // ── Toast Notification ────────────────────────────────────────
    function showToast(message, type) {
        // type: 'success' | 'error' | 'info'
        const colors = {
            success: { bg: 'rgba(74,222,128,0.12)', border: 'rgba(74,222,128,0.3)', text: '#4ade80' },
            error:   { bg: 'rgba(239,68,68,0.12)',  border: 'rgba(239,68,68,0.3)',  text: '#f87171' },
            info:    { bg: 'rgba(99,102,241,0.12)', border: 'rgba(99,102,241,0.3)', text: '#818cf8' },
        };
        const c = colors[type] || colors.info;
        const toast = document.createElement('div');
        toast.style.cssText = `
            position:fixed; bottom:90px; left:50%; transform:translateX(-50%) translateY(20px);
            background:${c.bg}; border:1px solid ${c.border}; color:${c.text};
            padding:12px 22px; border-radius:10px; font-weight:600; font-size:0.9rem;
            z-index:99999; backdrop-filter:blur(10px); opacity:0;
            transition:opacity 0.3s, transform 0.3s; pointer-events:none;
            box-shadow: 0 8px 30px rgba(0,0,0,0.4);
        `;
        toast.textContent = message;
        document.body.appendChild(toast);
        requestAnimationFrame(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateX(-50%) translateY(0)';
        });
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(-50%) translateY(20px)';
            setTimeout(() => toast.remove(), 350);
        }, 3500);
    }

    // ── DM Incoming Call Modal ────────────────────────────────────
    let pendingCallerId = null;

    function showIncomingCallModal(callerId, callerName, callerAvatar) {
        pendingCallerId = callerId;
        stopRing();
        playRing();

        // Build modal if not exists
        let modal = document.getElementById('sv-incoming-call-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'sv-incoming-call-modal';
            modal.innerHTML = `
                <div id="sv-call-modal-inner" style="
                    position:fixed; inset:0; z-index:99999;
                    display:flex; align-items:center; justify-content:center;
                    background:rgba(0,0,0,0.7); backdrop-filter:blur(8px);
                ">
                    <div style="
                        background:linear-gradient(135deg,rgba(20,20,35,0.98),rgba(30,30,50,0.98));
                        border:1px solid rgba(99,102,241,0.4); border-radius:20px;
                        padding:36px 40px; max-width:340px; width:90%; text-align:center;
                        box-shadow:0 30px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(99,102,241,0.1);
                        animation: callPulse 2s ease infinite;
                    ">
                        <div style="position:relative; display:inline-block; margin-bottom:20px;">
                            <img id="sv-caller-avatar" src="" alt=""
                                style="width:72px;height:72px;border-radius:50%;object-fit:cover;
                                       border:3px solid rgba(99,102,241,0.5);">
                            <div style="
                                position:absolute; bottom:0; right:0;
                                width:20px; height:20px; background:#6366f1;
                                border-radius:50%; display:grid; place-items:center;
                                border:2px solid rgba(20,20,35,0.98);
                            "><i class="fa-solid fa-phone" style="font-size:0.55rem;color:white;"></i></div>
                        </div>
                        <div style="font-size:0.78rem;color:rgba(255,255,255,0.45);letter-spacing:1px;
                                    text-transform:uppercase;margin-bottom:6px;">Incoming Call</div>
                        <div id="sv-caller-name" style="font-size:1.3rem;font-weight:700;color:#fff;margin-bottom:4px;"></div>
                        <div style="font-size:0.82rem;color:rgba(255,255,255,0.4);margin-bottom:28px;">
                            is calling you…
                        </div>
                        <div style="display:flex;gap:16px;justify-content:center;">
                            <button id="sv-decline-call" style="
                                width:56px;height:56px;border-radius:50%;border:none;
                                background:rgba(239,68,68,0.9);color:white;font-size:1.2rem;
                                cursor:pointer;display:grid;place-items:center;
                                box-shadow:0 4px 20px rgba(239,68,68,0.4);
                                transition:transform 0.15s, box-shadow 0.15s;
                            " title="Decline">
                                <i class="fa-solid fa-phone-slash"></i>
                            </button>
                            <button id="sv-answer-call" style="
                                width:56px;height:56px;border-radius:50%;border:none;
                                background:rgba(74,222,128,0.9);color:black;font-size:1.2rem;
                                cursor:pointer;display:grid;place-items:center;
                                box-shadow:0 4px 20px rgba(74,222,128,0.4);
                                transition:transform 0.15s, box-shadow 0.15s;
                                animation: answerPulse 1.2s ease infinite;
                            " title="Answer">
                                <i class="fa-solid fa-phone"></i>
                            </button>
                        </div>
                    </div>
                </div>
                <style>
                    @keyframes callPulse {
                        0%,100% { box-shadow:0 30px 80px rgba(0,0,0,0.6),0 0 0 0 rgba(99,102,241,0.3); }
                        50%     { box-shadow:0 30px 80px rgba(0,0,0,0.6),0 0 0 12px rgba(99,102,241,0); }
                    }
                    @keyframes answerPulse {
                        0%,100% { box-shadow:0 4px 20px rgba(74,222,128,0.4),0 0 0 0 rgba(74,222,128,0.3); }
                        50%     { box-shadow:0 4px 20px rgba(74,222,128,0.4),0 0 0 10px rgba(74,222,128,0); }
                    }
                    #sv-answer-call:hover  { transform:scale(1.1); }
                    #sv-decline-call:hover { transform:scale(1.1); }
                </style>
            `;
            document.body.appendChild(modal);

            document.getElementById('sv-answer-call').addEventListener('click', answerCall);
            document.getElementById('sv-decline-call').addEventListener('click', declineCall);
        }

        document.getElementById('sv-caller-avatar').src = callerAvatar || `https://ui-avatars.com/api/?name=${encodeURIComponent(callerName)}&background=random`;
        document.getElementById('sv-caller-name').textContent = callerName;
        modal.style.display = 'block';

        // Auto-timeout: 30 seconds
        if (callTimeoutTimer) clearTimeout(callTimeoutTimer);
        callTimeoutTimer = setTimeout(() => {
            hideIncomingCallModal();
            showToast('Missed call — no answer', 'info');
        }, 30000);
    }

    function hideIncomingCallModal() {
        const modal = document.getElementById('sv-incoming-call-modal');
        if (modal) modal.style.display = 'none';
        stopRing();
        if (callTimeoutTimer) { clearTimeout(callTimeoutTimer); callTimeoutTimer = null; }
        pendingCallerId = null;
    }

    function answerCall() {
        if (!pendingCallerId) return;
        const callerId = pendingCallerId;
        hideIncomingCallModal();

        // Tell caller we accepted
        if (window.svSocket) {
            window.svSocket.emit('dm_call_response', { caller_id: callerId, accepted: true });
        }

        // Open Jitsi in new tab — room unique to this pair (sorted user IDs)
        const myId = window.CURRENT_USER_ID || 0;
        const uid1 = Math.min(parseInt(myId), parseInt(callerId));
        const uid2 = Math.max(parseInt(myId), parseInt(callerId));
        const roomName = `studyverse-dm-${uid1}-${uid2}`;
        const displayName = window.CURRENT_USER_NAME || 'User';
        const jitsiUrl = `/call?room=${roomName}`;
        window.open(jitsiUrl, '_blank');
    }

    function declineCall() {
        if (!pendingCallerId) return;
        const callerId = pendingCallerId;
        hideIncomingCallModal();
        if (window.svSocket) {
            window.svSocket.emit('dm_call_response', { caller_id: callerId, accepted: false });
        }
    }

    // ── DM Call Initiation ────────────────────────────────────────
    window.startDmCall = function(friendId, friendName) {
        if (!window.svSocket) { showToast('Not connected. Please refresh.', 'error'); return; }

        // Show "Calling…" toast
        showToast(`📞 Calling ${friendName}…`, 'info');

        window.svSocket.emit('start_dm_call', { target_user_id: friendId });

        // Open Jitsi in new tab immediately for caller too
        const myId = window.CURRENT_USER_ID || 0;
        const uid1 = Math.min(parseInt(myId), parseInt(friendId));
        const uid2 = Math.max(parseInt(myId), parseInt(friendId));
        const roomName = `studyverse-dm-${uid1}-${uid2}`;
        const displayName = window.CURRENT_USER_NAME || 'User';
        const jitsiUrl = `/call?room=${roomName}`;
        window.open(jitsiUrl, '_blank');

        // Listen for result
        const onResult = function(data) {
            if (String(data.responder_id) === String(friendId)) {
                if (data.accepted) {
                    showToast(`✅ ${data.responder_name} joined the call!`, 'success');
                } else {
                    showToast(`❌ ${data.responder_name} declined the call.`, 'error');
                }
                window.svSocket.off('dm_call_result', onResult);
            }
        };
        window.svSocket.on('dm_call_result', onResult);
        // Auto-remove listener after 60s
        setTimeout(() => window.svSocket.off('dm_call_result', onResult), 60000);
    };

    // ── Group Call — Opens in dedicated /call page ────────────────
    let jitsiApi = null;

    window.startGroupCall = function(groupId, inviteCode, displayName) {
        if (jitsiApi) return; // already in call

        const roomName = `studyverse-grp-${groupId}-${inviteCode}`;

        // Notify other group members via socket
        if (window.svSocket) {
            window.svSocket.emit('start_group_call', { group_id: groupId });
        }

        // Open in our premium /call page (same as DM calls)
        // On hangup, call.html will redirect back to /friends automatically
        window.open(`/call?room=${encodeURIComponent(roomName)}`, '_blank');

        // Mark as "in call" locally for button state
        jitsiApi = true;

        // Update call buttons
        const startBtn = document.getElementById('groupCallStartBtn');
        const endBtn   = document.getElementById('groupCallEndBtn');
        if (startBtn) startBtn.style.display = 'none';
        if (endBtn)   endBtn.style.display   = 'flex';
    };

    window.endGroupCall = function(groupId) {
        jitsiApi = null;
        if (window.svSocket && groupId) {
            window.svSocket.emit('end_group_call', { group_id: groupId });
        }
        // Reset call buttons
        const startBtn = document.getElementById('groupCallStartBtn');
        const endBtn   = document.getElementById('groupCallEndBtn');
        if (startBtn) startBtn.style.display = 'flex';
        if (endBtn)   endBtn.style.display   = 'none';
    };

    // ── Group Call Banner (shown to other members) ────────────────
    function showGroupCallBanner(callerName, callerAvatar, groupId) {
        let banner = document.getElementById('sv-group-call-banner');
        if (!banner) {
            banner = document.createElement('div');
            banner.id = 'sv-group-call-banner';
            banner.style.cssText = `
                position:fixed; bottom:80px; left:50%; transform:translateX(-50%) translateY(30px);
                background:linear-gradient(135deg,rgba(99,102,241,0.95),rgba(139,92,246,0.95));
                border:1px solid rgba(255,255,255,0.15); border-radius:14px;
                padding:14px 20px; display:flex; align-items:center; gap:14px;
                z-index:99998; box-shadow:0 12px 40px rgba(99,102,241,0.4);
                max-width:380px; width:90%; opacity:0;
                transition:opacity 0.35s, transform 0.35s;
                backdrop-filter:blur(12px);
            `;
            document.body.appendChild(banner);
        }

        banner.innerHTML = `
            <img src="${callerAvatar || ''}" alt="" style="width:38px;height:38px;border-radius:50%;object-fit:cover;border:2px solid rgba(255,255,255,0.3);flex-shrink:0;">
            <div style="flex:1;min-width:0;">
                <div style="font-weight:700;color:#fff;font-size:0.88rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                    📞 ${callerName} started a call
                </div>
                <div style="font-size:0.75rem;color:rgba(255,255,255,0.65);">Tap Join to enter the group call</div>
            </div>
            <div style="display:flex;gap:8px;flex-shrink:0;">
                <button onclick="joinGroupCallFromBanner()" style="
                    padding:7px 14px;border-radius:8px;border:none;
                    background:rgba(255,255,255,0.2);color:white;
                    font-weight:700;font-size:0.8rem;cursor:pointer;
                    transition:background 0.15s;
                " onmouseover="this.style.background='rgba(255,255,255,0.3)'"
                   onmouseout="this.style.background='rgba(255,255,255,0.2)'">
                    Join
                </button>
                <button onclick="document.getElementById('sv-group-call-banner').style.opacity='0'" style="
                    width:28px;height:28px;border-radius:50%;border:none;
                    background:rgba(255,255,255,0.15);color:white;
                    cursor:pointer;display:grid;place-items:center;font-size:0.75rem;
                "><i class="fa-solid fa-xmark"></i></button>
            </div>
        `;

        requestAnimationFrame(() => {
            banner.style.opacity = '1';
            banner.style.transform = 'translateX(-50%) translateY(0)';
        });

        // Auto-dismiss after 30s
        setTimeout(() => {
            banner.style.opacity = '0';
            banner.style.transform = 'translateX(-50%) translateY(30px)';
        }, 30000);
    }

    window.joinGroupCallFromBanner = function() {
        if (window.switchTab) window.switchTab('call');
    };

    // ── Socket Listener Setup ─────────────────────────────────────
    // Called after socket is ready (from group_chat.js or layout.html)
    window.initCallSocketListeners = function(socket) {
        window.svSocket = socket;

        // Someone else started a group call
        socket.on('group_call_started', function(data) {
            const myId = String(window.CURRENT_USER_ID || '');
            if (String(data.caller_id) === myId) return; // I started it, don't show banner
            showGroupCallBanner(data.caller_name, data.caller_avatar, data.group_id);
        });

        socket.on('group_call_ended', function() {
            const banner = document.getElementById('sv-group-call-banner');
            if (banner) { banner.style.opacity = '0'; }
        });

        // Incoming DM call
        socket.on('dm_call_incoming', function(data) {
            showIncomingCallModal(data.caller_id, data.caller_name, data.caller_avatar);
        });
    };

    // Auto-join personal room on connect (belt-and-suspenders)
    window.svCallsReady = true;

})();
