/**
 * Real-time Collaborative Whiteboard Logic
 */
document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('whiteboard');
    if (!canvas) return; // Not on whiteboard page

    const ctx = canvas.getContext('2d');
    const socket = io('/', { transports: ['polling', 'websocket'] });
    const group_id = typeof GROUP_ID !== 'undefined' ? GROUP_ID : null;

    if (!group_id) return;

    // Join room
    socket.emit('join', { username: 'User', room: group_id });

    // State
    let drawing = false;
    let current = { x: 0, y: 0 };
    let color = '#000000';
    let size = 2;

    // Stroke history for undo (local only)
    // Each entry: { type: 'line' | 'snapshot', data: {...} }
    const history = [];

    // Controls
    const colorPicker = document.getElementById('wb-color');
    const sizePicker = document.getElementById('wb-size');
    const clearBtn = document.getElementById('wb-clear');
    const saveBtn = document.getElementById('wb-save');
    const undoBtn = document.getElementById('wb-undo');

    if (colorPicker) {
        colorPicker.addEventListener('change', (e) => color = e.target.value);
        color = colorPicker.value;
    }
    if (sizePicker) {
        sizePicker.addEventListener('change', (e) => size = parseInt(e.target.value));
        size = parseInt(sizePicker.value);
    }
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            clearCanvas();
            history.length = 0;
            socket.emit('wb_clear', { room: group_id });
        });
    }
    if (saveBtn) {
        saveBtn.addEventListener('click', () => {
            const link = document.createElement('a');
            link.download = `whiteboard-${Date.now()}.png`;
            link.href = canvas.toDataURL();
            link.click();
        });
    }

    if (undoBtn) {
        undoBtn.addEventListener('click', () => {
            if (!history.length) return;
            history.pop(); // remove last stroke
            redrawFromHistory();
            socket.emit('wb_undo', { room: group_id });
        });
    }

    // Resize
    function resize() {
        const parent = canvas.parentElement;
        canvas.width = parent.clientWidth;
        canvas.height = parent.clientHeight;
    }

    // Initial resize
    setTimeout(resize, 100);
    window.addEventListener('resize', resize);

    // ── Core drawLine helper ──────────────────────────────────────────────
    function drawLine(x0, y0, x1, y1, strokeColor, strokeSize, emit) {
        ctx.beginPath();
        ctx.moveTo(x0, y0);
        ctx.lineTo(x1, y1);
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = strokeSize;
        ctx.lineCap = 'round';
        ctx.stroke();
        ctx.closePath();

        if (!emit) return;

        // Record in local history
        history.push({
            type: 'line',
            data: { x0, y0, x1, y1, color: strokeColor, size: strokeSize }
        });

        socket.emit('wb_draw', {
            room: group_id,
            x0: x0 / canvas.width,
            y0: y0 / canvas.height,
            x1: x1 / canvas.width,
            y1: y1 / canvas.height,
            color: strokeColor,
            size: strokeSize
        });
    }

    function clearCanvas() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    function redrawFromHistory() {
        clearCanvas();
        for (const entry of history) {
            if (entry.type === 'line') {
                const d = entry.data;
                drawLine(d.x0, d.y0, d.x1, d.y1, d.color, d.size, false);
            } else if (entry.type === 'snapshot') {
                const img = new Image();
                img.onload = () => ctx.drawImage(img, 0, 0);
                img.src = entry.data.snap;
            }
        }
    }

    // Mouse Events
    canvas.addEventListener('mousedown', (e) => {
        drawing = true;
        current.x = e.offsetX;
        current.y = e.offsetY;
    });

    canvas.addEventListener('mouseup', (e) => {
        if (!drawing) return;
        drawing = false;
        drawLine(current.x, current.y, e.offsetX, e.offsetY, color, size, true);
    });

    canvas.addEventListener('mousemove', (e) => {
        if (!drawing) return;
        drawLine(current.x, current.y, e.offsetX, e.offsetY, color, size, true);
        current.x = e.offsetX;
        current.y = e.offsetY;
    });

    // Touch Events
    canvas.addEventListener('touchstart', (e) => {
        drawing = true;
        const touch = e.touches[0];
        const rect = canvas.getBoundingClientRect();
        current.x = touch.clientX - rect.left;
        current.y = touch.clientY - rect.top;
        e.preventDefault();
    });

    canvas.addEventListener('touchmove', (e) => {
        if (!drawing) return;
        const touch = e.touches[0];
        const rect = canvas.getBoundingClientRect();
        const x = touch.clientX - rect.left;
        const y = touch.clientY - rect.top;
        drawLine(current.x, current.y, x, y, color, size, true);
        current.x = x;
        current.y = y;
        e.preventDefault();
    });

    canvas.addEventListener('touchend', () => { drawing = false; });

    // Socket Listeners
    socket.on('wb_draw', (data) => {
        const x0 = data.x0 * canvas.width;
        const y0 = data.y0 * canvas.height;
        const x1 = data.x1 * canvas.width;
        const y1 = data.y1 * canvas.height;
        drawLine(x0, y0, x1, y1, data.color, data.size, false);
        history.push({
            type: 'line',
            data: { x0, y0, x1, y1, color: data.color, size: data.size }
        });
    });

    socket.on('wb_clear', () => {
        clearCanvas();
        history.length = 0;
    });

    socket.on('wb_undo', () => {
        if (!history.length) return;
        history.pop();
        redrawFromHistory();
    });

    // Tab switching fix
    window.triggerWhiteboardResize = function () { setTimeout(resize, 50); };

    // ════════════════════════════════════════════════════════════════════════
    // VERSE AI DRAWING ENGINE
    // Called by the Verse voice assistant: window.verseDrawOnWhiteboard(cmd)
    // ════════════════════════════════════════════════════════════════════════
    window.verseDrawOnWhiteboard = function (command) {
        // Make sure canvas is sized
        if (canvas.width < 10) resize();

        const cmd = (command || '').toLowerCase();
        const W = canvas.width || 600;
        const H = canvas.height || 400;
        const cx = W / 2, cy = H / 2;

        // Detect color hints
        const aiColor = detectColor(cmd) || '#4ade80'; // verse green default
        const aiSize = 3;

        // Auto-switch to whiteboard tab if on chat tab
        if (typeof switchTab === 'function') switchTab('whiteboard');
        setTimeout(() => { if (canvas.width < 10) resize(); }, 60);

        setTimeout(() => {
            ctx.save();
            ctx.strokeStyle = aiColor;
            ctx.fillStyle = aiColor;
            ctx.lineWidth = aiSize;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';

            // ── Shape dispatcher ──────────────────────────────────────────
            if (cmd.includes('tree')) {
                drawTree(cx, cy + 80, H * 0.35);
            } else if (cmd.includes('house') || cmd.includes('home')) {
                drawHouse(cx, cy);
            } else if (cmd.includes('circle') || cmd.includes('sun')) {
                drawCircle(cx, cy, Math.min(W, H) * 0.22);
            } else if (cmd.includes('triangle') || cmd.includes('mountain')) {
                drawTriangle(cx, cy);
            } else if (cmd.includes('star')) {
                drawStar(cx, cy, 5, Math.min(W, H) * 0.22, Math.min(W, H) * 0.1);
            } else if (cmd.includes('arrow')) {
                drawArrow(W * 0.2, cy, W * 0.8, cy);
            } else if (cmd.includes('heart')) {
                drawHeart(cx, cy, Math.min(W, H) * 0.18);
            } else if (cmd.includes('smiley') || cmd.includes('face') || cmd.includes('smile')) {
                drawSmiley(cx, cy, Math.min(W, H) * 0.2);
            } else if (cmd.includes('rectangle') || cmd.includes('box') || cmd.includes('square')) {
                const s = Math.min(W, H) * 0.3;
                ctx.strokeRect(cx - s, cy - s * 0.6, s * 2, s * 1.2);
            } else {
                // Default: a smooth diagonal line with label
                animateLine(W * 0.15, H * 0.75, W * 0.85, H * 0.25, aiColor, aiSize);
                ctx.restore();
                return;
            }

            ctx.restore();

            // Snapshot the canvas and share via socket so others see it
            broadcastSnapshot();
        }, 80);
    };

    // ── Color detector ───────────────────────────────────────────────────
    function detectColor(cmd) {
        const map = {
            'red': '#ef4444', 'blue': '#3b82f6', 'green': '#22c55e',
            'yellow': '#facc15', 'orange': '#f97316', 'purple': '#a855f7',
            'pink': '#ec4899', 'white': '#ffffff', 'black': '#111111',
            'brown': '#92400e', 'cyan': '#06b6d4', 'teal': '#14b8a6'
        };
        for (const [k, v] of Object.entries(map)) {
            if (cmd.includes(k)) return v;
        }
        return null;
    }

    // ── Broadcast canvas snapshot via socket ─────────────────────────────
    // We re-use wb_draw_snapshot event; server just needs to relay it.
    function broadcastSnapshot() {
        try {
            const snap = canvas.toDataURL('image/png');
            history.push({ type: 'snapshot', data: { snap } });
            socket.emit('wb_snapshot', { room: group_id, snap });
        } catch (e) { /* cross-origin canvas — skip */ }
    }

    socket.on('wb_snapshot', (data) => {
        const img = new Image();
        img.onload = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0);
            history.push({ type: 'snapshot', data: { snap: data.snap } });
        };
        img.src = data.snap;
    });

    // ── Shape drawing functions ──────────────────────────────────────────

    // Animated straight line
    function animateLine(x0, y0, x1, y1, col, sz) {
        let t = 0; const steps = 40;
        const iv = setInterval(() => {
            const px = x0 + (x1 - x0) * (t / steps);
            const py = y0 + (y1 - y0) * (t / steps);
            if (t > 0) {
                ctx.beginPath();
                ctx.moveTo(x0 + (x1 - x0) * ((t - 1) / steps), y0 + (y1 - y0) * ((t - 1) / steps));
                ctx.lineTo(px, py);
                ctx.strokeStyle = col; ctx.lineWidth = sz; ctx.lineCap = 'round';
                ctx.stroke(); ctx.closePath();
            }
            t++;
            if (t > steps) { clearInterval(iv); broadcastSnapshot(); }
        }, 12);
    }

    function drawTree(bx, by, h) {
        const c = ctx;
        // Trunk
        c.lineWidth = 8;
        c.strokeStyle = '#92400e';
        c.beginPath(); c.moveTo(bx, by); c.lineTo(bx, by - h * 0.3); c.stroke();

        // Three layers of foliage
        c.fillStyle = '#15803d';
        [[0, 0, h * 0.55], [-h * 0.1, -h * 0.25, h * 0.5], [-h * 0.18, -h * 0.48, h * 0.42]].forEach(([ox, oy, r]) => {
            c.beginPath();
            c.moveTo(bx + ox, by - h * 0.28 + oy);
            c.lineTo(bx + ox - r * 0.6, by - h * 0.28 + oy + r * 0.9);
            c.lineTo(bx + ox + r * 0.6, by - h * 0.28 + oy + r * 0.9);
            c.closePath(); c.fill();
        });

        // Add a few highlight dots
        c.fillStyle = '#4ade80';
        [[-0.15, -0.6], [0.2, -0.75], [-0.05, -0.9], [0.18, -0.55], [-0.22, -0.72]].forEach(([dx, dy]) => {
            c.beginPath(); c.arc(bx + dx * h * 0.5, by + dy * h * 0.6, 4, 0, Math.PI * 2); c.fill();
        });
    }

    function drawHouse(cx, cy) {
        const W = canvas.width, H = canvas.height;
        const w = Math.min(W, H) * 0.38, h = Math.min(W, H) * 0.28;
        const x = cx - w / 2, y = cy - h / 2 + h * 0.1;
        // Body
        ctx.strokeRect(x, y, w, h);
        // Roof
        ctx.beginPath();
        ctx.moveTo(x - w * 0.07, y);
        ctx.lineTo(cx, cy - h * 0.8);
        ctx.lineTo(x + w + w * 0.07, y);
        ctx.closePath(); ctx.stroke();
        // Door
        const dw = w * 0.22, dh = h * 0.42;
        ctx.strokeRect(cx - dw / 2, y + h - dh, dw, dh);
        // Window
        const ww = w * 0.2;
        ctx.strokeRect(x + w * 0.12, y + h * 0.18, ww, ww);
        ctx.strokeRect(x + w - w * 0.12 - ww, y + h * 0.18, ww, ww);
    }

    function drawCircle(cx, cy, r) {
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.stroke();
    }

    function drawTriangle(cx, cy) {
        const W = canvas.width, H = canvas.height;
        const s = Math.min(W, H) * 0.38;
        ctx.beginPath();
        ctx.moveTo(cx, cy - s * 0.55);
        ctx.lineTo(cx - s * 0.5, cy + s * 0.45);
        ctx.lineTo(cx + s * 0.5, cy + s * 0.45);
        ctx.closePath(); ctx.stroke();
    }

    function drawStar(cx, cy, spikes, outerR, innerR) {
        let rot = (Math.PI / 2) * 3, step = Math.PI / spikes;
        ctx.beginPath();
        ctx.moveTo(cx, cy - outerR);
        for (let i = 0; i < spikes; i++) {
            ctx.lineTo(cx + Math.cos(rot) * outerR, cy + Math.sin(rot) * outerR); rot += step;
            ctx.lineTo(cx + Math.cos(rot) * innerR, cy + Math.sin(rot) * innerR); rot += step;
        }
        ctx.lineTo(cx, cy - outerR); ctx.closePath(); ctx.stroke(); ctx.fill();
    }

    function drawArrow(x1, y1, x2, y2) {
        const angle = Math.atan2(y2 - y1, x2 - x1);
        const hs = 22;
        ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(x2, y2);
        ctx.lineTo(x2 - hs * Math.cos(angle - Math.PI / 7), y2 - hs * Math.sin(angle - Math.PI / 7));
        ctx.lineTo(x2 - hs * Math.cos(angle + Math.PI / 7), y2 - hs * Math.sin(angle + Math.PI / 7));
        ctx.closePath(); ctx.fill();
    }

    function drawHeart(cx, cy, r) {
        ctx.beginPath();
        ctx.moveTo(cx, cy + r * 0.3);
        ctx.bezierCurveTo(cx, cy - r * 0.1, cx - r * 1.2, cy - r * 0.5, cx - r, cy - r * 0.1);
        ctx.bezierCurveTo(cx - r * 1.2, cy - r * 0.8, cx - r * 0.2, cy - r * 1.2, cx, cy - r * 0.4);
        ctx.bezierCurveTo(cx + r * 0.2, cy - r * 1.2, cx + r * 1.2, cy - r * 0.8, cx + r, cy - r * 0.1);
        ctx.bezierCurveTo(cx + r * 1.2, cy - r * 0.5, cx, cy - r * 0.1, cx, cy + r * 0.3);
        ctx.closePath(); ctx.fill(); ctx.stroke();
    }

    function drawSmiley(cx, cy, r) {
        // Face
        ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
        // Eyes
        ctx.beginPath(); ctx.arc(cx - r * 0.35, cy - r * 0.2, r * 0.1, 0, Math.PI * 2); ctx.fill();
        ctx.beginPath(); ctx.arc(cx + r * 0.35, cy - r * 0.2, r * 0.1, 0, Math.PI * 2); ctx.fill();
        // Smile
        ctx.beginPath();
        ctx.arc(cx, cy + r * 0.05, r * 0.45, 0.2, Math.PI - 0.2);
        ctx.stroke();
    }
});
