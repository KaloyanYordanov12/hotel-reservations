# Demo reset (cron)

The public demo at `reservations-demo.kaloyanyordanov.dev` shows seeded sample
data. Every 30 minutes it is wiped and reseeded to a known clean state so it
always looks alive and anything visitors booked is cleared.

This is a cron-invoked script, not an HTTP endpoint: it has no public surface,
so there is nothing for a bot or a recruiter to spam, and no token to manage.

## What runs

`scripts/reset_demo.py` wipes every reservation and reseeds the fixed Bulgarian
demo set from `scripts/seed_demo.py`. Rooms are never touched (they come from the
migrations).

### Safety guard

The script refuses to run unless `DATABASE_URL` names a database called exactly
`hotel_demo`, checked before anything is wiped. `hotel`, `hotel_test`,
`HOTEL_DEMO`, `hotel_demo_2` are all refused, and the run exits non-zero so a
misconfiguration shows up as a failure in the log rather than a silent wipe. This
is the same spirit as the test-suite guard in `tests/conftest.py`. The guard is
covered by `tests/test_reset_demo.py`.

## The crontab line (install on the VPS in Step 5, not before)

Runs at :00 and :30. It sources the demo env file first, so the app sees the
`hotel_demo` `DATABASE_URL` (plus the `SESSION_SECRET` and `APP_PASSWORD_HASH`
the app requires to start, even though the demo has no login), then runs the
reset from the app root as a module so `import scripts.seed_demo` resolves.

It is installed as a system cron drop-in that runs as the unprivileged
`hotel-demo` user (the same user the demo service runs as, which can read the env
file and write the log dir). `docs/deploy-demo.md` Step 10 is the authoritative
install step; the drop-in it writes is:

```
# /etc/cron.d/hotel-demo-reset
# Reset the public hotel demo to clean seeded data every 30 minutes (:00 and :30).
*/30 * * * * hotel-demo cd /opt/hotel-demo && set -a && . /etc/hotel-demo/hotel-demo.env && set +a && /opt/hotel-demo/venv/bin/python -m scripts.reset_demo >> /var/log/hotel-demo/reset.log 2>&1
```

The `hotel-demo` field after the schedule is the user to run as; it is required in
`/etc/cron.d` files and absent from a personal `crontab -e`. The paths
(`/opt/hotel-demo` app root, `/opt/hotel-demo/venv` venv,
`/etc/hotel-demo/hotel-demo.env` env file, `/var/log/hotel-demo/reset.log` log)
are the layout `docs/deploy-demo.md` creates.

Run it once by hand first to confirm it seeds and the guard passes:

```
cd /opt/hotel-demo && set -a && . /etc/hotel-demo/hotel-demo.env && set +a && /opt/hotel-demo/venv/bin/python -m scripts.reset_demo
```
