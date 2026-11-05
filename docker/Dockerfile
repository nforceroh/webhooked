FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/app \
    SQLITE_PATH=/data/db.sqlite3

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential pkg-config default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app

RUN pip install --no-cache-dir '.[mariadb]' \
    && python app/manage.py collectstatic --noinput \
    && groupadd --system --gid 10001 webhooked \
    && useradd --system --uid 10001 --gid webhooked --home-dir /app webhooked \
    && mkdir /data \
    && chown -R webhooked:webhooked /app /data

VOLUME /data

USER webhooked

EXPOSE 8000

CMD ["sh", "-c", "python app/manage.py migrate && gunicorn webhooked.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 30"]
