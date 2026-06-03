# Reference: deploy internals (Fly + nginx)

The home for the deploy mechanics and the hard-won nginx lessons. `modules/SHIP.md`
§2 links here.

## Topology

One Astro project, one Fly app: `app/Dockerfile` -> nginx, `app/fly.toml`,
`app/nginx.conf`. Canonical ship path is `uv run tools/local-web-deploy.py` (builds +
`flyctl deploy` + live-origin assertion). Raw one-off:
`flyctl deploy {app-abs-path} --config {fly.toml} --remote-only` (then owe the
live-origin check by hand).

## nginx config — locked and load-bearing

`nginx.conf` MUST keep:

```
absolute_redirect off;
port_in_redirect off;
server_name_in_redirect off;
```

nginx behind the Fly TLS edge only sees `http` on `:8080`, so without these the
trailing-slash 301 leaks `http://host:8080/...` and every `/<slug>` page dies with
`ERR_CONNECTION_RESET` in-browser (server-side curl still 200s — verify by following
redirects, not just status). Regression class, 2026-05-18 (see incidents.md).

Stronger still:

```
try_files $uri $uri/index.html $uri.html $uri/ =404;
```

so the no-slash URL serves the index DIRECTLY (200, no 301) and you link the slash
form in nav. A 301 gets cached persistently by browsers, so once a bad target is
cached no server fix can evict it; the only safe state is emitting no redirect at all.

## The cached-redirect trap (verification method)

A cached-redirect bug is invisible to `curl` (no cache): reproduce the client path or
use a fresh profile, never declare it fixed on a server-side 200 alone. "Live" is a
fact about the `fly.dev` origin serving this exact build, confirmed by
`tools/local-web-deploy.py`'s content-hash assertion — not a localhost render.
