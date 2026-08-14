document.addEventListener('DOMContentLoaded', () => {
    // ----------------------------------------------------
    // DOM References
    // ----------------------------------------------------
    const chatInput       = document.getElementById('groupChatInput');
    const sendButton      = document.getElementById('groupSendButton');
    const messagesContainer = document.getElementById('groupMessagesContainer');
    const uploadBtn       = document.getElementById('uploadBtn');
    const fileInput       = document.getElementById('fileInput');
    const chatForm        = document.getElementById('groupChatForm');
    const previewContainer = document.getElementById('filePreviewContainer');
    const previewName     = document.getElementById('previewFileName');

    // ----------------------------------------------------
    // Auto-resize textarea + Enter key
    // ----------------------------------------------------
    if (chatInput) {
        chatInput.addEventListener('input', () => {
            chatInput.style.height = 'auto';
            chatInput.style.height = Math.min(chatInput.scrollHeight, 200) + 'px';
        });
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (chatForm) chatForm.dispatchEvent(new Event('submit'));
            }
        });
    }

    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // ----------------------------------------------------
    // Single File Upload Preview
    // ----------------------------------------------------
    if (uploadBtn && fileInput) {
        uploadBtn.addEventListener('click', () => fileInput.click());

        const removeFileBtn = document.getElementById('removeFileBtn');

        fileInput.addEventListener('change', () => {
            const files = fileInput.files;
            if (files.length > 0) {
                uploadBtn.classList.add('text-primary');
                if (previewContainer && previewName) {
                    previewContainer.style.display = 'flex';
                    previewName.textContent = files[0].name;
                }
            } else {
                clearFileSelection();
            }
        });

        if (removeFileBtn) {
            removeFileBtn.addEventListener('click', clearFileSelection);
        }

        function clearFileSelection() {
            fileInput.value = '';
            uploadBtn.classList.remove('text-primary');
            if (previewContainer) previewContainer.style.display = 'none';
        }

        chatForm.clearFileSelection = clearFileSelection;
    }

    // ----------------------------------------------------
    // Polling: new messages every 2 seconds
    // ----------------------------------------------------
    let lastMessageId = 0;
    const seenMessageIds = new Set();

    const existingMessages = document.querySelectorAll('[data-message-id]');
    if (existingMessages.length > 0) {
        const lastMsg = existingMessages[existingMessages.length - 1];
        lastMessageId = parseInt(lastMsg.getAttribute('data-message-id')) || 0;
        existingMessages.forEach(el => {
            const id = parseInt(el.getAttribute('data-message-id'));
            if (id) seenMessageIds.add(id);
        });
    }

    setInterval(async () => {
        try {
            const response = await fetch(`/group/${GROUP_ID}/messages?since=${lastMessageId}`);
            if (response.ok) {
                const data = await response.json();
                if (data.messages && data.messages.length > 0) {
                    data.messages.forEach(msg => appendMessage(msg));
                }
            }
        } catch (err) {
            console.error('Polling error:', err);
        }
    }, 2000);

    // ----------------------------------------------------
    // Socket.IO
    // ----------------------------------------------------
    if (typeof io !== 'undefined' && GROUP_ID) {
        const socket = io('/', {
            transports: ['polling', 'websocket'],
            upgrade: true,
            rememberUpgrade: true
        });

        // Expose socket globally for calls.js
        window.svSocket = socket;

        socket.on('connect', () => {
            console.log('Connected. Transport:', socket.io.engine.transport.name);
            socket.emit('join', { group_id: GROUP_ID });
        });

        socket.on('joined_room', (data) => {
            console.log('✓ Joined room:', data.room);
        });

        socket.on('receive_message', (data) => {
            appendMessage(data);
        });

        // Init call socket listeners from calls.js
        if (typeof window.initCallSocketListeners === 'function') {
            window.initCallSocketListeners(socket);
        }

        // ── Form Submit ──────────────────────────────────
        if (chatForm) {
            chatForm.addEventListener('submit', async (e) => {
                e.preventDefault();

                const message = chatInput.value.trim();
                const file    = fileInput.files[0];
                if (!message && !file) return;

                sendButton.disabled = true;

                // Upload file if present
                if (file) {
                    if (previewName) previewName.textContent = 'Uploading…';
                    const formData = new FormData();
                    formData.append('file', file);
                    try {
                        const response = await fetch('/group/upload', { method: 'POST', body: formData });
                        if (response.ok) {
                            const result = await response.json();
                            socket.emit('send_message', {
                                group_id: GROUP_ID, content: '', file_path: result.url
                            });
                        } else {
                            alert('Upload failed: ' + file.name);
                        }
                    } catch (err) {
                        console.error('Upload error:', err);
                    }
                }

                // Send text if present
                if (message) {
                    socket.emit('send_message', {
                        group_id: GROUP_ID, content: message, file_path: null
                    });
                    // Optimistic temp bubble
                    appendMessage({
                        id: 'temp-' + Date.now(),
                        user_id: CURRENT_USER_ID, username: CURRENT_USER_NAME,
                        avatar: CURRENT_USER_AVATAR, content: message,
                        file_path: null,
                        created_at: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true }),
                        role: 'user', is_temp: true
                    });
                }

                // Reset UI
                chatInput.value = '';
                chatInput.style.height = 'auto';
                if (chatForm.clearFileSelection) chatForm.clearFileSelection();
                sendButton.disabled = false;
            });
        }
    }

    // ----------------------------------------------------
    // appendMessage
    // ----------------------------------------------------
    function appendMessage(data) {
        if (!messagesContainer) return;

        // Deduplication
        if (data.id && !String(data.id).startsWith('temp-')) {
            if (seenMessageIds.has(data.id)) return;
            seenMessageIds.add(data.id);
            if (typeof data.id === 'number') {
                lastMessageId = Math.max(lastMessageId, data.id);
            }
            // Remove temp bubbles when real message arrives
            const isMyMsg = String(data.user_id) === String(CURRENT_USER_ID);
            if (isMyMsg) {
                messagesContainer.querySelectorAll('[data-temp="true"]').forEach(t => t.remove());
            }
        }

        const isMe = String(data.user_id) === String(CURRENT_USER_ID);
        const isAI = data.role === 'assistant';

        const msgDiv = document.createElement('div');
        msgDiv.style.cssText = `display:flex;gap:10px;align-self:${isMe ? 'flex-end' : 'flex-start'};max-width:70%;${isMe ? 'flex-direction:row-reverse;' : ''}`;

        if (data.is_temp) {
            msgDiv.setAttribute('data-temp', 'true');
            msgDiv.style.opacity = '0.7';
        } else {
            msgDiv.setAttribute('data-message-id', data.id);
        }

        // Avatar
        let avatarHtml = '';
        if (isAI) {
            avatarHtml = `<div style="width:32px;height:32px;background:linear-gradient(135deg,#3b82f6,#8b5cf6);border-radius:50%;display:grid;place-items:center;color:white;font-size:0.8rem;flex-shrink:0;"><i class="fa-solid fa-robot"></i></div>`;
        } else {
            const avatarUrl = data.avatar || `https://ui-avatars.com/api/?name=${encodeURIComponent(data.username || 'User')}&background=random`;
            avatarHtml = `<img src="${avatarUrl}" style="width:32px;height:32px;border-radius:50%;object-fit:cover;flex-shrink:0;">`;
        }

        const nameLabel  = isAI ? 'AI Coach' : (isMe ? 'You' : data.username);
        const bubbleBg   = isMe ? 'var(--accent-green)' : (isAI ? 'rgba(59,130,246,0.2)' : 'rgba(255,255,255,0.1)');
        const bubbleClr  = isMe ? 'black' : 'white';
        const borderRad  = isMe ? '12px 0 12px 12px' : '0 12px 12px 12px';
        const borderClr  = isAI ? 'rgba(59,130,246,0.3)' : 'transparent';

        // Attachment
        let attachHtml = '';
        if (data.file_path) {
            const fpath = data.file_path.toLowerCase();
            const fname = fpath.split('/').pop();
            const displayName = fname.replace(/^\d{14}_/, '');
            if (/\.(html|css|js|java|py|ipynb|jsx|tsx|ts|cjs|mjs|json)$/.test(fpath)) {
                attachHtml = `<div style="margin-top:8px;padding-top:8px;border-top:1px solid rgba(0,0,0,0.1);"><a href="${data.file_path}" download style="text-decoration:none;display:flex;align-items:center;gap:6px;font-size:0.85rem;color:inherit;font-weight:600;background:rgba(59,130,246,0.1);padding:6px 10px;border-radius:7px;border:1px solid rgba(59,130,246,0.2);"><i class="fa-solid fa-file-code" style="color:#3b82f6;"></i>${escapeHtml(displayName)}<span style="margin-left:auto;font-size:0.75rem;opacity:0.7;">Download</span></a></div>`;
            } else if (/\.(zip|rar|7z|tar|gz)$/.test(fpath)) {
                attachHtml = `<div style="margin-top:8px;padding-top:8px;border-top:1px solid rgba(0,0,0,0.1);"><a href="${data.file_path}" download style="text-decoration:none;display:flex;align-items:center;gap:6px;font-size:0.85rem;color:inherit;font-weight:600;background:rgba(251,191,36,0.12);padding:6px 10px;border-radius:7px;border:1px solid rgba(251,191,36,0.25);"><i class="fa-solid fa-file-zipper" style="color:#fbbf24;"></i>${escapeHtml(displayName)}<span style="margin-left:auto;font-size:0.75rem;opacity:0.7;">Download ZIP</span></a></div>`;
            } else if (/\.pdf$/.test(fpath)) {
                attachHtml = `<div style="margin-top:8px;padding-top:8px;border-top:1px solid rgba(0,0,0,0.1);"><a href="${data.file_path}" target="_blank" style="text-decoration:none;display:flex;align-items:center;gap:6px;font-size:0.85rem;color:inherit;font-weight:600;background:rgba(239,68,68,0.1);padding:6px 10px;border-radius:7px;border:1px solid rgba(239,68,68,0.2);"><i class="fa-solid fa-file-pdf" style="color:#f87171;"></i>${escapeHtml(displayName)}</a></div>`;
            } else if (/\.(png|jpg|jpeg|gif|webp)$/.test(fpath)) {
                attachHtml = `<div style="margin-top:8px;"><img src="${data.file_path}" alt="Image" style="max-width:220px;max-height:180px;border-radius:8px;object-fit:cover;cursor:pointer;" onclick="window.open('${data.file_path}','_blank')"></div>`;
            } else {
                attachHtml = `<div style="margin-top:8px;padding-top:8px;border-top:1px solid rgba(0,0,0,0.1);"><a href="${data.file_path}" target="_blank" style="text-decoration:none;display:flex;align-items:center;gap:6px;font-size:0.85rem;color:inherit;font-weight:600;"><i class="fa-solid fa-paperclip"></i>${escapeHtml(displayName)}</a></div>`;
            }
        }

        msgDiv.innerHTML = `
            ${avatarHtml}
            <div style="display:flex;flex-direction:column;gap:4px;align-items:${isMe ? 'flex-end' : 'flex-start'};">
                <div data-meta-row="1" style="font-size:0.75rem;color:var(--text-secondary);margin:0 4px;display:flex;align-items:center;gap:5px;">
                    ${nameLabel} • <span>${data.created_at}</span>
                </div>
                <div style="background:${bubbleBg};color:${bubbleClr};padding:12px;border-radius:${borderRad};font-weight:500;font-size:0.95rem;border:1px solid ${borderClr};word-break:break-word;">
                    <span class="msg-text">${escapeHtml(data.content)}</span>
                    ${attachHtml}
                </div>
            </div>
        `;

        messagesContainer.appendChild(msgDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function escapeHtml(text) {
        if (!text) return '';
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }


}); // end DOMContentLoaded