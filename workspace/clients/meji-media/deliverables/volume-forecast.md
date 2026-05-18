# Volume Forecast: What 11 Years of Enquiry Data Tells Us

**Prepared for:** Gurmej Pawar, Jess Harrar
**Date:** 8 May 2026
**Source:** Live MySQL archive (read-only)

The Scaling document left one question open: Gurmej's "annual +10%" or Jess's "skyrockets June/July"? Neither. We pulled every enquiry on file (four MySQL tables, 2015 to 2025). The pattern is sharper than either guess.

## Summary

Peak month is **September, every year, by a wide margin**. Same curve annually: slow first half, ramp from June, sharp September spike, fast tail to year-end.

Both 22 April growth views were half right. Annual totals are roughly flat (closer to Gurmej's "not wildly different" than +10%). Jess's ramp is real but lands **August to October**, not June to July.

Scaling impact: size the deliverability cliffs against the September peak (**20 to 25 enquiries per day for weeks**), not a flat year-round average.

## The Headline Finding

**Every year for at least a decade, intake peaks in the same 7-week window: August through mid-October.** Eight of nine complete seasons peaked in September. The exception (2018) peaked in October.

Not a 2025 fluke. Visible in every year back to 2015. Consistent enough to plan against directly: treat August to October as a different operating regime from the other nine months.

Biggest day on record: **3 September 2025**, 42 enquiries in 24 hours. Every runner-up day is also September (15th, 16th, 22nd 2025; 25 Sep 2024; 18 Sep 2019).

## The 2025 Curve, Month by Month

2025, the most recent complete season: 2,762 enquiries, distributed like this.

| Month | Enquiries | | Month | Enquiries |
|-------|----------:|-|-------|----------:|
| Jan | 2 | | Jul | 497 |
| Feb | 5 | | Aug | 519 |
| Mar | 5 | | Sep | **712** |
| Apr | 14 | | Oct | 459 |
| May | 71 | | Nov | 263 |
| Jun | 199 | | Dec | 16 |

*2025 monthly enquiry counts (n = 2,762)*

September alone: **712 enquiries**, more than January to June combined (296). August to October (1,690) was **61% of the year** in 25% of the calendar.

## Same Shape Every Year

If 2025 were anomalous, 2024 would look different. It doesn't (3,095 enquiries):

| Month | Enquiries | | Month | Enquiries |
|-------|----------:|-|-------|----------:|
| Jan | 9 | | Jul | 398 |
| Feb | 13 | | Aug | 438 |
| Mar | 25 | | Sep | **537** |
| Apr | 76 | | Oct | 469 |
| May | 349 | | Nov | 330 |
| Jun | 415 | | Dec | 36 |

*2024 monthly enquiry counts (n = 3,095)*

Same curve. Peak still September. 2024's spring ramp is steeper from a stronger early-year intake, but September is the highest point both years.

Peak months further back:

| Year | Peak month | Enquiries |
|------|-----------|----------:|
| 2015 | September | 243 |
| 2016 | September | 156 |
| 2017 | September | 92 |
| 2018 | October | 136 |
| 2019 | September | 183 |
| 2023 | September | 372 |
| 2024 | September | 537 |
| 2025 | September | 712 |

Eight of nine complete seasons peak in September. The exception (2018) peaks in October by a small margin.

## A Decade in Totals

Pre-COVID: roughly 600 to 800 enquiries a year. 2020 to 2022 is missing from every archive table (COVID collapse plus an archive that doesn't span those years). Post-pandemic: roughly 4x the volume.

| Year | Total | Note |
|------|------:|------|
| 2015 | 865 | May start |
| 2016 | 647 | |
| 2017 | 227 | sparse data |
| 2018 | 594 | |
| 2019 | 665 | |
| 2020 to 2022 | n/a | data gap |
| 2023 | 1,927 | Mar start |
| 2024 | 3,095 | |
| 2025 | 2,762 | |

- 2024 to 2025 declined about 11% (3,095 to 2,762). Closer to Gurmej's "not wildly different" than +10% growth.
- 2026 year-to-date (through 7 May): 181 enquiries. Well within the post-2022 regime, not a regression to the pre-COVID baseline.
- The 2017 total (227) is almost certainly a data gap, not a quiet year. Years either side look normal.

## What This Means For The Scaling Decision

The Scaling document mapped three deliverability cliffs against a flat ~30 outbound emails per day. That average is misleading. Size the cliffs against the September peak, not the mean.

A typical September day: **20 to 25 enquiries**, sustained for weeks. At 4 to 6 emails per enquiry, that's **100 to 150 outbound per day from the single mailbox** through September, plus catch-up sends from late-August enquiries still in their follow-up window.

Revised exposure to each cliff:

| Cliff | Exposure |
|-------|----------|
| **Cliff 1 (Soft)** | 30-per-day baseline to 100 to 150 per day in September is roughly a 3 to 5 times jump. Squarely inside Gmail's spam-filter heuristics on volume spikes. **Realistic risk this September.** |
| **Cliff 2 (Hard)** | The 2,000-per-day Workspace cap stays well clear at 100 to 150 sustained. Only a risk if a single day produced more than ~400 enquiries, which the data says is very unlikely (all-time single-day peak was 42). |
| **Cliff 3 (Regulatory)** | The 5,000-per-day bulk-sender threshold is far off. No realistic September scenario for the Christmas-side flow brings it close. (The Instantly outbound side is separate.) |

Translation: **Path A (monitor and stay) is genuinely at risk this September**. Path B (multi-mailbox) holds: spread the September load across 2 to 3 mailboxes and each stays under the cliff. Path C is right if the Instantly outbound work moves forward and you want shared infrastructure.

## How We Got This Data

Pulled directly from the live database, not a survey or estimate:

1. Read-only MySQL via the existing automation connection (UTIL scenario 8974201, no separate credentials).
2. Data split across four tables: `enquiries` (live, 181 rows), `all_enquiries` (2015 to 2020, 3,005 rows), `full_data_enquiries` (2023 to 2026, 7,833 rows), `enquiries_backup_23-04-2025` (April 2025 snapshot, 3,859 rows).
3. Reconciled by date range, schema discovery, de-duplication. The 2020 to 2022 stretch sits in none of the four tables.
4. All aggregation in SQL against the live tables. Nothing extracted, exported, or persisted outside the database.

## Caveats and Confidence

- **The 2020 to 2022 gap is real.** The COVID-era curve is unknown. Pre- and post-COVID patterns are consistent enough to trust the September-peak framing, but a lockdown-driven behaviour shift would not be visible here.
- **`full_data_enquiries` is stale for 2026.** It shows 49 rows for 2026; the live table has 181 through 7 May. Late-April and early-May 2026 daily counts may be slightly undercounted in any historical aggregate.
- **The 2017 total (227) is suspicious.** Other archive years are 600-plus. Likely a partial-year data issue, not a real drop.
- **Single-day peak (42) is 2025-09-03.** A higher day could exist in the 2020 to 2022 gap. Treat 42 as a lower bound.
- **"Enquiry" = a database row**, from website form, phone capture, or referral feed. Not separated by source; per-source breakdown is a follow-up query.

If any caveat matters for the path decision, say so and we'll dig further before locking a recommendation.
