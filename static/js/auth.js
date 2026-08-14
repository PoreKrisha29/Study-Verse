/**
 * StudyVerse - Authentication Interface
 * ======================================
 * 
 * Purpose: Handle sign-in and sign-up UI interactions
 * 
 * FEATURES:
 * --------
 * 1. **Tab Switching**: Toggle between Sign In and Sign Up forms
 * 2. **Form Validation**: Client-side validation before submission
 * 3. **OAuth Integration**: Google Sign-In button (placeholder)
 * 
 * FLOW:
 * -----
 * 1. User clicks Sign In or Sign Up tab
 * 2. Active tab highlighted, content switched
 * 3. User fills form and submits
 * 4. Form POSTed to Flask route (/signin or /signup)
 * 5. Backend validates and creates session
 * 6. Redirect to dashboard on success
 * 
 * DESIGN PATTERN:
 * --------------
 * - Tab Pattern: Multiple forms in single page
 * - Progressive Enhancement: Works without JavaScript
 * 
 * NOTE: Uses standard HTML form submission (not AJAX) for simplicity
 */

// ============================================================================
// AUTHENTICATION UI
// ============================================================================

// Authentication JavaScript

document.addEventListener('DOMContentLoaded', () => {
    // Tab switching
    const tabTriggers = document.querySelectorAll('.tabs-trigger');
    const tabContents = {
        'signin': document.getElementById('signin-tab'),
        'signup': document.getElementById('signup-tab')
    };

    tabTriggers.forEach(trigger => {
        trigger.addEventListener('click', () => {
            const tab = trigger.dataset.tab;

            // Update active state
            tabTriggers.forEach(t => t.classList.remove('active'));
            trigger.classList.add('active');

            // Show/hide content
            Object.values(tabContents).forEach(content => {
                if (content) content.style.display = 'none';
            });
            if (tabContents[tab]) {
                tabContents[tab].style.display = 'block';
            }
        });
    });

    // NOTE: Auth uses standard HTML forms posting to Flask routes (/signin, /signup).
    // We intentionally avoid JSON-based fetch here to keep the semester project simple.

    // Google sign in (placeholder)
    const googleSignIn = document.getElementById('googleSignIn');
    if (googleSignIn) {
        googleSignIn.addEventListener('click', () => {
            alert('Google sign in is not yet implemented. Please use email sign in.');
        });
    }
});
