# Webhooked

Webhooked captures generic HTTP requests at per-integration UUIDv4 URLs and provides a compact private UI to inspect and export deliveries. The UUID is a write capability, not proof of sender identity. This app has no UI login; expose it only on a trusted homelab network.

## Local development

Python 3.13 or newer is required.

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
export DJANGO_DEBUG=1
python app/manage.py migrate
python app/manage.py runserver 0.0.0.0:8000
```

By default, local development uses SQLite at `db.sqlite3`. Open `http://localhost:8000` to create an endpoint. Its capture URL is displayed on the endpoint page.

## MariaDB

Install the optional database driver and set the connection environment:

```sh
pip install -e '.[mariadb]'
export DB_ENGINE=mariadb
export DB_NAME=webhooked
export DB_USER=webhooked
export DB_PASSWORD='change-me'
export DB_HOST=mariadb
export DB_PORT=3306
python app/manage.py migrate
```

`DB_CONN_MAX_AGE` defaults to 60 seconds. `DJANGO_SECRET_KEY` should be set to a stable, private value in a deployed environment. `DJANGO_ALLOWED_HOSTS` is a comma-separated host allowlist.

## Container

Build and run the app image:

```sh
docker build -f docker/Dockerfile -t webhooked .
docker run --rm -p 8000:8000 \
  -e DJANGO_SECRET_KEY='replace-with-a-private-random-value' \
  -e DJANGO_ALLOWED_HOSTS='localhost,webhooked.example.lan' \
  -e DB_ENGINE=mariadb \
  -e DB_NAME=webhooked \
  -e DB_USER=webhooked \
  -e DB_PASSWORD='change-me' \
  -e DB_HOST=mariadb \
  -e CAPTURE_BASE_URL='https://webhooked.example.lan' \
  webhooked
```

### SQLite in a container

The image defaults to SQLite at `/data/db.sqlite3` (`SQLITE_PATH`), so no database server is needed. Mount a volume at `/data` to persist it:

```sh
docker run --rm -p 8000:8000 -v webhooked-data:/data \
  -e DJANGO_SECRET_KEY='replace-with-a-private-random-value' \
  -e DJANGO_ALLOWED_HOSTS='localhost' \
  webhooked
```

The app runs as UID/GID 10001. In Kubernetes, mount a PersistentVolumeClaim at `/data` and set `securityContext: {runAsUser: 10001, runAsGroup: 10001, fsGroup: 10001}` so the volume is writable. Use a single replica (`strategy: Recreate`) with a `ReadWriteOnce` PVC, and avoid NFS-backed storage because SQLite locking is unreliable there.

The container applies migrations before starting Gunicorn. Persist MariaDB separately; the container itself is stateless. Set `CAPTURE_BASE_URL` when the app is behind a reverse proxy so generated capture URLs use the external scheme and host. Health checks are available at `/health/live` and `/health/ready`.

The body limit defaults to 1 MiB and can be changed with `MAX_CAPTURE_BODY_BYTES`. By default, the app records the direct peer IP and ignores forwarded IP headers. Configure `TRUSTED_PROXY_CIDRS` as a comma-separated list only when a known reverse proxy sets `X-Forwarded-For`.

## Tests and lint

```sh
python -m pytest
ruff check .
```
