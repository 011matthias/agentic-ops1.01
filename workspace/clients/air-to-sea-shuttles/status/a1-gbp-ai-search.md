---
project: air-to-sea-shuttles
workstream: a1-gbp-ai-search
group: ""
spec: ""
state: active
updated: 2026-11-20
---

# Air to Sea Shuttles / Business Profile + AI search presence (a1)

The first work Matthias committed to on the 2026-11-18 call with Harold Riley:
set up the Google Business Profile and get the business named in Google and
AI-assistant answers. The pay model under discussion is a setup fee plus a share
of tracked bookings (see `context/comms-log.md`, 2026-11-18), so the measurement
elements below double as the billing basis.

## Starting point (checked 2026-11-18)

- **Site:** WordPress 7.0.8 with Elementor Pro, hosted at Hostinger (DNS,
  hosting and mail are all on Hostinger). Pages: home, about, services, rates,
  schedule, fleet, booking and cancellation policies, legal pages.
- **Booking:** Zaui booking engine embedded from `air2seashuttles.zaui.net`.
- **Tracking:** no Google Analytics, Tag Manager or Search Console verification
  found, neither in the homepage source nor in DNS.
- **SEO basics:** no SEO plugin, no meta description, no structured data; the
  homepage title is only "Air to Sea Shuttles LLC". robots.txt allows all
  crawlers and the WordPress sitemap is live.
- **Google Business Profile:** none (Harold, 2026-11-17).
- **Footprint:** a web search for the exact name finds no third-party listing.
  Visit Galveston's directory lists competitors (Galveston Express, Island
  Breeze, Royal Galveston Shuttle) but not him.
- **Fare conflict:** the rates page shows two IAH-to-Galveston shared fares
  ($55 and $45 one way).
- **Not a route:** Google Things to Do excludes airport transfers, so Zaui's
  Things to Do connector does not apply.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Access + business facts | blocked | self-serve checklist email drafted 2026-11-20 (`context/drafts/2026-11-20-access-checklist.md`), not yet sent | Matthias fills in his invite address (needs a Google account on it) and sends; then log it verbatim | Matthias, then Harold | Harold's checklist is only GBP, Zaui, WordPress, Hostinger, logo/photos and the questions only he can answer; the rest below follows from those |
| Baseline | not started | | Pull 12 months of Zaui bookings by source and value; run the AI-answer baseline | Zaui login | Baseline below |
| Google Business Profile | not started | none exists | Harold creates it on the business Google account and adds Matthias as manager; Harold does the verification | Business Google account, verification | Service-area business, address hidden; primary category picked from Google's list (airport shuttle service) |
| Review flow | not started | | QR card in the vans + review request after each ride + one ask to past customers from Zaui | GBP live | No incentives, no asking only happy customers (Google policy) |
| Measurement | not started | | Search Console, Bing Webmaster Tools, GA4 + Tag Manager on site and in Zaui (Settings > Marketplace), tagged GBP booking link, tracking phone number on GBP | WordPress, Zaui, DNS access | Also the billing basis for the performance deal. Live BEFORE the profile goes live (use the verification wait), or the first uplift can't be attributed |
| Site SEO basics | not started | | SEO plugin, titles and descriptions, LocalBusiness + FAQ structured data, fix the fare conflict | WordPress admin | |
| Answer content | not started | | One page per route (IAH, Hobby, return after the cruise) + FAQ with short direct answers | WordPress admin, Harold's answers | What AI assistants quote |
| Listings | not started | | Bing Places, Apple Business Connect, Yelp, TripAdvisor, Facebook, Visit Galveston directory; identical name and phone everywhere | GBP verified first | Visit Galveston listing cost TBD |
| Third-party mentions | later | | Cruise-port guides and cruise forums that list shuttle options | Reviews on GBP first | |

## Access to request

Everything is created on Harold's accounts and stays his; Matthias gets his own
login or a delegated role, never Harold's passwords.

| # | Access | Role for Matthias | What it is for |
|---|---|---|---|
| 1 | Business Google account (create one on the sales@ address if none) | none; Harold owns it | Owner of the Business Profile, Search Console, GA4 and Tag Manager |
| 2 | Google Business Profile | Manager | Build and run the profile, reply to reviews, see calls and clicks |
| 3 | WordPress | Administrator, own user | SEO plugin, titles, structured data, route and FAQ pages, Tag Manager, quote form |
| 4 | Hostinger | Account sharing, role Collaborator (Admin can buy on his saved card) | Domain verification for Search Console and Bing, backups before site changes, later mail-sending records |
| 5 | Zaui | Staff login with Reports and Settings > Marketplace | Bookings by source and value, Tag Manager in the booking engine, later automation |
| 6 | Google Search Console | Matthias sets it up (DNS via Hostinger), Harold's business account added as owner | Search queries and indexing |
| 7 | GA4 + Google Tag Manager | Matthias sets them up, Harold's business account added as admin | Visitors, bookings and quote requests by source |
| 8 | Bing Webmaster Tools + Bing Places | set up by Matthias, verified by Harold | Bing feeds Microsoft Copilot and is one of ChatGPT search's sources |
| 9 | Apple Business Connect | added by Harold | Apple Maps and Siri |
| 10 | Phone provider for the 832 and 844 numbers | provider name + call log | Count phone bookings; later a tracking number and missed-call text-back |
| 11 | Facebook, Instagram, Yelp, TripAdvisor (whichever exist) | manager or editor | Consistent details and review links |
| 12 | Logo originals, photos of vans and drivers | files | Profile and site; today's site icon is an AI-generated image |

Not needed: bank, payment processor, his email inbox.

## Business facts to get

- Bookings per month, peak season vs off-season, and average booking value
  for shared, private and group rides (Zaui reports may answer both).
- Where bookings come from today: site, phone, email, booking sites connected
  to Zaui, travel agents, hotels, cruise groups, repeat customers; and the
  commission he pays each (the anchor for the performance share).
- Group quotes: how many per month, how many book, how fast he replies.
- Capacity: vans, seats and drivers, and any days he already turns work away.
- Licences, permits and insurance (airport ground-transport permit, motor
  carrier registration) to show on the profile and site.
- The address Google will verify, the service area, hours, and which phone
  number is primary.
- His OK to send one review request to past customers.

## Baseline (before any change)

Run each prompt in ChatGPT, Google (AI Overview), Gemini, Perplexity and
Copilot; record whether Air to Sea is named and who is. Repeat monthly.

- best shuttle from IAH to the Galveston cruise port
- how do I get from Hobby airport to the Galveston cruise terminal
- shuttle for a group of 10 from Houston airport to Galveston cruise port
- shared shuttle IAH to Galveston price
- shuttle from the Galveston cruise port back to IAH after a cruise
- Air to Sea Shuttles reviews
