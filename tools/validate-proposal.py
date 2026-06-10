# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""
Proposal Quality Validator for Agentic Ops.

Validates proposal deliverables against established quality rules.
Every manual correction during proposal review should become a check here.

Usage:
    uv run tools/validate-proposal.py <slug>
    uv run tools/validate-proposal.py genius-pr
    uv run tools/validate-proposal.py alpha-research --verbose

Expects:
    platform/public/clients/{slug}/   -- site HTML files and downloadable artifacts
    workspace/proposals/{slug}/       -- cover letter, video script (working docs)
    platform/src/content/proposals/   -- proposal markdown with frontmatter
"""

import sys
import re
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from html.parser import HTMLParser


# ── Config ──────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
CLIENTS_DIR = ROOT / "platform" / "public" / "clients"
PROPOSALS_DIR = ROOT / "platform" / "src" / "content" / "proposals"
WORKING_DOCS_DIR = ROOT / "workspace" / "proposals"

REQUIRED_PAGES = ["index.html", "solution.html", "timeline.html",
                  "investment.html", "faq.html", "onboarding.html"]
OPTIONAL_PAGES = ["workflow.html", "gdpr.html", "print.html",
                  "proposal-pdf.html", "onboarding-pdf.html", "brief.html"]

OPENING_FORMULAS = [
    "Hi there, Nico here.",
    "Hi there, Matthias here.",
]

COVER_LETTER_BOUNDS = {
    "template_1_2": (8, 15),    # Track 1: 8-12 lines + some flexibility
    "template_3": (12, 35),     # Track 2: up to 30 lines + point-by-point
}

# Short-hook cover letter (pipeline change 2026-06-09, owner directive).
# The cover letter is now a <=225-character hook that does three jobs:
# (1) shows we understood the problem, (2) proves comparable past work,
# (3) names a short implementation. The Loom link + site URL + access code
# ride on a separate links block below a '---' divider and are NOT counted
# toward the 225. The new format is DETECTED by the presence of that '---'
# divider, so legacy long-form letters keep their old (line-count) rules and
# do not break `--all`.
COVER_LETTER_CHAR_CAP = 225

VIDEO_DURATION_CAPS = {
    "A": (2, 4),    # min target, hard cap
    "B": (2, 3),
    "C": (3, 4),
}

REQUIRED_FRONTMATTER = [
    "id", "slug", "prospect", "source", "project_title",
    "status", "track", "created", "deliverables",
]

TBD_PATTERNS = [
    r'\$TBD',
    r'\bTBD\b',
    r'\{[^}]*TBD[^}]*\}',
    r'_\{.*?pending.*?\}_',
    r'\[YOUR.*?\]',
    r'\[your.*?\]',
    r'\bVIDEO_LINK\b',
    r'\{VIDEO_LINK\}',
    r'\{loom_link\}',
    r'\{loom link\}',
    r'\{loom.*?pending\}',
]

# Abbreviation enforcement for video script SAY: lines.
# Per feedback_video_script_human_language.md: spoken lines must use plain language.
# Abbreviations need an inline gloss (3-8 words) the first time they appear,
# unless they're in COMMON_ABBREVIATIONS.
COMMON_ABBREVIATIONS = {
    # Truly ubiquitous tech
    'AI', 'API', 'UI', 'URL', 'HTML', 'CSS', 'JS', 'JSON', 'XML',
    'SQL', 'OS', 'CSV', 'HTTP', 'HTTPS', 'PDF', 'TCP', 'IP', 'DNS',
    # Business common
    'CRM', 'CEO', 'CTO', 'CFO', 'COO', 'CMO', 'VP',
    'B2B', 'B2C', 'KPI', 'ROI',
    'IT', 'HR', 'PR', 'QA', 'UX',
    # Geo
    'EU', 'US', 'UK', 'USA', 'EMEA', 'APAC',
    # Misc
    'AM', 'PM', 'OK', 'TBD', 'FAQ',
}
# Patterns that indicate an abbreviation is being explained inline.
# Checked in the ~120 chars right after the first occurrence.
EXPLANATION_PATTERNS = [
    r',\s+which\s+(?:is\s+)?',
    r',\s+the\s+',
    r',\s+a\s+',
    r',\s+two\s+',
    r',\s+three\s+',
    r',\s+meaning\s+',
    r',\s+essentially\s+',
    r',\s+just\s+',
    r',\s+that\s+is\s+',
    r'\s+\([^)]{6,}\)',     # parenthetical with 6+ chars (gloss-sized)
    r'\s+stands\s+for\s+',
    r'\s+aka\s+',
    r'\s+also\s+known\s+as\s+',
]

# Public platform directories to scan for client name leaks
PUBLIC_PLATFORM_DIRS = [
    "platform/src/app",
    "platform/src/components",
]


# ── Data ────────────────────────────────────────────────────────────────

@dataclass
class Check:
    name: str
    status: str  # PASS, FAIL, WARN, SKIP
    detail: str = ""

    def __str__(self):
        line = f"{self.status}: {self.name}"
        if self.detail:
            line += f" -- {self.detail}"
        return line


@dataclass
class ValidationReport:
    slug: str
    checks: list[Check] = field(default_factory=list)

    def add(self, name: str, status: str, detail: str = ""):
        self.checks.append(Check(name, status, detail))

    @property
    def passes(self):
        return [c for c in self.checks if c.status == "PASS"]

    @property
    def fails(self):
        return [c for c in self.checks if c.status == "FAIL"]

    @property
    def warns(self):
        return [c for c in self.checks if c.status == "WARN"]

    @property
    def skips(self):
        return [c for c in self.checks if c.status == "SKIP"]


# ── HTML Heading Extractor ──────────────────────────────────────────────

class HeadingExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.headings: list[str] = []
        self.nav_links: list[str] = []
        self._in_heading = False
        self._in_nav = False
        self._in_a = False
        self._current_text = ""
        self._heading_tags = {"h1", "h2", "h3", "h4"}
        self.has_theme_toggle = False
        self.has_data_theme = False
        self.has_access_gate = False
        self._raw = ""

    def feed(self, data):
        self._raw = data
        super().feed(data)

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag in self._heading_tags:
            self._in_heading = True
            self._current_text = ""
        if tag == "nav":
            self._in_nav = True
        if tag == "a" and self._in_nav:
            self._in_a = True
            self._current_text = ""
        if "data-theme" in attrs_dict:
            self.has_data_theme = True
        if attrs_dict.get("class", "").find("access") != -1:
            self.has_access_gate = True
        if attrs_dict.get("id", "").find("access") != -1:
            self.has_access_gate = True
        # Password inputs in proposal sites are access gates
        if tag == "input" and attrs_dict.get("type") == "password":
            self.has_access_gate = True

    def handle_endtag(self, tag):
        if tag in self._heading_tags and self._in_heading:
            self._in_heading = False
            text = self._current_text.strip()
            if text:
                self.headings.append(text)
        if tag == "nav":
            self._in_nav = False
        if tag == "a" and self._in_a:
            self._in_a = False
            text = self._current_text.strip()
            if text:
                self.nav_links.append(text)

    def handle_data(self, data):
        if self._in_heading or self._in_a:
            self._current_text += data
        if "toggleTheme" in data or "toggle-theme" in data or "themeToggle" in data:
            self.has_theme_toggle = True
        if "access-gate" in data or "accessGate" in data or "checkAccess" in data:
            self.has_access_gate = True


# ── Frontmatter Parser ──────────────────────────────────────────────────

def parse_frontmatter(text: str) -> dict | None:
    """Extract YAML frontmatter from markdown file."""
    import yaml
    match = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
    if not match:
        return None
    try:
        return yaml.safe_load(match.group(1))
    except Exception:
        return None


def parse_cover_letter(content: str) -> tuple[str, str, bool]:
    """Split a cover letter into (hook_text, links_text, is_short_format).

    The short-hook format separates the <=225-char hook from the links block
    with a standalone '---' divider:

        # Cover Letter -- Prospect (p026)

        <hook paragraph, <=225 chars, covers understand/proof/implementation>

        ---
        Walkthrough: https://loom.com/...
        Full plan: https://unpauseai.com/clients/slug/  (access code: slug-2026)

    hook_text  = everything before the first standalone '---', minus markdown
                 header lines ('# ...'), joined to a single string.
    links_text = everything after the divider.
    is_short_format = True when a divider is present (the new pipeline format).
                 Legacy long letters have no divider -> keep their old rules.
    """
    body = content.strip()
    parts = re.split(r'(?m)^[ \t]*---[ \t]*$', body, maxsplit=1)
    hook_raw = parts[0]
    links_raw = parts[1] if len(parts) > 1 else ""
    hook_lines = [
        l.strip() for l in hook_raw.split("\n")
        if l.strip() and not l.strip().startswith("#")
    ]
    hook_text = " ".join(hook_lines).strip()
    is_short_format = len(parts) > 1
    return hook_text, links_raw.strip(), is_short_format


# ── Check Functions ─────────────────────────────────────────────────────

def check_frontmatter(report: ValidationReport, fm: dict | None, slug: str):
    """Validate proposal markdown frontmatter."""
    if fm is None:
        report.add("Frontmatter exists", "FAIL", "No frontmatter found in proposal markdown")
        return

    report.add("Frontmatter exists", "PASS")

    missing = [f for f in REQUIRED_FRONTMATTER if f not in fm]
    if missing:
        report.add("Required frontmatter fields", "FAIL", f"Missing: {', '.join(missing)}")
    else:
        report.add("Required frontmatter fields", "PASS")

    if fm.get("status") == "sent" and fm.get("sent") is None:
        report.add("Sent date consistency", "FAIL", "Status is 'sent' but sent date is null")
    else:
        report.add("Sent date consistency", "PASS")


def check_deliverables_match(report: ValidationReport, fm: dict, client_dir: Path, working_dir: Path):
    """Verify deliverables flags match actual files."""
    if not fm or "deliverables" not in fm:
        report.add("Deliverables consistency", "SKIP", "No deliverables in frontmatter")
        return

    deliverables = fm["deliverables"]

    # Check cover letter (in working docs dir or legacy client dir)
    has_letter_file = (any(working_dir.glob("cover-letter*")) if working_dir.exists() else False) or \
                      any(client_dir.glob("cover-letter*"))
    letter_flag = deliverables.get("letter", False)
    if letter_flag and not has_letter_file:
        report.add("Deliverables: letter flag", "FAIL",
                    "letter: true but no cover-letter file found")
    elif not letter_flag and has_letter_file:
        report.add("Deliverables: letter flag", "WARN",
                    "cover-letter file exists but letter: false in frontmatter")
    else:
        report.add("Deliverables: letter flag", "PASS")

    # Check video script (in working docs dir or legacy client dir)
    has_video_file = (any(working_dir.glob("video-script*")) if working_dir.exists() else False) or \
                     any(client_dir.glob("video-script*"))
    video_flag = deliverables.get("video", False)
    if video_flag and not has_video_file:
        report.add("Deliverables: video flag", "FAIL",
                    "video: true but no video-script file found")
    elif not video_flag and has_video_file:
        report.add("Deliverables: video flag", "WARN",
                    "video-script file exists but video: false in frontmatter")
    else:
        report.add("Deliverables: video flag", "PASS")

    # Check site
    has_site = (client_dir / "index.html").exists()
    site_flag = deliverables.get("site", False)
    if site_flag and not has_site:
        report.add("Deliverables: site flag", "FAIL",
                    "site: true but no index.html found")
    elif not site_flag and has_site:
        report.add("Deliverables: site flag", "WARN",
                    "index.html exists but site: false in frontmatter")
    else:
        report.add("Deliverables: site flag", "PASS")


def check_cover_letter(report: ValidationReport, client_dir: Path, fm: dict, working_dir: Path | None = None):
    """Validate cover letter.

    Two formats are recognised:
      * short-hook (current pipeline, owner directive 2026-06-09): a <=225-char
        hook + a '---' divider + a links block. Detected by the divider; the
        hook char cap is a hard FAIL.
      * legacy long-form: the old line-count template rules. Kept intact so
        already-sent proposals stay green under `--all`.
    """
    letter_files = list((working_dir or client_dir).glob("cover-letter*.md"))
    if not letter_files:
        # Fallback to client_dir for legacy proposals
        letter_files = list(client_dir.glob("cover-letter*.md"))
    if not letter_files:
        report.add("Cover letter exists", "SKIP", "No cover letter found")
        return

    track = fm.get("track", 1) if fm else 1
    access_code = fm.get("access_code") if fm else None

    for letter_path in letter_files:
        suffix = f" ({letter_path.name})" if len(letter_files) > 1 else ""
        content = letter_path.read_text(encoding="utf-8")

        # No em dashes (both formats)
        if "\u2014" in content:
            report.add(f"No em dashes{suffix}", "FAIL",
                       f"Found {content.count(chr(0x2014))} em dash(es) -- use commas/semicolons")
        else:
            report.add(f"No em dashes{suffix}", "PASS")

        hook_text, links_text, is_short = parse_cover_letter(content)
        if is_short:
            _check_short_hook_letter(report, suffix, hook_text, links_text, track, access_code)
        else:
            _check_legacy_letter(report, suffix, content, track, access_code)


def _check_short_hook_letter(report, suffix, hook_text, links_text, track, access_code):
    """Checks for the <=225-char short-hook format (the current pipeline)."""
    n = len(hook_text)
    if n == 0:
        report.add(f"Cover letter hook <=225 chars{suffix}", "FAIL",
                   "No hook text found before the '---' links divider.")
    elif n > COVER_LETTER_CHAR_CAP:
        report.add(f"Cover letter hook <=225 chars{suffix}", "FAIL",
                   f"Hook is {n} chars (max {COVER_LETTER_CHAR_CAP}). Trim to the three "
                   f"jobs: understanding, comparable past work, short implementation.")
    else:
        report.add(f"Cover letter hook <=225 chars{suffix}", "PASS", f"{n} chars")

    # Plain text (no markdown) in the hook -- it gets pasted into Upwork
    md_hit = any(re.search(p, hook_text) for p in (r'\*\*[^*]+\*\*', r'\[[^\]]+\]\([^)]+\)'))
    if md_hit:
        report.add(f"Hook plain text (no markdown){suffix}", "WARN",
                   "Markdown formatting found in the hook")
    else:
        report.add(f"Hook plain text (no markdown){suffix}", "PASS")

    # Walkthrough pointer lives in the links block
    has_video = bool(re.search(
        r'(loom\.com|youtube\.com|youtu\.be|vimeo\.com|loom link|video link|walkthrough)',
        links_text, re.I))
    if has_video:
        report.add(f"Walkthrough link in links block{suffix}", "PASS")
    else:
        report.add(f"Walkthrough link in links block{suffix}", "WARN",
                   "No Loom/video link or 'walkthrough' pointer in the links block")

    # Track 2: site URL + access code live in the links block
    if track == 2:
        if re.search(r'https?://\S+', links_text):
            report.add(f"Site URL in links block{suffix}", "PASS")
        else:
            report.add(f"Site URL in links block{suffix}", "WARN",
                       "No site URL in the links block")
        if access_code:
            if access_code.lower() in links_text.lower():
                report.add(f"Access code in links block{suffix}", "PASS")
            else:
                report.add(f"Access code in links block{suffix}", "FAIL",
                           f"Access code '{access_code}' not found in the links block")


def _check_legacy_letter(report, suffix, content, track, access_code):
    """Legacy long-form template rules (pre-2026-06-09 proposals)."""
    lines = content.strip().split("\n")
    body_lines = []
    in_body = False
    for line in lines:
        stripped = line.strip()
        if not in_body:
            if stripped.startswith("## Upwork") or stripped.startswith("## Plain"):
                in_body = True
                continue
            if not stripped.startswith("#") and stripped:
                in_body = True
                body_lines.append(line)
        else:
            if stripped:
                body_lines.append(line)

    if not body_lines:
        body_lines = [l for l in lines if l.strip() and not l.strip().startswith("#")]

    if track == 2 and access_code:
        first_3 = "\n".join(body_lines[:3]).lower()
        if access_code.lower() not in first_3:
            report.add(f"Template 3: access code in first 3 lines{suffix}", "FAIL",
                       f"Access code '{access_code}' not found in first 3 lines of letter body")
        else:
            report.add(f"Template 3: access code in first 3 lines{suffix}", "PASS")

    first_3_text = "\n".join(body_lines[:3])
    has_video_link = bool(re.search(r'(loom\.com|youtube\.com|youtu\.be|vimeo\.com)', first_3_text, re.I))
    has_video_placeholder = bool(re.search(r'(loom link|video link|walkthrough)', first_3_text, re.I))
    if has_video_link or has_video_placeholder:
        report.add(f"Video link in first 3 lines{suffix}", "PASS")
    else:
        report.add(f"Video link in first 3 lines{suffix}", "WARN",
                   "No video link or placeholder found in first 3 lines")

    markdown_patterns = [
        (r'\*\*[^*]+\*\*', "bold (**text**)"),
        (r'\*[^*]+\*', "italic (*text*)"),
        (r'\[([^\]]+)\]\([^)]+\)', "markdown links"),
    ]
    md_issues = []
    for pattern, desc in markdown_patterns:
        for i, line in enumerate(body_lines):
            if re.search(pattern, line):
                md_issues.append(f"line {i+1}: {desc}")
                break
    if md_issues:
        report.add(f"Plain text format (no markdown){suffix}", "WARN",
                   f"Found: {'; '.join(md_issues[:3])}")
    else:
        report.add(f"Plain text format (no markdown){suffix}", "PASS")

    non_empty = [l for l in body_lines if l.strip()]
    bounds = COVER_LETTER_BOUNDS["template_3"] if track == 2 else COVER_LETTER_BOUNDS["template_1_2"]
    if len(non_empty) < bounds[0]:
        report.add(f"Cover letter length{suffix}", "WARN",
                   f"{len(non_empty)} lines (minimum {bounds[0]})")
    elif len(non_empty) > bounds[1]:
        report.add(f"Cover letter length{suffix}", "WARN",
                   f"{len(non_empty)} lines (maximum {bounds[1]})")
    else:
        report.add(f"Cover letter length{suffix}", "PASS",
                   f"{len(non_empty)} lines")

    full_text = content.lower()
    has_forward = any(p in full_text for p in [
        "if we move forward", "if we work together",
        "if you'd like to move forward", "if this direction",
        "if this aligns", "if useful",
    ])
    if has_forward:
        report.add(f"Forward/optionality block{suffix}", "PASS")
    else:
        report.add(f"Forward/optionality block{suffix}", "WARN",
                   "No 'if we move forward' or optionality statement found")


def _check_video_guide(report, suffix, content):
    """Checks for the content-guide video format (owner directive 2026-06-09).

    The video deliverable is now a guide to what each part needs to land,
    spoken in the proposer's own words, not a verbatim SAY:/>> teleprompter
    script. So the script-specific checks (opening formula, BEAT markers,
    SAY/>> interleaving, LOOM NOTES) do not apply. A guide is checked for
    zero em dashes and a sectioned structure instead.
    """
    if "—" in content:
        report.add(f"No em dashes in video guide{suffix}", "FAIL",
                   f"Found {content.count(chr(0x2014))} em dash(es)")
    else:
        report.add(f"No em dashes in video guide{suffix}", "PASS")

    sections = re.findall(r'(?m)^##\s+\S', content)
    if len(sections) >= 3:
        report.add(f"Video guide structure{suffix}", "PASS", f"{len(sections)} sections")
    else:
        report.add(f"Video guide structure{suffix}", "WARN",
                   f"only {len(sections)} '##' sections (expected 3+ beats to cover)")

    # Blueprint marker: the guide ends with a "Terms to gloss" section so any
    # spoken jargon gets a plain-language gloss on camera. See VIDEO-SCRIPT.md.
    if re.search(r'(?im)^##\s+.*terms?\s+to\s+gloss', content):
        report.add(f"Video guide terms-to-gloss block{suffix}", "PASS")
    else:
        report.add(f"Video guide terms-to-gloss block{suffix}", "WARN",
                   "No '## Terms to gloss' section. The blueprint ends with a short "
                   "list glossing any spoken jargon (see VIDEO-SCRIPT.md).")

    report.add(f"Video format{suffix}", "PASS", "content guide (not verbatim script)")


def check_video_script(report: ValidationReport, client_dir: Path, site_headings: dict[str, list[str]], working_dir: Path | None = None):
    """Validate video deliverable. Two formats:

    * content guide (current, owner directive 2026-06-09): points to land in
      the proposer's own words. Detected by the ABSENCE of SAY:/>> markers.
    * legacy verbatim script: SAY:/>> teleprompter lines, BEAT markers, LOOM
      NOTES. Kept so already-shipped proposals stay green.
    """
    script_files = list((working_dir or client_dir).glob("*video-script*.md"))
    if not script_files:
        # Fallback to client_dir for legacy proposals
        script_files = list(client_dir.glob("*video-script*.md"))
    if not script_files:
        report.add("Video script exists", "SKIP", "No video script found")
        return

    for script_path in script_files:
        suffix = f" ({script_path.name})" if len(script_files) > 1 else ""
        content = script_path.read_text(encoding="utf-8")

        # Format detection: a content guide has no SAY:/>> markers. Route it
        # to the lighter guide checks and skip the verbatim-script checks.
        is_script = bool(re.search(r'(?m)^\s*SAY:', content)) or bool(re.search(r'(?m)^\s*>>', content))
        if not is_script:
            _check_video_guide(report, suffix, content)
            continue

        # Opening formula (accept any registered proposer)
        if any(formula in content for formula in OPENING_FORMULAS):
            report.add(f"Opening formula{suffix}", "PASS")
        else:
            report.add(f"Opening formula{suffix}", "FAIL",
                       f'Expected one of: {OPENING_FORMULAS}')

        # 3-beat structure
        beats_found = []
        if re.search(r'BEAT\s*1', content, re.I):
            beats_found.append("1")
        if re.search(r'BEAT\s*2', content, re.I):
            beats_found.append("2")
        if re.search(r'BEAT\s*3', content, re.I):
            beats_found.append("3")

        if len(beats_found) == 3:
            report.add(f"3-beat structure{suffix}", "PASS")
        elif len(beats_found) > 0:
            report.add(f"3-beat structure{suffix}", "WARN",
                       f"Found beats {', '.join(beats_found)} -- expected 1, 2, 3")
        else:
            report.add(f"3-beat structure{suffix}", "FAIL", "No BEAT markers found")

        # SAY/>> interleaving check
        lines = content.split("\n")
        action_lines = []
        say_lines = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(">>"):
                action_lines.append(i)
            elif stripped.startswith("SAY:"):
                say_lines.append(i)

        # Check that actions and speech are interleaved, not front-loaded
        if action_lines and say_lines:
            # Find stretches of 3+ consecutive >> without a SAY
            consecutive_actions = 0
            max_consecutive = 0
            for i in range(len(lines)):
                stripped = lines[i].strip()
                if stripped.startswith(">>"):
                    consecutive_actions += 1
                    max_consecutive = max(max_consecutive, consecutive_actions)
                elif stripped.startswith("SAY:"):
                    consecutive_actions = 0
                elif stripped and not stripped.startswith(("-", "=", "#", "---")):
                    consecutive_actions = 0

            if max_consecutive >= 4:
                report.add(f"SAY/>> interleaving{suffix}", "WARN",
                           f"Found {max_consecutive} consecutive >> actions without SAY")
            else:
                report.add(f"SAY/>> interleaving{suffix}", "PASS")
        else:
            report.add(f"SAY/>> interleaving{suffix}", "FAIL",
                       "No SAY:/>> markers found -- video script must use SAY: for speech and >> for screen actions")

        # Check for LOOM NOTES VERSION section (required for teleprompter)
        if "LOOM NOTES" in content.upper():
            report.add(f"Loom Notes section{suffix}", "PASS")
        else:
            report.add(f"Loom Notes section{suffix}", "FAIL",
                       "Missing ## LOOM NOTES VERSION section -- required for teleprompter/Loom Notes")

        # Cross-check >> page/section references against actual HTML headings
        # Only check "Scroll to" and "Click {nav item}" -- skip UI interactions
        if site_headings:
            # Match: >> Scroll to "X", >> Click "X" in top nav
            section_refs = re.findall(
                r'>>\s*(?:Scroll to|Navigate to)\s+"?([^"\n]+)"?', content)
            nav_click_refs = re.findall(
                r'>>\s*Click\s+"?([^"\n]+?)"?\s+in\s+(?:top\s+)?nav', content)
            all_refs = section_refs + nav_click_refs

            all_headings_flat = []
            for page_headings in site_headings.values():
                all_headings_flat.extend(page_headings)

            # Also check against page filenames (nav clicks like "Solution" -> solution.html)
            page_names = [p.stem.replace("-", " ").title()
                          for p in client_dir.glob("*.html")]

            mismatches = []
            for ref in all_refs:
                ref_clean = ref.strip().rstrip(".").strip('"')
                found = False
                # Check headings
                for heading in all_headings_flat:
                    if ref_clean.lower() in heading.lower() or heading.lower() in ref_clean.lower():
                        found = True
                        break
                # Check page names (for nav clicks)
                if not found:
                    for pname in page_names:
                        if ref_clean.lower() == pname.lower():
                            found = True
                            break
                # Check if it matches a filename directly
                if not found:
                    if (client_dir / f"{ref_clean.lower()}.html").exists():
                        found = True
                if not found:
                    mismatches.append(ref_clean)

            if mismatches:
                report.add(f"Video script heading cross-check{suffix}", "WARN",
                           f"References not found in HTML headings: {', '.join(mismatches[:5])}")
            elif all_refs:
                report.add(f"Video script heading cross-check{suffix}", "PASS",
                           f"Checked {len(all_refs)} section/nav references")
            else:
                report.add(f"Video script heading cross-check{suffix}", "SKIP",
                           "No section/nav references found in script")

        # No em dashes in script
        if "\u2014" in content:
            report.add(f"No em dashes in script{suffix}", "FAIL",
                       f"Found {content.count(chr(0x2014))} em dash(es)")
        else:
            report.add(f"No em dashes in script{suffix}", "PASS")


def check_video_script_abbreviations(report: ValidationReport, client_dir: Path, working_dir: Path | None = None):
    """Flag abbreviations in SAY: lines that don't have an inline gloss.

    Spoken content needs to land in the ear on first pass. Per
    feedback_video_script_human_language.md, any abbreviation not in
    COMMON_ABBREVIATIONS must be followed by a short explanation
    (matched against EXPLANATION_PATTERNS) within ~120 chars of first mention.

    Only SAY: lines are scanned (>> stage directions and LOOM NOTES are exempt).
    """
    script_files = list((working_dir or client_dir).glob("*video-script*.md"))
    if not script_files:
        script_files = list(client_dir.glob("*video-script*.md"))
    if not script_files:
        return

    for script_path in script_files:
        suffix = f" ({script_path.name})" if len(script_files) > 1 else ""
        content = script_path.read_text(encoding="utf-8")

        # Cut LOOM NOTES section out (teleprompter cues are silent, abbreviations OK)
        loom_split = re.split(r'(?im)^##\s*LOOM\s+NOTES', content)
        spoken_section = loom_split[0]

        # Collect only SAY: line text
        say_lines = [
            re.sub(r'^\s*SAY:\s*', '', line)
            for line in spoken_section.split("\n")
            if line.strip().startswith("SAY:")
        ]
        if not say_lines:
            report.add(f"Video script: abbreviation glosses{suffix}", "SKIP",
                       "No SAY: lines found")
            continue
        say_text = "\n".join(say_lines)

        # Find ALL-CAPS abbreviations (2-6 chars, word boundary).
        # \b[A-Z][A-Z0-9]{1,5}\b — must start with letter, can include digits (e.g. B2B).
        candidates_raw = re.findall(r'\b[A-Z][A-Z0-9]{1,5}\b', say_text)
        candidates = set(candidates_raw) - COMMON_ABBREVIATIONS

        if not candidates:
            report.add(f"Video script: abbreviation glosses{suffix}", "PASS")
            continue

        violations = []
        for abbr in sorted(candidates):
            first_match = re.search(rf'\b{re.escape(abbr)}\b', say_text)
            if not first_match:
                continue
            # Window: 120 chars after first occurrence
            context = say_text[first_match.end():first_match.end() + 120]
            has_gloss = any(re.search(pat, context, re.I) for pat in EXPLANATION_PATTERNS)
            if not has_gloss:
                violations.append(abbr)

        if violations:
            report.add(
                f"Video script: abbreviation glosses{suffix}",
                "FAIL",
                f"Abbreviations without inline gloss in SAY: lines: {', '.join(violations)}. "
                f"Keep the abbreviation in (it signals expertise) and add a 3-8 word inline gloss "
                f"the first time it appears, e.g., 'SKU, the product code each supplier uses' or "
                f"'a CLI, a command-line tool you run in the terminal'. "
                f"Do not strip the term to plain language; that removes signal. "
                f"Exempt (no gloss needed): {', '.join(sorted(COMMON_ABBREVIATIONS))}. "
                f"See rule_deliverables.md 'Video script humanness' and feedback_video_script_human_language.md.",
            )
        else:
            report.add(f"Video script: abbreviation glosses{suffix}", "PASS")


def check_html_site(report: ValidationReport, client_dir: Path, fm: dict) -> dict[str, list[str]]:
    """Validate HTML site pages. Returns extracted headings per page."""
    site_headings: dict[str, list[str]] = {}

    if not (client_dir / "index.html").exists():
        report.add("HTML site exists", "SKIP", "No index.html found")
        return site_headings

    report.add("HTML site exists", "PASS")

    # Required pages
    present = []
    missing = []
    for page in REQUIRED_PAGES:
        if (client_dir / page).exists():
            present.append(page)
        else:
            missing.append(page)

    if missing:
        report.add("Required pages present", "FAIL",
                    f"Missing: {', '.join(missing)}")
    else:
        report.add("Required pages present", "PASS",
                    f"All {len(REQUIRED_PAGES)} required pages found")

    # Extract headings and check per-page requirements
    html_files = sorted(client_dir.glob("*.html"))
    for html_path in html_files:
        try:
            content = html_path.read_text(encoding="utf-8")
        except Exception:
            continue

        extractor = HeadingExtractor()
        try:
            extractor.feed(content)
        except Exception:
            continue

        site_headings[html_path.name] = extractor.headings

        # Theme toggle check (only on index.html to avoid noise)
        if html_path.name == "index.html":
            if extractor.has_data_theme:
                report.add("Theme toggle (data-theme)", "PASS")
            else:
                report.add("Theme toggle (data-theme)", "FAIL",
                           "No data-theme attribute found on index.html")

            if extractor.has_theme_toggle:
                report.add("Theme toggle (JS function)", "PASS")
            else:
                report.add("Theme toggle (JS function)", "WARN",
                           "No toggleTheme function detected")

        # Access gate check
        if html_path.name == "index.html" and fm and fm.get("access_code"):
            if extractor.has_access_gate:
                report.add("Access gate present", "PASS")
            else:
                report.add("Access gate present", "FAIL",
                           f"access_code is '{fm['access_code']}' but no access gate found in HTML")

    # TBD placeholder scan across all HTML
    tbd_findings = []
    for html_path in html_files:
        try:
            content = html_path.read_text(encoding="utf-8")
        except Exception:
            continue

        for i, line in enumerate(content.split("\n"), 1):
            # Skip script/style blocks for TBD scan
            if "<script" in line.lower() or "<style" in line.lower():
                continue
            for pattern in TBD_PATTERNS:
                if re.search(pattern, line, re.I):
                    tbd_findings.append(f"{html_path.name}:{i}")
                    break

    if tbd_findings:
        report.add("No TBD placeholders in HTML", "FAIL",
                    f"Found at {', '.join(tbd_findings[:5])}" +
                    (f" (+{len(tbd_findings)-5} more)" if len(tbd_findings) > 5 else ""))
    else:
        report.add("No TBD placeholders in HTML", "PASS")

    # Credential/API key input fields (Alpha Research R2: never put these in proposals)
    credential_findings = []
    for html_path in html_files:
        try:
            content = html_path.read_text(encoding="utf-8")
        except Exception:
            continue
        # Scan for input fields that look like credential/secret inputs
        cred_patterns = [
            (r'<input[^>]*type=["\']password["\']', "password input"),
            (r'<input[^>]*(?:api.?key|secret|token|credential)', "credential input"),
            (r'<textarea[^>]*(?:api.?key|secret|token|credential)', "credential textarea"),
        ]
        for pattern, desc in cred_patterns:
            matches = re.finditer(pattern, content, re.I)
            for m in matches:
                line_num = content[:m.start()].count("\n") + 1
                # Skip auth-gate password inputs (access code entry, not a credential field)
                ctx_start = max(0, m.start() - 200)
                surrounding = content[ctx_start:m.end() + 100]
                if 'auth-gate' in surrounding or 'auth-input' in surrounding or 'access code' in surrounding.lower():
                    continue
                credential_findings.append(f"{html_path.name}:{line_num} ({desc})")

    if credential_findings:
        report.add("No credential input fields in HTML", "FAIL",
                    f"Found: {', '.join(credential_findings[:3])}")
    else:
        report.add("No credential input fields in HTML", "PASS")

    # CSS HTML entity rendering bug (Alpha Research R2: &#xxxx; in CSS content = literal text)
    css_entity_findings = []
    for html_path in html_files:
        try:
            content = html_path.read_text(encoding="utf-8")
        except Exception:
            continue
        # Find <style> blocks and scan for HTML entities in content properties
        style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', content, re.DOTALL | re.I)
        for block in style_blocks:
            for i, line in enumerate(block.split("\n")):
                if "content:" in line and "&#" in line:
                    css_entity_findings.append(
                        f"{html_path.name}: CSS content with HTML entity (use Unicode escape like \\2713)")

    if css_entity_findings:
        report.add("No HTML entities in CSS content", "FAIL",
                    f"Found: {', '.join(css_entity_findings[:3])}")
    else:
        report.add("No HTML entities in CSS content", "PASS")

    # Nav link resolution (only check inter-page links, not Vercel clean URLs)
    broken_nav = []
    for html_path in html_files:
        try:
            content = html_path.read_text(encoding="utf-8")
        except Exception:
            continue

        # Only check href links that point to sibling HTML files
        nav_hrefs = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>', content)
        for href in nav_hrefs:
            # Skip external, mailto, anchor, and absolute path links (work on Vercel)
            if (href.startswith("http") or href.startswith("mailto:") or
                    href.startswith("#") or href.startswith("/")):
                continue
            # Check relative links to sibling files
            target = href.split("#")[0].split("?")[0]
            if target and not (client_dir / target).exists():
                broken_nav.append(f"{html_path.name} -> {href}")

    if broken_nav:
        report.add("Nav link resolution (relative links)", "WARN",
                    f"{len(broken_nav)} broken: {', '.join(broken_nav[:3])}")
    else:
        report.add("Nav link resolution (relative links)", "PASS")

    # Run validate-html.py if available
    validate_html = ROOT / "tools" / "validate-html.py"
    if validate_html.exists():
        try:
            result = subprocess.run(
                ["uv", "run", str(validate_html)] + [str(f) for f in html_files],
                capture_output=True, text=True, timeout=30,
                cwd=str(ROOT)
            )
            error_count = 0
            for line in result.stdout.split("\n"):
                if "ERROR:" in line:
                    error_count += 1
            if error_count > 0:
                report.add("HTML structural validation (validate-html.py)", "WARN",
                           f"{error_count} error(s) from validate-html.py")
            else:
                report.add("HTML structural validation (validate-html.py)", "PASS")
        except Exception as e:
            report.add("HTML structural validation (validate-html.py)", "SKIP",
                       f"Could not run: {e}")

    return site_headings


def check_pricing_not_tbd(report: ValidationReport, client_dir: Path):
    """Verify investment page has actual pricing, not placeholders."""
    investment = client_dir / "investment.html"
    if not investment.exists():
        report.add("Pricing: actual numbers present", "SKIP", "No investment.html")
        return

    content = investment.read_text(encoding="utf-8")
    # Strip script/style blocks to avoid false positives from JS variables
    stripped = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.I)
    stripped = re.sub(r'<style[^>]*>.*?</style>', '', stripped, flags=re.DOTALL | re.I)

    # Look for at least one actual price ($ or EUR followed by digit)
    has_price = bool(re.search(r'[\$\u20AC]\s*[\d,]+', stripped)) or \
                bool(re.search(r'EUR\s*[\d,]+', stripped, re.I))
    if has_price:
        report.add("Pricing: actual numbers present", "PASS")
    else:
        report.add("Pricing: actual numbers present", "FAIL",
                    "investment.html has no price ($X or EUR X). Never ship $TBD pricing.")


def check_pricing_bridge(report: ValidationReport, client_dir: Path, fm: dict, working_dir: Path | None = None):
    """Warn if cover letter lacks pricing bridge language for Upwork proposals."""
    if not fm or fm.get("source") != "upwork":
        return  # Only relevant for Upwork proposals

    letter = (working_dir or client_dir) / "cover-letter.md"
    if not letter.exists():
        letter = client_dir / "cover-letter.md"  # Fallback
    if not letter.exists():
        return

    raw = letter.read_text(encoding="utf-8")

    # A <=225-char hook has no room for a pricing-bridge sentence; the budget
    # acknowledgment lives on the investment page instead. Skip for short format.
    _, _, is_short = parse_cover_letter(raw)
    if is_short:
        report.add("Pricing bridge language", "SKIP",
                   "short-hook format (pricing bridge lives on investment.html)")
        return

    content = raw.lower()

    # Look for pricing bridge language
    bridge_patterns = [
        r"hourly",
        r"fixed[- ]price",
        r"above the .{0,30}range",
        r"above .{0,30}budget",
        r"listed (this )?as hourly",
        r"realize .{0,30}\$",
        r"pricing (format|structure|model)",
        r"prefer hourly",
        r"open to .{0,20}(hourly|rate)",
    ]
    has_bridge = any(re.search(p, content) for p in bridge_patterns)

    if has_bridge:
        report.add("Pricing bridge language", "PASS")
    else:
        report.add("Pricing bridge language", "WARN",
                    "Upwork proposal but no pricing bridge in cover letter. "
                    "If the job asks hourly or states a budget range, acknowledge the discrepancy.")


def check_client_name_leaks(report: ValidationReport, fm: dict, slug: str):
    """Check that prospect name doesn't appear on public platform pages."""
    if not fm or "prospect" not in fm:
        report.add("Privacy: no client name leaks", "SKIP", "No prospect name in frontmatter")
        return

    prospect = fm["prospect"]
    if not prospect or len(prospect) < 3:
        report.add("Privacy: no client name leaks", "SKIP", "Prospect name too short to scan")
        return

    # Build patterns: prospect name as a standalone word (not inside a slug/URL path)
    # e.g. "Menovia" in visible text is a leak, but "menovia-patient-journey" in a slug is not
    prospect_lower = prospect.lower()

    leaks = []
    for dir_path in PUBLIC_PLATFORM_DIRS:
        scan_dir = ROOT / dir_path
        if not scan_dir.exists():
            continue
        for f in scan_dir.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix not in (".tsx", ".ts", ".jsx", ".js", ".html", ".md", ".json"):
                continue
            try:
                text = f.read_text(encoding="utf-8")
            except Exception:
                continue
            # Find all occurrences and check context
            for m in re.finditer(re.escape(prospect_lower), text.lower()):
                start, end = m.start(), m.end()
                # Check surrounding characters -- if embedded in a slug/path, skip
                before = text[max(0, start-1):start] if start > 0 else " "
                after = text[end:end+1] if end < len(text) else " "
                # Slug context: preceded/followed by hyphen, slash, or quote+hyphen
                if before in ("-", "/") or after in ("-", "/"):
                    continue
                # Inside a string that looks like a slug comparison (e.g., === "menovia-...")
                ctx = text[max(0, start-30):end+30]
                if re.search(r'["\'][\w-]*' + re.escape(prospect_lower) + r'[\w-]*["\']', ctx, re.I):
                    # Check if it's just a slug string, not user-visible text
                    if "-" in ctx[ctx.lower().find(prospect_lower)-5:ctx.lower().find(prospect_lower)+len(prospect)+5]:
                        continue
                rel = f.relative_to(ROOT)
                leaks.append(str(rel))
                break  # One leak per file is enough

    if leaks:
        report.add("Privacy: no client name leaks", "FAIL",
                    f"'{prospect}' found in public files: {', '.join(leaks[:5])}")
    else:
        report.add("Privacy: no client name leaks", "PASS")


def check_template3_structure(report: ValidationReport, client_dir: Path, fm: dict, working_dir: Path | None = None):
    """Verify Track 2 cover letters follow Template 3 structure."""
    track = fm.get("track", 1) if fm else 1
    if track != 2:
        return

    letter_files = list((working_dir or client_dir).glob("cover-letter*.md"))
    if not letter_files:
        letter_files = list(client_dir.glob("cover-letter*.md"))
    if not letter_files:
        return  # Already caught by cover letter existence check

    for letter_path in letter_files:
        suffix = f" ({letter_path.name})" if len(letter_files) > 1 else ""
        content = letter_path.read_text(encoding="utf-8")

        # The <=225-char short-hook format does not carry the Template-3
        # long-form structure (URL in first 5 lines, "The site includes:"
        # bullet list, optionality close). Those moved to the site + links
        # block. Skip the legacy structure check for short letters.
        _, _, is_short = parse_cover_letter(content)
        if is_short:
            report.add(f"Template 3 structure{suffix}", "SKIP",
                       "short-hook format (Template-3 long-form structure not applicable)")
            continue

        lower = content.lower()

        issues = []

        # Check for URL in first 5 lines
        lines = [l for l in content.strip().split("\n") if l.strip() and not l.strip().startswith("#")]
        first_5 = "\n".join(lines[:5])
        if not re.search(r'https?://\S+', first_5):
            issues.append("no URL in first 5 lines")

        # "The site includes:" bullet list
        if "the site includes:" not in lower and "site includes:" not in lower:
            issues.append("missing 'The site includes:' section")

        # Optionality close (already checked elsewhere but part of T3 structure)
        has_optionality = any(p in lower for p in [
            "if we move forward", "if we work together",
            "if you'd like to move forward", "if this direction",
            "if this aligns", "happy to answer", "happy to discuss",
        ])
        if not has_optionality:
            issues.append("missing optionality close")

        if issues:
            report.add(f"Template 3 structure{suffix}", "WARN",
                       f"Structural drift: {'; '.join(issues)}")
        else:
            report.add(f"Template 3 structure{suffix}", "PASS")


def check_n8n_sticky_containment(report: ValidationReport, client_dir: Path):
    """Check that n8n workflow JSON sticky notes contain their labeled nodes."""
    import json
    json_files = list(client_dir.glob("*.json"))
    if not json_files:
        return

    for json_path in json_files:
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        # Must be an n8n workflow (has nodes array)
        nodes = data.get("nodes", [])
        if not nodes:
            continue

        stickies = [n for n in nodes if n.get("type") == "n8n-nodes-base.stickyNote"]
        non_stickies = [n for n in nodes if n.get("type") != "n8n-nodes-base.stickyNote"]

        if not stickies:
            continue

        containment_issues = []
        for sticky in stickies:
            sp = sticky.get("position", [0, 0])
            params = sticky.get("parameters", {})
            sw = params.get("width", 300)
            sh = params.get("height", 240)
            sx1, sy1 = sp[0], sp[1]
            sx2, sy2 = sx1 + sw, sy1 + sh

            # Find nodes that are CLOSE to this sticky (within 100px buffer)
            # but not fully contained
            for node in non_stickies:
                np = node.get("position", [0, 0])
                nx, ny = np[0], np[1]
                # Node is "near" sticky if within 100px of its boundaries
                near = (sx1 - 100 <= nx <= sx2 + 100 and
                        sy1 - 100 <= ny <= sy2 + 100)
                # Node is inside sticky
                inside = (sx1 <= nx <= sx2 and sy1 <= ny <= sy2)
                if near and not inside:
                    containment_issues.append(
                        f"'{node.get('name', '?')}' near but outside sticky "
                        f"'{sticky.get('name', '?')}'")

        if containment_issues:
            report.add(f"n8n sticky containment ({json_path.name})", "WARN",
                       f"{len(containment_issues)} node(s) outside stickies: "
                       f"{'; '.join(containment_issues[:3])}")
        else:
            report.add(f"n8n sticky containment ({json_path.name})", "PASS")


def check_tbd_in_text_files(report: ValidationReport, client_dir: Path, working_dir: Path | None = None):
    """Scan cover letters, video scripts, and other .md files for TBD placeholders."""
    scanned = set()
    # Scan working docs dir first (cover letters, video scripts)
    if working_dir and working_dir.exists():
        for md_path in working_dir.glob("*.md"):
            scanned.add(md_path.name)
            try:
                content = md_path.read_text(encoding="utf-8")
            except Exception:
                continue
            findings = []
            for i, line in enumerate(content.split("\n"), 1):
                for pattern in TBD_PATTERNS:
                    if re.search(pattern, line, re.I):
                        findings.append(f"line {i}")
                        break
            if findings:
                report.add(f"No TBD placeholders ({md_path.name})", "FAIL",
                           f"Found at {', '.join(findings[:5])}")
            else:
                report.add(f"No TBD placeholders ({md_path.name})", "PASS")
    # Then scan client dir for remaining .md files (e.g., blueprint-walkthrough.md)
    for md_path in client_dir.glob("*.md"):
        if md_path.name in scanned:
            continue
        try:
            content = md_path.read_text(encoding="utf-8")
        except Exception:
            continue

        findings = []
        for i, line in enumerate(content.split("\n"), 1):
            for pattern in TBD_PATTERNS:
                if re.search(pattern, line, re.I):
                    findings.append(f"line {i}")
                    break

        if findings:
            report.add(f"No TBD placeholders ({md_path.name})", "FAIL",
                       f"Found at {', '.join(findings[:5])}")
        else:
            report.add(f"No TBD placeholders ({md_path.name})", "PASS")


# ── Main ────────────────────────────────────────────────────────────────

def find_proposal_markdown(slug: str) -> Path | None:
    """Find the proposal markdown file for a slug."""
    # Try exact match first
    for md in PROPOSALS_DIR.glob("*.md"):
        if md.stem == slug:
            return md
    # Try prefix match
    for md in PROPOSALS_DIR.glob("*.md"):
        if slug in md.stem:
            return md
    return None


def validate_proposal(slug: str, verbose: bool = False) -> ValidationReport:
    """Run all validation checks for a proposal."""
    report = ValidationReport(slug=slug)
    client_dir = CLIENTS_DIR / slug
    working_dir = WORKING_DOCS_DIR / slug

    if not client_dir.exists():
        report.add("Client directory exists", "FAIL",
                    f"Not found: {client_dir}")
        return report

    report.add("Client directory exists", "PASS")

    # Load frontmatter
    md_path = find_proposal_markdown(slug)
    fm = None
    if md_path:
        fm = parse_frontmatter(md_path.read_text(encoding="utf-8"))
        check_frontmatter(report, fm, slug)
    else:
        report.add("Proposal markdown exists", "WARN",
                    f"No markdown found in {PROPOSALS_DIR} matching '{slug}'")

    # Deliverables consistency
    if fm:
        check_deliverables_match(report, fm, client_dir, working_dir)

    # Cover letter
    check_cover_letter(report, client_dir, fm or {}, working_dir)

    # Template 3 structural check (Track 2 only)
    check_template3_structure(report, client_dir, fm or {}, working_dir)

    # HTML site
    site_headings = check_html_site(report, client_dir, fm or {})

    # Pricing validation (investment page)
    check_pricing_not_tbd(report, client_dir)

    # Pricing bridge check (Upwork proposals)
    check_pricing_bridge(report, client_dir, fm or {}, working_dir)

    # Video script (needs site headings for cross-check)
    check_video_script(report, client_dir, site_headings, working_dir)

    # Video script: abbreviation glosses (SAY: lines must use plain language
    # or include a 3-8 word inline explanation). See
    # feedback_video_script_human_language.md.
    check_video_script_abbreviations(report, client_dir, working_dir)

    # TBD in text files
    check_tbd_in_text_files(report, client_dir, working_dir)

    # n8n workflow JSON layout validation
    check_n8n_sticky_containment(report, client_dir)

    # Client name leak detection (public platform pages)
    if fm:
        check_client_name_leaks(report, fm, slug)

    return report


def print_report(report: ValidationReport):
    """Print formatted validation report."""
    print(f"\nPROPOSAL VALIDATION: {report.slug}")
    print("=" * 60)

    for check in report.checks:
        print(f"  {check}")

    print("=" * 60)
    print(f"{len(report.passes)} passed, {len(report.fails)} failed, "
          f"{len(report.warns)} warnings, {len(report.skips)} skipped")

    if report.fails:
        print("\nRESULT: FAIL -- fix errors before sending")
        return 1
    elif report.warns:
        print("\nRESULT: PASS with warnings")
        return 0
    else:
        print("\nRESULT: PASS")
        return 0


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run tools/validate-proposal.py <slug> [--verbose]")
        print("\nAvailable proposals:")
        if CLIENTS_DIR.exists():
            for d in sorted(CLIENTS_DIR.iterdir()):
                if d.is_dir():
                    print(f"  {d.name}")
        sys.exit(1)

    slug = sys.argv[1]
    verbose = "--verbose" in sys.argv

    # Support validating all proposals
    if slug == "--all":
        exit_code = 0
        for d in sorted(CLIENTS_DIR.iterdir()):
            if d.is_dir():
                report = validate_proposal(d.name, verbose)
                code = print_report(report)
                if code != 0:
                    exit_code = code
                print()
        sys.exit(exit_code)

    report = validate_proposal(slug, verbose)
    sys.exit(print_report(report))


if __name__ == "__main__":
    main()
