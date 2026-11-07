# hal-floor

Public, no-auth status page for the team's four HAL boxes: who holds each one, when it frees, and
what is queued behind it. Claims made here are advisory; the CTF workbench polls them and keeps its
agents off a claimed box.

- `GET /` — page
- `GET /api/floor` — boxes + claims + waiting queue (from the workbench snapshot)
- `POST /api/state` — workbench snapshot, requires `X-Floor-Key: $HAL_FLOOR_KEY`
- `POST /api/claim` `{host, owner, note, minutes}` — no auth, rate limited per IP
- `POST /api/claims/clear` `{host}`
- `GET /api/claims` — claims for the workbench to poll
- `GET /healthz`

State lives in `/data` (mount a volume). Claims expire on their own (10–180 minutes).
