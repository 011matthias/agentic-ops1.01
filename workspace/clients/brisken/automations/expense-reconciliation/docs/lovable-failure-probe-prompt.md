# Lovable prompt: report a failed request so the next one is provable

> **NOT YET APPLIED.** Paste after the item-50 backend deploy.
>
> This one is invisible to the user by design. It adds no screen and
> changes no layout. Without it the backend half does nothing at all: the
> app can only record a failure the browser tells it about, and today the
> browser tells it nothing.

Backend is deployed. On 2026-09-10 Criss hit **"Failed to fetch"** in the
Attach bank statement dialog. That error comes from the browser, not from
us: the request never reached the server, so nothing on our side recorded
it, and the machine serving that hour was replaced before anyone looked.
We could not explain it then and we still cannot. This change means the
next one explains itself.

The app now accepts a short report whenever a request fails, and stamps it
with which server process answered and how long that process had been
running. If a failure happened thirty seconds ago and the process taking
the report is ten seconds old, the machine was replaced underneath the
request, and that is visible from the report alone.

---

## 1. Report a failed request

Wherever the app calls the API, catch the case where the call **rejects**
(the network-level failure, not a 4xx or 5xx response, which already
arrive as normal responses) and send one report:

```
POST /api/client-errors
{
  "kind": "fetch-failed",
  "url": "<the URL that was being called>",
  "method": "POST",
  "message": "<the error message, e.g. Failed to fetch>",
  "occurred_at": "<ISO timestamp from the browser>",
  "seconds_ago": 0.4,
  "duration_ms": 1200,
  "online": true,
  "detail": { "screen": "attach-statement", "file": "August2026.xlsx" }
}
```

Rules that matter:

- **`seconds_ago` is required for the report to be worth anything.**
  Measure it inside the browser: record the time when the request failed,
  and subtract it from the time when you send the report. Do not compute
  it from the two clocks, and do not omit it. A browser clock can be
  minutes off the server's, and the server uses this number to decide
  whether it restarted; a wrong number invents or hides a restart.
- **Send it after the failure, not instead of handling it.** The user
  still sees whatever error the screen shows today. This is a side
  report; it changes nothing the user sees.
- **Never let the report itself break anything.** Wrap it so a failure to
  send is swallowed silently. If the network is still down the report
  cannot arrive, and that is expected and acceptable.
- **Do not retry the report.** The server drops more than 20 reports per
  minute from one caller anyway, and a retry loop would push the
  interesting older reports out of the log.
- `detail` is free-form; include whatever names the screen and the action
  ("attach-statement", "upload-receipts", the file name). It is capped at
  2000 characters, so keep it small and do not put file contents in it.

The reply is always a 200 and needs no handling. It carries `recorded`
and `process_predates_failure` if you ever want to show them, but nothing
in the UI has to.

## 2. Where to hook it

Every API call the app makes should be covered, because we do not know
which one will fail next. If the app has one shared fetch wrapper, that
is the single place to put this. If it does not, the ones that matter
most are the uploads, because they are long-running and that is where the
reported failure happened: attach a statement, add receipts, add
expenses.

## 3. What NOT to do

- **Do not report normal error responses.** A 400, 401, 404 or 500 is a
  response; the server already knows about it. This is only for the case
  where the call rejects and there is no response at all.
- **Do not add a screen, a toast, or a banner for this.** It is a silent
  diagnostic. The user already saw one error; a second message about
  reporting the first one is noise.
- **Do not send anything from the receipts or statements themselves.** File
  names are fine, file contents are not.

## 4. Optional, only if it is easy

The app can show the server's build health on the Guide or Settings page
from `GET /healthz`, which now returns a `server` block with the machine
id, region, the time the process started and its uptime in seconds. This
is useful when someone is watching a deploy land. Skip it if it adds any
friction; the reporting in section 1 is the part that matters.
