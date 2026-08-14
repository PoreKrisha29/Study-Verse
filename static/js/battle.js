/**
 * StudyVerse - Battle Mode (Byte Battle)
 * ========================================
 * 
 * Purpose: Real-time competitive quiz battles between two users
 * 
 * SYSTEM ARCHITECTURE:
 * -------------------
 * - Client-Server Model: Socket.IO for real-time bidirectional communication
 * - Room-Based System: Each battle is isolated in a unique room
 * - State Machine: waiting → setup → battle → judging → result
 * 
 * BATTLE FLOW:
 * -----------
 * 1. **Matchmaking Phase**:
 *    - Host creates room → receives unique room code
 *    - Guest requests to join → host accepts/rejects
 * 
 * 2. **Setup Phase**:
 *    - Both players in room
 *    - Chat enabled for coordination
 *    - Host configures difficulty and language
 * 
 * 3. **Battle Phase**:
 *    - AI generates coding problem
 *    - Timer starts (configurable duration)
 *    - Both players write code simultaneously
 *    - First to submit or timer expires
 * 
 * 4. **Judging Phase**:
 *    - Backend evaluates code correctness
 *    - Calculates scores based on:
 *      * Correctness (pass/fail)
 *      * Time taken (faster = more points)
 *      * Code quality (optional)
 * 
 * 5. **Result Phase**:
 *    - Winner announced
 *    - XP rewards distributed
 *    - Rematch voting system
 * 
 * SOCKET.IO EVENTS:
 * ----------------
 * Emitted (Client → Server):
 * - battle_create: Create new battle room
 * - battle_join_request: Request to join room
 * - battle_join_response: Host accepts/rejects join
 * - battle_confirm_join: Guest confirms entry
 * - battle_chat_send: Send chat message
 * - battle_submit: Submit code solution
 * - battle_rematch_vote: Vote for rematch
 * - battle_heartbeat: Keep connection alive
 * - battle_rejoin_attempt: Reconnect to existing room
 * 
 * Received (Server → Client):
 * - battle_created: Room created successfully
 * - battle_join_request_notify: Notify host of join request
 * - join_accepted: Join request approved
 * - battle_entered: Both players in room
 * - battle_chat_message: Receive chat message
 * - battle_started: Battle phase begins
 * - battle_notification: Important event occurred
 * - battle_state_change: State transition
 * - battle_result: Battle finished, winner determined
 * - battle_restart: Rematch approved
 * - battle_rematch_declined: Rematch rejected
 * - battle_rejoined: Reconnection successful
 * - battle_error: Error occurred
 * 
 * DATA STRUCTURES:
 * ---------------
 * - Room State Object: {room_code, players[], state, problem, timer}
 * - Player Object: {id, name, score, submitted, code}
 * - Problem Object: {title, description, input_format, output_format, test_cases}
 * 
 * ALGORITHMS:
 * ----------
 * - Timer: Countdown using setInterval (1-second ticks)
 * - Score Calculation: base_points * (time_remaining / total_time)
 * - Reconnection: Exponential backoff for retry attempts
 * 
 * DESIGN PATTERNS:
 * ---------------
 * - State Machine: Battle progresses through defined states
 * - Observer Pattern: Socket.IO event listeners
 * - Session Persistence: sessionStorage for room code
 * 
 * ERROR HANDLING:
 * --------------
 * - Connection errors: Auto-reconnect with heartbeat
 * - Invalid room: Clear session and return to entry
 * - Timeout: Fallback UI reset after 10 seconds
 */

// ============================================================================
// INITIALIZATION AND SETUP
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // --- Socket.IO Initialization ---
    // Auto-detection of best transport method (Polling first, then upgrade to WebSocket)
    const socket = io();

    // --- State Variables ---
    let currentRoom = sessionStorage.getItem('battle_room_code'); // Persist room across page refreshes
    let isHost = false;  // Track if current user created the room
    let battleTimer = null;  // Reference to countdown interval

    // --- Elements ---
    const screens = {
        entry: document.getElementById('screen-entry'),
        battle: document.getElementById('screen-battle')
    };

    const modals = {
        joinReq: document.getElementById('modal-join-req'),
        result: document.getElementById('modal-result')
    };

    const display = {
        room: document.getElementById('room-display'),
        timer: document.getElementById('timer-display'),
        status: document.getElementById('status-display'),
        lang: document.getElementById('lang-display'),
        chat: document.getElementById('chat-log')
    };

    const problem = {
        title: document.getElementById('problem-title'),
        desc: document.getElementById('problem-desc'),
        details: document.getElementById('problem-details'),
        in: document.getElementById('prob-in'),
        out: document.getElementById('prob-out')
    };

    const inputs = {
        code: document.getElementById('code-editor'),
        chat: document.getElementById('chat-input')
    };

    const buttons = {
        create: document.getElementById('btn-create'),
        join: document.getElementById('btn-join'),
        submit: document.getElementById('btn-submit'),
        accept: document.getElementById('btn-accept'),
        reject: document.getElementById('btn-reject'),
        voteYes: document.getElementById('btn-vote-yes'),
        voteNo: document.getElementById('btn-vote-no')
    };

    // --- Helpers ---
    function showScreen(name) {
        Object.values(screens).forEach(el => el.classList.add('hidden'));
        if (screens[name]) {
            screens[name].classList.remove('hidden');
            screens[name].style.display = 'flex'; // Ensure flex layout applies
        }
    }

    function addChatMsg(sender, text, type = 'user') {
        const div = document.createElement('div');
        div.className = `chat-msg ${type}`;
        if (type === 'system') div.className += ' system';
        if (sender === 'ByteBot') div.className = 'chat-msg bot';
        if (sender === 'You') div.className = 'chat-msg user';

        const bubble = document.createElement('div');
        bubble.className = 'msg-bubble';

        // Handle bolding for system msgs (markdown-ish)
        if (type === 'system' || sender === 'ByteBot') {
            text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            text = text.replace(/\n/g, '<br>');
        }

        bubble.innerHTML = (sender && type !== 'system' && sender !== 'You' ? `<strong>${sender}:</strong> ` : '') + text;
        div.appendChild(bubble);
        display.chat.appendChild(div);
        display.chat.scrollTop = display.chat.scrollHeight;
    }

    function setStatus(text, active = false) {
        display.status.textContent = text;
        display.status.classList.remove('judging');
        if (active) display.status.classList.add('active');
        else display.status.classList.remove('active');
    }

    // --- 1. Entry Logic ---

    // --- Debug UI ---
    const debugDiv = document.createElement('div');
    debugDiv.id = 'battle-debug';
    debugDiv.style.cssText = "position: fixed; bottom: 10px; right: 10px; background: rgba(0,0,0,0.8); color: lime; padding: 5px 10px; font-size: 10px; border-radius: 4px; pointer-events: none; opacity: 0.7; z-index: 9999;";
    debugDiv.innerHTML = 'Status: <span id="debug-status">Init...</span>';
    document.body.appendChild(debugDiv);

    function setDebug(msg) {
        const el = document.getElementById('debug-status');
        if (el) el.textContent = msg;
        console.log('[BattleDebug]', msg);
    }

    // Add connection status handling
    socket.on('connect', () => {
        setDebug('Connected');
        console.log('[Battle] Socket connected successfully');

        // Auto-rejoin if we have a room code and we are not already cleanly inside
        if (currentRoom) { // currentRoom loaded from sessionStorage on init
            setDebug('Attempting Rejoin...');
            console.log('[Battle] Attempting to rejoin room:', currentRoom);
            socket.emit('battle_rejoin_attempt', { room_code: currentRoom });
        } else {
            setDebug('Ready (No Room)');
        }

        // Start heartbeat to keep connection alive
        startHeartbeat();
    });

    socket.on('connect_error', (error) => {
        setDebug('Conn Error');
        console.error('[Battle] Socket connection error:', error);
        stopHeartbeat();
    });

    socket.on('disconnect', (reason) => {
        setDebug('Disconnected');
        console.log('[Battle] Socket disconnected:', reason);
        stopHeartbeat();
    });

    // Heartbeat mechanism to keep connection alive
    let heartbeatInterval = null;

    function startHeartbeat() {
        stopHeartbeat(); // Clear any existing interval
        heartbeatInterval = setInterval(() => {
            if (currentRoom) {
                socket.emit('battle_heartbeat', { room_code: currentRoom });
                console.log('[Battle] Heartbeat sent for room:', currentRoom);
            }
        }, 30000); // Send heartbeat every 30 seconds
    }

    function stopHeartbeat() {
        if (heartbeatInterval) {
            clearInterval(heartbeatInterval);
            heartbeatInterval = null;
        }
    }

    if (buttons.create) {
        buttons.create.addEventListener('click', () => {
            // ... existing create logic ...
            setDebug('Creating Room...');
            // ...
        });
    }

    // ...

    socket.on('battle_error', (data) => {
        setDebug('Error: ' + data.message);
        console.error('[Battle] Error:', data.message);
        alert(data.message);

        // If room is invalid, clear session to prevent stuck loop
        if (data.message.includes('Invalid room') || data.message.includes('expired') || data.message.includes('not in this room')) {
            sessionStorage.removeItem('battle_room_code');
            currentRoom = null;
            showScreen('entry');
            setDebug('Session Cleared');
        }

        // Reset join button if it was in a loading state
        if (buttons.join.textContent === "Requesting...") {
            buttons.join.textContent = "Join";
            buttons.join.disabled = false;
        }
        // Hide modal if open
        if (modals.joinReq) modals.joinReq.style.display = 'none';
    });



    if (buttons.create) {
        buttons.create.addEventListener('click', () => {
            console.log('[Battle] Create button clicked, emitting battle_create');
            buttons.create.textContent = "Creating...";
            buttons.create.disabled = true;
            socket.emit('battle_create', {});

            // Timeout fallback
            setTimeout(() => {
                if (buttons.create.textContent === "Creating...") {
                    buttons.create.textContent = "Create Room";
                    buttons.create.disabled = false;
                    alert("Failed to create room. Server might not be responding. Please try again.");
                }
            }, 10000);
        });
    } else {
        console.error('[Battle] btn-create element not found!');
    }

    buttons.join.addEventListener('click', () => {
        const code = document.getElementById('join-code').value.trim();
        if (!code) return alert("Enter a room code!");

        // Change button to loading state
        buttons.join.textContent = "Requesting...";
        buttons.join.disabled = true;

        socket.emit('battle_join_request', { room_code: code });
        currentRoom = code;
    });



    socket.on('battle_rejoined', (data) => {
        console.log('[Battle] Rejoined room:', data.room_code);
        currentRoom = data.room_code;
        isHost = data.is_host;

        display.room.textContent = currentRoom;

        // Restore UI state
        // If battle holds state like code content, we should restore it here if server sent it
        // For now, just show the screen
        showScreen('battle');
        setStatus(data.state === 'waiting' ? "WAITING FOR PLAYER" : "BATTLE IN PROGRESS");

        if (isHost && data.state === 'waiting') {
            addChatMsg("ByteBot", "Reconnected successfully. Waiting for opponent...", 'system');
        } else {
            addChatMsg("ByteBot", "Reconnected successfully.", 'system');
        }
    });

    socket.on('battle_created', (data) => {
        console.log('[Battle] Room created:', data.room_code);
        currentRoom = data.room_code;
        sessionStorage.setItem('battle_room_code', currentRoom); // Save to session
        isHost = true;
        display.room.textContent = currentRoom;

        // Reset create button
        if (buttons.create) {
            buttons.create.textContent = "Create Room";
            buttons.create.disabled = false;
        }

        showScreen('battle');
        setStatus("WAITING FOR PLAYER");
        addChatMsg("ByteBot", "Room created. Waiting for opponent to join...");
        addChatMsg("ByteBot", `Invite Code: **${currentRoom}**`, 'system');
    });



    // --- 2. Join Request Flow (Host Side) ---

    socket.on('battle_join_request_notify', (data) => {
        document.getElementById('req-name').textContent = data.player_name;
        modals.joinReq.style.display = 'flex';
    });

    buttons.accept.addEventListener('click', () => {
        socket.emit('battle_join_response', { room_code: currentRoom, accepted: true });
        modals.joinReq.style.display = 'none';
    });

    buttons.reject.addEventListener('click', () => {
        socket.emit('battle_join_response', { room_code: currentRoom, accepted: false });
        modals.joinReq.style.display = 'none';
    });

    // --- 3. Join Accepted (Guest Side) ---

    socket.on('join_accepted', (data) => {
        currentRoom = data.room_code;
        socket.emit('battle_confirm_join', { room_code: currentRoom });
    });

    // --- 4. Setup Phase ---

    socket.on('battle_entered', (data) => {
        if (!currentRoom) currentRoom = data.room_code; // Ensure set for guest
        display.room.textContent = currentRoom;
        showScreen('battle');
        setStatus("SETUP");
    });

    socket.on('battle_chat_message', (data) => {
        addChatMsg(data.sender, data.message, data.type);
    });

    // Chat Input
    inputs.chat.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const msg = inputs.chat.value.trim();
            if (msg) {
                // Optimistic UI
                addChatMsg("You", msg, 'user');
                socket.emit('battle_chat_send', { room_code: currentRoom, message: msg });
                inputs.chat.value = '';
            }
        }
    });

    // --- 5. Battle Phase ---

    socket.on('battle_started', (data) => {
        setStatus("BATTLE IN PROGRESS", true);

        // Update Language Display
        if (data.language) {
            display.lang.textContent = data.language;
        }

        // Update Problem
        problem.title.textContent = data.problem.title;
        problem.desc.textContent = data.problem.description;
        problem.in.textContent = data.problem.input_format;
        problem.out.textContent = data.problem.output_format;
        problem.details.classList.remove('hidden');

        // Reset Editor
        inputs.code.value = "";
        buttons.submit.disabled = false;
        buttons.submit.textContent = "SUBMIT CODE";

        // Start Timer
        startTimer(data.duration);
    });

    socket.on('battle_notification', (data) => {
        // Play sound
        const audio = document.getElementById('sound-bell');
        if (audio) audio.play().catch(e => { });

        // Flash border
        document.body.style.borderColor = 'var(--battle-accent)';
        setTimeout(() => document.body.style.borderColor = 'transparent', 500);
    });

    buttons.submit.addEventListener('click', () => {
        const code = inputs.code.value;
        if (!code.trim()) return alert("Write some code first!");

        if (confirm("Submit solution?")) {
            socket.emit('battle_submit', { room_code: currentRoom, code: code });
            buttons.submit.disabled = true;
            buttons.submit.textContent = "Submitted ✅";
        }
    });

    socket.on('battle_state_change', (data) => {
        if (data.state === 'judging') {
            setStatus("JUDGING...");
            display.status.classList.add('judging');
            stopTimer();
        }
    });

    // --- 6. Result & Rematch ---

    socket.on('battle_result', (data) => {
        display.status.classList.remove('judging');
        modals.result.style.display = 'flex';
        document.getElementById('res-winner').textContent = `Winner: ${data.winner}`;
        document.getElementById('res-reason').textContent = data.reason;

        // Reset vote buttons
        buttons.voteYes.disabled = false;
        buttons.voteNo.disabled = false;
        document.getElementById('vote-status').textContent = "";
    });

    buttons.voteYes.addEventListener('click', () => {
        socket.emit('battle_rematch_vote', { room_code: currentRoom, vote: 'yes' });
        disableVotes("Waiting for opponent...");
    });

    buttons.voteNo.addEventListener('click', () => {
        socket.emit('battle_rematch_vote', { room_code: currentRoom, vote: 'no' });
        disableVotes("You declined. Notifying opponent...");
        // Don't close modal here - let backend's battle_rematch_declined event handle it
    });

    function disableVotes(msg) {
        buttons.voteYes.disabled = true;
        buttons.voteNo.disabled = true;
        document.getElementById('vote-status').textContent = msg;
    }

    socket.on('battle_restart', () => {
        modals.result.style.display = 'none';
        setStatus("SETUP");
        problem.title.textContent = "Waiting for host configuration...";
        problem.desc.textContent = "Host is selecting new difficulty/language via chat.";
        problem.details.classList.add('hidden');
        inputs.code.value = "";
    });

    socket.on('battle_rematch_declined', () => {
        // Close result modal and return both players to entry screen
        modals.result.style.display = 'none';

        // Clear room state completely (room is expired on server)
        sessionStorage.removeItem('battle_room_code');
        currentRoom = null;
        isHost = false;

        // Clear chat
        display.chat.innerHTML = '';

        showScreen('entry');
        addChatMsg('ByteBot', 'Match ended. Room has been closed. Create or join a new room to play again!', 'system');
    });

    // Handle room closed by host leaving
    socket.on('battle_room_closed', (data) => {
        // Notify user and kick to entry screen
        modals.result.style.display = 'none';
        modals.joinReq.style.display = 'none';

        sessionStorage.removeItem('battle_room_code');
        currentRoom = null;
        isHost = false;
        stopTimer();

        display.chat.innerHTML = '';
        showScreen('entry');

        // Show a brief toast notification
        const msg = (data && data.reason) ? data.reason : 'The room has expired.';
        const toast = document.createElement('div');
        toast.style.cssText = 'position:fixed;top:20px;right:20px;z-index:9999;background:#1a1a1a;border:1px solid #ef4444;color:#fca5a5;padding:14px 20px;border-radius:10px;font-size:14px;box-shadow:0 4px 20px rgba(239,68,68,0.3);animation:fadeInDown 0.3s ease;';
        toast.innerHTML = `<i class="fa-solid fa-door-open" style="margin-right:8px;color:#ef4444;"></i>${msg}`;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    });

    // --- Timer Util ---
    function startTimer(duration) {
        let timeLeft = duration;
        stopTimer();
        updateTimerDisplay(timeLeft);

        battleTimer = setInterval(() => {
            timeLeft--;
            updateTimerDisplay(timeLeft);
            if (timeLeft <= 0) {
                stopTimer();
                // Auto submit or end
            }
        }, 1000);
    }

    function stopTimer() {
        if (battleTimer) clearInterval(battleTimer);
    }

    function updateTimerDisplay(seconds) {
        const m = Math.floor(seconds / 60).toString().padStart(2, '0');
        const s = (seconds % 60).toString().padStart(2, '0');
        display.timer.textContent = `${m}:${s}`;

        if (seconds < 60) display.timer.style.color = '#ef4444'; // Red
        else display.timer.style.color = 'inherit';
    }

    // ── Leave Room (expire for everyone) ──────────────────────────────────
    window.leaveRoom = function () {
        if (!confirm('Are you sure you want to leave? This will close the room for both players.')) return;

        if (currentRoom) {
            // Tell server to expire room and kick other player
            socket.emit('battle_leave', { room_code: currentRoom });
        }

        // Clear local state and navigate away
        sessionStorage.removeItem('battle_room_code');
        currentRoom = null;
        window.location.href = '/battle';
    };
});