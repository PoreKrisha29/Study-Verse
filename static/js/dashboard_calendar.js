
/* ========================================
   CALENDAR & EVENT LOGIC
   ======================================== */
document.addEventListener('DOMContentLoaded', () => {

    // --- 1. Global State ---
    const today = new Date();
    let currentMonth = today.getMonth(); // 0-11
    let currentYear = today.getFullYear();
    let selectedDate = formatDate(today); // "YYYY-MM-DD"
    let todaysEventsQueue = []; // Local cache for precise timing

    const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

    // Elements
    const monthLabel = document.querySelector('.cal-header span');
    const dayGrid = document.querySelector('.cal-days-grid');
    const prevBtn = document.querySelector('.cal-nav-btn:first-child');
    const nextBtn = document.querySelector('.cal-nav-btn:last-child');
    const timelineInfo = document.querySelector('.timeline-info');
    const eventListContainer = document.getElementById('eventListContainer');
    const initEventBtn = document.querySelector('.btn-init-event');

    // --- 2. Helper Functions ---
    function formatDate(date) {
        // Returns YYYY-MM-DD local
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, '0');
        const d = String(date.getDate()).padStart(2, '0');
        return `${y}-${m}-${d}`;
    }

    function renderCalendar(month, year) {
        // Update header
        monthLabel.textContent = `${monthNames[month]} ${year}`;

        // Clear old days (keep labels)
        const labels = Array.from(dayGrid.children).slice(0, 7);
        dayGrid.innerHTML = '';
        labels.forEach(l => dayGrid.appendChild(l));

        const firstDay = new Date(year, month, 1).getDay(); // 0 (Sun) - 6 (Sat)
        const daysInMonth = new Date(year, month + 1, 0).getDate();

        // Empty slots for previous month
        for (let i = 0; i < firstDay; i++) {
            const empty = document.createElement('div');
            empty.className = 'cal-day empty';
            dayGrid.appendChild(empty);
        }

        // Days
        for (let d = 1; d <= daysInMonth; d++) {
            const cell = document.createElement('div');
            cell.className = 'cal-day';
            cell.textContent = d;

            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
            cell.dataset.date = dateStr;

            if (dateStr === selectedDate) {
                cell.classList.add('active');
            }

            // Check if past date
            const cellDate = new Date(year, month, d);
            const todayZero = new Date();
            todayZero.setHours(0, 0, 0, 0);

            if (cellDate < todayZero) {
                cell.classList.add('past');
                cell.style.opacity = '0.3';
                cell.style.cursor = 'not-allowed';
            } else {
                // Interaction
                cell.addEventListener('click', () => {
                    document.querySelectorAll('.cal-day.active').forEach(el => el.classList.remove('active'));
                    cell.classList.add('active');
                    selectedDate = dateStr;
                    updateTimelineForDate(dateStr);

                    // Always re-enable button when a valid date is clicked
                    if (initEventBtn) {
                        initEventBtn.disabled = false;
                        initEventBtn.style.opacity = '1';
                        initEventBtn.style.cursor = 'pointer';
                    }
                });
            }

            dayGrid.appendChild(cell);
        }
    }

    function updateTimelineForDate(dateStr) {
        // Update header info "Timeline // Jan 25"
        const d = new Date(dateStr);
        const parts = dateStr.split('-');
        const displayDate = new Date(parts[0], parts[1] - 1, parts[2]);

        const dayName = displayDate.toLocaleString('default', { month: 'short', day: 'numeric' });
        timelineInfo.innerHTML = `<i class="fa-regular fa-clock"></i> Timeline // ${dayName}`;

        // Fetch events from API
        eventListContainer.innerHTML = `<div style="padding: 20px; text-align: center;"><i class="fa-solid fa-spinner fa-spin"></i></div>`;

        fetch(`/api/events?date=${dateStr}`)
            .then(r => r.json())
            .then(data => {
                const events = data.events;
                // Update local queue for precise triggering
                if (dateStr === formatDate(new Date())) {
                    const now = new Date();
                    const nowStr = now.getHours().toString().padStart(2, '0') + ":" + now.getMinutes().toString().padStart(2, '0');

                    todaysEventsQueue = events.map(e => {
                        // If current time is past or equal to event time, mark as notified 
                        // so refresh doesn't trigger it.
                        if (e.time <= nowStr) {
                            e.is_notified = true;
                        }
                        return e;
                    }).filter(e => !e.is_notified);
                }
                if (events.length === 0) {
                    eventListContainer.innerHTML = `
                        <div class="event-placeholder" id="eventPlaceholder">
                            <i class="fa-regular fa-clock"></i>
                            <div style="font-size: 0.85rem; font-weight: 600;">Zero Collisions Detected</div>
                            <div style="font-size: 0.7rem;">No scheduled events for today</div>
                        </div>
                    `;
                } else {
                    let html = `<div style="display: flex; flex-direction: column; gap: 10px; width: 100%;">`;
                    events.forEach(e => {
                        html += `
                            <div class="event-item" style="background: rgba(255,255,255,0.05); padding: 12px; border-radius: 12px; border-left: 3px solid var(--accent-green); position: relative; group;">
                                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-right: 60px;">
                                    <div>
                                        <div style="font-weight: 700; color: #fff;">${e.title}</div>
                                        <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 4px;">${e.description}</div>
                                    </div>
                                    <div style="font-size: 0.75rem; color: var(--accent-green); font-weight: 700;">${e.time || ''}</div>
                                </div>
                                <div class="event-actions" style="position: absolute; right: 10px; top: 12px; display: flex; gap: 8px;">
                                    <i class="fa-solid fa-pen-to-square" onclick="editEvent(${JSON.stringify(e).replace(/"/g, '&quot;')})" style="cursor: pointer; color: #888; font-size: 0.85rem; transition: 0.3s;" onmouseover="this.style.color='var(--accent-green)'" onmouseout="this.style.color='#888'"></i>
                                    <i class="fa-solid fa-trash-can" onclick="deleteEvent(${e.id})" style="cursor: pointer; color: #888; font-size: 0.85rem; transition: 0.3s;" onmouseover="this.style.color='#ef4444'" onmouseout="this.style.color='#888'"></i>
                                </div>
                            </div>
                        `;
                    });
                    html += `</div>`;
                    eventListContainer.innerHTML = html;
                }
            });
    }

    function editEvent(event) {
        document.getElementById('editEventId').value = event.id;
        document.getElementById('eventModalTitle').textContent = 'Edit Event';
        document.getElementById('btnSaveEvent').textContent = 'Update Event';

        document.getElementById('eventTitle').value = event.title;
        document.getElementById('eventDescription').value = event.description;
        document.getElementById('eventTime').value = event.time;

        document.getElementById('createEventModal').style.display = 'flex';
    }

    function deleteEvent(eventId) {
        if (!confirm("Are you sure you want to delete this event?")) return;

        fetch(`/api/events/${eventId}`, {
            method: 'DELETE'
        })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'success') {
                    updateTimelineForDate(selectedDate);
                }
            });
    }

    function openCreateEventModal() {
        document.getElementById('editEventId').value = '';
        document.getElementById('eventModalTitle').textContent = 'Initialize Event';
        document.getElementById('btnSaveEvent').textContent = 'Initialize Event';

        document.getElementById('createEventModal').style.display = 'flex';
        document.getElementById('eventTitle').value = '';
        document.getElementById('eventDescription').value = '';

        // Default to current time
        const now = new Date();
        const currentTime = now.getHours().toString().padStart(2, '0') + ":" + now.getMinutes().toString().padStart(2, '0');
        document.getElementById('eventTime').value = currentTime;
    }

    function saveEvent() {
        const title = document.getElementById('eventTitle').value;
        const desc = document.getElementById('eventDescription').value;
        const time = document.getElementById('eventTime').value;
        const editId = document.getElementById('editEventId').value;

        if (!title) {
            alert("Title is required");
            return;
        }

        const url = editId ? `/api/events/${editId}` : '/api/events';
        const method = editId ? 'PUT' : 'POST';

        fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: title,
                description: desc,
                date: selectedDate,
                time: time
            })
        })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'success') {
                    document.getElementById('createEventModal').style.display = 'none';
                    updateTimelineForDate(selectedDate);
                } else {
                    alert("Failed to save event");
                }
            })
            .catch(err => {
                console.error("Save error:", err);
                alert("An error occurred while saving the event.");
            });
    }

    // Assign to window AFTER they are defined (though hoisting handles it anyway)
    window.openCreateEventModal = openCreateEventModal;
    window.saveEvent = saveEvent;
    window.editEvent = editEvent;
    window.deleteEvent = deleteEvent;

    // --- 4. Event Reminder Popup Check ---
    function checkReminders() {
        // 1. Check local queue first for second-level precision (19:02:00)
        const now = new Date();
        const currentTimeStr = now.getHours().toString().padStart(2, '0') + ":" + now.getMinutes().toString().padStart(2, '0');

        const triggerableIndex = todaysEventsQueue.findIndex(e => e.time === currentTimeStr && !e.is_notified);

        if (triggerableIndex !== -1) {
            const event = todaysEventsQueue[triggerableIndex];
            event.is_notified = true; // Mark locally so it doesn't fire multiple times in same minute
            showEventPopup(event);
            return; // Exit to avoid double fire if server check also returns it
        }

        // 2. Fallback: Periodic server check for missed events or sync
        // We only do the server hit every 10 iterations to save bandwidth
        if (window._reminderTick === undefined) window._reminderTick = 0;
        window._reminderTick++;

        if (window._reminderTick % 10 === 0) {
            fetch('/api/events/check-warnings')
                .then(r => r.json())
                .then(data => {
                    if (data.has_warning && data.event) {
                        // Ensure we haven't already shown this locally
                        if (!document.getElementById('event-popup-' + data.event.id)) {
                            showEventPopup(data.event);
                        }
                    }
                });
        }
    }

    function showEventPopup(event) {
        // Create custom modal matching system UI
        const modalId = 'event-popup-' + event.id;
        if (document.getElementById(modalId)) return; // already showing

        // Optional: Play a soft notification sound
        try {
            const audio = new Audio('https://assets.mixkit.co/active_storage/sfx/2857/2857-preview.mp3');
            audio.volume = 0.5;
            audio.play().catch(e => console.log("Audio play blocked"));
        } catch (e) { }

        const modal = document.createElement('div');
        modal.id = modalId;
        modal.style.position = 'fixed';
        modal.style.top = '30px';
        modal.style.left = '0';
        modal.style.right = '0';
        modal.style.zIndex = '100000';
        modal.style.display = 'flex';
        modal.style.justifyContent = 'center';
        modal.style.pointerEvents = 'none';

        modal.innerHTML = `
            <div class="alert shadow-lg d-flex align-items-center" role="alert" 
                 style="width: 95%; max-width: 650px; border-radius: 16px; padding: 18px 24px; pointer-events: auto; animation: slideDown 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275); background-color: #ffffff !important; border: 2px solid #198754 !important; border-left: 10px solid #198754 !important; color: #333 !important;">
                
                <!-- Fixed Logo Section -->
                <div class="d-flex align-items-center justify-content-center me-3 flex-shrink-0" 
                     style="width: 45px; height: 45px; background-color: #198754 !important; border-radius: 50%; box-shadow: 0 4px 10px rgba(25, 135, 84, 0.3);">
                    <i class="fa-solid fa-graduation-cap" style="font-size: 1.4rem; color: #ffffff !important;"></i>
                </div>
                
                <!-- Content Section -->
                <div class="flex-grow-1 overflow-hidden" style="margin-right: 15px;">
                    <div style="font-size: 0.85rem; font-weight: 800; color: #198754 !important; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 2px;">
                        Event Arrived
                    </div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #000000 !important; line-height: 1.2;" class="text-truncate">
                        ${event.title}
                    </div>
                    <div style="font-size: 0.95rem; color: #555555 !important; margin-top: 4px; font-weight: 500;" class="text-truncate">
                        ${event.description || "Time to start your scheduled activity!"}
                    </div>
                </div>
                
                <!-- Action Section -->
                <div class="d-flex align-items-center gap-2">
                    <button type="button" id="btn-dismiss-${event.id}" class="btn" 
                            style="background-color: #f8f9fa !important; border: 1px solid #dee2e6 !important; color: #333 !important; font-weight: 600; padding: 8px 16px; border-radius: 10px; font-size: 0.9rem; transition: all 0.2s;">
                        Dismiss
                    </button>
                    <button type="button" id="btn-close-icon-${event.id}" class="btn-close" aria-label="Close" style="filter: brightness(0); font-size: 0.8rem;"></button>
                </div>
                
                <style>
                    @keyframes slideDown {
                        from { transform: translateY(-120px); opacity: 0; }
                        to { transform: translateY(0); opacity: 1; }
                    }
                    #btn-dismiss-${event.id}:hover {
                        background-color: #e9ecef !important;
                        transform: translateY(-1px);
                    }
                </style>
            </div>
        `;

        document.body.appendChild(modal);

        // Attempt Browser Notification
        if ("Notification" in window && Notification.permission === "granted") {
            new Notification(`🔔 ${event.title}`, {
                body: event.description || "Event starting now!",
                icon: "/static/img/logo.png"
            });
        }

        // Trigger confetti
        if (window.triggerConfetti) {
            window.triggerConfetti();
        }

        // Dismiss Logic
        const dismissHandler = () => {
            fetch(`/api/events/${event.id}/dismiss`, { method: 'POST' })
                .then(() => {
                    modal.style.opacity = '0';
                    modal.style.transform = 'translateY(-20px)';
                    modal.style.transition = 'all 0.3s ease';
                    setTimeout(() => modal.remove(), 300);
                })
                .catch(() => modal.remove());
        };

        document.getElementById(`btn-dismiss-${event.id}`).addEventListener('click', dismissHandler);
        document.getElementById(`btn-close-icon-${event.id}`).addEventListener('click', dismissHandler);

        // Auto-dismiss after 45 seconds
        setTimeout(() => {
            if (document.getElementById(modalId)) {
                modal.style.opacity = '0';
                modal.style.transform = 'translateY(-20px)';
                modal.style.transition = 'all 0.5s ease';
                setTimeout(() => modal.remove(), 500);
            }
        }, 45000);
    }

    // --- 5. Initializers ---
    renderCalendar(currentMonth, currentYear);
    updateTimelineForDate(selectedDate); // Load today's events initially
    // checkReminders(); // Removed: No alert on refresh, wait for scheduled time transition

    // Poll for reminders every 1 second for precision (19:02:00)
    setInterval(checkReminders, 1000);

    // Listeners
    prevBtn.addEventListener('click', () => {
        currentMonth--;
        if (currentMonth < 0) { currentMonth = 11; currentYear--; }
        renderCalendar(currentMonth, currentYear);
    });

    nextBtn.addEventListener('click', () => {
        currentMonth++;
        if (currentMonth > 11) { currentMonth = 0; currentYear++; }
        renderCalendar(currentMonth, currentYear);
    });

    // Event listener removed as we use onclick="openCreateEventModal()" in HTML to avoid scope issues.
    // initEventBtn.addEventListener('click', openCreateEventModal);
});
