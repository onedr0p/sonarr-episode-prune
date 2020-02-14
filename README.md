# sonarr-episode-prune

Delete episodes from specified series in Sonarr. Useful for shows that air daily.

## Usage

### CLI

```bash
python3 sonarr-episode-prune.py \
  --hostname http://192.168.1.161:8989/sonarr \
  --api-key 9cfe6e5d8d3c466699e209b439bba6dc \
  --prune-series the-daily-show,conan-2010,the-late-show-with-stephen-colbert \
  --keep-episodes 10 \
  --dry-run
```

### Docker

```yaml
version: '3.7'
services:
  sonarr-episode-prune:
    image: onedr0p/sonarr-episode-prune:v3.0.0
    environment:
      SONARR_HOSTNAME: http://192.168.1.161:8989/sonarr
      SONARR_APIKEY: 9cfe6e5d8d3c466699e209b439bba6dc
      SONARR_PRUNE_SERIES: the-daily-show,conan-2010,the-late-show-with-stephen-colbert
      SONARR_KEEP_EPISODES: 10
      DRY_RUN: True
```