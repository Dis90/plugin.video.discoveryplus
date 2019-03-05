# -*- coding: utf-8 -*-

import sys
from urlparse import parse_qsl
import json

from resources.lib.kodihelper import KodiHelper

base_url = sys.argv[0]
handle = int(sys.argv[1])
helper = KodiHelper(base_url, handle)

def list_pages():
    collections = helper.d.get_homepage()

    helper.add_item(helper.language(30009), params={'action': 'list_show_categories'})
    helper.add_item(helper.language(30010), params={'action': 'list_channels'})
    helper.add_item(helper.language(30007), params={'action': 'search'})

    # List frontpage show categories
    for collection in collections['included']:
        if collection['type'] == 'collection' and collection['attributes'].get('title'):

            params = {
                'action': 'list_collection_shows',
                'collection_data': json.dumps(collection['relationships']['items']['data'])
            }

            info = {
                'plot': collection['attributes'].get('name')
            }

            helper.add_item(collection['attributes'].get('title'), params, info=info)

    helper.eod()

def list_show_categories():
    helper.add_item(helper.language(30014), params={'action': 'list_shows'})
    helper.add_item('A - Ö', params={'action': 'list_alphabet'})
    helper.eod()

def list_shows(search_query=None, letter=None):
    if search_query:
        shows = helper.d.get_shows(search_query=search_query)
    elif letter:
        shows = helper.d.get_shows(letter=letter)
    else: # List popular shows
        shows = helper.d.get_shows()

    for show in shows['data']:
        title = show['attributes']['name'].encode('utf-8')

        params = {
            'action': 'list_seasons',
            'show_id': show['id'],
            'seasons': json.dumps(show['attributes']['seasonNumbers'])
            }

        info = {
            'mediatype': 'tvshow',
            'plot': show['attributes'].get('description')
        }

        fanart_image = json.loads(helper.d.get_metadata(json.dumps(shows['included']), show['relationships']['images']['data'][0]['id']))['src'] if show['relationships'].get('images') else None
        thumb_image = json.loads(helper.d.get_metadata(json.dumps(shows['included']), show['relationships']['images']['data'][-1]['id']))['src'] if show['relationships'].get('images') else None
        clearlogo = thumb_image if len(show['relationships']['images']['data']) == 2 else None

        show_art = {
            'fanart': fanart_image,
            'thumb': thumb_image,
            'clearlogo': clearlogo
            }

        helper.add_item(title, params, info=info, art=show_art, content='tvshows')
    helper.eod()

def list_alphabet():
    alpha = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'Å', 'Ä', 'Ö', '#']

    for letter in alpha:

        params = {
            'action': 'list_shows',
            'letter': letter
        }

        helper.add_item(letter, params=params)
    helper.eod()

# There has to be better way to do this!
def list_collection_shows(collection_data):
    collections = helper.d.get_homepage()

    # List all collectionsItem id's in collection_data
    for collection in json.loads(collection_data):
        # Get frontpage data
        for collectionItem in collections['included']:
            # Match collectionItem id's to get actual show id
            if collectionItem['id'] == collection['id']:
                # Is it show or video?
                if collectionItem['relationships'].get('show'):
                    show_id = collectionItem['relationships']['show']['data']['id']

                    for show_data in collections['included']:
                        if show_data['id'] == show_id:
                            if show_data['attributes'].get('name'): # parse content

                                title = show_data['attributes']['name'].encode('utf-8')

                                params = {
                                    'action': 'list_seasons',
                                    'show_id': show_data['id'],
                                    'seasons': json.dumps(show_data['attributes']['seasonNumbers'])
                                }

                                info = {
                                    'mediatype': 'tvshow',
                                    'plot': show_data['attributes'].get('description')
                                }

                                fanart_image = json.loads(helper.d.get_metadata(json.dumps(collections['included']),
                                                                                show_data['relationships']['images']['data'][
                                                                                    0]['id']))['src'] if show_data[
                                    'relationships'].get('images') else None
                                thumb_image = json.loads(helper.d.get_metadata(json.dumps(collections['included']),
                                                                               show_data['relationships']['images']['data'][
                                                                                   -1]['id']))['src'] if show_data[
                                    'relationships'].get('images') else None
                                clearlogo = thumb_image if len(show_data['relationships']['images']['data']) == 2 else None

                                show_art = {
                                    'fanart': fanart_image,
                                    'thumb': thumb_image,
                                    'clearlogo': clearlogo
                                }

                                helper.add_item(title, params, info=info, art=show_art, content='tvshows')

                else: # Is video
                    video_id = collectionItem['relationships']['video']['data']['id']

                    for video_data in collections['included']:
                        if video_data['id'] == video_id:

                            # Dplay+ content check
                            # If first package is Registered show has been or is available for free
                            if video_data['attributes']['availabilityWindows'][0]['package'] == 'Registered':
                                # Check if there is ending time for free availability
                                if video_data['attributes']['availabilityWindows'][0].get('playableEnd'):
                                    # Check if show is still available for free
                                    if helper.d.parse_datetime(video_data['attributes']['availabilityWindows'][0][
                                                                   'playableStart']) < helper.d.get_current_time() < helper.d.parse_datetime(
                                        video_data['attributes']['availabilityWindows'][0]['playableEnd']):

                                        dplayplus = False  # Show is still available for free
                                    else:  # Show is not anymore available for free
                                        dplayplus = True
                                else:  # No ending time for free availability
                                    dplayplus = False
                            else:
                                dplayplus = True  # Dplay+ subscription is needed

                            if dplayplus == True:
                                list_title = video_data['attributes'].get('name').lstrip() + ' [Dplay+]'
                            else:
                                list_title = video_data['attributes'].get('name').lstrip()

                            params = {
                                'action': 'play',
                                'video_id': video_data['id'],
                                'video_type': 'video'
                            }

                            show_title = json.loads(helper.d.get_metadata(json.dumps(collections['included']), video_data['relationships']['show']['data']['id']))['name']

                            fanart_image = json.loads(helper.d.get_metadata(json.dumps(collections['included']),
                                                                            video_data['relationships']['images']['data'][0][
                                                                                'id']))['src'] if video_data[
                                'relationships'].get('images') else None

                            duration = video_data['attributes']['videoDuration'] / 1000.0 if video_data['attributes'].get(
                                'videoDuration') else None

                            episode_info = {
                                'mediatype': 'episode',
                                'title': video_data['attributes'].get('name').lstrip(),
                                'tvshowtitle': show_title,
                                'season': video_data['attributes'].get('seasonNumber'),
                                'episode': video_data['attributes'].get('episodeNumber'),
                                'plot': video_data['attributes'].get('description'),
                                'duration': duration,
                                'aired': video_data['attributes'].get('airDate')
                            }

                            # Watched status from Dplay
                            if video_data['attributes']['viewingHistory']['viewed']:
                                if video_data['attributes']['viewingHistory']['completed']: # Watched video
                                    episode_info['playcount'] = 1
                                    resume = 0
                                    total = duration
                                else: # Partly watched video
                                    resume = video_data['attributes']['viewingHistory']['position'] / 1000.0
                                    total = duration
                            else: # Unwatched video
                                episode_info['playcount'] = 0
                                resume = 0
                                total = 1

                            episode_art = {
                                'fanart': fanart_image,
                                'thumb': fanart_image
                            }

                            helper.add_item(list_title, params=params, info=episode_info, art=episode_art,
                                            content='episodes', playable=True, resume=resume, total=total)


    helper.eod()

def list_seasons(show_id, seasons):
    for season in json.loads(seasons):

        title = helper.language(30011) + ' ' + str(season)
        params = {
            'action': 'list_videos',
            'show_id': show_id,
            'season_number': season
        }

        info = {
            'mediatype': 'season'
        }

        helper.add_item(title, params, info=info, content='seasons')
    helper.eod()

def list_videos(show_id, season_number):
    videos = helper.d.get_videos(show_id, season_number)

    for i in videos['data']:

        # Dplay+ content check
        # If first package is Registered show has been or is available for free
        if i['attributes']['availabilityWindows'][0]['package'] == 'Registered':
            # Check if there is ending time for free availability
            if i['attributes']['availabilityWindows'][0].get('playableEnd'):
                # Check if show is still available for free
                if helper.d.parse_datetime(i['attributes']['availabilityWindows'][0][
                                               'playableStart']) < helper.d.get_current_time() < helper.d.parse_datetime(
                        i['attributes']['availabilityWindows'][0]['playableEnd']):

                    dplayplus = False # Show is still available for free
                else: # Show is not anymore available for free
                    dplayplus = True
            else: # No ending time for free availability
                dplayplus = False
        else:
            dplayplus = True # Dplay+ subscription is needed


        if dplayplus == True:
            list_title = i['attributes'].get('name').lstrip() + ' [Dplay+]'
        else:
            list_title = i['attributes'].get('name').lstrip()

        params = {
            'action': 'play',
            'video_id': i['id'],
            'video_type': 'video'
        }

        show_title = json.loads(helper.d.get_metadata(json.dumps(videos['included']),
                                                      i['relationships']['show']['data']['id']))['name']

        fanart_image = json.loads(
            helper.d.get_metadata(json.dumps(videos['included']), i['relationships']['images']['data'][0]['id']))[
            'src'] if i['relationships'].get('images') else None

        duration = i['attributes']['videoDuration']/1000.0 if i['attributes'].get('videoDuration') else None

        episode_info = {
            'mediatype': 'episode',
            'title': i['attributes'].get('name').lstrip(),
            'tvshowtitle': show_title,
            'season': i['attributes'].get('seasonNumber'),
            'episode': i['attributes'].get('episodeNumber'),
            'plot': i['attributes'].get('description'),
            'duration': duration,
            'aired': i['attributes'].get('airDate')
        }

        # Watched status from Dplay
        if i['attributes']['viewingHistory']['viewed']:
            if i['attributes']['viewingHistory']['completed']: # Watched video
                episode_info['playcount'] = 1
                resume = 0
                total = duration
            else: # Partly watched video
                resume = i['attributes']['viewingHistory']['position']/1000.0
                total = duration
        else: # Unwatched video
            episode_info['playcount'] = 0
            resume = 0
            total = 1

        episode_art = {
            'fanart': fanart_image,
            'thumb': fanart_image
        }

        helper.add_item(list_title, params=params, info=episode_info, art=episode_art, content='episodes', playable=True,
                    resume=resume, total=total)

    helper.eod()

def list_channels():
    channels = helper.d.get_channels()

    for i in channels['included']:
        if i['type'] == 'channel':
            params = {
                'action': 'list_channel_shows',
                'channel_id': i['id']
            }

            channel_info = {
                'mediatype': 'tvshow',
                'title': i['attributes'].get('name'),
                'plot': i['attributes'].get('description')
            }

            fanart_image = json.loads(
                helper.d.get_metadata(json.dumps(channels['included']), i['relationships']['images']['data'][0]['id']))[
                'src'] if i['relationships'].get('images') else None
            thumb_image = json.loads(helper.d.get_metadata(json.dumps(channels['included']),
                                                           i['relationships']['images']['data'][1]['id']))['src'] if \
            i['relationships'].get('images') else None

            channel_art = {
                'fanart': fanart_image,
                'thumb': thumb_image
            }

            helper.add_item(i['attributes'].get('name'), params=params, info=channel_info, art=channel_art)
    helper.eod()

def list_channel_shows(channel_id):
    shows = helper.d.get_channel_shows(channel_id)

    for i in shows['included']:
        # List channel livestream if available
        if i['type'] == 'channel' and i['id'] == channel_id and i['attributes']['hasLiveStream']:
            params = {
                'action': 'play',
                'video_id': i['id'],
                'video_type': 'channel'
            }

            channel_info = {
                'mediatype': 'video',
                'title': i['attributes'].get('name'),
                'plot': i['attributes'].get('description')
            }

            fanart_image = json.loads(helper.d.get_metadata(json.dumps(shows['included']), i['relationships']['images']['data'][0]['id']))['src'] if i['relationships'].get('images') else None
            thumb_image = json.loads(helper.d.get_metadata(json.dumps(shows['included']),
                                                           i['relationships']['images']['data'][1]['id']))['src'] if \
            i['relationships'].get('images') else None
            clearlogo = thumb_image if len(i['relationships']['images']['data']) >= 2 else None

            channel_art = {
                'fanart': fanart_image,
                'thumb': thumb_image,
                'clearlogo': clearlogo
            }

            helper.add_item(i['attributes'].get('name'), params=params, info=channel_info, art=channel_art, playable=True)

        # Channel shows
        if i['type'] == 'show':

            title = i['attributes']['name'].encode('utf-8')

            params = {
                'action': 'list_seasons',
                'show_id': i['id'],
                'seasons': json.dumps(i['attributes']['seasonNumbers'])
            }

            info = {
                'mediatype': 'tvshow',
                'plot': i['attributes'].get('description')
            }

            fanart_image = json.loads(
                helper.d.get_metadata(json.dumps(shows['included']), i['relationships']['images']['data'][0]['id']))[
                'src'] if i['relationships'].get('images') else None
            thumb_image = json.loads(helper.d.get_metadata(json.dumps(shows['included']),
                                                           i['relationships']['images']['data'][-1]['id']))['src'] if \
            i['relationships'].get('images') else None
            clearlogo = thumb_image if len(i['relationships']['images']['data']) == 2 else None

            show_art = {
                'fanart': fanart_image,
                'thumb': thumb_image,
                'clearlogo': clearlogo
            }

            helper.add_item(title, params, info=info, art=show_art, content='tvshows')
    helper.eod()


def search():
    search_query = helper.get_user_input(helper.language(30007))
    if search_query:
        list_shows(search_query=search_query)
    else:
        helper.log('No search query provided.')
        return False

def router(paramstring):
    """
    Router function that calls other functions
    depending on the provided paramstring
    :param paramstring: URL encoded plugin paramstring
    :type paramstring: str
    """
    # Parse a URL-encoded paramstring to the dictionary of
    # {<parameter>: <value>} elements
    params = dict(parse_qsl(paramstring))
    # Check the parameters passed to the plugin
    if 'setting' in params:
        if params['setting'] == 'reset_credentials':
            helper.reset_credentials()
        if params['setting'] == 'set_locale':
            helper.set_locale()
    elif 'action' in params:
        if params['action'] == 'list_show_categories':
            list_show_categories()
        elif params['action'] == 'list_shows':
            if 'letter' in params:
                list_shows(letter=params['letter'])
            else:
                list_shows()
        elif params['action'] == 'list_alphabet':
            list_alphabet()
        elif params['action'] == 'list_collection_shows':
            list_collection_shows(collection_data=params['collection_data'])
        elif params['action'] == 'list_channels':
            list_channels()
        elif params['action'] == 'list_channel_shows':
            list_channel_shows(channel_id=params['channel_id'])
        elif params['action'] == 'list_seasons':
            list_seasons(show_id=params['show_id'], seasons=params['seasons'])
        elif params['action'] == 'list_videos':
            list_videos(show_id=params['show_id'], season_number=params['season_number'])
        elif params['action'] == 'play':
            # Play a video from a provided URL.
            helper.play_item(params['video_id'], params['video_type'])
        elif params['action'] == 'search':
            search()
    else:
        try:
            if helper.check_for_prerequisites():
                list_pages()
        except helper.d.DplayError as error:
            if error.value == 'unauthorized': # Login error, wrong email or password
                helper.dialog('ok', helper.language(30006), helper.language(30012))
            else:
                helper.dialog('ok', helper.language(30006), error.value)

if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])
