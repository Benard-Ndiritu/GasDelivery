#!/usr/bin/env bash
# Render build command: ./build.sh
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --noinput
# Hosted Postgres poolers occasionally drop connections (e.g. right after a
# paused database is restored). Each migration is transactional on PostgreSQL,
# so retrying simply resumes from the first unapplied one.
# repair_token_blacklist undoes a migration that was committed but not recorded
# when a connection dropped; it is a no-op otherwise.
for attempt in 1 2 3; do
  python manage.py repair_token_blacklist && python manage.py migrate --noinput && break
  if [ "$attempt" -eq 3 ]; then
    echo "migrate failed after $attempt attempts" >&2
    exit 1
  fi
  echo "migrate failed (attempt $attempt), retrying in 15s..." >&2
  sleep 15
done

python manage.py create_admin
