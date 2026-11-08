# hal-floor

Public, no-auth status page for the team's four HAL boxes: who holds each one, when it frees, and
what is queued behind it. Claims made here are advisory; the CTF workbench polls them and keeps its
agents off a claimed box.

- `GET /` — page
- `GET /api/floor` — boxes + claims + waiting queue + the rival summary (from the workbench snapshot)
- `POST /api/state` — workbench snapshot, requires `X-Floor-Key: $HAL_FLOOR_KEY`
- `POST /api/claim` `{host, owner, note, minutes}` — no auth, rate limited per IP
- `POST /api/claims/clear` `{host}`
- `POST /api/stop` `{host, owner}` — ask the workbench to stop a box; the name must match the box's
  current claim. The workbench refuses while an agent supervisor/worker is on any challenge the box
  serves, and otherwise stops it on its next tick (~30 s).
- `GET /api/requests`, `POST /api/requests/ack` `{ids}` — the workbench's queue and acknowledgement
- `GET /api/claims` — claims for the workbench to poll
- `GET /healthz`

State lives in `/data` (mount a volume). Claims expire on their own (10–180 minutes).

The snapshot may also carry `rivals`, a public-safe summary published by the workbench: team name, score/place for
both sides, the gaps, shared/unique solve counts, scan progress, and the board top five. The server whitelists those
fields (`clean_rivals`); challenge names and per-challenge detail are never accepted or shown.
