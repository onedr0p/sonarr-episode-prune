FROM python:alpine

WORKDIR /app

COPY requirements.txt /app

# hadolint ignore=DL3018
RUN apk add --no-cache bash curl tini procps jq ca-certificates \
    && pip install -r requirements.txt

COPY docker-entrypoint.sh /
COPY sonarr-episode-prune.py ./sonarr-episode-prune.py 

ENTRYPOINT [ "/sbin/tini", "--", "/docker-entrypoint.sh"]