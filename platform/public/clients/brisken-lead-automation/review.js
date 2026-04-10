/**
 * Review Mode v2 — inline comment system for scope page review.
 *
 * Features:
 * - Always-visible comment icons on each section (no toggle required)
 * - Multiple comments per section
 * - Text selection commenting (highlight text → comment on that quote)
 * - Timestamps and edit/delete on saved comments
 * - Cross-page comment summary panel
 * - Export: copy to clipboard + mailto
 * - First-visit onboarding pulse
 */
(function() {
    var STORAGE_KEY = 'brisken-review-comments';
    var RECIPIENT = 'nicolas.neumann@unpauseai.com';
    var pageName = location.pathname.split('/').filter(Boolean).pop() || 'overview';
    var PAGE_LABELS = { 'brisken-lead-automation': 'Overview', 'solution': 'Solution', 'timeline': 'Timeline', 'faq': 'FAQ' };
    var pageLabel = PAGE_LABELS[pageName] || pageName;

    // --- Storage ---
    function getAll() {
        try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); }
        catch(e) { return []; }
    }
    function saveAll(arr) { localStorage.setItem(STORAGE_KEY, JSON.stringify(arr)); }
    function getForSection(sectionId) {
        return getAll().filter(function(c) { return c.page === pageName && c.section === sectionId; });
    }
    function addComment(sectionId, sectionTitle, text, quote) {
        var all = getAll();
        all.push({ id: Date.now() + '-' + Math.random().toString(36).substr(2, 5), page: pageName, pageLabel: pageLabel, section: sectionId, sectionTitle: sectionTitle, text: text, quote: quote || null, date: new Date().toISOString() });
        saveAll(all);
    }
    function updateComment(id, newText) {
        var all = getAll();
        for (var i = 0; i < all.length; i++) { if (all[i].id === id) { all[i].text = newText; all[i].editedAt = new Date().toISOString(); break; } }
        saveAll(all);
    }
    function deleteComment(id) {
        saveAll(getAll().filter(function(c) { return c.id !== id; }));
    }

    // --- Helpers ---
    function esc(str) { var d = document.createElement('div'); d.textContent = str; return d.innerHTML; }
    function fmtDate(iso) {
        var d = new Date(iso);
        return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) + ', ' + d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
    }
    function totalCount() { return getAll().length; }

    // --- Styles ---
    var css = document.createElement('style');
    css.textContent = '\
/* Review button */\
.rv-fab{position:fixed;bottom:24px;right:24px;z-index:9000;display:flex;align-items:center;gap:8px;\
background:var(--purple,#7c3aed);color:#fff;border:none;border-radius:12px;padding:10px 18px;\
font-size:13px;font-weight:600;cursor:pointer;box-shadow:0 4px 16px rgba(124,58,237,.35);transition:all .2s;}\
.rv-fab:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(124,58,237,.45);}\
.rv-fab .rv-count{background:rgba(255,255,255,.25);padding:1px 7px;border-radius:10px;font-size:11px;margin-left:2px;}\
@keyframes rv-pulse{0%,100%{box-shadow:0 4px 16px rgba(124,58,237,.35)}50%{box-shadow:0 4px 24px rgba(124,58,237,.7)}}\
.rv-fab.rv-pulse{animation:rv-pulse 2s ease-in-out 3;}\
/* Section comment icon */\
.rv-add{display:inline-flex;align-items:center;gap:4px;margin-left:10px;background:var(--purple-light,#ede9fe);\
color:var(--purple-dark,#5b21b6);border:1px solid color-mix(in srgb,var(--purple,#7c3aed) 20%,var(--border,#e5e7eb));\
border-radius:6px;padding:3px 9px;font-size:11px;font-weight:600;cursor:pointer;vertical-align:middle;transition:all .15s;opacity:.6;}\
.rv-add:hover{opacity:1;background:var(--purple,#7c3aed);color:#fff;}\
[data-theme="dark"] .rv-add{background:var(--purple-bg,#1e1040);color:var(--purple-dark,#c4b5fd);}\
/* Badge */\
.rv-badge{display:inline-flex;align-items:center;gap:3px;background:var(--purple,#7c3aed);color:#fff;\
font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px;margin-left:6px;vertical-align:middle;cursor:pointer;}\
/* Comment panel */\
.rv-panel{display:none;background:var(--purple-bg,#f5f3ff);border:1px solid color-mix(in srgb,var(--purple,#7c3aed) 15%,var(--border,#e5e7eb));\
border-radius:10px;padding:16px;margin:12px 0 20px;}\
.rv-panel.open{display:block;}\
.rv-panel-quote{font-size:12px;color:var(--purple-dark,#5b21b6);border-left:3px solid var(--purple,#7c3aed);\
padding:6px 12px;margin:0 0 10px;background:color-mix(in srgb,var(--purple,#7c3aed) 5%,var(--bg,#fff));border-radius:0 6px 6px 0;font-style:italic;}\
.rv-panel textarea{width:100%;min-height:70px;border:1px solid var(--border,#e5e7eb);border-radius:8px;\
padding:10px 12px;font-size:13px;font-family:inherit;background:var(--bg,#fff);color:var(--text,#1a1a1a);resize:vertical;}\
.rv-panel textarea:focus{outline:none;border-color:var(--purple,#7c3aed);box-shadow:0 0 0 3px rgba(124,58,237,.1);}\
.rv-panel-actions{display:flex;gap:8px;margin-top:10px;justify-content:flex-end;}\
.rv-panel-actions button{padding:7px 16px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;border:none;transition:all .15s;}\
.rv-btn-save{background:var(--purple,#7c3aed);color:#fff;}\
.rv-btn-save:hover{opacity:.9;}\
.rv-btn-cancel{background:var(--surface2,#f1f5f9);color:var(--text2,#6b7280);border:1px solid var(--border,#e5e7eb);}\
.rv-btn-cancel:hover{background:var(--border,#e5e7eb);}\
/* Saved comments */\
.rv-comments{margin:8px 0 20px;}\
.rv-comment{background:var(--purple-bg,#f5f3ff);border-left:3px solid var(--purple,#7c3aed);\
padding:12px 14px;margin:6px 0;border-radius:0 8px 8px 0;position:relative;}\
.rv-comment-header{display:flex;align-items:center;gap:8px;margin-bottom:6px;}\
.rv-comment-date{font-size:10px;color:var(--text2,#6b7280);}\
.rv-comment-edited{font-size:10px;color:var(--text2,#6b7280);font-style:italic;}\
.rv-comment-quote{font-size:12px;color:var(--purple-dark,#5b21b6);border-left:2px solid color-mix(in srgb,var(--purple,#7c3aed) 40%,var(--border,#e5e7eb));\
padding:4px 10px;margin:0 0 8px;font-style:italic;background:color-mix(in srgb,var(--purple,#7c3aed) 3%,var(--bg,#fff));border-radius:0 4px 4px 0;}\
.rv-comment-text{font-size:13px;color:var(--text,#1a1a1a);white-space:pre-wrap;line-height:1.55;}\
.rv-comment-actions{display:flex;gap:4px;margin-top:8px;}\
.rv-comment-actions button{background:transparent;border:none;font-size:11px;font-weight:600;cursor:pointer;padding:3px 8px;border-radius:4px;transition:all .15s;}\
.rv-comment-actions .rv-act-edit{color:var(--purple-dark,#5b21b6);}\
.rv-comment-actions .rv-act-edit:hover{background:var(--purple-light,#ede9fe);}\
.rv-comment-actions .rv-act-del{color:#ef4444;}\
.rv-comment-actions .rv-act-del:hover{background:#fef2f2;}\
/* Text selection popup */\
.rv-sel-popup{position:absolute;z-index:9500;background:var(--purple,#7c3aed);color:#fff;border:none;border-radius:8px;\
padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;box-shadow:0 4px 12px rgba(124,58,237,.4);\
display:none;white-space:nowrap;transition:opacity .15s;}\
.rv-sel-popup:hover{background:var(--purple-dark,#5b21b6);}\
.rv-sel-popup::after{content:"";position:absolute;bottom:-6px;left:50%;transform:translateX(-50%);\
border-left:6px solid transparent;border-right:6px solid transparent;border-top:6px solid var(--purple,#7c3aed);}\
/* Summary panel */\
.rv-overlay{position:fixed;inset:0;z-index:9800;background:rgba(0,0,0,.4);display:none;transition:opacity .2s;}\
.rv-overlay.open{display:flex;align-items:center;justify-content:center;}\
.rv-summary{background:var(--bg,#fff);border-radius:16px;width:90%;max-width:620px;max-height:80vh;overflow-y:auto;\
box-shadow:0 20px 60px rgba(0,0,0,.2);padding:28px;position:relative;}\
.rv-summary-title{font-size:18px;font-weight:700;color:var(--text-strong,#111827);margin-bottom:4px;}\
.rv-summary-sub{font-size:13px;color:var(--text2,#6b7280);margin-bottom:20px;}\
.rv-summary-page{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;\
color:var(--purple-dark,#5b21b6);margin:16px 0 8px;padding-bottom:4px;border-bottom:1px solid var(--border,#e5e7eb);}\
.rv-summary-item{padding:10px 0;border-bottom:1px solid color-mix(in srgb,var(--border,#e5e7eb) 50%,transparent);}\
.rv-summary-item:last-child{border-bottom:none;}\
.rv-summary-section{font-size:12px;font-weight:600;color:var(--text-strong,#111827);}\
.rv-summary-text{font-size:13px;color:var(--text,#1a1a1a);margin-top:4px;white-space:pre-wrap;}\
.rv-summary-quote{font-size:12px;color:var(--purple-dark,#5b21b6);font-style:italic;margin-top:4px;}\
.rv-summary-date{font-size:10px;color:var(--text2,#6b7280);margin-top:2px;}\
.rv-summary-actions{display:flex;gap:10px;margin-top:20px;padding-top:16px;border-top:1px solid var(--border,#e5e7eb);}\
.rv-summary-actions button{flex:1;padding:10px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;border:none;transition:all .15s;}\
.rv-summary-copy{background:var(--blue,#2563eb);color:#fff;}\
.rv-summary-copy:hover{opacity:.9;}\
.rv-summary-email{background:var(--purple,#7c3aed);color:#fff;}\
.rv-summary-email:hover{opacity:.9;}\
.rv-summary-close{position:absolute;top:16px;right:16px;background:var(--surface2,#f1f5f9);border:1px solid var(--border,#e5e7eb);\
border-radius:8px;padding:6px 10px;font-size:12px;cursor:pointer;color:var(--text2,#6b7280);}\
.rv-summary-close:hover{background:var(--border,#e5e7eb);}\
.rv-toast{position:fixed;bottom:80px;right:24px;z-index:9900;background:#059669;color:#fff;\
padding:10px 20px;border-radius:10px;font-size:13px;font-weight:600;box-shadow:0 4px 16px rgba(5,150,105,.35);\
opacity:0;transition:opacity .3s;pointer-events:none;}\
.rv-toast.show{opacity:1;}\
';
    document.head.appendChild(css);

    // --- Selection popup ---
    var selPopup = document.createElement('button');
    selPopup.className = 'rv-sel-popup';
    selPopup.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="margin-right:5px;vertical-align:-1px"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>Comment on this';
    document.body.appendChild(selPopup);
    var selectedQuote = '';
    var selectedSection = null;

    // --- Toast ---
    var toast = document.createElement('div');
    toast.className = 'rv-toast';
    document.body.appendChild(toast);
    function showToast(msg) {
        toast.textContent = msg;
        toast.classList.add('show');
        setTimeout(function() { toast.classList.remove('show'); }, 2000);
    }

    // --- Summary overlay ---
    var overlay = document.createElement('div');
    overlay.className = 'rv-overlay';
    overlay.innerHTML = '<div class="rv-summary" id="rvSummary"></div>';
    document.body.appendChild(overlay);
    overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.classList.remove('open'); });

    // --- FAB button ---
    var fab = document.createElement('button');
    fab.className = 'rv-fab';
    updateFab();
    document.body.appendChild(fab);
    fab.onclick = function() { openSummary(); };

    // First visit pulse
    if (!localStorage.getItem('brisken-review-seen')) {
        fab.classList.add('rv-pulse');
        localStorage.setItem('brisken-review-seen', '1');
    }

    function updateFab() {
        var n = totalCount();
        fab.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg> Feedback' + (n ? ' <span class="rv-count">' + n + '</span>' : '');
    }

    // --- Section setup ---
    var sections = document.querySelectorAll('h2[id]');
    var sectionData = {};

    sections.forEach(function(h2) {
        var sid = h2.id;
        var title = h2.childNodes[0] ? h2.childNodes[0].textContent.trim() : h2.textContent.trim();

        // Add button
        var btn = document.createElement('button');
        btn.className = 'rv-add';
        btn.innerHTML = '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>';
        h2.appendChild(btn);

        // Panel
        var panel = document.createElement('div');
        panel.className = 'rv-panel';
        h2.parentNode.insertBefore(panel, h2.nextSibling);

        // Comments container
        var commentsDiv = document.createElement('div');
        commentsDiv.className = 'rv-comments';
        panel.parentNode.insertBefore(commentsDiv, panel.nextSibling);

        sectionData[sid] = { h2: h2, btn: btn, panel: panel, commentsDiv: commentsDiv, title: title };

        btn.onclick = function(e) { e.preventDefault(); openPanel(sid); };
    });

    function openPanel(sid, quote) {
        var d = sectionData[sid];
        d.panel.innerHTML = (quote ? '<div class="rv-panel-quote">"' + esc(quote) + '"</div>' : '') +
            '<textarea placeholder="Your comment' + (quote ? ' on this text' : ' on this section') + '..."></textarea>' +
            '<div class="rv-panel-actions">' +
            '<button class="rv-btn-cancel">Cancel</button>' +
            '<button class="rv-btn-save">Save</button>' +
            '</div>';
        d.panel.classList.add('open');
        d.panel.querySelector('textarea').focus();
        d.panel.querySelector('.rv-btn-cancel').onclick = function() { d.panel.classList.remove('open'); };
        d.panel.querySelector('.rv-btn-save').onclick = function() {
            var text = d.panel.querySelector('textarea').value.trim();
            if (!text) return;
            addComment(sid, d.title, text, quote || null);
            d.panel.classList.remove('open');
            renderComments(sid);
            updateFab();
            showToast('Comment saved');
        };
    }

    function renderComments(sid) {
        var d = sectionData[sid];
        var comments = getForSection(sid);
        d.commentsDiv.innerHTML = '';

        // Update badge
        var oldBadge = d.h2.querySelector('.rv-badge');
        if (oldBadge) oldBadge.remove();
        if (comments.length) {
            var badge = document.createElement('span');
            badge.className = 'rv-badge';
            badge.textContent = comments.length;
            badge.onclick = function() { d.commentsDiv.scrollIntoView({ behavior: 'smooth', block: 'center' }); };
            d.h2.appendChild(badge);
        }

        comments.forEach(function(c) {
            var el = document.createElement('div');
            el.className = 'rv-comment';
            el.innerHTML = '<div class="rv-comment-header"><span class="rv-comment-date">' + fmtDate(c.date) + '</span>' +
                (c.editedAt ? '<span class="rv-comment-edited">(edited)</span>' : '') + '</div>' +
                (c.quote ? '<div class="rv-comment-quote">"' + esc(c.quote) + '"</div>' : '') +
                '<div class="rv-comment-text">' + esc(c.text) + '</div>' +
                '<div class="rv-comment-actions">' +
                '<button class="rv-act-edit">Edit</button>' +
                '<button class="rv-act-del">Delete</button>' +
                '</div>';
            d.commentsDiv.appendChild(el);

            el.querySelector('.rv-act-del').onclick = function() {
                deleteComment(c.id);
                renderComments(sid);
                updateFab();
                showToast('Comment removed');
            };
            el.querySelector('.rv-act-edit').onclick = function() {
                var textEl = el.querySelector('.rv-comment-text');
                var actionsEl = el.querySelector('.rv-comment-actions');
                textEl.innerHTML = '<textarea style="width:100%;min-height:60px;border:1px solid var(--border);border-radius:6px;padding:8px;font-size:13px;font-family:inherit;background:var(--bg);color:var(--text);resize:vertical;">' + esc(c.text) + '</textarea>';
                actionsEl.innerHTML = '<button class="rv-act-edit">Save</button><button class="rv-act-del">Cancel</button>';
                textEl.querySelector('textarea').focus();
                actionsEl.querySelector('.rv-act-edit').onclick = function() {
                    var newText = textEl.querySelector('textarea').value.trim();
                    if (newText && newText !== c.text) { updateComment(c.id, newText); }
                    renderComments(sid);
                    showToast('Comment updated');
                };
                actionsEl.querySelector('.rv-act-del').onclick = function() { renderComments(sid); };
            };
        });
    }

    // Initial render
    sections.forEach(function(h2) { renderComments(h2.id); });

    // --- Text selection commenting ---
    document.addEventListener('mouseup', function(e) {
        var sel = window.getSelection();
        if (!sel || sel.isCollapsed || !sel.toString().trim()) {
            selPopup.style.display = 'none';
            return;
        }
        // Find which section this selection belongs to
        var node = sel.anchorNode;
        var foundSection = null;
        while (node && node !== document.body) {
            if (node.previousElementSibling) {
                var prev = node.previousElementSibling;
                while (prev) {
                    if (prev.tagName === 'H2' && prev.id && sectionData[prev.id]) {
                        foundSection = prev.id;
                        break;
                    }
                    prev = prev.previousElementSibling;
                }
            }
            if (foundSection) break;
            node = node.parentNode;
        }
        // Fallback: find closest h2 above in document order
        if (!foundSection) {
            var allH2 = Array.from(sections);
            var range = sel.getRangeAt(0);
            var rect = range.getBoundingClientRect();
            for (var i = allH2.length - 1; i >= 0; i--) {
                if (allH2[i].getBoundingClientRect().top < rect.top) {
                    foundSection = allH2[i].id;
                    break;
                }
            }
        }
        if (!foundSection || !sectionData[foundSection]) { selPopup.style.display = 'none'; return; }

        selectedQuote = sel.toString().trim().substring(0, 300);
        selectedSection = foundSection;

        var r = sel.getRangeAt(0).getBoundingClientRect();
        selPopup.style.display = 'block';
        selPopup.style.left = (r.left + r.width / 2 - 70 + window.scrollX) + 'px';
        selPopup.style.top = (r.top - 40 + window.scrollY) + 'px';
    });

    selPopup.onclick = function() {
        selPopup.style.display = 'none';
        if (selectedSection && selectedQuote) {
            openPanel(selectedSection, selectedQuote);
            window.getSelection().removeAllRanges();
        }
    };

    document.addEventListener('mousedown', function(e) {
        if (e.target !== selPopup && !selPopup.contains(e.target)) {
            selPopup.style.display = 'none';
        }
    });

    // --- Summary panel ---
    function openSummary() {
        var all = getAll();
        var sumEl = document.getElementById('rvSummary');
        var html = '<button class="rv-summary-close" id="rvClose">Close</button>';
        html += '<div class="rv-summary-title">Your Feedback</div>';
        html += '<div class="rv-summary-sub">' + all.length + ' comment' + (all.length !== 1 ? 's' : '') + ' across all pages</div>';

        if (!all.length) {
            html += '<p style="color:var(--text2);font-size:13px;padding:20px 0;">No comments yet. Click the comment icon next to any section header, or highlight text and click "Comment on this" to get started.</p>';
        } else {
            // Group by page
            var byPage = {};
            all.forEach(function(c) {
                var p = c.pageLabel || c.page;
                if (!byPage[p]) byPage[p] = [];
                byPage[p].push(c);
            });
            Object.keys(byPage).forEach(function(p) {
                html += '<div class="rv-summary-page">' + esc(p) + '</div>';
                byPage[p].forEach(function(c) {
                    html += '<div class="rv-summary-item">';
                    html += '<div class="rv-summary-section">' + esc(c.sectionTitle) + '</div>';
                    if (c.quote) html += '<div class="rv-summary-quote">"' + esc(c.quote) + '"</div>';
                    html += '<div class="rv-summary-text">' + esc(c.text) + '</div>';
                    html += '<div class="rv-summary-date">' + fmtDate(c.date) + (c.editedAt ? ' (edited)' : '') + '</div>';
                    html += '</div>';
                });
            });
        }

        html += '<div class="rv-summary-actions">';
        html += '<button class="rv-summary-copy" id="rvCopy"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:6px;vertical-align:-2px"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>Copy All</button>';
        html += '<button class="rv-summary-email" id="rvEmail"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:6px;vertical-align:-2px"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>Email to Nico</button>';
        html += '</div>';

        sumEl.innerHTML = html;
        overlay.classList.add('open');

        document.getElementById('rvClose').onclick = function() { overlay.classList.remove('open'); };
        document.getElementById('rvCopy').onclick = function() {
            var text = buildExportText(all);
            navigator.clipboard.writeText(text).then(function() { showToast('Copied to clipboard'); });
        };
        document.getElementById('rvEmail').onclick = function() {
            var text = buildExportText(all);
            window.open('mailto:' + RECIPIENT + '?subject=' + encodeURIComponent('Scope Page Feedback - Brisken') + '&body=' + encodeURIComponent(text), '_blank');
        };
    }

    function buildExportText(all) {
        var text = 'Feedback on Brisken Scope Page\nDate: ' + new Date().toLocaleDateString() + '\n' + '='.repeat(40) + '\n\n';
        var byPage = {};
        all.forEach(function(c) { var p = c.pageLabel || c.page; if (!byPage[p]) byPage[p] = []; byPage[p].push(c); });
        Object.keys(byPage).forEach(function(p) {
            text += '## ' + p + '\n\n';
            byPage[p].forEach(function(c) {
                text += '### ' + c.sectionTitle + '\n';
                if (c.quote) text += '> "' + c.quote + '"\n';
                text += c.text + '\n';
                text += '(' + fmtDate(c.date) + ')\n\n';
            });
        });
        return text;
    }

})();
