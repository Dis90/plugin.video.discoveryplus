# -*- coding: utf-8 -*-

import sys
from urlparse import parse_qsl
import json

from resources.lib.kodihelper import KodiHelper

base_url = sys.argv[0]
handle = int(sys.argv[1])
helper = KodiHelper(base_url, handle)

def list_pages():
    helper.add_item(helper.language(30001), params={'action': 'list_page', 'page_path': '/home'})
    helper.add_item(helper.language(30016), params={'action': 'list_favorites'})
    helper.add_item(helper.language(30007), params={'action': 'search'})

    # List menu items (Shows, Categories)
    page_data = helper.d.parse_page('menu')

    collections = page_data['collections']
    collectionItems = page_data['collectionItems']
    images = page_data['images']
    links = page_data['links']
    routes = page_data['routes']

    for data_collection in page_data['data']['relationships']['items']['data']:
        for collectionItem in collectionItems:
            if data_collection['id'] == collectionItem['id']:
                for collection in collections:
                    if collectionItem['relationships']['collection']['data']['id'] == collection['id']:
                        for collectionItem2 in collectionItems:
                            if collection['relationships']['items']['data'][0]['id'] == collectionItem2['id']:
                                # Get only links
                                if collectionItem2['relationships'].get('link'):
                                    for link in links:
                                        # Hide unwanted menu links
                                        if collectionItem2['relationships']['link']['data']['id'] == link['id'] and \
                                                link['attributes'][
                                                    'kind'] == 'Internal Link' and collection['attributes'][
                                            'title'] not in helper.d.unwanted_menu_items:

                                            # Find page path from routes
                                            for route in routes:
                                                if route['id'] == \
                                                        link['relationships']['linkedContentRoutes']['data'][0][
                                                            'id']:
                                                    next_page_path = route['attributes']['url']

                                            params = {
                                                'action': 'list_page',
                                                'page_path': next_page_path
                                            }

                                            link_info = {
                                                'plot': link['attributes'].get('description')
                                            }

                                            if link['relationships'].get('images'):
                                                for i in images:
                                                    if i['id'] == link['relationships']['images']['data'][0]['id']:
                                                        image = i['attributes']['src']
                                            else:
                                                image = None

                                            link_art = {
                                                'fanart': image,
                                                'thumb': image
                                            }
                                            # Have to use collection title instead link title because some links doesn't have title
                                            helper.add_item(collection['attributes']['title'], params, info=link_info,
                                                            content='videos',
                                                            art=link_art)

    helper.eod()

def list_page(page_path=None):
    page_data = helper.d.parse_page(page_path)

    user_favorites = ",".join([str(x['id']) for x in helper.d.get_favorites()['data']['relationships']['favorites']['data']])

    pages = page_data['pages']
    pageItems = page_data['pageItems']
    collections = page_data['collections']
    collectionItems = page_data['collectionItems']
    images = page_data['images']
    shows = page_data['shows']
    channels = page_data['channels']
    genres = page_data['genres']
    routes = page_data['routes']

    if page_data['data']['type'] == 'route':
        for page in pages:
            # If only one pageItem in page -> relationships -> items -> data, list content page (categories)
            if len(page['relationships']['items']['data']) == 1:
                for collection in collections:
                    if collection['attributes'].get('component'):

                        # List genre categories (Popular, All) and page content from Programs, Eurosport channels, Categories etc)
                        if collection['attributes']['component']['id'] == 'content-grid':
                            if collection['attributes'].get('title'):

                                params = {
                                    'action': 'list_collection_items',
                                    'page_path': page_path,
                                    'collection_id': collection['id']
                                }

                                info = {
                                    'mediatype': 'video'
                                }

                                helper.add_item(collection['attributes']['title'], params, info=info,
                                                content='tvshows',
                                                folder_name=page['attributes'].get('pageMetadataTitle'))

                            # Category has no subpages -> list shows, example categories in Dplay.dk
                            else:
                                for collection_relationship in collection['relationships']['items']['data']:
                                    for collectionItem in collectionItems:
                                        if collection_relationship['id'] == collectionItem['id']:

                                            # List shows
                                            if collectionItem['relationships'].get('show'):
                                                for show in shows:
                                                    if collectionItem['relationships']['show']['data']['id'] == show[
                                                        'id']:
                                                        attributes = show['attributes']
                                                        relationships = show['relationships']

                                                        title = attributes['name'].encode('utf-8')

                                                        # Find page path from routes
                                                        for route in routes:
                                                            if route['id'] == relationships['routes']['data'][0]['id']:
                                                                next_page_path = route['attributes']['url']

                                                        params = {
                                                            'action': 'list_page',
                                                            'page_path': next_page_path
                                                        }

                                                        g = []
                                                        if relationships.get('genres'):
                                                            for genre in genres:
                                                                for show_genre in relationships['genres']['data']:
                                                                    if genre['id'] == show_genre['id']:
                                                                        g.append(genre['attributes']['name'])

                                                        if relationships.get('primaryChannel'):
                                                            for channel in channels:
                                                                if channel['id'] == \
                                                                        relationships['primaryChannel']['data'][
                                                                            'id']:
                                                                    primaryChannel = channel['attributes']['name']
                                                        else:
                                                            primaryChannel = None

                                                        info = {
                                                            'mediatype': 'tvshow',
                                                            'plot': attributes.get('description'),
                                                            'genre': g,
                                                            'studio': primaryChannel
                                                        }

                                                        # Add or delete favorite context menu
                                                        if str(show['id']) not in user_favorites:
                                                            menu = []
                                                            menu.append((helper.language(30009),
                                                                         'RunPlugin(plugin://' + helper.addon_name + '/?action=add_favorite&show_id=' + str(
                                                                             show['id']) + ')',))
                                                        else:
                                                            menu = []
                                                            menu.append((helper.language(30010),
                                                                         'RunPlugin(plugin://' + helper.addon_name + '/?action=delete_favorite&show_id=' + str(
                                                                             show['id']) + ')',))

                                                        if relationships.get('images'):
                                                            for image in images:
                                                                if image['id'] == relationships['images']['data'][0][
                                                                    'id']:
                                                                    if image['attributes'].get('src'):
                                                                        fanart_image = image['attributes']['src']
                                                                    else:
                                                                        fanart_image = None
                                                                if image['id'] == relationships['images']['data'][-1][
                                                                    'id']:
                                                                    if image['attributes'].get('src'):
                                                                        thumb_image = image['attributes']['src']
                                                                    else:
                                                                        thumb_image = None
                                                        else:
                                                            fanart_image = None
                                                            thumb_image = None

                                                        show_art = {
                                                            'fanart': fanart_image,
                                                            'thumb': thumb_image
                                                        }

                                                        if relationships.get('images'):
                                                            show_art['clearlogo'] = thumb_image if len(
                                                                relationships['images']['data']) == 2 else None

                                                        helper.add_item(title, params, info=info, art=show_art,
                                                                        content='tvshows',
                                                                        menu=menu,
                                                                        folder_name=page['attributes'].get('pageMetadataTitle'),
                                                                        sort_method='unsorted')

            # More than one pageItem (homepage, seasons, channels)
            else:
                for page_relationship in page['relationships']['items']['data']:
                    for pageItem in pageItems:
                        if page_relationship['id'] == pageItem['id']:
                            for collection in collections:
                                # PageItems have only one collection
                                if pageItem['relationships']['collection']['data']['id'] == collection['id']:

                                    # Use content hero to get channel livestream
                                    if collection['attributes']['component']['id'] == 'content-hero':
                                        for c in collection['relationships']['items']['data']:
                                            for collectionItem in collectionItems:
                                                if c['id'] == collectionItem['id']:
                                                    if collectionItem['relationships'].get('channel'):
                                                        for channel in channels:
                                                            if collectionItem['relationships']['channel']['data']['id'] == channel['id']:
                                                                params = {
                                                                    'action': 'play',
                                                                    'video_id': channel['id'],
                                                                    'video_type': 'channel'
                                                                }

                                                                channel_info = {
                                                                    'mediatype': 'video',
                                                                    'title': channel['attributes'].get('name'),
                                                                    'plot': channel['attributes'].get('description'),
                                                                    'playcount': '0'
                                                                }

                                                                if channel['relationships'].get('images'):
                                                                    for i in images:
                                                                        if i['id'] == \
                                                                                channel['relationships']['images'][
                                                                                    'data'][0][
                                                                                    'id']:
                                                                            fanart_image = i['attributes']['src']
                                                                        if i['id'] == \
                                                                                channel['relationships']['images'][
                                                                                    'data'][-1][
                                                                                    'id']:
                                                                            thumb_image = i['attributes']['src']
                                                                else:
                                                                    fanart_image = None
                                                                    thumb_image = None

                                                                channel_art = {
                                                                    'fanart': fanart_image,
                                                                    'thumb': thumb_image
                                                                }

                                                                if channel['relationships'].get('images'):
                                                                    channel_art['clearlogo'] = thumb_image if len(
                                                                        channel['relationships']['images'][
                                                                            'data']) >= 2 else None

                                                                helper.add_item(
                                                                    helper.language(30014) + ' ' + channel[
                                                                        'attributes'].get('name'),
                                                                    params=params,
                                                                    art=channel_art, info=channel_info,
                                                                    content='videos',
                                                                    playable=True)

                                    # Homepage, Channel -> subcategories (New videos, Shows).
                                    # Hide promotion grids and hide empty grids (example upcoming events when there is no upcoming events).
                                    if collection['attributes']['component']['id'] == 'content-grid' and collection.get('relationships'):
                                        params = {
                                            'action': 'list_collection_items',
                                            'page_path': page_path,
                                            'collection_id': collection['id']
                                        }

                                        info = {
                                            'mediatype': 'video'
                                        }

                                        helper.add_item(collection['attributes']['title'], params, info=info,
                                                    content='tvshows',
                                                    folder_name=page['attributes'].get('pageMetadataTitle'))

                                    # List series season grid
                                    if collection['attributes']['component']['id'] == 'tabbed-content':
                                        # Check if there's any seasons of show or sport event
                                        if collection['attributes']['component'].get('filters'):
                                            for option in collection['attributes']['component']['filters'][0]['options']:
                                                title = helper.language(30011) + ' ' + str(option['id'])
                                                params = {
                                                    'action': 'list_videos',
                                                    'collection_id': collection['id'], # 66290614510668341673562607828298581172
                                                    'mandatoryParams': collection['attributes']['component'].get(
                                                        'mandatoryParams'),  # pf[show.id]=12423
                                                    'parameter': option['parameter']  # pf[seasonNumber]=1
                                                }

                                                info = {
                                                    'mediatype': 'season'
                                                }

                                                helper.add_item(title, params, info=info, content='seasons',
                                                        folder_name=page['attributes'].get('pageMetadataTitle'), sort_method='sort_label')


                                    # Channels page
                                    # Use generic-hero (promotion) only in channels page
                                    elif collection['attributes']['component']['id'] == 'generic-hero':
                                        # Get channel name and path
                                        for c in collection['relationships']['items']['data']:
                                            for collectionItem in collectionItems:
                                                if c['id'] == collectionItem['id']:
                                                    if collectionItem['relationships'].get('channel'):
                                                        # Get all channels in page data
                                                        for channel in channels:
                                                            if collectionItem['relationships']['channel']['data']['id'] == channel[
                                                                'id']:
                                                                # Find page path from routes
                                                                for route in routes:
                                                                    if route['id'] == \
                                                                            channel['relationships']['routes']['data'][
                                                                                0]['id']:
                                                                        next_page_path = route['attributes']['url']

                                                                params = {
                                                                    'action': 'list_page',
                                                                    'page_path': next_page_path
                                                                }

                                                                channel_info = {
                                                                    'mediatype': 'video',
                                                                    'title': channel['attributes'].get('name'),
                                                                    'plot': channel['attributes'].get('description')
                                                                }

                                                                if channel['relationships'].get('images'):
                                                                    for i in images:
                                                                        if i['id'] == \
                                                                                channel['relationships']['images'][
                                                                                    'data'][0]['id']:
                                                                            fanart_image = i['attributes']['src']
                                                                        if i['id'] == \
                                                                                channel['relationships']['images'][
                                                                                    'data'][-1]['id']:
                                                                            thumb_image = i['attributes']['src']
                                                                else:
                                                                    fanart_image = None
                                                                    thumb_image = None

                                                                channel_art = {
                                                                    'fanart': fanart_image,
                                                                    'thumb': thumb_image
                                                                }

                                                                if channel['relationships'].get('images'):
                                                                    channel_art['clearlogo'] = thumb_image if len(
                                                                        channel['relationships']['images'][
                                                                            'data']) >= 2 else None


                                                                helper.add_item(channel['attributes'].get('name'),
                                                                                params, info=channel_info, content='videos', art=channel_art, folder_name=page['attributes'].get('pageMetadataTitle'), sort_method='unsorted')

    helper.eod()

def list_collection_items(page_path, collection_id):
    page_data = helper.d.parse_page(page_path)

    user_favorites = ",".join([str(x['id']) for x in helper.d.get_favorites()['data']['relationships']['favorites']['data']])
    user_packages = ",".join([str(x) for x in helper.d.get_user_data()['attributes']['packages']])

    collections = page_data['collections']
    collectionItems = page_data['collectionItems']
    images = page_data['images']
    shows = page_data['shows']
    videos = page_data['videos']
    channels = page_data['channels']
    genres = page_data['genres']
    links = page_data['links']
    routes = page_data['routes']

    for collection in collections:
        if collection['id'] == collection_id:
            for collection_relationship in collection['relationships']['items']['data']:
                for collectionItem in collectionItems:
                    if collection_relationship['id'] == collectionItem['id']:

                        # List shows
                        if collectionItem['relationships'].get('show'):
                            for show in shows:
                                if collectionItem['relationships']['show']['data']['id'] == show['id']:
                                    attributes = show['attributes']
                                    relationships = show['relationships']

                                    title = attributes['name'].encode('utf-8')

                                    # Find page path from routes
                                    for route in routes:
                                        if route['id'] == relationships['routes']['data'][0]['id']:
                                            next_page_path = route['attributes']['url']

                                    params = {
                                        'action': 'list_page',
                                        'page_path': next_page_path
                                    }

                                    g = []
                                    if relationships.get('genres'):
                                        for genre in genres:
                                            for show_genre in relationships['genres']['data']:
                                                if genre['id'] == show_genre['id']:
                                                    g.append(genre['attributes']['name'])

                                    if relationships.get('primaryChannel'):
                                        for channel in channels:
                                            if channel['id'] == relationships['primaryChannel']['data']['id']:
                                                primaryChannel = channel['attributes']['name']
                                    else:
                                        primaryChannel = None

                                    info = {
                                        'mediatype': 'tvshow',
                                        'plot': attributes.get('description'),
                                        'genre': g,
                                        'studio': primaryChannel
                                    }

                                    # Add or delete favorite context menu
                                    if str(show['id']) not in user_favorites:
                                        menu = []
                                        menu.append((helper.language(30009),
                                                     'RunPlugin(plugin://' + helper.addon_name + '/?action=add_favorite&show_id=' + str(
                                                         show['id'])  + ')',))
                                    else:
                                        menu = []
                                        menu.append((helper.language(30010),
                                                     'RunPlugin(plugin://' + helper.addon_name + '/?action=delete_favorite&show_id=' + str(
                                                         show['id'])  + ')',))

                                    if relationships.get('images'):
                                        for image in images:
                                            if image['id'] == relationships['images']['data'][0]['id']:
                                                if image['attributes'].get('src'):
                                                    fanart_image = image['attributes']['src']
                                                else:
                                                    fanart_image = None
                                            if image['id'] == relationships['images']['data'][-1]['id']:
                                                if image['attributes'].get('src'):
                                                    thumb_image = image['attributes']['src']
                                                else:
                                                    thumb_image = None
                                    else:
                                        fanart_image = None
                                        thumb_image = None

                                    show_art = {
                                        'fanart': fanart_image,
                                        'thumb': thumb_image
                                    }

                                    if relationships.get('images'):
                                        show_art['clearlogo'] = thumb_image if len(
                                            relationships['images']['data']) == 2 else None

                                    helper.add_item(title, params, info=info, art=show_art, content='tvshows', menu=menu, folder_name=collection['attributes'].get('title'), sort_method='unsorted')

                        # List videos
                        if collectionItem['relationships'].get('video'):
                            for video in videos:
                                if collectionItem['relationships']['video']['data']['id'] == video['id']:
                                    attributes = video['attributes']
                                    relationships = video['relationships']

                                    params = {
                                        'action': 'play',
                                        'video_id': video['id'],
                                        'video_type': 'video'
                                    }

                                    for s in shows:
                                        if s['id'] == relationships['show']['data']['id']:
                                            show_title = s['attributes']['name']

                                    g = []
                                    if relationships.get('genres'):
                                        for genre in genres:
                                            for video_genre in relationships['genres']['data']:
                                                if genre['id'] == video_genre['id']:
                                                    g.append(genre['attributes']['name'])

                                    if relationships.get('primaryChannel'):
                                        for channel in channels:
                                            if channel['id'] == relationships['primaryChannel']['data']['id']:
                                                primaryChannel = channel['attributes']['name']
                                    else:
                                        primaryChannel = None

                                    if relationships.get('images'):
                                        for i in images:
                                            if i['id'] == relationships['images']['data'][0]['id']:
                                                fanart_image = i['attributes']['src']
                                    else:
                                        fanart_image = None

                                    duration = attributes['videoDuration'] / 1000.0 if attributes.get(
                                        'videoDuration') else None

                                    # If episode is not yet playable, show playable time in plot
                                    if attributes.get('earliestPlayableStart'):
                                        if helper.d.parse_datetime(
                                                attributes['earliestPlayableStart']) > helper.d.get_current_time():
                                            playable = str(
                                                helper.d.parse_datetime(attributes['earliestPlayableStart']).strftime(
                                                    '%d.%m.%Y %H:%M'))
                                            if attributes.get('description'):
                                                plot = helper.language(30002) + playable + ' ' + attributes.get(
                                                    'description')
                                            else:
                                                plot = helper.language(30002) + playable
                                        else:
                                            plot = attributes.get('description')
                                    else:
                                        plot = attributes.get('description')

                                    # Dplay+ content check
                                    # Check for Dplay+ content only if user doesn't have subscription
                                    if 'Premium' not in user_packages:
                                        if len(attributes['packages']) > 1:
                                            # Get all available packages in availabilityWindows
                                            for availabilityWindow in attributes['availabilityWindows']:
                                                if availabilityWindow['package'] == 'Free':
                                                    # Check if there is ending time for free availability
                                                    if availabilityWindow.get('playableEnd'):
                                                        # Check if video is still available for free
                                                        if helper.d.parse_datetime(availabilityWindow[
                                                                                       'playableStart']) < helper.d.get_current_time() < helper.d.parse_datetime(
                                                            availabilityWindow['playableEnd']):
                                                            plot = plot

                                                        else:  # Video is not anymore available for free
                                                            plot = '[Dplay+] ' + plot
                                        else:  # Only one package in packages = Premium
                                            plot = '[Dplay+] ' + plot

                                    episode_info = {
                                        'mediatype': 'episode',
                                        'title': attributes.get('name').lstrip(),
                                        'tvshowtitle': show_title,
                                        'season': attributes.get('seasonNumber'),
                                        'episode': attributes.get('episodeNumber'),
                                        'plot': plot,
                                        'genre': g,
                                        'studio': primaryChannel,
                                        'duration': duration,
                                        'aired': attributes.get('airDate')
                                    }

                                    # Watched status from Dplay
                                    if attributes['viewingHistory']['viewed']:
                                        if attributes['viewingHistory']['completed']:  # Watched video
                                            episode_info['playcount'] = '1'
                                            resume = 0
                                            total = duration
                                        else:  # Partly watched video
                                            episode_info['playcount'] = '0'
                                            resume = attributes['viewingHistory']['position'] / 1000.0
                                            total = duration
                                    else:  # Unwatched video
                                        episode_info['playcount'] = '0'
                                        resume = 0
                                        total = 1

                                    episode_art = {
                                        'fanart': fanart_image,
                                        'thumb': fanart_image
                                    }

                                    helper.add_item(attributes.get('name').lstrip(), params=params, info=episode_info, art=episode_art,
                                                content='episodes', playable=True, resume=resume, total=total,
                                                folder_name=collection['attributes'].get('title'), sort_method='sort_episodes')

                        # List channels
                        # Used when coming from collection (example Eurosport -> Channels)
                        if collectionItem['relationships'].get('channel'):
                            for channel in channels:
                                if collectionItem['relationships']['channel']['data']['id'] == channel['id']:
                                    attributes = channel['attributes']
                                    relationships = channel['relationships']

                                    if attributes.get('hasLiveStream'):
                                        params = {
                                            'action': 'play',
                                            'video_id': channel['id'],
                                            'video_type': 'channel'
                                        }

                                        channel_info = {
                                            'mediatype': 'video',
                                            'title': attributes.get('name'),
                                            'plot': attributes.get('description'),
                                            'playcount': '0'
                                        }

                                        if relationships.get('images'):
                                            for i in images:
                                                if i['id'] == relationships['images']['data'][0]['id']:
                                                    fanart_image = i['attributes']['src']
                                                if i['id'] == relationships['images']['data'][-1]['id']:
                                                    thumb_image = i['attributes']['src']
                                        else:
                                            fanart_image = None
                                            thumb_image = None

                                        channel_art = {
                                            'fanart': fanart_image,
                                            'thumb': thumb_image
                                        }

                                        if relationships.get('images'):
                                            channel_art['clearlogo'] = thumb_image if len(
                                                relationships['images']['data']) >= 2 else None

                                        helper.add_item(helper.language(30014) + ' ' + attributes.get('name'), params=params,
                                                        info=channel_info, content='videos', art=channel_art,
                                                        playable=True, folder_name=collection['attributes'].get('title'))

                        # List categories (Reality, Comedy etc)
                        if collectionItem['relationships'].get('link'):
                            for link in links:
                                if collectionItem['relationships']['link']['data']['id'] == link['id']:
                                    # Find page path from routes
                                    for route in routes:
                                        if route['id'] == \
                                                    link['relationships']['linkedContentRoutes'][
                                                        'data'][0]['id']:
                                            next_page_path = route['attributes']['url']

                                    params = {
                                        'action': 'list_page',
                                        'page_path': next_page_path
                                    }

                                    info = {
                                        'mediatype': 'video'
                                    }

                                    if link['relationships'].get('images'):
                                        for i in images:
                                            if i['id'] == \
                                                        link['relationships']['images']['data'][0][
                                                            'id']:
                                                image = i['attributes']['src']
                                    else:
                                        image = None

                                    category_art = {
                                        'fanart': image,
                                        'thumb': image
                                    }

                                    # Category titles have stored in different places
                                    if collectionItem['attributes'].get('title'):
                                        link_title = collectionItem['attributes']['title']
                                    elif link['attributes'].get('title'):
                                        link_title = link['attributes']['title']
                                    elif link['attributes'].get('name'):
                                        link_title = link['attributes']['name']
                                    else:
                                        link_title = None

                                    helper.add_item(link_title, params, info=info,
                                                        content='videos',
                                                        art=category_art,
                                                        folder_name=collection['attributes'].get('title'))

    helper.eod()

def list_search_shows(search_query):
    page_data = helper.d.parse_page(page_path='search', search_query=search_query)

    user_favorites = ",".join([str(x['id']) for x in helper.d.get_favorites()['data']['relationships']['favorites']['data']])

    images = page_data['images']
    genres = page_data['genres']
    routes = page_data['routes']

    for show in page_data['data']:
        title = show['attributes']['name'].encode('utf-8')

        # Find page path from routes
        for route in routes:
            if route['id'] == show['relationships']['routes']['data'][0]['id']:
                next_page_path = route['attributes']['url']

        params = {
            'action': 'list_page',
            'page_path': next_page_path
        }

        g = []
        if show['relationships'].get('genres'):
            for genre in genres:
                for show_genre in show['relationships']['genres']['data']:
                    if genre['id'] == show_genre['id']:
                        g.append(genre['attributes']['name'])

        info = {
            'mediatype': 'tvshow',
            'plot': show['attributes'].get('description'),
            'genre': g
        }

        # Add or delete favorite context menu
        if str(show['id']) not in user_favorites:
            menu = []
            menu.append((helper.language(30009),
                         'RunPlugin(plugin://' + helper.addon_name + '/?action=add_favorite&show_id=' + str(
                             show['id']) + ')',))
        else:
            menu = []
            menu.append((helper.language(30010),
                         'RunPlugin(plugin://' + helper.addon_name + '/?action=delete_favorite&show_id=' + str(
                             show['id']) + ')',))

        if show['relationships'].get('images'):
            for i in images:
                if i['id'] == show['relationships']['images']['data'][0]['id']:
                    fanart_image = i['attributes']['src']
                if i['id'] == show['relationships']['images']['data'][-1]['id']:
                    thumb_image = i['attributes']['src']
        else:
            fanart_image = None
            thumb_image = None

        show_art = {
            'fanart': fanart_image,
            'thumb': thumb_image
        }

        if show['relationships'].get('images'):
            show_art['clearlogo'] = thumb_image if len(
                show['relationships']['images']['data']) == 2 else None

        folder_name = helper.language(30007) + ' / ' + search_query

        helper.add_item(title, params, info=info, art=show_art, content='tvshows', menu=menu, folder_name=folder_name, sort_method='unsorted')
    helper.eod()

def list_favorites():
    page_data = helper.d.parse_page('favorites')

    images = page_data['images']
    shows = page_data['shows']
    channels = page_data['channels']
    genres = page_data['genres']
    routes = page_data['routes']

    for favorite in page_data['data']['relationships']['favorites']['data']:
        for show_data in shows:
            if show_data['id'] == favorite['id']:

                title = show_data['attributes']['name'].encode('utf-8')

                # Find page path from routes
                for route in routes:
                    if route['id'] == show_data['relationships']['routes']['data'][0]['id']:
                        next_page_path = route['attributes']['url']

                params = {
                    'action': 'list_page',
                    'page_path': next_page_path
                }

                g = []
                if show_data['relationships'].get('genres'):
                    for genre in genres:
                        for show_genre in show_data['relationships']['genres']['data']:
                            if genre['id'] == show_genre['id']:
                                g.append(genre['attributes']['name'])

                if show_data['relationships'].get('primaryChannel'):
                    for channel in channels:
                        if channel['id'] == show_data['relationships']['primaryChannel']['data']['id']:
                            primaryChannel = channel['attributes']['name']
                else:
                    primaryChannel = None

                info = {
                    'mediatype': 'tvshow',
                    'plot': show_data['attributes'].get('description'),
                    'genre': g,
                    'studio': primaryChannel
                }

                menu = []
                menu.append((helper.language(30010),
                             'RunPlugin(plugin://' + helper.addon_name + '/?action=delete_favorite&show_id=' + str(
                                 favorite['id']) + ')',))

                if show_data['relationships'].get('images'):
                    for i in images:
                        if i['id'] == show_data['relationships']['images']['data'][0]['id']:
                            fanart_image = i['attributes']['src']
                        if i['id'] == show_data['relationships']['images']['data'][-1]['id']:
                            thumb_image = i['attributes']['src']
                else:
                    fanart_image = None
                    thumb_image = None

                show_art = {
                    'fanart': fanart_image,
                    'thumb': thumb_image
                }

                if show_data['relationships'].get('images'):
                    show_art['clearlogo'] = thumb_image if len(
                        show_data['relationships']['images']['data']) == 2 else None

                helper.add_item(title, params, info=info, art=show_art, content='tvshows', menu=menu, folder_name=helper.language(30016), sort_method='unsorted')

    helper.eod()

def list_videos(collection_id, mandatoryParams=None, parameter=None):
    if mandatoryParams and parameter:
        page_data = helper.d.parse_page(collection_id=collection_id, mandatoryParams=mandatoryParams, parameter=parameter)
    elif mandatoryParams is None and parameter:
        page_data = helper.d.parse_page(collection_id=collection_id, parameter=parameter)
    else:
        page_data = helper.d.parse_page(collection_id=collection_id, mandatoryParams=mandatoryParams)

    user_packages = ",".join([str(x) for x in helper.d.get_user_data()['attributes']['packages']])

    collectionItems = page_data['collectionItems']
    images = page_data['images']
    shows = page_data['shows']
    videos = page_data['videos']
    channels = page_data['channels']
    genres = page_data['genres']

    # Don't try to list empty season
    if page_data['data'].get('relationships'):
        # Get order of episodes from page_data['data']
        for collection in page_data['data']['relationships']['items']['data']:
            for collectionItem in collectionItems:
                # Match collectionItem id's from collection listing to all collectionItems in data
                if collection['id'] == collectionItem['id']:
                    for video in videos:
                        # Match collectionItem's video id to all video id's in data
                        if collectionItem['relationships']['video']['data']['id'] == video['id']:
                            attributes = video['attributes']
                            relationships = video['relationships']

                            params = {
                                'action': 'play',
                                'video_id': video['id'],
                                'video_type': 'video'
                            }

                            for s in shows:
                                if s['id'] == relationships['show']['data']['id']:
                                    show_title = s['attributes']['name']

                            g = []
                            if relationships.get('genres'):
                                for genre in genres:
                                    for video_genre in relationships['genres']['data']:
                                        if genre['id'] == video_genre['id']:
                                            g.append(genre['attributes']['name'])

                            if relationships.get('primaryChannel'):
                                for channel in channels:
                                    if channel['id'] == relationships['primaryChannel']['data']['id']:
                                        primaryChannel = channel['attributes']['name']
                            else:
                                primaryChannel = None

                            if relationships.get('images'):
                                for i in images:
                                    if i['id'] == relationships['images']['data'][0]['id']:
                                        fanart_image = i['attributes']['src']
                            else:
                                fanart_image = None

                            duration = attributes['videoDuration'] / 1000.0 if attributes.get('videoDuration') else None

                            # If episode is not yet playable, show playable time in plot
                            if attributes.get('earliestPlayableStart'):
                                if helper.d.parse_datetime(
                                        attributes['earliestPlayableStart']) > helper.d.get_current_time():
                                    playable = str(
                                        helper.d.parse_datetime(attributes['earliestPlayableStart']).strftime(
                                            '%d.%m.%Y %H:%M'))
                                    if attributes.get('description'):
                                        plot = helper.language(30002) + playable + ' ' + attributes.get('description')
                                    else:
                                        plot = helper.language(30002) + playable
                                else:
                                    plot = attributes.get('description')
                            else:
                                plot = attributes.get('description')

                            # Dplay+ content check
                            # Check for Dplay+ content only if user doesn't have subscription
                            if 'Premium' not in user_packages:
                                if len(attributes['packages']) > 1:
                                    # Get all available packages in availabilityWindows
                                    for availabilityWindow in attributes['availabilityWindows']:
                                        if availabilityWindow['package'] == 'Free':
                                            # Check if there is ending time for free availability
                                            if availabilityWindow.get('playableEnd'):
                                                # Check if video is still available for free
                                                if helper.d.parse_datetime(availabilityWindow[
                                                                               'playableStart']) < helper.d.get_current_time() < helper.d.parse_datetime(
                                                    availabilityWindow['playableEnd']):
                                                    plot = plot

                                                else:  # Video is not anymore available for free
                                                    plot = '[Dplay+] ' + plot
                                else: # Only one package in packages = Premium
                                    plot = '[Dplay+] ' + plot

                            episode_info = {
                                'mediatype': 'episode',
                                'title': attributes.get('name').lstrip(),
                                'tvshowtitle': show_title,
                                'season': attributes.get('seasonNumber'),
                                'episode': attributes.get('episodeNumber'),
                                'plot': plot,
                                'genre': g,
                                'studio': primaryChannel,
                                'duration': duration,
                                'aired': attributes.get('airDate')
                            }

                            # Watched status from Dplay
                            if attributes['viewingHistory']['viewed']:
                                if attributes['viewingHistory']['completed']:  # Watched video
                                    episode_info['playcount'] = '1'
                                    resume = 0
                                    total = duration
                                else:  # Partly watched video
                                    episode_info['playcount'] = '0'
                                    resume = attributes['viewingHistory']['position'] / 1000.0
                                    total = duration
                            else:  # Unwatched video
                                episode_info['playcount'] = '0'
                                resume = 0
                                total = 1

                            episode_art = {
                                'fanart': fanart_image,
                                'thumb': fanart_image
                            }

                            # parameter = list season
                            if parameter:
                                folder_name = show_title + ' / ' + helper.language(30011) + ' ' + str(
                                    attributes.get('seasonNumber'))
                            else:
                                folder_name = show_title

                            helper.add_item(attributes.get('name').lstrip(), params=params, info=episode_info, art=episode_art,
                                            content='episodes', playable=True, resume=resume, total=total,
                                            folder_name=folder_name, sort_method='sort_episodes')

    helper.eod()

def search():
    search_query = helper.get_user_input(helper.language(30007))
    if search_query:
        list_search_shows(search_query)
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
        if params['setting'] == 'set_locale':
            helper.set_locale()
    elif 'action' in params:
        if params['action'] == 'list_page':
            list_page(page_path=params['page_path'])
        elif params['action'] == 'list_favorites':
            list_favorites()
        elif params['action'] == 'list_collection_items':
            list_collection_items(page_path=params['page_path'], collection_id=params['collection_id'])
        elif params['action'] == 'list_videos':
            if params.get('mandatoryParams') and params.get('parameter'):
                list_videos(collection_id=params['collection_id'], mandatoryParams=params['mandatoryParams'], parameter=params['parameter'])
            elif params.get('mandatoryParams') is None and params.get('parameter'):
                list_videos(collection_id=params['collection_id'], parameter=params['parameter'])
            else:
                list_videos(collection_id=params['collection_id'], mandatoryParams=params['mandatoryParams'])
        elif params['action'] == 'play':
            # Play a video from a provided URL.
            helper.play_item(params['video_id'], params['video_type'])
        elif params['action'] == 'play_upnext':
            helper.play_upnext(next_video_id=params['next_video_id'])
        elif params['action'] == 'search':
            search()
        elif params['action'] == 'add_favorite':
            helper.d.add_or_delete_favorite(method='post', show_id=params['show_id'])
            helper.refresh_list()
        elif params['action'] == 'delete_favorite':
            helper.d.add_or_delete_favorite(method='delete',show_id=params['show_id'])
            helper.refresh_list()

    else:
        try:
            if helper.check_for_prerequisites():
                list_pages()
        except helper.d.DplayError as error:
            helper.dialog('ok', helper.language(30006), error.value)

if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])
