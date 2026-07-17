/* Wärme Wimmer doc-site comment widget.
 *
 * Two modes co-exist:
 *   1. Page-level thread (legacy/fallback). Bottom-of-page mount on
 *      <div id="wimmer-comments">. Comments with selectionAnchor=null appear here.
 *   2. Inline-highlight comments (primary mode). User selects text in the doc
 *      body, the floating "Kommentieren" pill appears near the selection,
 *      click opens a popover thread. The anchor (W3C TextQuoteSelector triple
 *      {exact, prefix, suffix}) is stored with the comment and re-rendered as
 *      a yellow highlight when the page loads. Click highlight -> popover thread.
 *
 * Reads + writes via /api/wimmer-comments. Passcode-gated for read,
 * Auth.js + email allowlist gated for write. Soft-delete own within 24h or admin.
 */
(function () {
  "use strict";

  const ENDPOINT = "/api/wimmer-comments";
  const MAX_BODY_LENGTH = 5000;
  const ANCHOR_CONTEXT_CHARS = 50;
  const HIGHLIGHT_CLASS = "wc-highlight";

  let me = null;
  let allComments = [];
  /** Comments that have a selectionAnchor, keyed by anchor.exact. */
  let anchoredById = {};
  /** Currently-open popover element (if any). */
  let activePopover = null;
  /** Container we restrict selections to (the doc body). */
  let docRoot = null;

  // ---------- DOM helpers ----------

  function el(tag, attrs, children) {
    const e = document.createElement(tag);
    if (attrs) {
      for (const k in attrs) {
        if (k === "class") e.className = attrs[k];
        else if (k === "html") e.innerHTML = attrs[k];
        else if (k === "style" && typeof attrs[k] === "object") {
          Object.assign(e.style, attrs[k]);
        }
        else if (k.startsWith("on") && typeof attrs[k] === "function") e.addEventListener(k.slice(2).toLowerCase(), attrs[k]);
        else e.setAttribute(k, attrs[k]);
      }
    }
    if (children) {
      (Array.isArray(children) ? children : [children]).forEach(function (c) {
        if (c == null) return;
        if (typeof c === "string") e.appendChild(document.createTextNode(c));
        else e.appendChild(c);
      });
    }
    return e;
  }

  function fmtTs(iso) {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      return d.toLocaleString("de-DE", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
    } catch (_) { return iso; }
  }

  /** Minimal markdown -> safe HTML. Escapes everything, then re-applies a handful
   *  of inline patterns. No raw HTML pass-through. */
  function renderBody(md) {
    const esc = (md || "").replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
    return esc
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\bhttps?:\/\/\S+/g, function (u) {
        const safe = u.replace(/[&<>"']/g, function (c) {
          return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
        });
        return '<a href="' + safe + '" target="_blank" rel="noopener noreferrer">' + safe + "</a>";
      })
      .replace(/\n/g, "<br>");
  }

  function pageSlug() {
    let p = window.location.pathname || "";
    if (p.endsWith("/")) p = p.slice(0, -1);
    const m = p.match(/\/docs\/warme-wimmer\/?(.*)$/);
    let slug = m ? m[1] : "";
    slug = slug.replace(/\.html$/, "");
    return slug || "index";
  }

  function buildTree(rows) {
    const byId = {};
    rows.forEach(function (r) { r._children = []; byId[r.id] = r; });
    const roots = [];
    rows.forEach(function (r) {
      if (r.parentId && byId[r.parentId]) byId[r.parentId]._children.push(r);
      else roots.push(r);
    });
    return roots;
  }

  function getDocRoot() {
    return document.querySelector(".main") || document.body;
  }

  function isInsideWidget(node) {
    return node && (
      (node.closest && (
        node.closest("#wimmer-comments") ||
        node.closest(".wc-popover") ||
        node.closest(".wc-floating-action")
      )) || false
    );
  }

  // ---------- Anchor capture + resolution ----------

  /** Build a W3C-style TextQuoteSelector triple from the current Selection.
   *  Walks the surrounding text to capture up to ANCHOR_CONTEXT_CHARS of
   *  prefix and suffix context for fuzzy re-matching. */
  function captureTextQuote(selection) {
    if (!selection || selection.rangeCount === 0) return null;
    const range = selection.getRangeAt(0);
    const exact = selection.toString();
    if (!exact || exact.trim().length < 2) return null;
    if (isInsideWidget(range.startContainer) || isInsideWidget(range.endContainer)) return null;
    if (!docRoot.contains(range.commonAncestorContainer)) return null;

    // Gather text content of the doc root, then locate the exact match.
    // Simple but robust: serialize text nodes in DOM order, find the selection
    // by content + adjacent context. Falls back to {exact} only on ambiguity.
    const fullText = docRoot.textContent || "";
    const idx = fullText.indexOf(exact);
    if (idx === -1) return { exact: exact };  // shouldn't happen but safe fallback
    return {
      exact: exact,
      prefix: fullText.substring(Math.max(0, idx - ANCHOR_CONTEXT_CHARS), idx),
      suffix: fullText.substring(idx + exact.length, idx + exact.length + ANCHOR_CONTEXT_CHARS),
    };
  }

  /** Find the DOM Range matching a stored anchor. Strategy:
   *    1. Locate all occurrences of anchor.exact in the doc.
   *    2. Score each by how well prefix/suffix match the surrounding text.
   *    3. Return the highest-scoring occurrence as a Range; null if none. */
  function findAnchorRange(anchor) {
    if (!anchor || !anchor.exact) return null;
    const text = docRoot.textContent || "";
    const exact = anchor.exact;
    const occurrences = [];
    let from = 0;
    while (from < text.length) {
      const idx = text.indexOf(exact, from);
      if (idx === -1) break;
      let score = 0;
      if (anchor.prefix) {
        const seen = text.substring(Math.max(0, idx - anchor.prefix.length), idx);
        if (seen === anchor.prefix) score += 100;
        else if (seen.endsWith(anchor.prefix.slice(-10))) score += 30;
      }
      if (anchor.suffix) {
        const seen = text.substring(idx + exact.length, idx + exact.length + anchor.suffix.length);
        if (seen === anchor.suffix) score += 100;
        else if (seen.startsWith(anchor.suffix.slice(0, 10))) score += 30;
      }
      occurrences.push({ idx: idx, score: score });
      from = idx + 1;
    }
    if (occurrences.length === 0) return null;
    occurrences.sort(function (a, b) { return b.score - a.score; });
    return buildRangeAtOffset(occurrences[0].idx, exact.length);
  }

  /** Convert a (startCharOffset, length) within docRoot.textContent to a DOM Range. */
  function buildRangeAtOffset(startOffset, length) {
    const walker = document.createTreeWalker(docRoot, NodeFilter.SHOW_TEXT, null);
    let charSeen = 0;
    let startNode = null, startNodeOffset = 0, endNode = null, endNodeOffset = 0;
    while (walker.nextNode()) {
      const node = walker.currentNode;
      const nodeLen = node.textContent.length;
      if (!startNode && charSeen + nodeLen > startOffset) {
        startNode = node;
        startNodeOffset = startOffset - charSeen;
      }
      if (!endNode && charSeen + nodeLen >= startOffset + length) {
        endNode = node;
        endNodeOffset = startOffset + length - charSeen;
        break;
      }
      charSeen += nodeLen;
    }
    if (!startNode || !endNode) return null;
    const r = document.createRange();
    try {
      r.setStart(startNode, startNodeOffset);
      r.setEnd(endNode, endNodeOffset);
    } catch (_) { return null; }
    return r;
  }

  /** Wrap a Range with a highlight span. Returns the span, or null on failure
   *  (e.g. range spans elements that can't safely contain a span wrapper). */
  function wrapRangeWithHighlight(range, commentId) {
    try {
      const span = document.createElement("span");
      span.className = HIGHLIGHT_CLASS;
      span.setAttribute("data-comment-id", commentId);
      span.setAttribute("tabindex", "0");
      span.setAttribute("role", "button");
      span.setAttribute("aria-label", "Kommentar zu dieser Stelle anzeigen");
      range.surroundContents(span);
      span.addEventListener("click", function (ev) {
        ev.stopPropagation();
        openAnchorPopover(commentId, span);
      });
      return span;
    } catch (_) {
      return null;
    }
  }

  // ---------- API ----------

  async function fetchComments() {
    const res = await fetch(ENDPOINT + "?pageSlug=" + encodeURIComponent(pageSlug()), {
      credentials: "same-origin",
    });
    if (!res.ok) {
      return { error: res.status };
    }
    return await res.json();
  }

  async function postComment(payload) {
    const res = await fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(function () { return {}; });
      throw new Error(err.error || res.statusText);
    }
    return await res.json();
  }

  async function deleteComment(id) {
    const res = await fetch(ENDPOINT + "/" + encodeURIComponent(id), { method: "DELETE" });
    return res.ok;
  }

  // ---------- Rendering ----------

  function renderCommentRow(c) {
    const canDelete = !c.deleted && me && (
      (c.authorEmail && me.email && c.authorEmail.toLowerCase() === me.email.toLowerCase().split("@")[0]) ||
      me.role === "admin"
    );
    const name = c.authorName || c.authorEmail || "anon";
    const wrapper = el("div", { class: "wc-comment" + (c.deleted ? " wc-deleted" : ""), "data-id": c.id });
    wrapper.appendChild(el("div", { class: "wc-header" }, [
      el("span", { class: "wc-author" }, name),
      el("span", { class: "wc-ts" }, fmtTs(c.createdAt) + (c.editedAt ? " · bearbeitet" : "")),
    ]));
    wrapper.appendChild(el("div", { class: "wc-body", html: renderBody(c.bodyMd) }));
    const actions = el("div", { class: "wc-actions" }, [
      me && me.canPost
        ? el("button", {
            class: "wc-btn wc-btn-link",
            type: "button",
            onclick: function () { openReplyForm(c, wrapper); },
          }, "Antworten")
        : null,
      canDelete
        ? el("button", {
            class: "wc-btn wc-btn-link wc-btn-danger",
            type: "button",
            onclick: async function () {
              if (!window.confirm("Kommentar löschen?")) return;
              if (await deleteComment(c.id)) refresh();
            },
          }, "Löschen")
        : null,
    ]);
    wrapper.appendChild(actions);
    if (c._children && c._children.length) {
      const kids = el("div", { class: "wc-children" });
      c._children.forEach(function (k) { kids.appendChild(renderCommentRow(k)); });
      wrapper.appendChild(kids);
    }
    return wrapper;
  }

  function openReplyForm(parent, parentEl) {
    const existing = parentEl.querySelector(":scope > .wc-reply-form");
    if (existing) { existing.remove(); return; }
    parentEl.appendChild(renderForm(parent.id, parent.selectionAnchor || null));
  }

  function renderForm(parentId, selectionAnchor, opts) {
    opts = opts || {};
    const ta = el("textarea", {
      class: "wc-textarea",
      placeholder: parentId ? "Antwort schreiben…" : (selectionAnchor ? "Kommentar zu dieser Stelle…" : "Kommentar schreiben…"),
      maxlength: String(MAX_BODY_LENGTH),
      rows: "3",
    });
    const status = el("div", { class: "wc-form-status" });
    const submitBtn = el("button", {
      class: "wc-btn wc-btn-primary",
      type: "button",
      onclick: async function () {
        const body = ta.value.trim();
        if (!body) return;
        submitBtn.disabled = true;
        status.textContent = "Sende…";
        try {
          await postComment({
            pageSlug: pageSlug(),
            parentId: parentId || null,
            bodyMd: body,
            selection_anchor: selectionAnchor || null,
          });
          ta.value = "";
          status.textContent = "";
          if (opts.onSubmit) opts.onSubmit();
          await refresh();
        } catch (e) {
          status.textContent = "Fehler: " + e.message;
          submitBtn.disabled = false;
        }
      },
    }, parentId ? "Antworten" : "Senden");
    const cancelBtn = (parentId || opts.cancellable)
      ? el("button", {
          class: "wc-btn wc-btn-link",
          type: "button",
          onclick: function () {
            if (opts.onCancel) opts.onCancel();
            else {
              const f = ta.closest(".wc-reply-form, .wc-popover, .wc-new-form");
              if (f) f.remove();
            }
          },
        }, "Abbrechen")
      : null;
    return el("div", { class: parentId ? "wc-reply-form" : (selectionAnchor ? "wc-anchor-form" : "wc-new-form") }, [
      ta,
      el("div", { class: "wc-form-row" }, [submitBtn, cancelBtn, status]),
    ]);
  }

  // ---------- Popover (anchored thread) ----------

  function closeActivePopover() {
    if (activePopover) {
      activePopover.remove();
      activePopover = null;
    }
  }

  function positionPopover(pop, anchorRect) {
    const padding = 8;
    const docHeight = document.documentElement.scrollHeight;
    const docWidth = document.documentElement.scrollWidth;
    let top = window.scrollY + anchorRect.bottom + padding;
    let left = window.scrollX + anchorRect.left;
    if (left + 360 > docWidth) left = docWidth - 360 - padding;
    if (left < padding) left = padding;
    pop.style.top = top + "px";
    pop.style.left = left + "px";
  }

  function openAnchorPopover(rootCommentId, anchorEl) {
    closeActivePopover();
    const rootComment = allComments.find(function (c) { return c.id === rootCommentId; });
    if (!rootComment) return;
    // Collect root + all descendants
    const tree = buildTree(allComments);
    const rootNode = (function findNode(nodes) {
      for (const n of nodes) {
        if (n.id === rootCommentId) return n;
        const sub = findNode(n._children || []);
        if (sub) return sub;
      }
      return null;
    })(tree);
    if (!rootNode) return;
    const pop = el("div", { class: "wc-popover", role: "dialog", "aria-label": "Inline-Kommentarfaden" });
    pop.appendChild(el("div", { class: "wc-popover-close-row" }, [
      el("button", {
        class: "wc-btn wc-btn-link",
        type: "button",
        onclick: closeActivePopover,
      }, "Schließen"),
    ]));
    pop.appendChild(renderCommentRow(rootNode));
    if (me && me.canPost) {
      pop.appendChild(renderForm(rootCommentId, null));
    } else if (!me) {
      const callback = window.location.pathname + window.location.search;
      pop.appendChild(el("div", { class: "wc-signin-prompt-small" }, [
        el("a", { class: "wc-btn wc-btn-primary", href: "/login?callbackUrl=" + encodeURIComponent(callback) }, "Zum Antworten anmelden"),
      ]));
    }
    document.body.appendChild(pop);
    activePopover = pop;
    positionPopover(pop, anchorEl.getBoundingClientRect());
    // Close on outside click
    setTimeout(function () {
      document.addEventListener("click", function onDocClick(ev) {
        if (!pop.contains(ev.target) && ev.target !== anchorEl) {
          closeActivePopover();
          document.removeEventListener("click", onDocClick);
        }
      });
    }, 0);
  }

  function openNewAnchorComment(anchor, selectionRect) {
    closeActivePopover();
    if (!me || !me.canPost) return;
    const pop = el("div", { class: "wc-popover", role: "dialog", "aria-label": "Neuer Inline-Kommentar" });
    pop.appendChild(el("div", { class: "wc-popover-close-row" }, [
      el("button", { class: "wc-btn wc-btn-link", type: "button", onclick: closeActivePopover }, "Abbrechen"),
    ]));
    pop.appendChild(el("div", { class: "wc-anchor-preview" }, [
      el("span", { class: "wc-anchor-preview-label" }, "Markiert: "),
      el("span", { class: "wc-anchor-preview-text" }, '"' + anchor.exact + '"'),
    ]));
    pop.appendChild(renderForm(null, anchor, {
      cancellable: true,
      onCancel: closeActivePopover,
      onSubmit: closeActivePopover,
    }));
    document.body.appendChild(pop);
    activePopover = pop;
    positionPopover(pop, selectionRect);
  }

  // ---------- Floating "Kommentieren" action on selection ----------

  let floatingAction = null;

  function showFloatingAction(rect, anchor) {
    hideFloatingAction();
    const btn = el("button", {
      class: "wc-floating-action",
      type: "button",
      onclick: function (ev) {
        ev.stopPropagation();
        const r = btn.getBoundingClientRect();
        hideFloatingAction();
        openNewAnchorComment(anchor, r);
      },
    }, "Kommentieren");
    document.body.appendChild(btn);
    floatingAction = btn;
    const padding = 4;
    const top = window.scrollY + rect.top - 36;
    const left = window.scrollX + rect.left;
    btn.style.top = top + "px";
    btn.style.left = left + "px";
  }

  function hideFloatingAction() {
    if (floatingAction) {
      floatingAction.remove();
      floatingAction = null;
    }
  }

  function onSelectionChange() {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed) { hideFloatingAction(); return; }
    if (!me || !me.canPost) { hideFloatingAction(); return; }
    const text = sel.toString();
    if (!text || text.trim().length < 2) { hideFloatingAction(); return; }
    const range = sel.getRangeAt(0);
    if (isInsideWidget(range.startContainer) || isInsideWidget(range.endContainer)) {
      hideFloatingAction();
      return;
    }
    if (!docRoot.contains(range.commonAncestorContainer)) {
      hideFloatingAction();
      return;
    }
    const anchor = captureTextQuote(sel);
    if (!anchor) { hideFloatingAction(); return; }
    showFloatingAction(range.getBoundingClientRect(), anchor);
  }

  // ---------- Highlight rendering ----------

  function applyHighlights() {
    // Remove any existing highlight wrappers we previously added
    const existing = docRoot.querySelectorAll("." + HIGHLIGHT_CLASS);
    existing.forEach(function (sp) {
      const parent = sp.parentNode;
      while (sp.firstChild) parent.insertBefore(sp.firstChild, sp);
      parent.removeChild(sp);
      parent.normalize();
    });
    // Apply each anchored root comment's highlight (skip replies; replies inherit from root anchor)
    Object.keys(anchoredById).forEach(function (id) {
      const c = anchoredById[id];
      if (c.parentId) return;  // root anchors only
      if (!c.selectionAnchor) return;
      const range = findAnchorRange(c.selectionAnchor);
      if (range) wrapRangeWithHighlight(range, c.id);
    });
  }

  // ---------- Top-level refresh + render ----------

  function renderBottomThread(mount) {
    mount.classList.remove("wc-loading");
    mount.innerHTML = "";
    mount.appendChild(el("h2", { class: "wc-title" }, "Seiten-Kommentare"));
    mount.appendChild(el("p", { class: "wc-sub" }, "Kommentare zur ganzen Seite. Für Anmerkungen zu bestimmten Textstellen markiere oben einen Abschnitt und klicke „Kommentieren”."));

    const pageLevel = allComments.filter(function (c) { return !c.selectionAnchor; });
    if (pageLevel.length === 0) {
      mount.appendChild(el("p", { class: "wc-empty" }, "Noch keine Seiten-Kommentare."));
    } else {
      const tree = buildTree(pageLevel);
      const list = el("div", { class: "wc-list" });
      tree.forEach(function (c) { list.appendChild(renderCommentRow(c)); });
      mount.appendChild(list);
    }

    if (!me) {
      const callback = window.location.pathname + window.location.search;
      mount.appendChild(el("div", { class: "wc-signin-prompt" }, [
        el("p", null, "Zum Kommentieren anmelden."),
        el("a", { class: "wc-btn wc-btn-primary", href: "/login?callbackUrl=" + encodeURIComponent(callback) }, "Anmelden"),
      ]));
    } else if (!me.canPost) {
      mount.appendChild(el("div", { class: "wc-signin-prompt" }, [
        el("p", null, "Du bist als " + me.email + " angemeldet, aber nicht in der Wärme-Wimmer-Allowlist. Nicolas hinzufügen lassen."),
      ]));
    } else {
      mount.appendChild(el("div", { class: "wc-form-wrap" }, [
        el("div", { class: "wc-me-line" }, "Angemeldet als " + (me.name || me.email) + "."),
        renderForm(null, null),
      ]));
    }
  }

  async function refresh() {
    const mount = document.getElementById("wimmer-comments");
    if (mount) mount.classList.add("wc-loading");
    closeActivePopover();
    hideFloatingAction();
    const data = await fetchComments();
    if (data.error) {
      if (mount) mount.textContent = "Kommentare nicht verfügbar (Status " + data.error + ").";
      return;
    }
    me = data.me;
    allComments = data.comments || [];
    anchoredById = {};
    allComments.forEach(function (c) { if (c.selectionAnchor) anchoredById[c.id] = c; });
    if (mount) renderBottomThread(mount);
    applyHighlights();
  }

  // ---------- CSS ----------

  function injectCSS() {
    if (document.getElementById("wc-css")) return;
    const style = el("style", { id: "wc-css" });
    style.textContent =
      "#wimmer-comments{margin-top:48px;border-top:1px solid var(--border,#e2e8f0);padding-top:24px}" +
      "#wimmer-comments.wc-loading::before{content:'Lade Kommentare…';color:var(--text3,#94a3b8);font-size:13px}" +
      ".wc-title{font-size:18px;font-weight:700;margin-bottom:6px;color:var(--text,#0f172a)}" +
      ".wc-sub{font-size:12px;color:var(--text3,#94a3b8);margin-bottom:16px}" +
      ".wc-empty{color:var(--text3,#94a3b8);font-size:13px;margin-bottom:16px}" +
      ".wc-list{display:flex;flex-direction:column;gap:12px;margin-bottom:24px}" +
      ".wc-comment{background:var(--surface,#fff);border:1px solid var(--border,#e2e8f0);border-radius:8px;padding:12px 14px}" +
      ".wc-deleted{opacity:.55;font-style:italic}" +
      ".wc-header{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;gap:12px;flex-wrap:wrap}" +
      ".wc-author{font-weight:600;font-size:13px;color:var(--text,#0f172a)}" +
      ".wc-ts{font-size:11px;color:var(--text3,#94a3b8)}" +
      ".wc-body{font-size:14px;color:var(--text2,#475569);line-height:1.55;word-wrap:break-word}" +
      ".wc-body code{background:var(--surface2,#f1f5f9);padding:1px 5px;border-radius:4px;font-size:12px}" +
      ".wc-body a{color:var(--blue,#2563eb)}" +
      ".wc-actions{margin-top:8px;display:flex;gap:8px}" +
      ".wc-children{margin-left:20px;margin-top:10px;padding-left:12px;border-left:2px solid var(--border,#e2e8f0);display:flex;flex-direction:column;gap:10px}" +
      ".wc-btn{font-family:inherit;font-size:13px;padding:6px 14px;border-radius:6px;border:1px solid transparent;cursor:pointer;transition:background .15s,border-color .15s}" +
      ".wc-btn-primary{background:var(--blue,#2563eb);color:white;border-color:var(--blue,#2563eb);font-weight:600}" +
      ".wc-btn-primary:hover{background:var(--blue-dark,#1e40af)}" +
      ".wc-btn-primary:disabled{opacity:.5;cursor:not-allowed}" +
      ".wc-btn-link{background:transparent;color:var(--text2,#475569);font-size:12px;padding:4px 8px}" +
      ".wc-btn-link:hover{background:var(--surface2,#f1f5f9)}" +
      ".wc-btn-danger{color:var(--red,#dc2626)}" +
      ".wc-textarea{width:100%;font-family:inherit;font-size:14px;padding:10px 12px;border:1px solid var(--border,#e2e8f0);border-radius:8px;background:var(--surface,#fff);color:var(--text,#0f172a);resize:vertical}" +
      ".wc-textarea:focus{outline:2px solid var(--blue-light,#dbeafe);outline-offset:-1px;border-color:var(--blue,#2563eb)}" +
      ".wc-form-row{display:flex;align-items:center;gap:10px;margin-top:8px;flex-wrap:wrap}" +
      ".wc-form-status{font-size:12px;color:var(--text3,#94a3b8)}" +
      ".wc-new-form,.wc-anchor-form{margin-top:12px}" +
      ".wc-reply-form{margin-top:10px;padding:10px;background:var(--surface2,#f1f5f9);border-radius:6px}" +
      ".wc-signin-prompt{background:var(--surface2,#f1f5f9);border:1px dashed var(--border,#e2e8f0);border-radius:8px;padding:16px;text-align:center}" +
      ".wc-signin-prompt p{font-size:13px;color:var(--text2,#475569);margin-bottom:10px}" +
      ".wc-signin-prompt-small{padding:8px;text-align:center;font-size:12px}" +
      ".wc-me-line{font-size:12px;color:var(--text3,#94a3b8);margin-bottom:6px}" +
      // Inline highlight + floating action + popover
      "." + HIGHLIGHT_CLASS + "{background:rgba(252,211,77,0.45);cursor:pointer;padding:0 1px;border-radius:2px;transition:background .12s}" +
      "." + HIGHLIGHT_CLASS + ":hover{background:rgba(252,211,77,0.7)}" +
      "." + HIGHLIGHT_CLASS + ":focus{outline:2px solid var(--blue,#2563eb);outline-offset:1px}" +
      ".wc-floating-action{position:absolute;z-index:1000;font-family:inherit;font-size:12px;padding:6px 12px;border-radius:6px;background:var(--text,#0f172a);color:white;border:none;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,0.15)}" +
      ".wc-floating-action:hover{background:var(--blue,#2563eb)}" +
      ".wc-popover{position:absolute;z-index:1001;width:360px;max-width:calc(100vw - 16px);background:var(--surface,#fff);border:1px solid var(--border,#e2e8f0);border-radius:10px;box-shadow:0 12px 32px rgba(0,0,0,0.18);padding:12px}" +
      ".wc-popover-close-row{display:flex;justify-content:flex-end;margin-bottom:4px}" +
      ".wc-anchor-preview{background:var(--surface2,#f1f5f9);border-radius:6px;padding:8px 10px;margin-bottom:10px;font-size:12px;color:var(--text2,#475569)}" +
      ".wc-anchor-preview-label{font-weight:600;color:var(--text3,#94a3b8);text-transform:uppercase;letter-spacing:0.05em;font-size:10px;margin-right:6px}" +
      ".wc-anchor-preview-text{font-style:italic}";
    document.head.appendChild(style);
  }

  // ---------- Init ----------

  function init() {
    docRoot = getDocRoot();
    injectCSS();
    // Selection events: capture on mouseup so the browser has already updated
    // the Selection. Trim with selectionchange for keyboard selection too.
    document.addEventListener("mouseup", function () {
      // Defer so selection finalizes
      setTimeout(onSelectionChange, 10);
    });
    document.addEventListener("selectionchange", function () {
      // Debounce: only hide on collapse, don't show until mouseup
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed) hideFloatingAction();
    });
    // Close popover on Escape
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") {
        closeActivePopover();
        hideFloatingAction();
      }
    });
    refresh();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
