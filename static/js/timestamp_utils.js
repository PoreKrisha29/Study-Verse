// Utility function to format timestamps to Indian Standard Time (IST) in 12-hour format
function formatTimestampIST(timestamp) {
    if (!timestamp) return '';

    // Parse the timestamp - the timestamp from server is in UTC
    let utcDate;
    try {
        if (typeof timestamp === 'string') {
            // Handle ISO format: "2024-01-04T03:37:25.123456" or with Z
            if (!timestamp.endsWith('Z') && timestamp.includes('T')) {
                // Add Z to indicate it's UTC
                timestamp = timestamp + 'Z';
            }
            utcDate = new Date(timestamp);
        } else {
            utcDate = new Date(timestamp);
        }

        // Validate the date
        if (isNaN(utcDate.getTime())) {
            console.error('Invalid date:', timestamp);
            return timestamp;
        }
    } catch (e) {
        console.error('Error parsing timestamp:', timestamp, e);
        return timestamp;
    }

    // Convert UTC to IST using toLocaleString with Asia/Kolkata timezone
    const options = {
        timeZone: 'Asia/Kolkata',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    };

    const istTimeString = utcDate.toLocaleString('en-US', options);
    return istTimeString;
}

// Convert UTC timestamp to IST time string (12-hour format with AM/PM)
function toISTTime(timestamp) {
    return formatTimestampIST(timestamp);
}

// Apply IST time formatting to all timestamps on page load
function applyTimestampFormatting() {
    // Format all elements with data-timestamp attribute
    document.querySelectorAll('[data-timestamp]').forEach(element => {
        const timestamp = element.getAttribute('data-timestamp');
        const timeString = formatTimestampIST(timestamp);
        element.textContent = timeString;

        // Add tooltip with full date in IST
        try {
            let utcDate = new Date(timestamp);
            if (!timestamp.endsWith('Z') && timestamp.includes('T')) {
                utcDate = new Date(timestamp + 'Z');
            }

            const dateOptions = {
                timeZone: 'Asia/Kolkata',
                weekday: 'short',
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: 'numeric',
                minute: '2-digit',
                hour12: true
            };

            const fullDateString = utcDate.toLocaleString('en-US', dateOptions);
            element.title = fullDateString;
        } catch (e) {
            // Ignore tooltip errors
        }
    });
}

// Update timestamps every minute to keep time current
function startTimestampUpdater() {
    // Update immediately
    applyTimestampFormatting();

    // Then update every 60 seconds to keep time accurate
    setInterval(applyTimestampFormatting, 60000);
}

// Auto-start when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startTimestampUpdater);
} else {
    startTimestampUpdater();
}
