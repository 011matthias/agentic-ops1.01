/**
 * Review Mode — inline comment system for scope page review.
 *
 * - Floating "Review" button toggles review mode
 * - Each h2 section gets a comment icon when active
 * - Comments stored in localStorage (per page + section)
 * - "Send Feedback" exports all comments as formatted text via mailto:
 * - Saved comments show as inline badges even when review mode is off
 */
(function() {
    var STORAGE_KEY = 'brisken-review-comments';
    var RECIPIENT = 'nicolas.neumann@unpauseai.com';
    var pageName = location.pathname.split('/').filter(Boolean).pop() || 'overview';

    // --- State ---
    var reviewMode = false;

    function getComments() {
        try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); }
        catch(e) { return {}; }
    }

    function saveComments(data) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    }

    function commentKey(sectionId) {
        return pageName + '::' + sectionId;
    }

    // --- Styles ---
    var style = document.createElement('style');
    style.textContent = [
        '.review-toggle{position:fixed;bottom:24px;right:24px;z-index:9000;display:flex;align-items:center;gap:8px;',
        'background:var(--purple,#7c3aed);color:#fff;border:none;border-radius:10px;padding:10px 18px;',
        'font-size:13px;font-weight:600;cursor:pointer;box-shadow:0 4px 16px rgba(124,58,237,.35);transition:all .2s;}',
        '.review-toggle:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(124,58,237,.45);}',
        '.review-toggle.active{background:#059669;}',
        '.review-badge{display:inline-flex;align-items:center;gap:4px;background:var(--purple-light,#ede9fe);',
        'color:var(--purple-dark,#5b21b6);font-size:11px;font-weight:600;padding:2px 8px;border-radius:12px;',
        'margin-left:8px;cursor:pointer;vertical-align:middle;}',
        '[data-theme="dark"] .review-badge{background:var(--purple-bg,#1e1040);color:var(--purple-dark,#c4b5fd);}',
        '.review-comment-btn{display:none;margin-left:8px;background:var(--purple-light,#ede9fe);color:var(--purple-dark,#5b21b6);',
        'border:1px solid color-mix(in srgb,var(--purple,#7c3aed) 30%,var(--border,#e5e7eb));border-radius:6px;',
        'padding:2px 8px;font-size:11px;font-weight:600;cursor:pointer;vertical-align:middle;transition:all .15s;}',
        '.review-comment-btn:hover{background:var(--purple,#7c3aed);color:#fff;}',
        '.review-active .review-comment-btn{display:inline-flex;}',
        '.review-panel{display:none;background:var(--purple-bg,#f5f3ff);border:1px solid color-mix(in srgb,var(--purple,#7c3aed) 20%,var(--border,#e5e7eb));',
        'border-radius:8px;padding:14px;margin:12px 0 20px;position:relative;}',
        '.review-panel.open{display:block;}',
        '.review-panel textarea{width:100%;min-height:80px;border:1px solid var(--border,#e5e7eb);border-radius:6px;',
        'padding:10px;font-size:13px;font-family:inherit;background:var(--bg,#fff);color:var(--text,#1a1a1a);resize:vertical;}',
        '.review-panel textarea:focus{outline:none;border-color:var(--purple,#7c3aed);}',
        '.review-panel-actions{display:flex;gap:8px;margin-top:8px;justify-content:flex-end;}',
        '.review-panel-actions button{padding:6px 14px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;border:none;transition:all .15s;}',
        '.review-save{background:var(--purple,#7c3aed);color:#fff;}',
        '.review-save:hover{opacity:.9;}',
        '.review-cancel{background:var(--surface2,#f1f5f9);color:var(--text2,#6b7280);border:1px solid var(--border,#e5e7eb);}',
        '.review-cancel:hover{background:var(--border,#e5e7eb);}',
        '.review-delete{background:transparent;color:#ef4444;font-size:11px;padding:4px 8px;}',
        '.review-delete:hover{background:#fef2f2;}',
        '.review-saved{background:var(--purple-bg,#f5f3ff);border-left:3px solid var(--purple,#7c3aed);',
        'padding:10px 14px;margin:8px 0 16px;border-radius:0 6px 6px 0;font-size:13px;color:var(--text,#1a1a1a);position:relative;}',
        '.review-saved-label{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;',
        'color:var(--purple-dark,#5b21b6);margin-bottom:4px;}',
        '.review-saved-text{white-space:pre-wrap;line-height:1.5;}',
        '.review-export{position:fixed;bottom:24px;right:170px;z-index:9000;background:var(--blue,#2563eb);color:#fff;',
        'border:none;border-radius:10px;padding:10px 18px;font-size:13px;font-weight:600;cursor:pointer;',
        'box-shadow:0 4px 16px rgba(37,99,235,.35);transition:all .2s;display:none;}',
        '.review-export:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(37,99,235,.45);}',
        '.review-active .review-export{display:flex;}'
    ].join('\n');
    document.head.appendChild(style);

    // --- Build UI ---
    // Toggle button
    var toggleBtn = document.createElement('button');
    toggleBtn.className = 'review-toggle';
    toggleBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg> Review';
    document.body.appendChild(toggleBtn);

    // Export button
    var exportBtn = document.createElement('button');
    exportBtn.className = 'review-export';
    exportBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:6px"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg> Send Feedback';
    document.body.appendChild(exportBtn);

    // --- Section setup ---
    var sections = document.querySelectorAll('h2[id]');
    var panels = {};

    sections.forEach(function(h2) {
        var sectionId = h2.id;
        var key = commentKey(sectionId);

        // Comment button (inline with h2)
        var btn = document.createElement('button');
        btn.className = 'review-comment-btn';
        btn.textContent = '+ Comment';
        btn.onclick = function(e) {
            e.preventDefault();
            var panel = panels[sectionId];
            if (panel.classList.contains('open')) {
                panel.classList.remove('open');
            } else {
                panel.classList.add('open');
                panel.querySelector('textarea').focus();
            }
        };
        h2.appendChild(btn);

        // Comment panel (below h2)
        var panel = document.createElement('div');
        panel.className = 'review-panel';
        panel.innerHTML = [
            '<textarea placeholder="Leave your comment about this section..."></textarea>',
            '<div class="review-panel-actions">',
            '<button class="review-cancel" data-action="cancel">Cancel</button>',
            '<button class="review-save" data-action="save">Save Comment</button>',
            '</div>'
        ].join('');
        h2.parentNode.insertBefore(panel, h2.nextSibling);
        panels[sectionId] = panel;

        // Panel actions
        panel.querySelector('[data-action="cancel"]').onclick = function() {
            panel.classList.remove('open');
        };
        panel.querySelector('[data-action="save"]').onclick = function() {
            var text = panel.querySelector('textarea').value.trim();
            if (!text) return;
            var comments = getComments();
            comments[key] = { text: text, page: pageName, section: sectionId, sectionTitle: h2.textContent.replace('+ Comment', '').trim(), date: new Date().toISOString() };
            saveComments(comments);
            panel.classList.remove('open');
            panel.querySelector('textarea').value = '';
            renderSavedComment(h2, sectionId);
        };
    });

    // --- Render saved comments ---
    function renderSavedComment(h2, sectionId) {
        var key = commentKey(sectionId);
        var comments = getComments();
        var existing = h2.parentNode.querySelector('.review-saved[data-section="' + sectionId + '"]');
        if (existing) existing.remove();

        // Remove old badge
        var oldBadge = h2.querySelector('.review-badge');
        if (oldBadge) oldBadge.remove();

        if (!comments[key]) return;

        // Add badge to h2
        var badge = document.createElement('span');
        badge.className = 'review-badge';
        badge.innerHTML = '<svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg> 1';
        badge.onclick = function() {
            var saved = h2.parentNode.querySelector('.review-saved[data-section="' + sectionId + '"]');
            if (saved) saved.scrollIntoView({ behavior: 'smooth', block: 'center' });
        };
        h2.appendChild(badge);

        // Show saved comment block
        var panel = panels[sectionId];
        var saved = document.createElement('div');
        saved.className = 'review-saved';
        saved.setAttribute('data-section', sectionId);
        saved.innerHTML = [
            '<div class="review-saved-label">Your comment</div>',
            '<div class="review-saved-text">' + escapeHtml(comments[key].text) + '</div>',
            '<button class="review-delete" data-section="' + sectionId + '">Remove</button>'
        ].join('');
        panel.parentNode.insertBefore(saved, panel.nextSibling);

        saved.querySelector('.review-delete').onclick = function() {
            var c = getComments();
            delete c[key];
            saveComments(c);
            renderSavedComment(h2, sectionId);
        };
    }

    function escapeHtml(str) {
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // Initial render of any saved comments
    sections.forEach(function(h2) {
        renderSavedComment(h2, h2.id);
    });

    // --- Toggle review mode ---
    toggleBtn.onclick = function() {
        reviewMode = !reviewMode;
        document.body.classList.toggle('review-active', reviewMode);
        toggleBtn.classList.toggle('active', reviewMode);
        toggleBtn.innerHTML = reviewMode
            ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg> Reviewing'
            : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg> Review';
    };

    // --- Export ---
    exportBtn.onclick = function() {
        var comments = getComments();
        var keys = Object.keys(comments).sort();
        if (!keys.length) {
            alert('No comments to send. Add comments to sections first.');
            return;
        }

        var body = 'Feedback on Brisken Scope Page\n';
        body += 'Date: ' + new Date().toLocaleDateString() + '\n';
        body += '---\n\n';

        keys.forEach(function(key) {
            var c = comments[key];
            body += 'Page: ' + c.page + '\n';
            body += 'Section: ' + c.sectionTitle + '\n';
            body += 'Comment: ' + c.text + '\n\n---\n\n';
        });

        var subject = encodeURIComponent('Scope Page Feedback - Brisken');
        var mailBody = encodeURIComponent(body);
        window.open('mailto:' + RECIPIENT + '?subject=' + subject + '&body=' + mailBody, '_blank');
    };
})();
