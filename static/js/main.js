/**
 * StudyVerse - Main JavaScript File
 * ==================================
 * 
 * Purpose: Core UI functionality and utility functions used across all pages
 * 
 * Features:
 * 1. Sidebar Navigation: Toggle and active state management
 * 2. Toast Notifications: User feedback system
 * 3. Utility Functions: Time/date formatting
 * 4. API Helper: Centralized fetch wrapper with error handling
 * 
 * Design Pattern: Module Pattern
 * - Encapsulates functionality
 * - Exposes public API via window.StudyVerse
 * - Prevents global namespace pollution
 */

// ============================================================================
// DOM READY INITIALIZATION
// ============================================================================

// Wait for DOM to be fully loaded before attaching event listeners
document.addEventListener('DOMContentLoaded', () => {
    // Get sidebar elements
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarLogo = document.getElementById('sidebarLogo');

    // Sidebar Toggle Functionality
    // Allows users to collapse/expand sidebar for more screen space
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');  // Toggle CSS class for animation
        });
    }

    // ========================================================================
    // ACTIVE NAVIGATION HIGHLIGHTING
    // ========================================================================

    // Highlight current page in navigation menu
    // Helps users understand which page they're on
    const currentPath = window.location.pathname;
    const navItems = document.querySelectorAll('.nav-item');

    navItems.forEach(item => {
        const href = item.getAttribute('href');
        // Check if current path matches nav item href
        // Special case: '/' and '/dashboard' are treated as the same
        if (currentPath === href || (href === '/dashboard' && currentPath === '/')) {
            item.classList.add('active');  // Add active class for styling
        }
    });
});

// ============================================================================
// TOAST NOTIFICATION SYSTEM
// ============================================================================

/**
 * Display a toast notification to the user
 * 
 * Purpose: Provide non-intrusive feedback for user actions
 * 
 * Flow:
 * 1. Create toast element dynamically
 * 2. Add to DOM with slide-in animation
 * 3. Auto-remove after 3 seconds with slide-out animation
 * 
 * @param {string} message - The message to display
 * @param {string} type - Toast type: 'success', 'error', 'info', 'warning'
 * 
 * Usage:
 *   showToast('Task completed!', 'success');
 *   showToast('An error occurred', 'error');
 */
function showToast(message, type = 'success') {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;  // CSS classes for styling
    toast.textContent = message;
    document.body.appendChild(toast);  // Add to DOM

    // Auto-remove after 3 seconds
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease-out reverse';  // Slide out animation
        setTimeout(() => toast.remove(), 300);  // Remove from DOM after animation
    }, 3000);
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Format seconds into MM:SS format
 * 
 * Used by: Pomodoro timer, Battle countdown
 * 
 * @param {number} seconds - Total seconds
 * @returns {string} Formatted time string (e.g., "25:00")
 * 
 * Algorithm: Simple division and modulo
 * - Minutes = floor(seconds / 60)
 * - Seconds = seconds % 60
 * - Pad with zeros for consistent display
 */
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Format date string into human-readable format
 * 
 * Used by: Calendar, Task list, Event display
 * 
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date (e.g., "Mon, Jan 15")
 * 
 * Uses JavaScript Intl.DateTimeFormat for localization
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        weekday: 'short',  // Mon, Tue, etc.
        month: 'short',    // Jan, Feb, etc.
        day: 'numeric'     // 1, 2, 3, etc.
    });
}

// ============================================================================
// API HELPER FUNCTIONS
// ============================================================================

/**
 * Centralized API call wrapper with error handling
 * 
 * Purpose: Standardize all API requests across the application
 * 
 * Features:
 * 1. Automatic JSON content-type header
 * 2. Unified error handling
 * 3. Automatic toast notifications for errors
 * 4. Promise-based async/await support
 * 
 * @param {string} url - API endpoint URL
 * @param {object} options - Fetch options (method, body, headers, etc.)
 * @returns {Promise} Resolves with response data, rejects with error
 * 
 * Usage:
 *   const data = await apiCall('/api/tasks', {
 *     method: 'POST',
 *     body: JSON.stringify({ title: 'New Task' })
 *   });
 */
async function apiCall(url, options = {}) {
    try {
        // Make fetch request with default headers
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',  // Default to JSON
                ...options.headers  // Allow override
            }
        });

        // Parse JSON response
        const data = await response.json();

        // Check for HTTP errors
        if (!response.ok) {
            throw new Error(data.error || 'An error occurred');
        }

        return data;
    } catch (error) {
        // Log error for debugging
        console.error('API call error:', error);
        // Show user-friendly error message
        showToast(error.message, 'error');
        throw error;  // Re-throw for caller to handle
    }
}

// ============================================================================
// PUBLIC API EXPORT
// ============================================================================

/**
 * Export utility functions for use in other scripts
 * 
 * Design Pattern: Namespace Pattern
 * - All utilities under window.StudyVerse
 * - Prevents naming conflicts
 * - Easy to use across multiple files
 * 
 * Usage in other files:
 *   StudyVerse.showToast('Success!', 'success');
 *   const formatted = StudyVerse.formatTime(125);
 */
// ============================================================================
// BROWSER NOTIFICATION SYSTEM
// ============================================================================

/**
 * Request notification permission once (after first user interaction)
 * Works in all modern browsers. Silently skips if already granted/denied.
 */
function requestNotifPermission() {
    if (!('Notification' in window)) return; // Browser doesn't support it
    if (Notification.permission === 'default') {
        // Ask after a small delay so it doesn't feel intrusive on load
        setTimeout(() => {
            Notification.requestPermission();
        }, 5000);
    }
}

/**
 * Show a browser notification
 * Falls back gracefully if permission not granted
 *
 * @param {string} title   - Notification title
 * @param {string} body    - Notification body text
 * @param {string} icon    - Icon URL (optional, defaults to StudyVerse favicon)
 * @param {string} tag     - Unique tag to prevent duplicate notifications
 * @param {string} url     - URL to open when notification is clicked (optional)
 */
function sendNotification(title, body, icon = '/static/img/favicon.png', tag = 'studyverse', url = null) {
    if (!('Notification' in window)) return;
    if (Notification.permission !== 'granted') return;

    const notif = new Notification(title, {
        body,
        icon,
        tag,           // Same tag = replaces previous notification (no spam)
        badge: '/static/img/favicon.png',
        silent: false
    });

    // Open URL on click if provided
    if (url) {
        notif.onclick = () => {
            window.focus();
            window.location.href = url;
            notif.close();
        };
    }

    // Auto close after 6 seconds
    setTimeout(() => notif.close(), 6000);
}

// Request permission after first interaction (click/keypress anywhere)
function _requestOnFirstInteraction() {
    const handler = () => {
        requestNotifPermission();
        document.removeEventListener('click', handler);
        document.removeEventListener('keydown', handler);
    };
    document.addEventListener('click', handler);
    document.addEventListener('keydown', handler);
}
_requestOnFirstInteraction();

// ============================================================================
// PUBLIC API EXPORT
// ============================================================================

window.StudyVerse = {
    showToast,
    formatTime,
    formatDate,
    apiCall,
    notify: sendNotification
};
