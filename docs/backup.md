# Backups: hotel reservations database

This is my mother's business data: every forward booking the hotel has taken. If
the VPS dies and there is no off-box copy, the hotel loses all of it.

The data is tiny (10 rooms and a flat reservations table), so a dump is
kilobytes to a few megabytes even after years. Storage cost is a rounding error;
the only real decision is where the off-box copy goes, and that is yours to make.

## What runs on the box

`deploy/pg_backup.sh` writes a gzipped, timestamped dump to
`/var/backups/hotel-reservations/` and prunes local dumps older than 14 days. It
runs as the `postgres` user (peer auth, no password).

Install the directory and the cron entry:

```
sudo mkdir -p /var/backups/hotel-reservations
sudo chown postgres:postgres /var/backups/hotel-reservations
sudo chmod 700 /var/backups/hotel-reservations

# /etc/cron.d/hotel-reservations-backup  (nightly at 03:15)
sudo tee /etc/cron.d/hotel-reservations-backup >/dev/null <<'CRON'
15 3 * * * postgres /opt/hotel-reservations/deploy/pg_backup.sh >> /var/log/hotel-reservations-backup.log 2>&1
CRON
```

Run it once by hand to confirm it works:

```
sudo -u postgres /opt/hotel-reservations/deploy/pg_backup.sh
ls -l /var/backups/hotel-reservations/
```

## Copy it off the box (your decision, do not skip)

A dump on the same disk as the database protects only against the likelier
accidents: a bad migration, deleted rows, a mistake at 1am. It does NOT protect
against the VPS dying, which is the case that loses every booking. So the dump
must leave the box, nightly, automatically.

I am not picking the destination. First, see what the box can already reach and
what tooling it has:

```
command -v rclone rsync sftp restic borg   # what is already installed
ping -c1 -W2 1.1.1.1                        # does the box have outbound network
```

Then choose from roughly these options (verify current pricing yourself; the
data is a few MB so all of them cost pennies per month):

- Hetzner Storage Box (BX11, ~1 TB). Same provider, low latency, ~EUR 3-4/mo.
  Access via SFTP/rsync/BorgBackup. Natural fit if the VPS is already Hetzner.
- Cloudflare R2. You already use Cloudflare. S3-compatible, no egress fees,
  ~USD 0.015/GB-mo storage, so effectively free at this size. Access via rclone.
- Backblaze B2. ~USD 6/TB-mo, S3-compatible, rclone.
- Amazon S3. ~USD 0.023/GB-mo, rclone or awscli.
- rsync/scp to a machine you control (home NAS, another server). Free if it is
  already online every night when the cron fires.

Tell me which one and I will wire the last line of `deploy/pg_backup.sh` (the
commented `rclone copy` example) to it, with the credentials stored in a
root-only file, and add a check that the off-box copy actually landed.

Until that is configured, leave that line commented so a half-configured copy
cannot fail silently and let you believe you are covered.

## Restore drill (do this at least once, before you trust any of it)

A backup you have never restored is a guess. Restore the latest dump into a
throwaway database and confirm the rooms and reservations are there:

```
latest=$(ls -t /var/backups/hotel-reservations/hotel-*.sql.gz | head -1)
sudo -u postgres createdb hotel_restore_test
gunzip -c "$latest" | sudo -u postgres psql hotel_restore_test
sudo -u postgres psql hotel_restore_test -c "SELECT count(*) FROM rooms;"          # expect 10
sudo -u postgres psql hotel_restore_test -c "SELECT count(*) FROM reservations;"   # expect your real count
sudo -u postgres dropdb hotel_restore_test
```

If the counts are right, the backup is real. If the restore errors or the counts
are wrong, the backup is not a backup, and that is exactly what you want to learn
now rather than on the night the disk dies.
