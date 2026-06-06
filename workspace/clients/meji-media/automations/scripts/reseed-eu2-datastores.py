# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///
"""Re-seed eu2 data store records with clean encoding.

Fixes UTF-8 corruption from initial deployment (em-dashes became replacement chars).
Uses ASCII hyphens in subjects, HTML entities in body where needed.

Usage:
    uv run workspace/clients/meji-media/automations/scripts/reseed-eu2-datastores.py
"""

import json
import os
import sys

import httpx

ZONE = "eu2.make.com"
TOKEN = os.environ["MAKE_API_TOKEN"]  # set MAKE_API_TOKEN in env; never hardcode
PIPELINE_DS = 153173
TEMPLATES_DS = 153175
BASE = f"https://{ZONE}/api/v2"
HEADERS = {"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"}


# --- Pipeline Config (fix signature + handoff_email) ---

SIGNATURE_HTML = (
    '<p style="margin-top:24px">Best regards,<br>'
    "<strong>The Meji Media Team</strong></p>"
    '<p style="font-size:13px;color:#555;margin-top:16px;'
    'border-top:1px solid #eee;padding-top:12px">'
    "Meji Media &#8212; Events &amp; Media Production<br>"
    '<a href="https://mejimedia.com">Website</a> &middot; '
    '<a href="https://mejimedia.com/portfolio">Our Work</a> &middot; '
    '<a href="https://mejimedia.com/book">Book a Call</a>'
    "</p>"
)

PIPELINE_UPDATES = {
    "email_signature_html": SIGNATURE_HTML,
    "handoff_email": "client.meji-media@unpauseai.com",
}


# --- Email Templates ---

TEMPLATES = {
    "initial_standard_a": {
        "subject": "Thanks for your enquiry, ##name## - Meji Media",
        "body_html": (
            "<p>Hi ##name##,</p>\n"
            "##ai_opening##\n"
            "<p>Thank you for getting in touch about ##topic##. "
            "We've received your enquiry and are excited to learn more about what you have in mind.</p>\n"
            "<p>We work with a wide range of clients across events, film, and media production, "
            "and we'd love to explore how we can help bring your vision to life.</p>\n"
            "<p>One of our team will review your details and get back to you shortly. "
            "In the meantime, feel free to reply to this email if there's anything else "
            "you'd like to share &#8212; we'd love to hear more.</p>\n"
            "##signature##"
        ),
        "active": "true",
        "updated_at": "2026-03-06T00:00:00Z",
    },
    "initial_standard_b": {
        "subject": "Thanks for your enquiry, ##name## - Meji Media",
        "body_html": (
            "<p>Hi ##name##,</p>\n"
            "##ai_opening##\n"
            "<p>Thank you for getting in touch about ##topic##. "
            "We've received your enquiry and are excited to learn more about what you have in mind.</p>\n"
            "<p>We work with a wide range of clients across events, film, and media production, "
            "and we'd love to explore how we can help bring your vision to life.</p>\n"
            "<p>One of our team will review your details and get back to you shortly. "
            "In the meantime, feel free to reply to this email if there's anything else "
            "you'd like to share &#8212; we'd love to hear more.</p>\n"
            "##signature##"
        ),
        "active": "true",
        "updated_at": "2026-03-06T00:00:00Z",
    },
    "initial_high_a": {
        "subject": "Thanks for your enquiry, ##name## - Meji Media",
        "body_html": (
            "<p>Hi ##name##,</p>\n"
            "##ai_opening##\n"
            "<p>Thank you so much for reaching out about ##topic##. "
            "This sounds like a brilliant project and exactly the kind of work we love getting involved in.</p>\n"
            "<p>We've had a look at your enquiry and we're keen to chat through the details with you "
            "as soon as possible. Would you be free for a quick call this week? "
            "Just reply with a time that works and we'll make it happen.</p>\n"
            "<p>In the meantime, feel free to take a look at some of our recent work "
            "&#8212; we think you'll get a great sense of what we can do together.</p>\n"
            "##signature##"
        ),
        "active": "true",
        "updated_at": "2026-03-06T00:00:00Z",
    },
    "initial_high_b": {
        "subject": "Thanks for your enquiry, ##name## - Meji Media",
        "body_html": (
            "<p>Hi ##name##,</p>\n"
            "##ai_opening##\n"
            "<p>Thank you so much for reaching out about ##topic##. "
            "This sounds like a brilliant project and exactly the kind of work we love getting involved in.</p>\n"
            "<p>We've had a look at your enquiry and we're keen to chat through the details with you "
            "as soon as possible. Would you be free for a quick call this week? "
            "Just reply with a time that works and we'll make it happen.</p>\n"
            "<p>In the meantime, feel free to take a look at some of our recent work "
            "&#8212; we think you'll get a great sense of what we can do together.</p>\n"
            "##signature##"
        ),
        "active": "true",
        "updated_at": "2026-03-06T00:00:00Z",
    },
    "step_2_a": {
        "subject": "Following up on your enquiry - ##topic## | Meji Media",
        "body_html": (
            "<p>Hi ##name##,</p>\n"
            "##ai_opening##\n"
            "<p>We wanted to follow up on your recent enquiry about ##topic##. "
            "We know things can get busy, so we just wanted to make sure your message "
            "didn't slip through the cracks.</p>\n"
            "<p>We've been thinking about your project and would love the chance to discuss it properly. "
            "Whether you have questions, want to explore ideas, or are ready to get started "
            "&#8212; we're here to help.</p>\n"
            "<p>Just reply to this email and we'll pick things up from there.</p>\n"
            "##signature##"
        ),
        "active": "true",
        "updated_at": "2026-03-06T00:00:00Z",
    },
    "step_2_b": {
        "subject": "Following up on your enquiry - ##topic## | Meji Media",
        "body_html": (
            "<p>Hi ##name##,</p>\n"
            "##ai_opening##\n"
            "<p>We wanted to follow up on your recent enquiry about ##topic##. "
            "We know things can get busy, so we just wanted to make sure your message "
            "didn't slip through the cracks.</p>\n"
            "<p>We've been thinking about your project and would love the chance to discuss it properly. "
            "Whether you have questions, want to explore ideas, or are ready to get started "
            "&#8212; we're here to help.</p>\n"
            "<p>Just reply to this email and we'll pick things up from there.</p>\n"
            "##signature##"
        ),
        "active": "true",
        "updated_at": "2026-03-06T00:00:00Z",
    },
    "step_3_a": {
        "subject": "One last check-in - ##topic## | Meji Media",
        "body_html": (
            "<p>Hi ##name##,</p>\n"
            "##ai_opening##\n"
            "<p>We're checking in one last time regarding your enquiry about ##topic##. "
            "We completely understand if now isn't the right time &#8212; "
            "plans change, and there's absolutely no pressure.</p>\n"
            "<p>If you are still interested, we'd be happy to pick up where we left off. "
            "And if your needs have changed, that's fine too &#8212; "
            "just let us know and we'll update our records.</p>\n"
            "<p>Either way, it was great to hear from you, "
            "and we're always here if you need us in the future.</p>\n"
            "##signature##"
        ),
        "active": "true",
        "updated_at": "2026-03-06T00:00:00Z",
    },
    "step_3_b": {
        "subject": "One last check-in - ##topic## | Meji Media",
        "body_html": (
            "<p>Hi ##name##,</p>\n"
            "##ai_opening##\n"
            "<p>We're checking in one last time regarding your enquiry about ##topic##. "
            "We completely understand if now isn't the right time &#8212; "
            "plans change, and there's absolutely no pressure.</p>\n"
            "<p>If you are still interested, we'd be happy to pick up where we left off. "
            "And if your needs have changed, that's fine too &#8212; "
            "just let us know and we'll update our records.</p>\n"
            "<p>Either way, it was great to hear from you, "
            "and we're always here if you need us in the future.</p>\n"
            "##signature##"
        ),
        "active": "true",
        "updated_at": "2026-03-06T00:00:00Z",
    },
}


def upsert_record(ds_id: int, key: str, data: dict) -> bool:
    """Update or create a data store record."""
    url = f"{BASE}/data-stores/{ds_id}/data/{key}"
    # PUT expects flat fields (no 'data' wrapper)
    with httpx.Client(timeout=30) as client:
        resp = client.put(url, headers=HEADERS, json=data)
        if resp.status_code == 404:
            url = f"{BASE}/data-stores/{ds_id}/data"
            body = {"key": key, **data}
            resp = client.post(url, headers=HEADERS, json=body)
    ok = resp.status_code in (200, 201)
    status = "OK" if ok else f"FAIL ({resp.status_code})"
    sys.stdout.buffer.write(f"  [{key}] {status}\n".encode("utf-8"))
    if not ok:
        sys.stdout.buffer.write(f"    {resp.text[:200]}\n".encode("utf-8"))
    return ok


def main() -> None:
    print("=== Re-seeding eu2 data stores with clean encoding ===\n")

    # 1. Pipeline Config — partial update (only fix corrupted fields)
    print(f"Pipeline Config (DS {PIPELINE_DS}):")
    ok = upsert_record(PIPELINE_DS, "main", PIPELINE_UPDATES)

    # 2. Email Templates — full re-seed
    print(f"\nEmail Templates (DS {TEMPLATES_DS}):")
    results = []
    for key, data in TEMPLATES.items():
        results.append(upsert_record(TEMPLATES_DS, key, data))

    # Summary
    total = 1 + len(TEMPLATES)
    passed = (1 if ok else 0) + sum(results)
    print(f"\n=== Done: {passed}/{total} records updated ===")
    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
