/**
 * StudyVerse – Progressive Syllabus Upload
 * ==========================================
 * Uses Server-Sent Events so each chapter appears as soon as
 * the AI generates it — just like the Topic Resolver.
 */

document.addEventListener('DOMContentLoaded', () => {
    const uploadPdf = document.getElementById('uploadPdf');
    const pdfInput  = document.getElementById('pdfInput');
    const form      = document.getElementById('syllabusUploadForm');

    // Trigger file picker on button click
    if (uploadPdf) {
        uploadPdf.addEventListener('click', () => pdfInput && pdfInput.click());
    }

    if (pdfInput) {
        pdfInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file || file.type !== 'application/pdf') return;
            await startProgressiveUpload(file, form);
        });
    }
});

// ─────────────────────────────────────────────────────────────
//  Progressive upload + live render
// ─────────────────────────────────────────────────────────────
async function startProgressiveUpload(file, form) {
    // 1. Show the overlay
    const overlay = document.getElementById('upload-progress-overlay');
    if (overlay) overlay.style.display = 'flex';

    setUploadStatus('📄 Reading your PDF…', 'processing');
    clearChapterList();

    // 2. Build multipart form
    const fd = new FormData();
    fd.append('pdf', file);
    const targetDate = form ? form.querySelector('[name="target_date"]') : null;
    if (targetDate && targetDate.value) fd.append('target_date', targetDate.value);

    // 3. Fetch with SSE-style reading
    let response;
    try {
        response = await fetch('/api/syllabus/upload-stream', {
            method:      'POST',
            body:        fd,
            credentials: 'same-origin',
        });
    } catch (err) {
        setUploadStatus('❌ Network error. Please try again.', 'error');
        return;
    }

    if (!response.ok) {
        setUploadStatus('❌ Server error. Please try again.', 'error');
        return;
    }

    // 4. Read the SSE stream
    const reader  = response.body.getReader();
    const decoder = new TextDecoder();
    let   buffer  = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Split on SSE double-newline boundary
        const parts = buffer.split('\n\n');
        buffer = parts.pop(); // keep incomplete tail

        for (const part of parts) {
            const line = part.trim();
            if (!line.startsWith('data:')) continue;

            let evt;
            try { evt = JSON.parse(line.slice(5).trim()); }
            catch (_) { continue; }

            handleEvent(evt);
        }
    }
}

// ─────────────────────────────────────────────────────────────
//  Event handlers
// ─────────────────────────────────────────────────────────────
function handleEvent(evt) {
    switch (evt.type) {
        case 'pages':
            setUploadStatus(
                evt.count
                    ? `📄 ${evt.count} pages detected — uploading to AI…`
                    : '📄 PDF loaded — uploading to AI…',
                'processing'
            );
            break;

        case 'status':
            setUploadStatus('🤖 ' + evt.msg, 'processing');
            break;

        case 'total':
            setUploadStatus(
                `✨ AI found ${evt.chapters} chapter${evt.chapters !== 1 ? 's' : ''}. Saving…`,
                'processing'
            );
            updateProgressBar(0, evt.chapters);
            break;

        case 'chapter':
            addChapterCard(evt);
            updateProgressBar(evt.index, evt.total);
            setUploadStatus(
                `⚡ Chapter ${evt.index}/${evt.total}: ${evt.title}`,
                'processing'
            );
            break;

        case 'done':
            setUploadStatus(
                `🎉 Done! Created ${evt.created} task${evt.created !== 1 ? 's' : ''}.`,
                'success'
            );
            updateProgressBar(1, 1);
            // Redirect after a short pause so user sees the animation
            setTimeout(() => {
                window.location.href = `/syllabus/${evt.doc_id}`;
            }, 2000);
            break;

        case 'error':
            setUploadStatus('❌ ' + evt.msg, 'error');
            break;
    }
}

// ─────────────────────────────────────────────────────────────
//  UI helpers
// ─────────────────────────────────────────────────────────────
function setUploadStatus(msg, state) {
    const el = document.getElementById('upload-status-text');
    if (!el) return;
    el.textContent = msg;
    el.className   = 'upload-status-text ' + (state || '');
}

function updateProgressBar(current, total) {
    const bar = document.getElementById('upload-progress-fill');
    if (!bar) return;
    const pct = total > 0 ? Math.round((current / total) * 100) : 0;
    bar.style.width = pct + '%';

    const label = document.getElementById('upload-progress-pct');
    if (label) label.textContent = pct + '%';
}

function clearChapterList() {
    const list = document.getElementById('chapter-stream-list');
    if (list) list.innerHTML = '';
}

function addChapterCard(evt) {
    const list = document.getElementById('chapter-stream-list');
    if (!list) return;

    const card = document.createElement('div');
    card.className = 'stream-chapter-card';
    card.innerHTML = `
        <div class="stream-chapter-header">
            <span class="stream-chapter-icon">📖</span>
            <span class="stream-chapter-title">${escapeHtml(evt.title)}</span>
            <span class="stream-chapter-count">${evt.subtasks.length} topics</span>
        </div>
        ${evt.subtasks.length ? `
        <ul class="stream-subtask-list">
            ${evt.subtasks.map(s => `<li>${escapeHtml(s)}</li>`).join('')}
        </ul>` : ''}
    `;
    list.appendChild(card);

    // Trigger animation on next frame
    requestAnimationFrame(() => card.classList.add('visible'));
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}