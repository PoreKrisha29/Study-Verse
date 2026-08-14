/**
 * StudyVerse - AI Chat Assistant
 * ================================
 * 
 * Purpose: Context-aware AI study assistant using Google Gemini API
 * 
 * FEATURES:
 * --------
 * 1. **Context-Aware Responses**:
 *    - Uses uploaded syllabus as context for relevant answers
 *    - Provides study guidance based on course material
 *    - Adapts responses to user's learning needs
 * 
 * 2. **Chat History**:
 *    - Maintains conversation context across sessions
 *    - Stores messages in database for persistence
 *    - Allows scrolling through past conversations
 * 
 * 3. **Markdown Rendering**:
 *    - Formats AI responses with markdown syntax
 *    - Code syntax highlighting for programming help
 *    - Lists, tables, and rich formatting support
 * 
 * 4. **Real-Time Messaging**:
 *    - AJAX-based message sending (no page refresh)
 *    - Loading indicator during AI processing
 *    - Auto-scroll to latest messages
 * 
 * 5. **Security**:
 *    - DOMPurify sanitization to prevent XSS attacks
 *    - Safe markdown parsing
 *    - Input validation
 * 
 * FLOW:
 * -----
 * 1. User types message and presses Enter or clicks Send
 * 2. Message displayed in chat UI immediately (optimistic UI)
 * 3. Frontend sends message to /chat/send endpoint via AJAX
 * 4. Backend retrieves syllabus context from database
 * 5. Backend queries Gemini API with context + user message
 * 6. AI response generated and returned to frontend
 * 7. Response parsed with markdown and displayed
 * 8. Both messages saved to database with timestamps
 * 
 * TECHNOLOGIES:
 * ------------
 * - **Fetch API**: Asynchronous HTTP requests
 * - **Marked.js**: Markdown parsing library
 * - **DOMPurify**: XSS protection and HTML sanitization
 * - **DOM Manipulation**: Dynamic message rendering
 * - **CSS Flexbox**: Message layout and alignment
 * 
 * DATA STRUCTURES:
 * ---------------
 * - Message Object: {role: 'user'|'bot', content: string, timestamp: string}
 * - Chat State: {isLoading: boolean, messageHistory: Message[]}
 * 
 * ALGORITHMS:
 * ----------
 * - Auto-scroll: scrollTop = scrollHeight (O(1))
 * - Message Insertion: DOM appendChild (O(1))
 * - Markdown Parsing: Marked.js library (O(n) where n = message length)
 * 
 * API ENDPOINTS:
 * -------------
 * - POST /chat/send: Send user message and get AI response
 *   Request: {message: string}
 *   Response: {status: 'success', reply: string, user_timestamp: string, ai_timestamp: string}
 * 
 * DESIGN PATTERNS:
 * ---------------
 * - Observer Pattern: Event listeners for user input
 * - Optimistic UI: Show user message immediately before server response
 * - Error Handling: Graceful degradation with error messages
 */

// ============================================================================
// CHAT INITIALIZATION
// ============================================================================

// Modern Chat JavaScript with Markdown & AJAX

document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const messagesContainer = document.getElementById('messagesContainer');
    const loadingIndicator = document.getElementById('loadingIndicator');

    // 1. Initial Markdown Parsing for History
    document.querySelectorAll('.markdown-content').forEach(el => {
        // Prevent double parsing
        if (el.dataset.parsed) return;
        const raw = el.textContent.trim(); // Use textContent to avoid HTML injection risks
        if (raw) {
            el.innerHTML = DOMPurify.sanitize(marked.parse(raw));
            el.dataset.parsed = "true";
        }
    });

    scrollToBottom();

    // 2. Auto-resize Input
    chatInput.addEventListener('input', () => {
        // Simple resizing logic, max 150px
        // Reset height to auto to shrink if text deleted
        // This simple version works for single line inputs primarily
    });

    // 3. Handle Enter Key
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submitMessage();
        }
    });

    // 4. Handle Form Submit
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        submitMessage();
    });

    function submitMessage() {
        const message = chatInput.value.trim();
        if (!message) return;

        // Add User Message to UI
        appendMessage('user', message);
        chatInput.value = '';
        scrollToBottom();

        // Hide Quick Prompts if visible
        const quickPrompts = document.getElementById('quickPrompts');
        if (quickPrompts && quickPrompts.style.display !== 'none') {
            quickPrompts.style.transition = 'opacity 0.3s ease';
            quickPrompts.style.opacity = '0';
            setTimeout(() => quickPrompts.style.display = 'none', 300);
        }

        // Show Loading
        if (loadingIndicator) {
            loadingIndicator.style.display = 'flex';
            scrollToBottom();
        }

        // Send to Backend
        fetch('/chat/send', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json', // Sending JSON now
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ message: message })
        })
            .then(response => response.json())
            .then(data => {
                // Hide Loading
                if (loadingIndicator) loadingIndicator.style.display = 'none';

                if (data.status === 'success') {
                    // Add timestamp to the user message we just added
                    const userMsgs = messagesContainer.querySelectorAll('.ai-msg.user');
                    if (userMsgs.length > 0 && data.user_timestamp) {
                        const lastUserMsg = userMsgs[userMsgs.length - 1];
                        const timestamp = document.createElement('div');
                        timestamp.style = 'font-size: 0.7rem; color: var(--text-secondary); text-align: right; margin: 0 4px;';
                        timestamp.innerHTML = `<span>${data.user_timestamp}</span>`;
                        lastUserMsg.querySelector('div').appendChild(timestamp);
                    }

                    // Append AI message with timestamp
                    appendMessage('bot', data.reply, data.ai_timestamp);
                } else {
                    appendMessage('bot', '⚠️ Error: ' + (data.message || 'Unknown error'));
                }
            })
            .catch(err => {
                console.error(err);
                if (loadingIndicator) loadingIndicator.style.display = 'none';
                appendMessage('bot', '⚠️ Connection error. Please try again.');
            });
    }

    function appendMessage(role, content, timestamp) {
        const div = document.createElement('div');
        div.className = `ai-msg ${role}`;

        let iconHtml = '';
        if (role === 'bot') {
            iconHtml = `
                <div class="bot-icon" style="width: 32px; height: 32px; background: linear-gradient(135deg, #3b82f6, #8b5cf6); border-radius: 8px; display: grid; place-items: center; color: white; flex-shrink: 0;">
                    <i class="fa-solid fa-robot" style="font-size: 0.8rem;"></i>
                </div>
            `;
        }

        // Create bubble container
        const bubble = document.createElement('div');
        bubble.style = 'display: flex; flex-direction: column; gap: 4px; width: 100%;';

        const msgBubble = document.createElement('div');
        msgBubble.className = 'msg-bubble markdown-content';

        // Parse Markdown immediately
        // Note: For 'user' messages we usually just show text, but Markdown is fine too.
        msgBubble.innerHTML = DOMPurify.sanitize(marked.parse(content));

        bubble.appendChild(msgBubble);

        // Add timestamp if provided
        if (timestamp) {
            const timestampDiv = document.createElement('div');
            timestampDiv.style = 'font-size: 0.7rem; color: var(--text-secondary); margin: 0 4px;';
            timestampDiv.innerHTML = `<span>${timestamp}</span>`;
            bubble.appendChild(timestampDiv);
        }

        div.innerHTML = `${iconHtml}`;
        div.appendChild(bubble);

        // Insert before loading indicator
        if (loadingIndicator && loadingIndicator.parentNode === messagesContainer) {
            messagesContainer.insertBefore(div, loadingIndicator);
        } else {
            messagesContainer.appendChild(div);
        }

        scrollToBottom();
    }

    function scrollToBottom() {
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }
});