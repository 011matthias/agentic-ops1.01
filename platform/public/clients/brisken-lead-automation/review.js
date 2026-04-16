/**
 * Review Mode v3 — Word-style inline commenting.
 *
 * - Highlight text → comment appears in right sidebar
 * - Highlighted text stays marked on the page with matching color
 * - Sidebar shows all comments, ordered by position
 * - Click comment → scrolls to highlight; click highlight → focuses comment
 * - Persistent across page loads (localStorage)
 * - Export: copy all or email
 */
(function() {
    'use strict';

    var STORE = 'brisken-rv3';
    var MAIL = 'nicolas.neumann@unpauseai.com';
    var WEBHOOK = 'https://hook.eu1.make.com/ixia13ls7admv5salw3h1p7lmcasmjuh';
    var page = location.pathname.split('/').filter(Boolean).pop() || 'overview';
    var PAGES = { 'brisken-lead-automation': 'Overview', solution: 'Solution', timeline: 'Timeline', faq: 'FAQ' };
    var pageLabel = PAGES[page] || page;

    // Notify webhook when a comment is added or edited
    function notify(action, comment) {
        try {
            fetch(WEBHOOK, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id: comment.id,
                    action: action,
                    page: comment.pageLabel || comment.page,
                    section: comment.sectionTitle,
                    quote: comment.quote || null,
                    comment: comment.text,
                    timestamp: comment.date || new Date().toISOString()
                })
            }).catch(function() { /* silent fail — don't block UX */ });
        } catch(e) { /* silent */ }
    }

    // Palette for comment markers (rotating)
    var COLORS = [
        { bg: 'rgba(124,58,237,.15)', border: '#7c3aed', text: '#5b21b6' },
        { bg: 'rgba(37,99,235,.15)', border: '#2563eb', text: '#1e40af' },
        { bg: 'rgba(5,150,105,.15)', border: '#059669', text: '#047857' },
        { bg: 'rgba(217,119,6,.15)', border: '#d97706', text: '#b45309' },
        { bg: 'rgba(220,38,38,.12)', border: '#dc2626', text: '#991b1b' },
    ];

    // ── Storage ──
    function load() { try { return JSON.parse(localStorage.getItem(STORE) || '[]'); } catch(e) { return []; } }
    function save(arr) { localStorage.setItem(STORE, JSON.stringify(arr)); }
    function forPage() { return load().filter(function(c) { return c.page === page; }); }
    function nextColor() { var all = load(); return COLORS[all.length % COLORS.length]; }

    // ── Helpers ──
    function esc(s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
    function fmtTime(iso) {
        var d = new Date(iso);
        return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) + ' ' +
               d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
    }
    function uid() { return Date.now().toString(36) + Math.random().toString(36).substr(2, 6); }

    // Find the nearest section (h2[id]) above a node
    function nearestSection(node) {
        var el = node.nodeType === 3 ? node.parentElement : node;
        while (el && el !== document.body) {
            var prev = el.previousElementSibling;
            while (prev) {
                if (prev.tagName === 'H2' && prev.id) return { id: prev.id, title: prev.textContent.trim() };
                prev = prev.previousElementSibling;
            }
            el = el.parentElement;
        }
        // Fallback: closest h2 above by position
        var all = document.querySelectorAll('h2[id]');
        for (var i = all.length - 1; i >= 0; i--) {
            if (all[i].compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING) {
                return { id: all[i].id, title: all[i].textContent.trim() };
            }
        }
        return { id: 'general', title: 'General' };
    }

    // ── Inject styles ──
    var style = document.createElement('style');
    style.textContent = '\
/* Sidebar */\
.rv-sidebar{position:fixed;top:56px;right:0;width:300px;height:calc(100vh - 56px);background:var(--bg,#fff);\
border-left:1px solid var(--border,#e5e7eb);z-index:800;overflow-y:auto;transform:translateX(100%);\
transition:transform .25s ease;padding:0;font-size:13px;}\
.rv-sidebar.open{transform:translateX(0);}\
.rv-sidebar-header{position:sticky;top:0;background:var(--bg,#fff);border-bottom:1px solid var(--border,#e5e7eb);\
padding:14px 16px;display:flex;align-items:center;justify-content:space-between;z-index:1;}\
.rv-sidebar-title{font-size:13px;font-weight:700;color:var(--text-strong,#111827);}\
.rv-sidebar-count{font-size:11px;color:var(--text2,#6b7280);font-weight:400;margin-left:6px;}\
.rv-sidebar-actions{display:flex;gap:4px;}\
.rv-sidebar-actions button{background:var(--surface2,#f1f5f9);border:1px solid var(--border,#e5e7eb);border-radius:6px;\
padding:4px 8px;font-size:11px;cursor:pointer;color:var(--text2,#6b7280);transition:all .15s;}\
.rv-sidebar-actions button:hover{background:var(--border,#e5e7eb);color:var(--text,#1a1a1a);}\
.rv-sidebar-empty{padding:40px 20px;text-align:center;color:var(--text2,#6b7280);font-size:12px;line-height:1.6;}\
.rv-sidebar-empty b{display:block;font-size:13px;color:var(--text,#1a1a1a);margin-bottom:6px;}\
/* Comment card */\
.rv-card{padding:14px 16px;border-bottom:1px solid var(--border,#e5e7eb);cursor:pointer;transition:background .1s;position:relative;}\
.rv-card:hover{background:var(--surface,#f8fafc);}\
.rv-card.active{background:var(--purple-bg,#f5f3ff);}\
.rv-card-marker{position:absolute;left:0;top:0;bottom:0;width:4px;border-radius:0 2px 2px 0;}\
.rv-card-section{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:var(--text2,#6b7280);margin-bottom:4px;padding-left:10px;}\
.rv-card-quote{font-size:12px;font-style:italic;padding:5px 10px;margin:4px 0 6px 10px;\
border-left:2px solid var(--border,#e5e7eb);color:var(--text2,#6b7280);max-height:44px;overflow:hidden;\
text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;line-height:1.4;}\
.rv-card-text{font-size:13px;color:var(--text,#1a1a1a);padding-left:10px;line-height:1.5;white-space:pre-wrap;}\
.rv-card-meta{display:flex;align-items:center;gap:8px;margin-top:6px;padding-left:10px;}\
.rv-card-date{font-size:10px;color:var(--text2,#6b7280);}\
.rv-card-btns{display:flex;gap:2px;margin-left:auto;opacity:0;transition:opacity .15s;}\
.rv-card:hover .rv-card-btns{opacity:1;}\
.rv-card-btns button{background:none;border:none;font-size:10px;font-weight:600;cursor:pointer;padding:2px 6px;border-radius:4px;}\
.rv-card-btns .rv-edit{color:var(--blue,#2563eb);}\
.rv-card-btns .rv-edit:hover{background:var(--blue-bg,#eff6ff);}\
.rv-card-btns .rv-del{color:#ef4444;}\
.rv-card-btns .rv-del:hover{background:#fef2f2;}\
/* Edit mode inside card */\
.rv-card-editing textarea{width:100%;min-height:60px;border:1px solid var(--border,#e5e7eb);border-radius:6px;\
padding:8px;font-size:12px;font-family:inherit;background:var(--bg,#fff);color:var(--text,#1a1a1a);resize:vertical;margin:4px 0;}\
.rv-card-editing textarea:focus{outline:none;border-color:var(--purple,#7c3aed);}\
.rv-card-editing .rv-edit-btns{display:flex;gap:6px;justify-content:flex-end;}\
.rv-card-editing .rv-edit-btns button{padding:5px 12px;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer;border:none;}\
.rv-card-editing .rv-save-btn{background:var(--purple,#7c3aed);color:#fff;}\
.rv-card-editing .rv-cancel-btn{background:var(--surface2,#f1f5f9);color:var(--text2,#6b7280);border:1px solid var(--border,#e5e7eb);}\
/* In-page highlight marks */\
mark.rv-highlight{border-radius:2px;cursor:pointer;transition:background .15s;padding:0 1px;}\
mark.rv-highlight:hover{filter:brightness(.92);}\
mark.rv-highlight.active{outline:2px solid var(--purple,#7c3aed);outline-offset:1px;}\
/* Selection popup */\
.rv-popup{position:absolute;z-index:9500;background:var(--purple,#7c3aed);color:#fff;border:none;border-radius:8px;\
padding:7px 14px;font-size:12px;font-weight:600;cursor:pointer;box-shadow:0 4px 14px rgba(124,58,237,.4);\
display:none;white-space:nowrap;}\
.rv-popup:hover{background:var(--purple-dark,#5b21b6);}\
.rv-popup::after{content:"";position:absolute;bottom:-6px;left:50%;transform:translateX(-50%);\
border-left:6px solid transparent;border-right:6px solid transparent;border-top:6px solid var(--purple,#7c3aed);}\
/* Comment input at bottom of sidebar */\
.rv-input{position:sticky;bottom:0;background:var(--bg,#fff);border-top:1px solid var(--border,#e5e7eb);padding:12px;display:none;}\
.rv-input.open{display:block;}\
.rv-input-quote{font-size:11px;font-style:italic;color:var(--purple-dark,#5b21b6);padding:6px 10px;margin-bottom:8px;\
border-left:3px solid var(--purple,#7c3aed);background:var(--purple-bg,#f5f3ff);border-radius:0 6px 6px 0;\
max-height:40px;overflow:hidden;}\
.rv-input textarea{width:100%;min-height:64px;border:1px solid var(--border,#e5e7eb);border-radius:8px;\
padding:10px;font-size:13px;font-family:inherit;background:var(--surface,#f8fafc);color:var(--text,#1a1a1a);resize:vertical;}\
.rv-input textarea:focus{outline:none;border-color:var(--purple,#7c3aed);box-shadow:0 0 0 3px rgba(124,58,237,.1);background:var(--bg,#fff);}\
.rv-input-actions{display:flex;gap:8px;margin-top:8px;justify-content:flex-end;}\
.rv-input-actions button{padding:7px 16px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;border:none;}\
.rv-input .rv-submit{background:var(--purple,#7c3aed);color:#fff;}\
.rv-input .rv-submit:hover{opacity:.9;}\
.rv-input .rv-discard{background:var(--surface2,#f1f5f9);color:var(--text2,#6b7280);border:1px solid var(--border,#e5e7eb);}\
/* FAB */\
.rv-fab{position:fixed;bottom:24px;right:24px;z-index:900;display:flex;align-items:center;gap:8px;\
background:var(--purple,#7c3aed);color:#fff;border:none;border-radius:12px;padding:10px 18px;\
font-size:13px;font-weight:600;cursor:pointer;box-shadow:0 4px 16px rgba(124,58,237,.35);transition:all .25s;}\
.rv-fab:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(124,58,237,.45);}\
.rv-fab .rv-cnt{background:rgba(255,255,255,.25);padding:1px 7px;border-radius:10px;font-size:11px;}\
@keyframes rv-intro{0%,100%{box-shadow:0 4px 16px rgba(124,58,237,.35)}50%{box-shadow:0 4px 28px rgba(124,58,237,.7)}}\
.rv-fab.intro{animation:rv-intro 1.5s ease-in-out 3;}\
/* Toast */\
.rv-toast{position:fixed;bottom:80px;left:50%;transform:translateX(-50%);z-index:9900;background:#059669;color:#fff;\
padding:8px 20px;border-radius:10px;font-size:13px;font-weight:600;box-shadow:0 4px 16px rgba(5,150,105,.3);\
opacity:0;transition:opacity .3s;pointer-events:none;}\
.rv-toast.show{opacity:1;}\
/* Layout shift when sidebar open */\
body.rv-open .main-content{margin-right:300px;transition:margin-right .25s ease;}\
@media(max-width:1000px){.rv-sidebar{width:100%;max-width:340px;}\
body.rv-open .main-content{margin-right:0;}}\
';
    document.head.appendChild(style);

    // ── Build sidebar ──
    var sidebar = document.createElement('aside');
    sidebar.className = 'rv-sidebar';
    sidebar.innerHTML = '\
<div class="rv-sidebar-header">\
<div><span class="rv-sidebar-title">Comments</span><span class="rv-sidebar-count" id="rvCount"></span></div>\
<div class="rv-sidebar-actions">\
<button id="rvCopy" title="Copy all comments">Copy</button>\
<button id="rvMail" title="Email comments">Email</button>\
<button id="rvClose" title="Close panel">&times;</button>\
</div></div>\
<div id="rvList"></div>\
<div class="rv-input" id="rvInput">\
<div class="rv-input-quote" id="rvInputQuote"></div>\
<textarea id="rvInputText" placeholder="Add your comment..."></textarea>\
<div class="rv-input-actions">\
<button class="rv-discard" id="rvDiscard">Cancel</button>\
<button class="rv-submit" id="rvSubmit">Comment</button>\
</div></div>';
    document.body.appendChild(sidebar);

    var listEl = document.getElementById('rvList');
    var inputEl = document.getElementById('rvInput');
    var inputQuoteEl = document.getElementById('rvInputQuote');
    var inputText = document.getElementById('rvInputText');
    var countEl = document.getElementById('rvCount');

    // ── Selection popup ──
    var popup = document.createElement('button');
    popup.className = 'rv-popup';
    popup.innerHTML = '\u270E Comment';
    document.body.appendChild(popup);

    // ── Toast ──
    var toastEl = document.createElement('div');
    toastEl.className = 'rv-toast';
    document.body.appendChild(toastEl);
    function toast(msg) { toastEl.textContent = msg; toastEl.classList.add('show'); setTimeout(function() { toastEl.classList.remove('show'); }, 2000); }

    // ── FAB ──
    var fab = document.createElement('button');
    fab.className = 'rv-fab';
    document.body.appendChild(fab);
    if (!localStorage.getItem('brisken-rv3-seen')) { fab.classList.add('intro'); localStorage.setItem('brisken-rv3-seen', '1'); }

    // ── State ──
    var sidebarOpen = false;
    var pendingQuote = '';
    var pendingSection = null;
    var pendingColor = null;
    var activeCardId = null;

    // ── Open / close sidebar ──
    function openSidebar() { sidebar.classList.add('open'); document.body.classList.add('rv-open'); sidebarOpen = true; }
    function closeSidebar() { sidebar.classList.remove('open'); document.body.classList.remove('rv-open'); sidebarOpen = false; clearActive(); }

    fab.onclick = function() { if (sidebarOpen) closeSidebar(); else { openSidebar(); render(); } };
    document.getElementById('rvClose').onclick = closeSidebar;

    function updateFab() {
        var n = load().length;
        fab.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg> Comments' + (n ? ' <span class="rv-cnt">' + n + '</span>' : '');
    }
    updateFab();

    // ── Render comments in sidebar ──
    function render() {
        var comments = forPage();
        countEl.textContent = comments.length ? '(' + comments.length + ')' : '';
        updateFab();

        if (!comments.length) {
            listEl.innerHTML = '<div class="rv-sidebar-empty"><b>No comments on this page yet</b>Select any text on the page to leave a comment.<br>Your highlighted text will be marked and linked here.</div>';
            return;
        }

        listEl.innerHTML = '';
        comments.forEach(function(c) {
            var color = COLORS[c.colorIdx || 0];
            var card = document.createElement('div');
            card.className = 'rv-card';
            card.setAttribute('data-id', c.id);
            card.innerHTML = '<div class="rv-card-marker" style="background:' + color.border + '"></div>' +
                '<div class="rv-card-section">' + esc(c.sectionTitle) + '</div>' +
                (c.quote ? '<div class="rv-card-quote" style="border-color:' + color.border + ';color:' + color.text + '">' + esc(c.quote) + '</div>' : '') +
                '<div class="rv-card-text">' + esc(c.text) + '</div>' +
                '<div class="rv-card-meta"><span class="rv-card-date">' + fmtTime(c.date) + (c.editedAt ? ' (edited)' : '') + '</span>' +
                '<div class="rv-card-btns"><button class="rv-edit">Edit</button><button class="rv-del">Delete</button></div></div>';
            listEl.appendChild(card);

            // Click card → scroll to highlight
            card.onclick = function(e) {
                if (e.target.closest('.rv-card-btns')) return;
                setActive(c.id);
                var mark = document.querySelector('mark.rv-highlight[data-id="' + c.id + '"]');
                if (mark) mark.scrollIntoView({ behavior: 'smooth', block: 'center' });
            };

            card.querySelector('.rv-del').onclick = function(e) {
                e.stopPropagation();
                deleteComment(c.id);
                removeHighlight(c.id);
                render();
                toast('Comment deleted');
            };

            card.querySelector('.rv-edit').onclick = function(e) {
                e.stopPropagation();
                var textDiv = card.querySelector('.rv-card-text');
                var metaDiv = card.querySelector('.rv-card-meta');
                card.classList.add('rv-card-editing');
                textDiv.innerHTML = '<textarea>' + esc(c.text) + '</textarea>';
                metaDiv.innerHTML = '<div class="rv-edit-btns"><button class="rv-cancel-btn">Cancel</button><button class="rv-save-btn">Save</button></div>';
                textDiv.querySelector('textarea').focus();
                metaDiv.querySelector('.rv-save-btn').onclick = function() {
                    var v = textDiv.querySelector('textarea').value.trim();
                    if (v) { updateComment(c.id, v); }
                    render();
                    toast('Comment updated');
                };
                metaDiv.querySelector('.rv-cancel-btn').onclick = function() { render(); };
            };
        });
    }

    function setActive(id) {
        clearActive();
        activeCardId = id;
        var card = listEl.querySelector('[data-id="' + id + '"]');
        if (card) card.classList.add('active');
        document.querySelectorAll('mark.rv-highlight').forEach(function(m) {
            m.classList.toggle('active', m.getAttribute('data-id') === id);
        });
    }

    function clearActive() {
        activeCardId = null;
        listEl.querySelectorAll('.rv-card.active').forEach(function(c) { c.classList.remove('active'); });
        document.querySelectorAll('mark.rv-highlight.active').forEach(function(m) { m.classList.remove('active'); });
    }

    // ── Comment CRUD ──
    function addCommentData(quote, sectionId, sectionTitle, text) {
        var all = load();
        var colorIdx = all.length % COLORS.length;
        var c = { id: uid(), page: page, pageLabel: pageLabel, section: sectionId, sectionTitle: sectionTitle, quote: quote, text: text, date: new Date().toISOString(), colorIdx: colorIdx };
        all.push(c);
        save(all);
        notify('new_comment', c);
        return c;
    }
    function updateComment(id, newText) {
        var all = load();
        for (var i = 0; i < all.length; i++) {
            if (all[i].id === id) {
                all[i].text = newText;
                all[i].editedAt = new Date().toISOString();
                notify('edit_comment', all[i]);
            }
        }
        save(all);
    }
    function deleteComment(id) { save(load().filter(function(c) { return c.id !== id; })); }

    // ── Highlights ──
    function applyHighlight(commentObj) {
        if (!commentObj.quote) return;
        var color = COLORS[commentObj.colorIdx || 0];
        // Walk text nodes in the main content to find the quote
        var content = document.querySelector('.content-inner');
        if (!content) return;
        var walker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT, null, false);
        var node;
        while (node = walker.nextNode()) {
            var idx = node.textContent.indexOf(commentObj.quote);
            if (idx === -1) continue;
            // Don't highlight inside existing marks or buttons
            if (node.parentElement.closest('mark.rv-highlight, button, .rv-sidebar, .rv-popup, .rv-input, script, style')) continue;
            var range = document.createRange();
            range.setStart(node, idx);
            range.setEnd(node, idx + commentObj.quote.length);
            var mark = document.createElement('mark');
            mark.className = 'rv-highlight';
            mark.setAttribute('data-id', commentObj.id);
            mark.style.background = color.bg;
            mark.onclick = function(cid) { return function() { openSidebar(); render(); setActive(cid); var card = listEl.querySelector('[data-id="' + cid + '"]'); if (card) card.scrollIntoView({ behavior: 'smooth', block: 'center' }); }; }(commentObj.id);
            try { range.surroundContents(mark); } catch(e) { /* cross-element selection, skip */ }
            return; // Only highlight first occurrence
        }
    }

    function removeHighlight(id) {
        var mark = document.querySelector('mark.rv-highlight[data-id="' + id + '"]');
        if (mark) { var parent = mark.parentNode; parent.replaceChild(document.createTextNode(mark.textContent), mark); parent.normalize(); }
    }

    function applyAllHighlights() {
        // Remove existing
        document.querySelectorAll('mark.rv-highlight').forEach(function(m) {
            var p = m.parentNode; p.replaceChild(document.createTextNode(m.textContent), m); p.normalize();
        });
        forPage().forEach(applyHighlight);
    }

    // ── Text selection → popup ──
    document.addEventListener('mouseup', function(e) {
        if (e.target.closest('.rv-sidebar, .rv-popup, .rv-fab')) return;
        setTimeout(function() {
            var sel = window.getSelection();
            if (!sel || sel.isCollapsed || !sel.toString().trim()) { popup.style.display = 'none'; return; }
            var text = sel.toString().trim();
            if (text.length < 3 || text.length > 500) { popup.style.display = 'none'; return; }
            var range = sel.getRangeAt(0);
            // Don't show popup inside sidebar
            if (range.commonAncestorContainer && (range.commonAncestorContainer.nodeType === 1 ? range.commonAncestorContainer : range.commonAncestorContainer.parentElement).closest('.rv-sidebar')) {
                popup.style.display = 'none'; return;
            }
            var rect = range.getBoundingClientRect();
            popup.style.display = 'block';
            popup.style.left = (rect.left + rect.width / 2 - 50 + window.scrollX) + 'px';
            popup.style.top = (rect.top - 38 + window.scrollY) + 'px';
            var sec = nearestSection(range.startContainer);
            pendingQuote = text;
            pendingSection = sec;
            pendingColor = nextColor();
        }, 10);
    });

    document.addEventListener('mousedown', function(e) {
        if (!e.target.closest('.rv-popup')) popup.style.display = 'none';
    });

    popup.onclick = function() {
        popup.style.display = 'none';
        window.getSelection().removeAllRanges();
        openSidebar();
        // Show input area with the quote
        inputQuoteEl.textContent = '"' + pendingQuote + '"';
        inputQuoteEl.style.display = 'block';
        inputEl.classList.add('open');
        inputText.value = '';
        inputText.focus();
        render();
    };

    // ── Submit new comment ──
    document.getElementById('rvSubmit').onclick = function() {
        var text = inputText.value.trim();
        if (!text) return;
        var c = addCommentData(pendingQuote, pendingSection.id, pendingSection.title, text);
        inputEl.classList.remove('open');
        inputText.value = '';
        pendingQuote = '';
        applyHighlight(c);
        render();
        toast('Comment saved');
        // Scroll to the new card
        setTimeout(function() {
            var card = listEl.querySelector('[data-id="' + c.id + '"]');
            if (card) { setActive(c.id); card.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
        }, 50);
    };

    document.getElementById('rvDiscard').onclick = function() {
        inputEl.classList.remove('open');
        inputText.value = '';
        pendingQuote = '';
    };

    // Submit on Ctrl+Enter
    inputText.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { document.getElementById('rvSubmit').click(); }
    });

    // ── Export ──
    function buildExport() {
        var all = load();
        if (!all.length) return '';
        var out = 'Brisken Scope Page — Feedback\nDate: ' + new Date().toLocaleDateString() + '\n' + '─'.repeat(40) + '\n\n';
        var byPage = {};
        all.forEach(function(c) { var p = c.pageLabel || c.page; if (!byPage[p]) byPage[p] = []; byPage[p].push(c); });
        Object.keys(byPage).forEach(function(p) {
            out += p.toUpperCase() + '\n\n';
            byPage[p].forEach(function(c) {
                out += '  ' + c.sectionTitle + '\n';
                if (c.quote) out += '  > "' + c.quote + '"\n';
                out += '  ' + c.text + '\n';
                out += '  (' + fmtTime(c.date) + ')\n\n';
            });
        });
        return out;
    }

    document.getElementById('rvCopy').onclick = function() {
        var text = buildExport();
        if (!text) { toast('No comments to copy'); return; }
        navigator.clipboard.writeText(text).then(function() { toast('Copied to clipboard'); });
    };

    document.getElementById('rvMail').onclick = function() {
        var text = buildExport();
        if (!text) { toast('No comments to email'); return; }
        window.open('mailto:' + MAIL + '?subject=' + encodeURIComponent('Scope Feedback — Brisken') + '&body=' + encodeURIComponent(text));
    };

    // ── Init ──
    applyAllHighlights();
    updateFab();

})();
