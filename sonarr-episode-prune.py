from urllib.parse import urlparse, urlencode
from operator import itemgetter
import click
import requests
import logging
import re
import os
import json

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

LOG = logging.getLogger("Sonarr Episode Prune")

class Hostname(click.ParamType):
    name = 'hostname'
    def convert(self, value, param, ctx):
        if not isinstance(value, tuple):
            url = urlparse(value)
            if url.scheme not in ('http', 'https'):
                self.fail('invalid URL scheme (%s).  Only HTTP URLs are '
                          'allowed' % url.scheme, param, ctx)
        return value

class ApiKey(click.ParamType):
    name = 'api-key'
    def convert(self, value, param, ctx):
        found = re.match(r'[0-9a-z]{32}', value)
        if not found:
            self.fail(
                f'{value} is not a 32-character string',
                param,
                ctx,
            )
        return value

class PruneSeries(click.ParamType):
    name = 'prune-series'
    def convert(self, value, param, ctx):
        found = re.match(r'^([a-z0-9-])+(,[a-z0-9-]+)*$', value)
        if not found:
            self.fail(
                f'{value} is not a valid series list',
                param,
                ctx,
            )
        return value

@click.command()
@click.option(
    '--hostname', '-h', envvar='SONARR_HOSTNAME', 
    type=Hostname(), 
    required=True,
    help='Sonarr instance Hostname URL e.g. "http://127.0.0.1:8989/sonarr"'
)
@click.option(
    '--api-key', '-a', envvar='SONARR_APIKEY', 
    type=ApiKey(), 
    required=True,
    help='Sonarr instance API key'
)
@click.option(
    '--prune-series', '-s', envvar='SONARR_PRUNE_SERIES', 
    type=PruneSeries(), 
    required=True,
    help='Comma separated list of Series to prune e.g. "the-daily-show,conan-2010"'
)
@click.option(
    '--keep-episodes', '-k', envvar='SONARR_KEEP_EPISODES', 
    type=int, 
    default=30,
    show_default=True,
    help='Number of episodes to keep per series'
)
@click.option(
    '--dry-run', '-d', envvar='DRY_RUN', 
    is_flag=True,
    default=False,
    required=False,
    help='Do not let this script delete or unmonitor any episodes'
)
@click.pass_context
def cli(ctx, hostname, api_key, prune_series, keep_episodes, dry_run):
    ctx.obj = {
        'hostname': hostname,
        'api_key': api_key,
        'prune_series': prune_series,
        'keep_episodes': keep_episodes,
        'dry_run': dry_run
    }

    all_series = api_request('GET', 'series')
    all_series = {x['titleSlug']: x for x in all_series}

    for show in prune_series.split(","):
        if show in prune_series:
            LOG.info(f"Checking series {show} for any episodes to delete")
            clean_series(all_series[show]['id'])
        else:
            LOG.warning(f"Series {show} was not found in Sonarr")

@click.pass_context
def api_request(ctx, method, endpoint, payload=None):
    """Make a API request to the Sonarr API
    """

    if payload == None:
        payload = {}

    headers = {
        'X-Api-Key': ctx.obj['api_key']
    }

    if method == 'PUT':
        url = "%s/api/%s" % (ctx.obj['hostname'], endpoint)
        LOG.debug(f"Sending API request to {url}")
        response = requests.put(url, headers=headers, data=payload)
    elif method == 'DELETE':
        url = "%s/api/%s" % (ctx.obj['hostname'], endpoint)
        LOG.debug(f"Sending API request to {url}")
        response = requests.delete(url, headers=headers)
    else:
        url = "%s/api/%s?%s" % (ctx.obj['hostname'], endpoint, urlencode(payload))
        LOG.debug(f"Sending API request to {url}")
        response = requests.get(url, headers=headers, data=payload)

    return response.json()

@click.pass_context
def clean_series(ctx, series_id):
    """Take a series id and remove old episodes based on the context
    """

    # Get the episodes for the series
    all_episodes = api_request('GET', 'episode', {'seriesId': series_id})

    # Filter only downloaded episodes
    episodes = [episode for episode in all_episodes if episode['hasFile']]
    
    # Sort episodes
    episodes = sorted(episodes, key=itemgetter('seasonNumber', 'episodeNumber'))
    LOG.debug(f"{len(episodes)} episodes downloaded")

    # Filter monitored episodes
    monitored_episodes = [episode for episode in all_episodes if episode['monitored']]
    LOG.debug(f"{len(monitored_episodes)} episodes monitored")
    monitored_episodes = sorted(monitored_episodes, key=itemgetter('seasonNumber', 'episodeNumber'))

    # Process episodes
    for episode in episodes[:-ctx.obj['keep_episodes']]:
        LOG.debug(f"Processing episode {episode['title']}")

        # Get information about the episode
        episode_file = api_request('GET', f"episodefile/{episode['episodeFileId']}")

        # Delete and unmonitor episode
        if ctx.obj['dry_run'] == False:
            LOG.debug(f"Deleting episode s{episode['seasonNumber']}e{episode['episodeNumber']}")
            episode['monitored'] = False
            api_request('DELETE', f"episodefile/{episode_file['id']}")
            api_request('PUT', 'episode', payload=json.dumps(episode))
            
    if ctx.obj['dry_run'] == True:
        LOG.info(f"Dry run set, not deleting {len(episodes[:-ctx.obj['keep_episodes']])} episodes")
    else:
        LOG.info(f"{len(episodes[:-ctx.obj['keep_episodes']])} episodes deleted")

if __name__ == "__main__":
    cli()
