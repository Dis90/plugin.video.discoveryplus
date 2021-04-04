# -*- coding: utf-8 -*-

import sys

try: # Python 3
    from urllib.parse import parse_qsl
except ImportError: # Python 2
    from urlparse import parse_qsl

from resources.lib.kodihelper import KodiHelper

base_url = sys.argv[0]
handle = int(sys.argv[1])
helper = KodiHelper(base_url, handle)

def list_pages():
    # discoveryplus.com all menu items will come from helper.d.get_menu()
    if helper.d.locale_suffix != 'us' and helper.d.locale_suffix != 'in':
        helper.add_item(helper.language(30001), params={'action': 'list_page', 'page_path': '/home'})
        helper.add_item(helper.language(30017), params={'action': 'list_favorites'})

    # List menu items (Shows, Categories)
    if helper.d.locale_suffix == 'in':
        helper.add_item(helper.language(30017), params={'action': 'list_page', 'page_path': '/liked-videos'})
        helper.add_item('Watchlist', params={'action': 'list_page', 'page_path': '/watch-later'})
        page_data = helper.d.get_menu('/bottom-menu-v3')
    else:
        page_data = helper.d.get_menu('/web-menubar')

    collections = list(filter(lambda x: x['type'] == 'collection', page_data['included']))
    collectionItems = list(filter(lambda x: x['type'] == 'collectionItem', page_data['included']))
    images = list(filter(lambda x: x['type'] == 'image', page_data['included']))
    links = list(filter(lambda x: x['type'] == 'link', page_data['included']))
    routes = list(filter(lambda x: x['type'] == 'route', page_data['included']))

    for data_collection in page_data['data']['relationships']['items']['data']:
        for collectionItem in collectionItems:
            if data_collection['id'] == collectionItem['id']:
                # discoveryplus.com uses links after collectionItems
                # Get only links
                if collectionItem['relationships'].get('link'):
                    for link in links:
                        # Hide unwanted menu links
                        if collectionItem['relationships']['link']['data']['id'] == link['id'] and \
                                link['attributes'][
                                    'kind'] == 'Internal Link' and link['attributes'][
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
                                for image in images:
                                    if image['id'] == link['relationships']['images']['data'][0]['id']:
                                        thumb_image = image['attributes']['src']
                            else:
                                thumb_image = None

                            link_art = {
                                'thumb': thumb_image
                            }
                            # Have to use collection title instead link title because some links doesn't have title
                            helper.add_item(link['attributes']['title'], params, info=link_info,
                                            content='videos',
                                            art=link_art)

                # All other discovery+ sites than US uses collections after collectionItems
                if collectionItem['relationships'].get('collection'):
                    for collection in collections:
                        if collectionItem['relationships']['collection']['data']['id'] == collection['id']:
                            for collectionItem2 in collectionItems:
                                if collection['relationships']['items']['data'][0]['id'] == collectionItem2['id']:
                                    # Get only links
                                    if collectionItem2['relationships'].get('link'):
                                        for link in links:
                                            # Hide unwanted menu links
                                            if collectionItem2['relationships']['link']['data']['id'] == link[
                                                'id'] and \
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
                                                    for image in images:
                                                        if image['id'] == \
                                                                link['relationships']['images']['data'][0][
                                                                    'id']:
                                                            thumb_image = image['attributes']['src']
                                                else:
                                                    thumb_image = None

                                                link_art = {
                                                    'thumb': thumb_image
                                                }
                                                # Have to use collection title instead link title because some links doesn't have title
                                                helper.add_item(collection['attributes']['title'], params,
                                                                info=link_info,
                                                                content='videos',
                                                                art=link_art)

    # Search
    helper.add_item(helper.language(30007), params={'action': 'search'})

    helper.eod()

# discoveryplus.com (US)
def list_page_us(page_path, search_query=None):
    if search_query:
        page_data = helper.d.get_page(page_path, search_query=search_query)
    else:
        page_data = helper.d.get_page(page_path)

    pages = list(filter(lambda x: x['type'] == 'page', page_data['included']))
    pageItems = list(filter(lambda x: x['type'] == 'pageItem', page_data['included']))
    collections = list(filter(lambda x: x['type'] == 'collection', page_data['included']))
    collectionItems = list(filter(lambda x: x['type'] == 'collectionItem', page_data['included']))
    images = list(filter(lambda x: x['type'] == 'image', page_data['included']))
    channels = list(filter(lambda x: x['type'] == 'channel', page_data['included']))
    links = list(filter(lambda x: x['type'] == 'link', page_data['included']))
    routes = list(filter(lambda x: x['type'] == 'route', page_data['included']))
    taxonomyNodes = list(filter(lambda x: x['type'] == 'taxonomyNode', page_data['included']))

    if page_data['data']['type'] == 'route':
        for page in pages:
            # If only one pageItem in page -> relationships -> items -> data, list content page (categories)
            if len(page['relationships']['items']['data']) == 1:
                for pageItem in pageItems:
                    if page['relationships']['items']['data'][0]['id'] == pageItem['id']:
                        for collection in collections:
                            if pageItem['relationships']['collection']['data']['id'] == collection['id']:
                                # Some collections doesn't have component
                                if collection['attributes'].get('component'):

                                    # if content-grid after pageItem -> list content (My List)
                                    if collection['attributes']['component']['id'] == 'content-grid':

                                        list_collection_items(collection_id=collection['id'], page_path=page_path)

                                    # discoveryplus.com (US) search result categories (Shows, Episodes, Specials, Collections, Extras)
                                    if collection['attributes']['component']['id'] == 'tabbed-component':
                                        for c in collection['relationships']['items']['data']:
                                            for collectionItem in collectionItems:
                                                if c['id'] == collectionItem['id']:
                                                    for c2 in collections:
                                                        if collectionItem['relationships']['collection']['data'][
                                                            'id'] == c2['id']:
                                                            if c2['attributes']['component']['id'] == 'content-grid':
                                                                # Hide empty collections
                                                                if c2.get('relationships'):
                                                                    params = {
                                                                        'action': 'list_collection',
                                                                        'collection_id': c2['id'],
                                                                        # 57814496346899699666089560202324254373
                                                                        'mandatoryParams':
                                                                            c2['attributes'][
                                                                                'component'].get(
                                                                                'mandatoryParams')
                                                                        # pf[query]=mythbusters
                                                                    }

                                                                    folder_name = helper.language(30007) + ' / ' + search_query

                                                                    helper.add_item(c2['attributes']['title'],
                                                                                    params,
                                                                                    content='videos',
                                                                                    folder_name=folder_name)

            # More than one pageItem (homepage, browse, channels...)
            else:
                for page_relationship in page['relationships']['items']['data']:
                    # Used in discoveryplus.com Home and Browse
                    if page['attributes'].get('component') and page['attributes']['component']['id'] == 'tabbed-page':
                        for pageItem in pageItems:
                            if page_relationship['id'] == pageItem['id']:
                                if pageItem['relationships'].get('link'):
                                    for link in links:
                                        if pageItem['relationships']['link']['data']['id'] == link['id']:
                                            # For You -link
                                            if link['relationships'].get('linkedContentRoutes'):
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

                                                link_art = {}

                                            # All, Channel pages listing (discovery+ Originals, HGTV...)
                                            else:
                                                params = {
                                                    'action': 'list_collection',
                                                    'collection_id': link['relationships']['linkedContent']['data']['id']
                                                }

                                                if link['relationships'].get('images'):
                                                    for image in images:
                                                        if image['id'] == link['relationships']['images']['data'][0][
                                                            'id']:
                                                            thumb_image = image['attributes']['src']
                                                else:
                                                    thumb_image = None

                                                link_art = {
                                                    'fanart': thumb_image,
                                                    'thumb': thumb_image
                                                }

                                            helper.add_item(link['attributes']['title'], params,
                                                            content='videos', art=link_art,
                                                            folder_name=page['attributes'].get('title'))

                                if pageItem['relationships'].get('collection'):
                                    for collection in collections:
                                        # Genres in US version
                                        if collection['attributes']['component']['id'] == 'taxonomy-container':
                                            for c in collection['relationships']['items']['data']:
                                                for collectionItem in collectionItems:
                                                    if c['id'] == collectionItem['id']:
                                                        if collectionItem['relationships'].get('taxonomyNode'):

                                                            for taxonomyNode in taxonomyNodes:
                                                                if taxonomyNode['id'] == collectionItem['relationships']['taxonomyNode']['data']['id']:
                                                                    # Find page path from routes
                                                                    for route in routes:
                                                                        if route['id'] == \
                                                                                taxonomyNode['relationships'][
                                                                                    'routes'][
                                                                                    'data'][0]['id']:
                                                                            next_page_path = route['attributes']['url']


                                                                    params = {
                                                                        'action': 'list_page',
                                                                        'page_path': next_page_path
                                                                    }

                                                                    helper.add_item(taxonomyNode['attributes']['name'], params,
                                                                            content='videos',
                                                                            folder_name=page['attributes'].get('pageMetadataTitle'))

                    # Some pages doesn't have component
                    # So we use this method to all non tabbed-page
                    else:
                        for pageItem in pageItems:
                            if page_relationship['id'] == pageItem['id']:
                                for collection in collections:
                                    # Some collections doesn't have component
                                    if collection['attributes'].get('component'):

                                        # PageItems have only one collection
                                        if pageItem['relationships']['collection']['data']['id'] == collection['id']:


                                            # Hide channel live streams because those aren't actually available
                                            # Uncomment this when available
                                            # Channel live streams in discoveryplus.com (US)
                                            # if collection['attributes']['component']['id'] == 'hero':
                                            #     if collection.get('relationships'):
                                            #         for c in collection['relationships']['items']['data']:
                                            #             for collectionItem in collectionItems:
                                            #                 if c['id'] == collectionItem['id']:
                                            #                     if collectionItem['relationships'].get('channel'):
                                            #                         for channel in channels:
                                            #                             if collectionItem['relationships']['channel'][
                                            #                                 'data']['id'] == channel['id']:
                                            #
                                            #                                 if channel['attributes'].get(
                                            #                                         'hasLiveStream'):
                                            #                                     params = {
                                            #                                         'action': 'play',
                                            #                                         'video_id': channel['id'],
                                            #                                         'video_type': 'channel'
                                            #                                     }
                                            #
                                            #                                     channel_info = {
                                            #                                         'mediatype': 'video',
                                            #                                         'title': helper.language(
                                            #                                             30014) + ' ' + channel[
                                            #                                                      'attributes'].get(
                                            #                                             'name'),
                                            #                                         'plot': channel['attributes'].get(
                                            #                                             'description'),
                                            #                                         'playcount': '0'
                                            #                                     }
                                            #
                                            #                                     channel_logo = None
                                            #                                     fanart_image = None
                                            #                                     if channel['relationships'].get(
                                            #                                             'images'):
                                            #                                         for image in images:
                                            #                                             for channel_images in \
                                            #                                             channel['relationships'][
                                            #                                                 'images']['data']:
                                            #                                                 if image['id'] == \
                                            #                                                         channel_images[
                                            #                                                             'id']:
                                            #                                                     if image['attributes'][
                                            #                                                         'kind'] == 'logo':
                                            #                                                         channel_logo = \
                                            #                                                         image['attributes'][
                                            #                                                             'src']
                                            #                                                     if image['attributes'][
                                            #                                                         'kind'] == 'default':
                                            #                                                         fanart_image = \
                                            #                                                         image['attributes'][
                                            #                                                             'src']
                                            #
                                            #                                     if channel_logo:
                                            #                                         thumb_image = channel_logo
                                            #                                     else:
                                            #                                         thumb_image = fanart_image
                                            #
                                            #                                     channel_art = {
                                            #                                         'fanart': fanart_image,
                                            #                                         'thumb': thumb_image
                                            #                                     }
                                            #
                                            #                                     helper.add_item(
                                            #                                         helper.language(30014) + ' ' +
                                            #                                         channel['attributes'].get('name'),
                                            #                                         params=params,
                                            #                                         info=channel_info, content='videos',
                                            #                                         art=channel_art,
                                            #                                         playable=True,
                                            #                                         folder_name=collection[
                                            #                                             'attributes'].get('title'))


                                            # Home -> For You -> categories
                                            if collection['attributes']['component']['id'] == 'content-grid':
                                                # Hide empty grids
                                                if collection.get('relationships'):
                                                    if collection['attributes'].get('title') or collection['attributes']['alias'] == 'networks':
                                                        params = {
                                                            'action': 'list_collection_items',
                                                            'page_path': page_path,
                                                            'collection_id': collection['id']
                                                        }

                                                        if collection['attributes'].get('title'):
                                                            title = collection['attributes']['title']
                                                        else:
                                                            title = collection['attributes']['name']

                                                        helper.add_item(title, params,
                                                                    content='videos',
                                                                    folder_name=page['attributes'].get(
                                                                        'pageMetadataTitle'))

                                            # Episodes, Extras, About the Show, You May Also Like
                                            if collection['attributes']['component']['id'] == 'tabbed-component':
                                                for c in collection['relationships']['items']['data']:
                                                    for collectionItem in collectionItems:
                                                        if c['id'] == collectionItem['id']:
                                                            for c2 in collections:
                                                                if collectionItem['relationships']['collection']['data']['id'] == c2['id']:
                                                                    # Episodes and Extras
                                                                    if c2['attributes']['component']['id'] == 'tabbed-content':
                                                                        # Hide empty Episodes and Extras folders
                                                                        if c2.get('relationships'):
                                                                            # Check if component is season list and check if there's season listing
                                                                            if c2['attributes']['component'].get(
                                                                                    'filters') and \
                                                                                    c2['attributes']['component'][
                                                                                        'filters'][0].get('options'):

                                                                                params = {
                                                                                    'action': 'list_collection_items',
                                                                                    'page_path': page_path,
                                                                                    'collection_id': c2['id']
                                                                                }

                                                                            # Extras and Episodes list when there's no season listing (movies)
                                                                            else:
                                                                                params = {
                                                                                    'action': 'list_collection',
                                                                                    'collection_id': c2['id'],
                                                                                    # 66290614510668341673562607828298581172
                                                                                    'mandatoryParams':
                                                                                        c2['attributes'][
                                                                                            'component'].get(
                                                                                            'mandatoryParams')
                                                                                    # pf[show.id]=12423
                                                                                }

                                                                            helper.add_item(c2['attributes']['title'],
                                                                                            params,
                                                                                            content='videos',
                                                                                            folder_name=page[
                                                                                                'attributes'].get(
                                                                                                'pageMetadataTitle'))

                                                                    # You May Also Like
                                                                    # Channel category and Extras on shows that doesn't have episodes
                                                                    if c2['attributes']['component']['id'] == 'content-grid':
                                                                        params = {
                                                                            'action': 'list_collection_items',
                                                                            'page_path': page_path,
                                                                            'collection_id': c2['id']
                                                                        }

                                                                        helper.add_item(c2['attributes']['title'],
                                                                                        params,
                                                                                        content='videos',
                                                                                        folder_name=page[
                                                                                            'attributes'].get(
                                                                                            'pageMetadataTitle'))

                                            # discoveryplus.com (US) -> search -> collections -> list content of collection
                                            if collection['attributes']['component']['id'] == 'playlist':
                                                list_collection(collection_id=collection['id'], page=1)

                                            # discoveryplus.com (US) -> Introducing discovery+ Channels -> channel page live stream
                                            if collection['attributes']['component']['id'] == 'player':
                                                if collection.get('relationships'):
                                                    for c in collection['relationships']['items']['data']:
                                                        for collectionItem in collectionItems:
                                                            if c['id'] == collectionItem['id']:
                                                                if collectionItem['relationships'].get('channel'):
                                                                    for channel in channels:
                                                                        if collectionItem['relationships']['channel'][
                                                                            'data']['id'] == channel['id']:

                                                                            if channel['attributes'].get(
                                                                                    'hasLiveStream'):
                                                                                params = {
                                                                                    'action': 'play',
                                                                                    'video_id': channel['id'],
                                                                                    'video_type': 'channel'
                                                                                }

                                                                                channel_info = {
                                                                                    'mediatype': 'video',
                                                                                    'title': helper.language(
                                                                                        30014) + ' ' + channel[
                                                                                                 'attributes'].get(
                                                                                        'name'),
                                                                                    'plot': channel['attributes'].get(
                                                                                        'description'),
                                                                                    'playcount': '0'
                                                                                }

                                                                                channel_logo = None
                                                                                fanart_image = None
                                                                                if channel['relationships'].get(
                                                                                        'images'):
                                                                                    for image in images:
                                                                                        for channel_images in \
                                                                                        channel['relationships'][
                                                                                            'images']['data']:
                                                                                            if image['id'] == \
                                                                                                    channel_images[
                                                                                                        'id']:
                                                                                                if image['attributes'][
                                                                                                    'kind'] == 'logo':
                                                                                                    channel_logo = \
                                                                                                    image['attributes'][
                                                                                                        'src']
                                                                                                if image['attributes'][
                                                                                                    'kind'] == 'default':
                                                                                                    fanart_image = \
                                                                                                    image['attributes'][
                                                                                                        'src']

                                                                                if channel_logo:
                                                                                    thumb_image = channel_logo
                                                                                else:
                                                                                    thumb_image = fanart_image

                                                                                channel_art = {
                                                                                    'fanart': fanart_image,
                                                                                    'thumb': thumb_image
                                                                                }

                                                                                helper.add_item(
                                                                                    helper.language(30014) + ' ' +
                                                                                    channel['attributes'].get('name'),
                                                                                    params=params,
                                                                                    info=channel_info, content='videos',
                                                                                    art=channel_art,
                                                                                    playable=True,
                                                                                    folder_name=collection[
                                                                                        'attributes'].get('title'))

    helper.eod()

# discoveryplus.in
def list_page_in(page_path):
    page_data = helper.d.get_page(page_path)

    pages = list(filter(lambda x: x['type'] == 'page', page_data['included']))
    pageItems = list(filter(lambda x: x['type'] == 'pageItem', page_data['included']))
    collections = list(filter(lambda x: x['type'] == 'collection', page_data['included']))
    collectionItems = list(filter(lambda x: x['type'] == 'collectionItem', page_data['included']))
    images = list(filter(lambda x: x['type'] == 'image', page_data['included']))
    channels = list(filter(lambda x: x['type'] == 'channel', page_data['included']))
    links = list(filter(lambda x: x['type'] == 'link', page_data['included']))
    routes = list(filter(lambda x: x['type'] == 'route', page_data['included']))
    taxonomyNodes = list(filter(lambda x: x['type'] == 'taxonomyNode', page_data['included']))

    if page_data['data']['type'] == 'route':
        if page_path == '/home':

            home_collections = helper.d.get_config_in()['data']['attributes']['config']['pageCollections']['home']
            for home_collection in home_collections:
                try:
                    collection = helper.d.get_collections(collection_id=home_collection)['data']
                except:
                    continue
                if collection['attributes']['component']['id'] == 'carousel':
                    params = {
                        'action': 'list_collection',
                        'collection_id': collection['id']
                    }

                    if collection['attributes'].get('title'):
                        title = collection['attributes']['title']
                    else:
                        title = collection['attributes']['name']

                    helper.add_item(title, params,
                                    content='videos')

        for page in pages:
            # If only one pageItem in page -> relationships -> items -> data, list content page
            if len(page['relationships']['items']['data']) == 1:
                for pageItem in pageItems:
                    if page['relationships']['items']['data'][0]['id'] == pageItem['id']:
                        for collection in collections:
                            if pageItem['relationships']['collection']['data']['id'] == collection['id']:
                                # Some collections doesn't have component
                                if collection['attributes'].get('component'):

                                    # if content-grid after pageItem -> list content
                                    if collection['attributes']['component']['id'] == 'content-grid':

                                        list_collection_items(collection_id=collection['id'], page_path=page_path)

                                    if collection['attributes']['component']['id'] == 'mindblown-composite' or collection['attributes']['component']['id'] == 'tab-bar':
                                        for collection_relationship in collection['relationships']['items']['data']:
                                            for collectionItem in collectionItems:
                                                if collection_relationship['id'] == collectionItem['id']:
                                                    for c2 in collections:
                                                        if c2['id'] == collectionItem['relationships']['collection']['data']['id']:

                                                            if c2['attributes']['component']['id']  == 'mindblown-videos-list':
                                                                list_collection_items(collection_id=c2['id'], page_path=page_path)

                                                            # Favorites (Episodes, Shorts, Shows) and Watchlist (Episodes, Shorts)
                                                            if c2['attributes']['component']['id']  == 'tab-bar-item':
                                                                if c2['attributes']['component'].get('customAttributes'):
                                                                    contentType = c2['attributes']['component']['customAttributes']['contentType']
                                                                    if contentType == 'watchlistVideos':
                                                                        params = {
                                                                            'action': 'list_favorite_watchlist_videos',
                                                                            'playlist': 'dplus-watchlist-videos'
                                                                        }
                                                                    elif contentType == 'watchlistShorts':
                                                                        params = {
                                                                            'action': 'list_favorite_watchlist_videos',
                                                                            'playlist': 'dplus-watchlist-shorts'
                                                                        }
                                                                    elif contentType == 'favoriteEpisodes':
                                                                        params = {
                                                                            'action': 'list_favorite_watchlist_videos',
                                                                            'videoType': 'EPISODE'
                                                                        }
                                                                    elif contentType == 'favoriteShorts':
                                                                        params = {
                                                                            'action': 'list_favorite_watchlist_videos',
                                                                            'videoType': 'CLIP'
                                                                        }
                                                                    elif contentType == 'favoriteShows':
                                                                        params = {
                                                                            'action': 'list_favorites'
                                                                        }
                                                                    else:
                                                                        params = {}

                                                                if c2['attributes'].get('title'):
                                                                    title = c2['attributes']['title']
                                                                else:
                                                                    title = c2['attributes']['name']

                                                                helper.add_item(title, params,
                                                                                content='videos',
                                                                                folder_name=collection[
                                                                                    'attributes'].get('title'))

            # More than one pageItem (explore, mindblown...)
            else:
                for page_relationship in page['relationships']['items']['data']:
                    for pageItem in pageItems:
                        if page_relationship['id'] == pageItem['id']:
                            for collection in collections:
                                # Some collections doesn't have component
                                if collection['attributes'].get('component'):

                                    # PageItems have only one collection
                                    if pageItem['relationships']['collection']['data']['id'] == collection['id']:

                                        if collection['attributes']['component']['id'] == 'promoted-shorts-list':
                                            if collection.get('relationships'):
                                                if collection['attributes'].get('title'):
                                                    params = {
                                                        'action': 'list_collection_items',
                                                        'page_path': page_path,
                                                        'collection_id': collection['id']
                                                    }

                                                    if collection['attributes'].get('title'):
                                                        title = collection['attributes']['title']
                                                    else:
                                                        title = collection['attributes']['name']

                                                    helper.add_item(title, params,
                                                                    content='videos',
                                                                    folder_name=page['attributes'].get(
                                                                        'pageMetadataTitle'))

                                        if collection['attributes']['component']['id'] == 'mindblown-listing':
                                            for c in collection['relationships']['items']['data']:
                                                for collectionItem in collectionItems:
                                                    if c['id'] == collectionItem['id']:
                                                        for c2 in collections:
                                                            if c2['id'] == \
                                                                    collectionItem['relationships']['collection'][
                                                                        'data']['id']:
                                                                for collectionItem2 in collectionItems:
                                                                    if collectionItem2['id'] == \
                                                                            c2['relationships']['items']['data'][0][
                                                                                'id']:

                                                                        thumb_image = None
                                                                        for link in links:
                                                                            if link['id'] == \
                                                                                    collectionItem2['relationships'][
                                                                                        'link']['data']['id']:

                                                                                # Find page path from routes
                                                                                for route in routes:
                                                                                    if route['id'] == \
                                                                                            link['relationships'][
                                                                                                'linkedContentRoutes'][
                                                                                                'data'][0]['id']:
                                                                                        next_page_path = \
                                                                                        route['attributes']['url']

                                                                                if link['relationships'].get('images'):
                                                                                    for image in images:
                                                                                        if image['id'] == \
                                                                                                link['relationships'][
                                                                                                    'images'][
                                                                                                    'data'][0][
                                                                                                    'id']:
                                                                                            thumb_image = \
                                                                                                image['attributes'][
                                                                                                    'src']

                                                                        params = {
                                                                            'action': 'list_page',
                                                                            'page_path': next_page_path
                                                                        }

                                                                        info = {
                                                                            'title': c2['attributes'].get(
                                                                                'title'),
                                                                            'plot': c2['attributes'].get(
                                                                                'description')
                                                                        }


                                                                        category_art = {
                                                                            'fanart': thumb_image,
                                                                            'thumb': thumb_image
                                                                        }

                                                                        helper.add_item(c2['attributes']['title'],
                                                                                        params,
                                                                                        info=info,
                                                                                        content='videos',
                                                                                        art=category_art,
                                                                                        folder_name=page[
                                                                                            'attributes'].get(
                                                                                            'pageMetadataTitle'))

                                        # Shows page in discoveryplus.in (Episodes, Shorts)
                                        if collection['attributes']['component']['id'] == 'show-container':
                                            list_collection_items(collection_id=collection['id'], page_path=page_path)

                                        # Channels page category links and 'Explore Shows and Full Episodes' -> BBC
                                        if collection['attributes']['component']['id'] == 'content-grid':
                                            # Hide empty grids (example upcoming events when there is no upcoming events).
                                            if collection.get('relationships'):
                                                if collection['attributes'].get('title'):
                                                    params = {
                                                        'action': 'list_collection_items',
                                                        'page_path': page_path,
                                                        'collection_id': collection['id']
                                                    }

                                                    if collection['attributes'].get('title'):
                                                        title = collection['attributes']['title']
                                                    else:
                                                        title = collection['attributes']['name']

                                                    helper.add_item(title, params,
                                                                    content='videos',
                                                                    folder_name=page['attributes'].get(
                                                                        'pageMetadataTitle'))
                                                # Explore Shows and Full Episodes -> BBC
                                                else:
                                                    list_collection_items(collection_id=collection['id'],
                                                                          page_path=page_path)

                                        # Channel livestream
                                        if collection['attributes']['component']['id'] == 'channel-hero-player':
                                            for collectionItem in collectionItems:
                                                if collection['relationships']['items']['data'][0]['id'] == collectionItem['id']:
                                                    if collectionItem['relationships'].get('channel'):

                                                        # Channel livestream
                                                        for channel in channels:
                                                            if \
                                                                    collectionItem['relationships']['channel'][
                                                                        'data'][
                                                                        'id'] == channel['id']:
                                                                params = {
                                                                    'action': 'play',
                                                                    'video_id': channel['id'],
                                                                    'video_type': 'channel'
                                                                }

                                                                channel_info = {
                                                                    'mediatype': 'video',
                                                                    'title': helper.language(30014) + ' ' +
                                                                             channel[
                                                                                 'attributes'].get('name'),
                                                                    'plot': channel['attributes'].get(
                                                                        'description'),
                                                                    'playcount': '0'
                                                                }

                                                                channel_logo = None
                                                                fanart_image = None
                                                                if channel['relationships'].get('images'):
                                                                    for image in images:
                                                                        for channel_images in \
                                                                                channel['relationships']['images'][
                                                                                    'data']:
                                                                            if image['id'] == channel_images[
                                                                                'id']:
                                                                                if image['attributes'][
                                                                                    'kind'] == 'logo':
                                                                                    channel_logo = \
                                                                                        image['attributes']['src']
                                                                                if image['attributes'][
                                                                                    'kind'] == 'default':
                                                                                    fanart_image = \
                                                                                        image['attributes']['src']

                                                                if channel_logo:
                                                                    thumb_image = channel_logo
                                                                else:
                                                                    thumb_image = fanart_image

                                                                channel_art = {
                                                                    'fanart': fanart_image,
                                                                    'thumb': thumb_image
                                                                }

                                                                helper.add_item(
                                                                    helper.language(30014) + ' ' + channel[
                                                                        'attributes'].get('name'),
                                                                    params=params,
                                                                    art=channel_art, info=channel_info,
                                                                    content='videos',
                                                                    playable=True)

                                        # Used in Premium page, Home (Category and OMG Moments!) and Shorts genres content
                                        if collection['attributes']['component']['id'] == 'carousel':
                                            params = {
                                                'action': 'list_collection',
                                                'collection_id': collection['id']
                                            }

                                            if collection['attributes'].get('title'):
                                                title = collection['attributes']['title']
                                            else:
                                                title = collection['attributes']['name']

                                            helper.add_item(title, params,
                                                            content='videos',
                                                            folder_name=page['attributes'].get('pageMetadataTitle'))

                                        # Shorts page categories
                                        if collection['attributes']['component']['id'] == 'all-taxonomies':
                                            for collectionItem in collectionItems:
                                                for collection_relationship in collection['relationships']['items']['data']:
                                                    if collectionItem['id'] == collection_relationship['id']:
                                                        if collectionItem['relationships'].get('collection'):
                                                            for c2 in collections:
                                                                if c2['id'] == collectionItem['relationships']['collection']['data']['id']:
                                                                    if c2.get('relationships'):
                                                                        for c2_relationship in \
                                                                        c2['relationships']['items']['data']:
                                                                            for collectionItem2 in collectionItems:
                                                                                if collectionItem2['id'] == \
                                                                                        c2_relationship['id']:
                                                                                    if collectionItem2[
                                                                                        'relationships'].get(
                                                                                            'taxonomyNode'):

                                                                                        for taxonomyNode in taxonomyNodes:
                                                                                            if taxonomyNode['id'] == \
                                                                                                    collectionItem2[
                                                                                                        'relationships'][
                                                                                                        'taxonomyNode'][
                                                                                                        'data']['id']:

                                                                                                # Find page path from routes
                                                                                                for route in routes:
                                                                                                    if route['id'] == \
                                                                                                            taxonomyNode[
                                                                                                                'relationships'][
                                                                                                                'routes'][
                                                                                                                'data'][
                                                                                                                0][
                                                                                                                'id']:
                                                                                                        next_page_path = \
                                                                                                        route[
                                                                                                            'attributes'][
                                                                                                            'url']

                                                                                                params = {
                                                                                                    'action': 'list_page',
                                                                                                    'page_path': next_page_path
                                                                                                }

                                                                                                helper.add_item(
                                                                                                    taxonomyNode[
                                                                                                        'attributes'][
                                                                                                        'name'], params,
                                                                                                    content='videos')

    helper.eod()

# European countries
def list_page(page_path):
    page_data = helper.d.get_page(page_path)

    pages = list(filter(lambda x: x['type'] == 'page', page_data['included']))
    pageItems = list(filter(lambda x: x['type'] == 'pageItem', page_data['included']))
    collections = list(filter(lambda x: x['type'] == 'collection', page_data['included']))
    collectionItems = list(filter(lambda x: x['type'] == 'collectionItem', page_data['included']))
    images = list(filter(lambda x: x['type'] == 'image', page_data['included']))
    shows = list(filter(lambda x: x['type'] == 'show', page_data['included']))
    channels = list(filter(lambda x: x['type'] == 'channel', page_data['included']))
    genres = list(filter(lambda x: x['type'] == 'genre', page_data['included']))
    links = list(filter(lambda x: x['type'] == 'link', page_data['included']))
    routes = list(filter(lambda x: x['type'] == 'route', page_data['included']))

    if page_data['data']['type'] == 'route':
        for page in pages:
            # If only one pageItem in page -> relationships -> items -> data, list content page (categories)
            if len(page['relationships']['items']['data']) == 1:
                for pageItem in pageItems:
                    if page['relationships']['items']['data'][0]['id'] == pageItem['id']:
                        for collection in collections:
                            if pageItem['relationships']['collection']['data']['id'] == collection['id']:
                                # Some collections doesn't have component
                                if collection['attributes'].get('component'):

                                    # if content-grid after pageItem -> list content
                                    if collection['attributes']['component']['id'] == 'content-grid':

                                        list_collection_items(collection_id=collection['id'], page_path=page_path)

                                    # Channel pages with only one pageItem
                                    # Content-hero (used in channels page where watch button is visible)
                                    # collection['relationships']['items']['data'][0] = channel name and livestream
                                    # collection['relationships']['items']['data'][1] = channel category items
                                    if collection['attributes']['component']['id'] == 'content-hero':
                                        for c in collection['relationships']['items']['data']:
                                            for collectionItem in collectionItems:
                                                if c['id'] == collectionItem['id']:
                                                    if collectionItem['relationships'].get('channel'):

                                                        # Channel livestream
                                                        for channel in channels:
                                                            if \
                                                                    collectionItem['relationships']['channel'][
                                                                        'data'][
                                                                        'id'] == channel['id']:
                                                                params = {
                                                                    'action': 'play',
                                                                    'video_id': channel['id'],
                                                                    'video_type': 'channel'
                                                                }

                                                                channel_info = {
                                                                    'mediatype': 'video',
                                                                    'title': helper.language(30014) + ' ' +
                                                                             channel[
                                                                                 'attributes'].get('name'),
                                                                    'plot': channel['attributes'].get(
                                                                        'description'),
                                                                    'playcount': '0'
                                                                }

                                                                channel_logo = None
                                                                fanart_image = None
                                                                if channel['relationships'].get('images'):
                                                                    for image in images:
                                                                        for channel_images in \
                                                                                channel['relationships']['images'][
                                                                                    'data']:
                                                                            if image['id'] == channel_images[
                                                                                'id']:
                                                                                if image['attributes'][
                                                                                    'kind'] == 'logo':
                                                                                    channel_logo = \
                                                                                        image['attributes']['src']
                                                                                if image['attributes'][
                                                                                    'kind'] == 'default':
                                                                                    fanart_image = \
                                                                                        image['attributes']['src']

                                                                if channel_logo:
                                                                    thumb_image = channel_logo
                                                                else:
                                                                    thumb_image = fanart_image

                                                                channel_art = {
                                                                    'fanart': fanart_image,
                                                                    'thumb': thumb_image
                                                                }

                                                                helper.add_item(
                                                                    helper.language(30014) + ' ' + channel[
                                                                        'attributes'].get('name'),
                                                                    params=params,
                                                                    art=channel_art, info=channel_info,
                                                                    content='videos',
                                                                    playable=True)

                                                                # List channel category
                                                                if len(collection['relationships']['items'][
                                                                           'data']) > 1:
                                                                    for collectionItem2 in collectionItems:
                                                                        # 1 = Channel category items
                                                                        if \
                                                                                collection['relationships'][
                                                                                    'items']['data'][1][
                                                                                    'id'] == collectionItem2[
                                                                                    'id']:
                                                                            collection_id = \
                                                                                collectionItem2[
                                                                                    'relationships'][
                                                                                    'collection']['data']['id']

                                                                    channel_info = {
                                                                        'title': channel['attributes'].get(
                                                                            'name'),
                                                                        'plot': channel['attributes'].get(
                                                                            'description')
                                                                    }

                                                                    params = {
                                                                        'action': 'list_collection_items',
                                                                        'page_path': page_path,
                                                                        'collection_id': collection_id
                                                                    }

                                                                    helper.add_item(
                                                                        channel['attributes'].get('name'),
                                                                        params=params, art=channel_art,
                                                                        info=channel_info, content='videos')

                                    # Categories -> Food -> (Popular, All) category listing
                                    if collection['attributes']['component']['id'] == 'generic-hero':
                                        for c in collection['relationships']['items']['data']:
                                            for collectionItem in collectionItems:
                                                if c['id'] == collectionItem['id']:
                                                    for c2 in collections:
                                                        # Don't list promoted show
                                                        if collectionItem['relationships'].get('collection'):
                                                            if collectionItem['relationships']['collection']['data'][
                                                                'id'] == c2['id']:
                                                                if c2['attributes']['component']['id'] == 'content-grid':
                                                                    if c2['attributes'].get('title'):
                                                                        params = {
                                                                            'action': 'list_collection_items',
                                                                            'page_path': page_path,
                                                                            'collection_id': c2['id']
                                                                        }

                                                                        helper.add_item(c2['attributes']['title'],
                                                                                        params,
                                                                                        content='videos',
                                                                                        folder_name=page[
                                                                                            'attributes'].get(
                                                                                            'pageMetadataTitle'))

                                                                    # Collection doesn't have title = list content
                                                                    else:
                                                                        list_collection_items(collection_id=c2['id'], page_path=page_path)

            # More than one pageItem (homepage, seasons, channels)
            else:
                for page_relationship in page['relationships']['items']['data']:
                    for pageItem in pageItems:
                        if page_relationship['id'] == pageItem['id']:
                            for collection in collections:
                                # Some collections doesn't have component
                                if collection['attributes'].get('component'):

                                    # PageItems have only one collection
                                    if pageItem['relationships']['collection']['data']['id'] == collection['id']:

                                        # Content-hero (used in channels page where watch button is visible)
                                        # collection['relationships']['items']['data'][0] = channel name and livestream
                                        # collection['relationships']['items']['data'][1] = channel category items
                                        if collection['attributes']['component']['id'] == 'content-hero':
                                            for c in collection['relationships']['items']['data']:
                                                for collectionItem in collectionItems:
                                                    if c['id'] == collectionItem['id']:
                                                        if collectionItem['relationships'].get('channel'):

                                                            # Channel livestream
                                                            for channel in channels:
                                                                if \
                                                                        collectionItem['relationships']['channel'][
                                                                            'data'][
                                                                            'id'] == channel['id']:
                                                                    params = {
                                                                        'action': 'play',
                                                                        'video_id': channel['id'],
                                                                        'video_type': 'channel'
                                                                    }

                                                                    channel_info = {
                                                                        'mediatype': 'video',
                                                                        'title': helper.language(30014) + ' ' +
                                                                                 channel[
                                                                                     'attributes'].get('name'),
                                                                        'plot': channel['attributes'].get(
                                                                            'description'),
                                                                        'playcount': '0'
                                                                    }

                                                                    channel_logo = None
                                                                    fanart_image = None
                                                                    if channel['relationships'].get('images'):
                                                                        for image in images:
                                                                            for channel_images in \
                                                                                    channel['relationships']['images'][
                                                                                        'data']:
                                                                                if image['id'] == channel_images[
                                                                                    'id']:
                                                                                    if image['attributes'][
                                                                                        'kind'] == 'logo':
                                                                                        channel_logo = \
                                                                                            image['attributes']['src']
                                                                                    if image['attributes'][
                                                                                        'kind'] == 'default':
                                                                                        fanart_image = \
                                                                                            image['attributes']['src']

                                                                    if channel_logo:
                                                                        thumb_image = channel_logo
                                                                    else:
                                                                        thumb_image = fanart_image

                                                                    channel_art = {
                                                                        'fanart': fanart_image,
                                                                        'thumb': thumb_image
                                                                    }

                                                                    helper.add_item(
                                                                        helper.language(30014) + ' ' + channel[
                                                                            'attributes'].get('name'),
                                                                        params=params,
                                                                        art=channel_art, info=channel_info,
                                                                        content='videos',
                                                                        playable=True)

                                                                    # List channel category
                                                                    if len(collection['relationships']['items'][
                                                                               'data']) > 1:
                                                                        for collectionItem2 in collectionItems:
                                                                            # 1 = Channel category items
                                                                            if \
                                                                                    collection['relationships'][
                                                                                        'items']['data'][1][
                                                                                        'id'] == collectionItem2[
                                                                                        'id']:
                                                                                collection_id = \
                                                                                    collectionItem2[
                                                                                        'relationships'][
                                                                                        'collection']['data']['id']

                                                                        channel_info = {
                                                                            'title': channel['attributes'].get(
                                                                                'name'),
                                                                            'plot': channel['attributes'].get(
                                                                                'description')
                                                                        }

                                                                        params = {
                                                                            'action': 'list_collection_items',
                                                                            'page_path': page_path,
                                                                            'collection_id': collection_id
                                                                        }

                                                                        helper.add_item(
                                                                            channel['attributes'].get('name'),
                                                                            params=params, art=channel_art,
                                                                            info=channel_info, content='videos')

                                        # Homepage, Channel -> subcategories (New videos, Shows).
                                        if collection['attributes']['component']['id'] == 'content-grid' or \
                                                collection['attributes']['component']['id'] == 'content-rail':
                                            # Hide empty grids (example upcoming events when there is no upcoming events).
                                            if collection.get('relationships'):
                                                if collection['attributes'].get('title'):
                                                    params = {
                                                        'action': 'list_collection_items',
                                                        'page_path': page_path,
                                                        'collection_id': collection['id']
                                                    }

                                                    if collection['attributes'].get('title'):
                                                        title = collection['attributes']['title']
                                                    else:
                                                        title = collection['attributes']['name']

                                                    helper.add_item(title, params,
                                                                    content='videos',
                                                                    folder_name=page['attributes'].get(
                                                                        'pageMetadataTitle'))

                                                # Collection doesn't have title = categories
                                                else:
                                                    # List categories (Reality, Comedy etc)
                                                    for c in collection['relationships']['items']['data']:
                                                        for collectionItem in collectionItems:
                                                            if c['id'] == collectionItem['id']:
                                                                if collectionItem['relationships'].get('link'):
                                                                    for link in links:
                                                                        if collectionItem['relationships']['link'][
                                                                            'data'][
                                                                            'id'] == link['id']:
                                                                            # Find page path from routes
                                                                            for route in routes:
                                                                                if route['id'] == \
                                                                                        link['relationships'][
                                                                                            'linkedContentRoutes'][
                                                                                            'data'][0]['id']:
                                                                                    next_page_path = \
                                                                                        route['attributes']['url']

                                                                            params = {
                                                                                'action': 'list_page',
                                                                                'page_path': next_page_path
                                                                            }

                                                                            if link['relationships'].get('images'):
                                                                                for image in images:
                                                                                    if image['id'] == \
                                                                                            link['relationships'][
                                                                                                'images'][
                                                                                                'data'][0][
                                                                                                'id']:
                                                                                        thumb_image = \
                                                                                            image['attributes']['src']
                                                                            else:
                                                                                thumb_image = None

                                                                            category_art = {
                                                                                'fanart': thumb_image,
                                                                                'thumb': thumb_image
                                                                            }

                                                                            # Category titles have stored in different places
                                                                            if collectionItem['attributes'].get(
                                                                                    'title'):
                                                                                link_title = \
                                                                                    collectionItem['attributes'][
                                                                                        'title']
                                                                            elif link['attributes'].get('title'):
                                                                                link_title = link['attributes'][
                                                                                    'title']
                                                                            elif link['attributes'].get('name'):
                                                                                link_title = link['attributes'][
                                                                                    'name']
                                                                            else:
                                                                                link_title = None

                                                                            helper.add_item(link_title, params,
                                                                                            content='videos',
                                                                                            art=category_art,
                                                                                            folder_name=collection[
                                                                                                'attributes'].get(
                                                                                                'title'))

                                        # List series season grid
                                        if collection['attributes']['component']['id'] == 'tabbed-content':
                                            # Check if there's any seasons of show or sport event
                                            if collection['attributes']['component'].get('filters'):
                                                for option in collection['attributes']['component']['filters'][0][
                                                    'options']:
                                                    title = helper.language(30011) + ' ' + str(option['id'])
                                                    params = {
                                                        'action': 'list_collection',
                                                        'collection_id': collection['id'],
                                                        # 66290614510668341673562607828298581172
                                                        'mandatoryParams': collection['attributes'][
                                                            'component'].get(
                                                            'mandatoryParams'),  # pf[show.id]=12423
                                                        'parameter': option['parameter']  # pf[seasonNumber]=1
                                                    }

                                                    info = {
                                                        'mediatype': 'season'
                                                    }

                                                    # Show metadata
                                                    show = shows[0]

                                                    info['tvshowtitle'] = show['attributes'].get('name')
                                                    info['plot'] = show['attributes'].get('description')
                                                    info['season'] = len(show['attributes']['seasonNumbers'])
                                                    info['episode'] = show['attributes']['episodeCount']

                                                    g = []
                                                    if show['relationships'].get('genres'):
                                                        for genre in genres:
                                                            for show_genre in show['relationships']['genres'][
                                                                'data']:
                                                                if genre['id'] == show_genre['id']:
                                                                    g.append(genre['attributes']['name'])

                                                    if show['relationships'].get('primaryChannel'):
                                                        for channel in channels:
                                                            if channel['id'] == \
                                                                    show['relationships']['primaryChannel']['data'][
                                                                        'id']:
                                                                primaryChannel = channel['attributes']['name']
                                                    else:
                                                        primaryChannel = None

                                                    info['genre'] = g
                                                    info['studio'] = primaryChannel

                                                    fanart_image = None
                                                    thumb_image = None
                                                    logo_image = None
                                                    poster_image = None
                                                    if show['relationships'].get('images'):
                                                        for image in images:
                                                            for show_images in show['relationships']['images']['data']:
                                                                if image['id'] == show_images['id']:
                                                                    if image['attributes']['kind'] == 'default':
                                                                        fanart_image = image['attributes']['src']
                                                                        thumb_image = image['attributes']['src']
                                                                    if image['attributes']['kind'] == 'logo':
                                                                        logo_image = image['attributes']['src']
                                                                    if image['attributes'][
                                                                        'kind'] == 'poster_with_logo':
                                                                        poster_image = image['attributes']['src']

                                                    show_art = {
                                                        'fanart': fanart_image,
                                                        'thumb': thumb_image,
                                                        'clearlogo': logo_image,
                                                        'poster': poster_image
                                                    }

                                                    helper.add_item(title, params, info=info, art=show_art,
                                                                    content='seasons',
                                                                    folder_name=page['attributes'].get(
                                                                        'pageMetadataTitle'),
                                                                    sort_method='sort_label')

                                        # Promotions and Channels page
                                        elif collection['attributes']['component']['id'] == 'generic-hero':
                                            for c in collection['relationships']['items']['data']:
                                                for collectionItem in collectionItems:
                                                    if c['id'] == collectionItem['id']:

                                                        # Promotion grids (grids with background image)
                                                        if collectionItem['relationships'].get('show') or \
                                                                collectionItem['relationships'].get('video') or \
                                                                collectionItem['relationships'].get('image') or \
                                                                collectionItem['relationships'].get('link'):
                                                            if len(collection['relationships']['items'][
                                                                       'data']) > 1:

                                                                # 0 = Promotion name (New, Crime etc) mostly used in homepage
                                                                if collection['relationships']['items']['data'][0][
                                                                    'id'] == collectionItem['id']:
                                                                    if collectionItem['attributes'].get('title'):
                                                                        title = collectionItem['attributes'][
                                                                            'title']
                                                                    # No title in collectionItem attributes, use show name
                                                                    elif collectionItem['relationships'].get(
                                                                            'show'):
                                                                        for show in shows:
                                                                            if show['id'] == \
                                                                                    collectionItem['relationships'][
                                                                                        'show']['data']['id']:
                                                                                title = show['attributes']['name']
                                                                    else:
                                                                        title = None

                                                                    # Fanart
                                                                    if collectionItem['relationships'].get('image'):
                                                                        fanart_id = \
                                                                            collectionItem['relationships'][
                                                                                'image'][
                                                                                'data']['id']
                                                                    elif collectionItem['relationships'].get(
                                                                            'images'):
                                                                        fanart_id = \
                                                                            collectionItem['relationships'][
                                                                                'images'][
                                                                                'data'][0]['id']
                                                                    elif collectionItem['relationships'].get(
                                                                            'show'):
                                                                        for show in shows:
                                                                            if show['id'] == \
                                                                                    collectionItem['relationships'][
                                                                                        'show']['data']['id']:
                                                                                fanart_id = \
                                                                                    show['relationships']['images'][
                                                                                        'data'][
                                                                                        -1]['id']
                                                                    else:
                                                                        fanart_id = None

                                                                    if fanart_id:
                                                                        for image in images:
                                                                            if image['id'] == fanart_id:
                                                                                fanart_image = image['attributes'][
                                                                                    'src']
                                                                    else:
                                                                        fanart_image = ''

                                                                    art = {
                                                                        'fanart': fanart_image,
                                                                        'thumb': fanart_image
                                                                    }

                                                                    for collectionItem2 in collectionItems:
                                                                        # 1 = Promotion items
                                                                        if \
                                                                                collection['relationships'][
                                                                                    'items']['data'][1][
                                                                                    'id'] == collectionItem2['id']:
                                                                            collection_id = \
                                                                                collectionItem2['relationships'][
                                                                                    'collection']['data']['id']

                                                                    params = {
                                                                        'action': 'list_collection_items',
                                                                        'page_path': page_path,
                                                                        'collection_id': collection_id
                                                                    }

                                                                    helper.add_item(title, params, art=art,
                                                                                    content='videos',
                                                                                    folder_name=page[
                                                                                        'attributes'].get(
                                                                                        'pageMetadataTitle'))

                                                        # Channels page generic-hero.
                                                        # Also used channel page promotions when there's no livestream.
                                                        # Still in use in some countries.
                                                        # Example Finland uses Content-grid -> list_collection_items
                                                        if collectionItem['relationships'].get('channel'):
                                                            if len(collection['relationships']['items']['data']) > 1:
                                                                # Get all channels in page data
                                                                for channel in channels:
                                                                    if \
                                                                            collectionItem['relationships'][
                                                                                'channel']['data'][
                                                                                'id'] == channel[
                                                                                'id']:
                                                                        # Find page path from routes
                                                                        for route in routes:
                                                                            if route['id'] == \
                                                                                    channel['relationships'][
                                                                                        'routes'][
                                                                                        'data'][
                                                                                        0]['id']:
                                                                                next_page_path = \
                                                                                    route['attributes'][
                                                                                        'url']

                                                                        # If more than 1 channel in page_data = all channels page
                                                                        if len(channels) > 1:
                                                                            params = {
                                                                                'action': 'list_page',
                                                                                'page_path': next_page_path
                                                                            }
                                                                        # Get link to display channel promotion shows
                                                                        else:
                                                                            for collectionItem2 in collectionItems:
                                                                                # 1 = Channel category items
                                                                                if \
                                                                                        collection['relationships'][
                                                                                            'items']['data'][1][
                                                                                            'id'] == \
                                                                                                collectionItem2[
                                                                                                    'id']:
                                                                                    collection_id = \
                                                                                        collectionItem2[
                                                                                            'relationships'][
                                                                                            'collection']['data'][
                                                                                            'id']

                                                                            params = {
                                                                                'action': 'list_collection_items',
                                                                                'page_path': page_path,
                                                                                'collection_id': collection_id
                                                                            }

                                                                        channel_info = {
                                                                            'title': channel['attributes'].get(
                                                                                'name'),
                                                                            'plot': channel['attributes'].get(
                                                                                'description')
                                                                        }

                                                                        channel_logo = None
                                                                        fanart_image = None
                                                                        if channel['relationships'].get('images'):
                                                                            for image in images:
                                                                                for channel_images in \
                                                                                        channel['relationships'][
                                                                                            'images'][
                                                                                            'data']:
                                                                                    if image['id'] == \
                                                                                            channel_images[
                                                                                                'id']:
                                                                                        if image['attributes'][
                                                                                            'kind'] == 'logo':
                                                                                            channel_logo = \
                                                                                                image['attributes'][
                                                                                                    'src']
                                                                                        if image['attributes'][
                                                                                            'kind'] == 'default':
                                                                                            fanart_image = \
                                                                                                image['attributes'][
                                                                                                    'src']

                                                                        if channel_logo:
                                                                            thumb_image = channel_logo
                                                                        else:
                                                                            thumb_image = fanart_image

                                                                        channel_art = {
                                                                            'fanart': fanart_image,
                                                                            'thumb': thumb_image
                                                                        }

                                                                        helper.add_item(
                                                                            channel['attributes'].get('name'),
                                                                            params, info=channel_info,
                                                                            content='videos', art=channel_art,
                                                                            folder_name=page['attributes'].get(
                                                                                'pageMetadataTitle'),
                                                                            sort_method='unsorted')

    helper.eod()

def list_collection_items(collection_id, page_path=None):
    page_data = helper.d.get_page(page_path)

    user_favorites = ",".join([str(x['id']) for x in helper.d.get_favorites()['data']['relationships']['favorites']['data']])
    user_packages = ",".join([str(x) for x in helper.d.get_user_data()['attributes']['packages']])

    pages = list(filter(lambda x: x['type'] == 'page', page_data['included']))
    collections = list(filter(lambda x: x['type'] == 'collection', page_data['included']))
    collectionItems = list(filter(lambda x: x['type'] == 'collectionItem', page_data['included']))
    images = list(filter(lambda x: x['type'] == 'image', page_data['included']))
    shows = list(filter(lambda x: x['type'] == 'show', page_data['included']))
    videos = list(filter(lambda x: x['type'] == 'video', page_data['included']))
    channels = list(filter(lambda x: x['type'] == 'channel', page_data['included']))
    genres = list(filter(lambda x: x['type'] == 'genre', page_data['included']))
    links = list(filter(lambda x: x['type'] == 'link', page_data['included']))
    routes = list(filter(lambda x: x['type'] == 'route', page_data['included']))
    taxonomyNodes = list(filter(lambda x: x['type'] == 'taxonomyNode', page_data['included']))

    for collection in collections:
        if collection['id'] == collection_id:
            # dicoveryplus.com (US) and discoveryplus.in list series season grid
            if collection['attributes'].get('component') and collection['attributes']['component']['id'] == 'tabbed-content':
                # Check if there's any seasons of show or sport event
                if collection['attributes']['component'].get('filters'):
                    for option in collection['attributes']['component']['filters'][0][
                        'options']:
                        title = helper.language(30011) + ' ' + str(option['id'])
                        params = {
                            'action': 'list_collection',
                            'collection_id': collection['id'],
                            # 66290614510668341673562607828298581172
                            'mandatoryParams': collection['attributes'][
                                'component'].get(
                                'mandatoryParams'),  # pf[show.id]=12423
                            'parameter': option['parameter']  # pf[seasonNumber]=1
                        }

                        info = {
                            'mediatype': 'season'
                        }

                        # Show metadata
                        # Some show pages doesn't have primaryContent = show id and also doesn't have metadata of show
                        if pages[0]['relationships'].get('primaryContent'):
                            for show in shows:
                                if show['id'] == pages[0]['relationships']['primaryContent']['data']['id']:

                                    info['tvshowtitle'] = show['attributes'].get('name')
                                    info['plot'] = show['attributes'].get('description')
                                    info['season'] = len(show['attributes']['seasonNumbers'])
                                    info['episode'] = show['attributes']['episodeCount']

                                    g = []
                                    # Show genres in discoveryplus.com (US)
                                    if show['relationships'].get('txGenres'):
                                        for taxonomyNode in taxonomyNodes:
                                            for show_genre in show['relationships']['txGenres']['data']:
                                                if taxonomyNode['id'] == show_genre['id']:
                                                    g.append(taxonomyNode['attributes']['name'])

                                    if show['relationships'].get('primaryChannel'):
                                        for channel in channels:
                                            if channel['id'] == \
                                                    show['relationships']['primaryChannel']['data'][
                                                        'id']:
                                                primaryChannel = channel['attributes']['name']
                                    else:
                                        primaryChannel = None

                                    info['genre'] = g
                                    info['studio'] = primaryChannel

                                    fanart_image = None
                                    thumb_image = None
                                    logo_image = None
                                    poster_image = None
                                    if show['relationships'].get('images'):
                                        for image in images:
                                            for show_images in show['relationships']['images']['data']:
                                                if image['id'] == show_images['id']:
                                                    if image['attributes']['kind'] == 'default':
                                                        fanart_image = image['attributes']['src']
                                                        thumb_image = image['attributes']['src']
                                                    if image['attributes']['kind'] == 'logo':
                                                        logo_image = image['attributes']['src']
                                                    if image['attributes']['kind'] == 'poster_with_logo':
                                                        poster_image = image['attributes']['src']

                                    show_art = {
                                        'fanart': fanart_image,
                                        'thumb': thumb_image,
                                        'clearlogo': logo_image,
                                        'poster': poster_image
                                    }

                                    if collection['attributes'].get('title'):
                                        folder_name = show['attributes'].get('name') + ' / ' + collection['attributes'].get(
                                            'title')
                                    else:
                                        folder_name = show['attributes'].get('name')
                        else:
                            info = {}
                            show_art = {}
                            folder_name = pages[0]['attributes'].get('title') + ' / ' + collection['attributes'].get('title')


                        helper.add_item(title, params, info=info, art=show_art,
                                        content='seasons', folder_name=folder_name,
                                        sort_method='sort_label')

            # content-grid, content-hero etc
            else:
                for collection_relationship in collection['relationships']['items']['data']:
                    for collectionItem in collectionItems:
                        if collection_relationship['id'] == collectionItem['id']:

                            # discoveryplus.in (Episodes, Shorts)
                            if collectionItem['relationships'].get('collection'):
                                for c2 in collections:
                                    if collectionItem['relationships']['collection']['data']['id'] == c2['id']:
                                        # Don't list empty category
                                        if c2.get('relationships'):
                                                params = {
                                                    'action': 'list_collection_items',
                                                    'page_path': page_path,
                                                    'collection_id': c2['id']
                                                }

                                                if c2['attributes'].get('name'):
                                                    if c2['attributes']['name'] == 'blueprint-show-seasons-grid':
                                                        title = 'Episodes'
                                                    elif c2['attributes']['name'] == 'blueprint-show-shorts':
                                                        title = 'Shorts'
                                                    else:
                                                        title = c2['attributes']['name']
                                                else:
                                                    title = ''

                                                helper.add_item(title, params, content='videos', folder_name=pages[0]['attributes'].get('title'))

                            # List shows
                            if collectionItem['relationships'].get('show'):
                                for show in shows:
                                    if collectionItem['relationships']['show']['data']['id'] == show['id']:

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

                                        # Show genres in discoveryplus.com (US)
                                        elif show['relationships'].get('txGenres'):
                                            for taxonomyNode in taxonomyNodes:
                                                for show_genre in show['relationships']['txGenres']['data']:
                                                    if taxonomyNode['id'] == show_genre['id']:
                                                        g.append(taxonomyNode['attributes']['name'])

                                        if show['relationships'].get('primaryChannel'):
                                            for channel in channels:
                                                if channel['id'] == show['relationships']['primaryChannel']['data'][
                                                    'id']:
                                                    primaryChannel = channel['attributes']['name']
                                        else:
                                            primaryChannel = None

                                        info = {
                                            'mediatype': 'tvshow',
                                            'plot': show['attributes'].get('description'),
                                            'genre': g,
                                            'studio': primaryChannel,
                                            'season': len(show['attributes'].get('seasonNumbers')),
                                            'episode': show['attributes'].get('episodeCount')
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

                                        fanart_image = None
                                        thumb_image = None
                                        logo_image = None
                                        poster_image = None
                                        if show['relationships'].get('images'):
                                            for image in images:
                                                for show_images in show['relationships']['images']['data']:
                                                    if image['id'] == show_images['id']:
                                                        if image['attributes']['kind'] == 'default':
                                                            fanart_image = image['attributes']['src']
                                                            thumb_image = image['attributes']['src']
                                                        if image['attributes']['kind'] == 'logo':
                                                            logo_image = image['attributes']['src']
                                                        if image['attributes']['kind'] == 'poster_with_logo':
                                                            poster_image = image['attributes']['src']

                                        show_art = {
                                            'fanart': fanart_image,
                                            'thumb': thumb_image,
                                            'clearlogo': logo_image,
                                            'poster': poster_image
                                        }

                                        helper.add_item(title, params, info=info, art=show_art, content='tvshows',
                                                        menu=menu, folder_name=collection['attributes'].get('title'),
                                                        sort_method='unsorted')

                            # List videos and live sports
                            if collectionItem['relationships'].get('video'):
                                for video in videos:
                                    if collectionItem['relationships']['video']['data']['id'] == video['id']:

                                        params = {
                                            'action': 'play',
                                            'video_id': video['id'],
                                            'video_type': video['attributes']['videoType']
                                        }

                                        show_fanart_image = None
                                        show_logo_image = None
                                        show_poster_image = None
                                        for show in shows:
                                            if show['id'] == video['relationships']['show']['data']['id']:
                                                show_title = show['attributes']['name']

                                                if show['relationships'].get('images'):
                                                    for image in images:
                                                        for show_images in show['relationships']['images']['data']:
                                                            if image['id'] == show_images['id']:
                                                                if image['attributes']['kind'] == 'default':
                                                                    show_fanart_image = image['attributes']['src']
                                                                if image['attributes']['kind'] == 'logo':
                                                                    show_logo_image = image['attributes']['src']
                                                                if image['attributes']['kind'] == 'poster_with_logo':
                                                                    show_poster_image = image['attributes']['src']

                                        g = []
                                        if video['relationships'].get('genres'):
                                            for genre in genres:
                                                for video_genre in video['relationships']['genres']['data']:
                                                    if genre['id'] == video_genre['id']:
                                                        g.append(genre['attributes']['name'])

                                        if video['relationships'].get('primaryChannel'):
                                            for channel in channels:
                                                if channel['id'] == video['relationships']['primaryChannel']['data'][
                                                    'id']:
                                                    primaryChannel = channel['attributes']['name']
                                        else:
                                            primaryChannel = None

                                        if video['relationships'].get('images'):
                                            for image in images:
                                                if image['id'] == video['relationships']['images']['data'][0]['id']:
                                                    video_thumb_image = image['attributes']['src']
                                        else:
                                            video_thumb_image = None

                                        duration = video['attributes']['videoDuration'] / 1000.0 if video[
                                            'attributes'].get(
                                            'videoDuration') else None

                                        # If episode is not yet playable, show playable time in plot
                                        if video['attributes'].get('earliestPlayableStart'):
                                            if helper.d.parse_datetime(
                                                    video['attributes'][
                                                        'earliestPlayableStart']) > helper.d.get_current_time():
                                                playable = str(
                                                    helper.d.parse_datetime(
                                                        video['attributes']['earliestPlayableStart']).strftime(
                                                        '%d.%m.%Y %H:%M'))
                                                if video['attributes'].get('description'):
                                                    plot = helper.language(30002) + playable + ' ' + video[
                                                        'attributes'].get(
                                                        'description')
                                                else:
                                                    plot = helper.language(30002) + playable
                                            else:
                                                plot = video['attributes'].get('description')
                                        else:
                                            plot = video['attributes'].get('description')

                                        # discovery+ subscription content check
                                        # Check for discovery+ subscription content only if user doesn't have subscription
                                        if 'Premium' not in user_packages:
                                            if len(video['attributes']['packages']) > 1:
                                                # Get all available packages in availabilityWindows
                                                for availabilityWindow in video['attributes']['availabilityWindows']:
                                                    if availabilityWindow['package'] == 'Free':
                                                        # Check if there is ending time for free availability
                                                        if availabilityWindow.get('playableEnd'):
                                                            # Check if video is still available for free
                                                            if helper.d.parse_datetime(availabilityWindow[
                                                                                           'playableStart']) < helper.d.get_current_time() < helper.d.parse_datetime(
                                                                availabilityWindow['playableEnd']):
                                                                plot = plot

                                                            else:  # Video is not anymore available for free
                                                                plot = '[discovery+] ' + plot
                                            else:  # Only one package in packages = Premium
                                                plot = '[discovery+] ' + plot

                                        episode_info = {
                                            'mediatype': 'episode',
                                            'title': video['attributes'].get('name').lstrip(),
                                            'tvshowtitle': show_title,
                                            'season': video['attributes'].get('seasonNumber'),
                                            'episode': video['attributes'].get('episodeNumber'),
                                            'plot': plot,
                                            'genre': g,
                                            'studio': primaryChannel,
                                            'duration': duration,
                                            'aired': video['attributes'].get('airDate')
                                        }

                                        # Watched status from Discovery+
                                        if helper.get_setting('sync_playback'):
                                            if video['attributes']['viewingHistory']['viewed']:
                                                if video['attributes']['viewingHistory'].get('completed'):  # Watched video
                                                    episode_info['playcount'] = '1'
                                                    resume = 0
                                                    total = duration
                                                else:  # Partly watched video
                                                    episode_info['playcount'] = '0'
                                                    resume = video['attributes']['viewingHistory']['position'] / 1000.0
                                                    total = duration
                                            else:  # Unwatched video
                                                episode_info['playcount'] = '0'
                                                resume = 0
                                                total = 1
                                        else:  # Kodis resume data used
                                            resume = None
                                            total = None

                                        episode_art = {
                                            'fanart': show_fanart_image,
                                            'thumb': video_thumb_image,
                                            'clearlogo': show_logo_image,
                                            'poster': show_poster_image
                                        }

                                        helper.add_item(video['attributes'].get('name').lstrip(), params=params,
                                                        info=episode_info, art=episode_art,
                                                        content='episodes', playable=True, resume=resume, total=total,
                                                        folder_name=collection['attributes'].get('title'),
                                                        sort_method='sort_episodes')

                            # List channels
                            # Used when coming from collection (example Eurosport -> Channels)
                            # Also used now on (5.1.2021) listing all channels at least in finnish discovery+
                            if collectionItem['relationships'].get('channel'):
                                for channel in channels:
                                    if collectionItem['relationships']['channel']['data']['id'] == channel['id']:
                                        # List channel pages
                                        if channel['relationships'].get('routes'):
                                            # Find page path from routes
                                            for route in routes:
                                                if route['id'] == channel['relationships']['routes']['data'][0]['id']:
                                                    next_page_path = route['attributes']['url']

                                            params = {
                                                'action': 'list_page',
                                                'page_path': next_page_path
                                            }

                                            channel_info = {
                                                'title': channel['attributes'].get('name'),
                                                'plot': channel['attributes'].get('description')
                                            }

                                            channel_logo = None
                                            fanart_image = None
                                            if channel['relationships'].get('images'):
                                                for image in images:
                                                    for channel_images in channel['relationships']['images']['data']:
                                                        if image['id'] == channel_images['id']:
                                                            if image['attributes']['kind'] == 'logo':
                                                                channel_logo = image['attributes']['src']
                                                            if image['attributes']['kind'] == 'default':
                                                                fanart_image = image['attributes']['src']

                                            if channel_logo:
                                                thumb_image = channel_logo
                                            else:
                                                thumb_image = fanart_image

                                            channel_art = {
                                                'fanart': fanart_image,
                                                'thumb': thumb_image
                                            }

                                            helper.add_item(channel['attributes'].get('name'), params,
                                                            info=channel_info,
                                                            content='videos', art=channel_art,
                                                            folder_name=pages[0]['attributes'].get('pageMetadataTitle'),
                                                            sort_method='unsorted')

                                        # List channel livestreams only if there's no route to channel page
                                        elif channel['attributes'].get('hasLiveStream'):
                                            params = {
                                                'action': 'play',
                                                'video_id': channel['id'],
                                                'video_type': 'channel'
                                            }

                                            channel_info = {
                                                'mediatype': 'video',
                                                'title': helper.language(30014) + ' ' + channel['attributes'].get(
                                                    'name'),
                                                'plot': channel['attributes'].get('description'),
                                                'playcount': '0'
                                            }

                                            channel_logo = None
                                            fanart_image = None
                                            if channel['relationships'].get('images'):
                                                for image in images:
                                                    for channel_images in channel['relationships']['images']['data']:
                                                        if image['id'] == channel_images['id']:
                                                            if image['attributes']['kind'] == 'logo':
                                                                channel_logo = image['attributes']['src']
                                                            if image['attributes']['kind'] == 'default':
                                                                fanart_image = image['attributes']['src']

                                            if channel_logo:
                                                thumb_image = channel_logo
                                            else:
                                                thumb_image = fanart_image

                                            channel_art = {
                                                'fanart': fanart_image,
                                                'thumb': thumb_image
                                            }

                                            helper.add_item(
                                                helper.language(30014) + ' ' + channel['attributes'].get('name'),
                                                params=params,
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

                                        if link['relationships'].get('images'):
                                            for image in images:
                                                if image['id'] == \
                                                        link['relationships']['images']['data'][0][
                                                            'id']:
                                                    thumb_image = image['attributes']['src']
                                        else:
                                            thumb_image = None

                                        category_art = {
                                            'fanart': thumb_image,
                                            'thumb': thumb_image
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

                                        helper.add_item(link_title, params, content='videos',
                                                        art=category_art,
                                                        folder_name=collection['attributes'].get('title'))

    helper.eod()

def list_search_shows(search_query):
    page_data = helper.d.get_search_shows(search_query=search_query)

    user_favorites = ",".join([str(x['id']) for x in helper.d.get_favorites()['data']['relationships']['favorites']['data']])

    images = list(filter(lambda x: x['type'] == 'image', page_data['included']))
    genres = list(filter(lambda x: x['type'] == 'genre', page_data['included']))
    routes = list(filter(lambda x: x['type'] == 'route', page_data['included']))

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
            'genre': g,
            'season': len(show['attributes'].get('seasonNumbers')),
            'episode': show['attributes'].get('episodeCount')
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

        fanart_image = None
        thumb_image = None
        logo_image = None
        poster_image = None
        if show['relationships'].get('images'):
            for image in images:
                for show_images in show['relationships']['images']['data']:
                    if image['id'] == show_images['id']:
                        if image['attributes']['kind'] == 'default':
                            fanart_image = image['attributes']['src']
                            thumb_image = image['attributes']['src']
                        if image['attributes']['kind'] == 'logo':
                            logo_image = image['attributes']['src']
                        if image['attributes']['kind'] == 'poster_with_logo':
                            poster_image = image['attributes']['src']

        show_art = {
            'fanart': fanart_image,
            'thumb': thumb_image,
            'clearlogo': logo_image,
            'poster': poster_image
        }

        folder_name = helper.language(30007) + ' / ' + search_query

        helper.add_item(title, params, info=info, art=show_art, content='tvshows', menu=menu, folder_name=folder_name,
                        sort_method='unsorted')

    helper.eod()

def list_favorites():
    page_data = helper.d.get_favorites()

    images = list(filter(lambda x: x['type'] == 'image', page_data['included']))
    shows = list(filter(lambda x: x['type'] == 'show', page_data['included']))
    channels = list(filter(lambda x: x['type'] == 'channel', page_data['included']))
    genres = list(filter(lambda x: x['type'] == 'genre', page_data['included']))
    routes = list(filter(lambda x: x['type'] == 'route', page_data['included']))

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
                    'studio': primaryChannel,
                    'season': len(show_data['attributes'].get('seasonNumbers')),
                    'episode': show_data['attributes'].get('episodeCount')
                }

                menu = []
                menu.append((helper.language(30010),
                             'RunPlugin(plugin://' + helper.addon_name + '/?action=delete_favorite&show_id=' + str(
                                 favorite['id']) + ')',))

                fanart_image = None
                thumb_image = None
                logo_image = None
                poster_image = None
                if show_data['relationships'].get('images'):
                    for image in images:
                        for show_images in show_data['relationships']['images']['data']:
                            if image['id'] == show_images['id']:
                                if image['attributes']['kind'] == 'default':
                                    fanart_image = image['attributes']['src']
                                    thumb_image = image['attributes']['src']
                                if image['attributes']['kind'] == 'logo':
                                    logo_image = image['attributes']['src']
                                if image['attributes']['kind'] == 'poster_with_logo':
                                    poster_image = image['attributes']['src']

                show_art = {
                    'fanart': fanart_image,
                    'thumb': thumb_image,
                    'clearlogo': logo_image,
                    'poster': poster_image
                }

                helper.add_item(title, params, info=info, art=show_art, content='tvshows', menu=menu,
                                folder_name=helper.language(30017), sort_method='unsorted')

    helper.eod()

# Favorite shows in discoveryplus.in
def list_favorites_in():
    page_data = helper.d.get_favorites_in()

    images = list(filter(lambda x: x['type'] == 'image', page_data['included']))
    routes = list(filter(lambda x: x['type'] == 'route', page_data['included']))
    taxonomyNodes = list(filter(lambda x: x['type'] == 'taxonomyNode', page_data['included']))

    for show in page_data['data']:
        title = data['attributes']['name'].encode('utf-8')

        # Find page path from routes
        for route in routes:
            if route['id'] == show['relationships']['routes']['data'][0]['id']:
                next_page_path = route['attributes']['url']

        params = {
            'action': 'list_page',
            'page_path': next_page_path
        }

        g = []
        if show['relationships'].get('txGenres'):
            for taxonomyNode in taxonomyNodes:
                for show_genre in show['relationships']['txGenres']['data']:
                    if taxonomyNode['id'] == show_genre['id']:
                        g.append(taxonomyNode['attributes']['name'])

        info = {
            'mediatype': 'tvshow',
            'plot': show['attributes'].get('description'),
            'genre': g,
            'season': len(show['attributes'].get('seasonNumbers')),
            'episode': show['attributes'].get('episodeCount')
        }

        menu = []
        menu.append((helper.language(30010),
                     'RunPlugin(plugin://' + helper.addon_name + '/?action=delete_favorite&show_id=' + str(
                         show['id']) + ')',))

        fanart_image = None
        thumb_image = None
        logo_image = None
        poster_image = None
        if show['relationships'].get('images'):
            for image in images:
                for show_images in show['relationships']['images']['data']:
                    if image['id'] == show_images['id']:
                        if image['attributes']['kind'] == 'default':
                            fanart_image = image['attributes']['src']
                            thumb_image = image['attributes']['src']
                        if image['attributes']['kind'] == 'logo':
                            logo_image = image['attributes']['src']
                        if image['attributes']['kind'] == 'poster_with_logo':
                            poster_image = image['attributes']['src']

        show_art = {
            'fanart': fanart_image,
            'thumb': thumb_image,
            'clearlogo': logo_image,
            'poster': poster_image
        }

        folder_name = helper.language(30017) + ' / Shows'

        helper.add_item(title, params, info=info, art=show_art, content='tvshows', menu=menu,
                        folder_name=folder_name,
                        sort_method='unsorted')

    helper.eod()

# Favorite and watchlist videos in discoveryplus.in
def list_favorite_watchlist_videos_in(videoType=None, playlist=None):
    if videoType:
        page_data = helper.d.get_favorite_videos_in(videoType)
    else:
        page_data = helper.d.get_watchlist_in(playlist)

    user_packages = ",".join([str(x) for x in helper.d.get_user_data()['attributes']['packages']])

    images = list(filter(lambda x: x['type'] == 'image', page_data['included']))
    shows = list(filter(lambda x: x['type'] == 'show', page_data['included']))
    channels = list(filter(lambda x: x['type'] == 'channel', page_data['included']))
    taxonomyNodes = list(filter(lambda x: x['type'] == 'taxonomyNode', page_data['included']))

    for video in page_data['data']:
        params = {
            'action': 'play',
            'video_id': video['id'],
            'video_type': video['attributes']['videoType']
        }

        show_fanart_image = None
        show_logo_image = None
        show_poster_image = None
        for show in shows:
            if show['id'] == video['relationships']['show']['data']['id']:
                show_title = show['attributes']['name']

            if show['relationships'].get('images'):
                for image in images:
                    for show_images in show['relationships']['images']['data']:
                        if image['id'] == show_images['id']:
                            if image['attributes']['kind'] == 'default':
                                show_fanart_image = image['attributes']['src']
                            if image['attributes']['kind'] == 'logo':
                                show_logo_image = image['attributes']['src']
                            if image['attributes']['kind'] == 'poster_with_logo':
                                show_poster_image = image['attributes']['src']

        g = []
        if video['relationships'].get('txGenres'):
            for taxonomyNode in taxonomyNodes:
                for video_genre in video['relationships']['txGenres']['data']:
                    if taxonomyNode['id'] == video_genre['id']:
                        g.append(taxonomyNode['attributes']['name'])

        if video['relationships'].get('primaryChannel'):
            for channel in channels:
                if channel['id'] == video['relationships']['primaryChannel']['data']['id']:
                    primaryChannel = channel['attributes']['name']
        else:
            primaryChannel = None

        if video['relationships'].get('images'):
            for image in images:
                if image['id'] == video['relationships']['images']['data'][0]['id']:
                    video_thumb_image = image['attributes']['src']
        else:
            video_thumb_image = None

        duration = video['attributes']['videoDuration'] / 1000.0 if video['attributes'].get(
            'videoDuration') else None

        # If episode is not yet playable, show playable time in plot
        if video['attributes'].get('earliestPlayableStart'):
            if helper.d.parse_datetime(
                    video['attributes']['earliestPlayableStart']) > helper.d.get_current_time():
                playable = str(
                    helper.d.parse_datetime(
                        video['attributes']['earliestPlayableStart']).strftime(
                        '%d.%m.%Y %H:%M'))
                if video['attributes'].get('description'):
                    plot = helper.language(30002) + playable + ' ' + video['attributes'].get(
                        'description')
                else:
                    plot = helper.language(30002) + playable
            else:
                plot = video['attributes'].get('description')
        else:
            plot = video['attributes'].get('description')

        # discovery+ subscription content check
        # Check for discovery+ subscription content only if user doesn't have subscription
        if 'Premium' not in user_packages:
            if len(video['attributes']['packages']) > 1:
                # Get all available packages in availabilityWindows
                for availabilityWindow in video['attributes']['availabilityWindows']:
                    if availabilityWindow['package'] == 'Free':
                        # Check if there is ending time for free availability
                        if availabilityWindow.get('playableEnd'):
                            # Check if video is still available for free
                            if helper.d.parse_datetime(availabilityWindow[
                                                           'playableStart']) < helper.d.get_current_time() < helper.d.parse_datetime(
                                availabilityWindow['playableEnd']):
                                plot = plot

                            else:  # Video is not anymore available for free
                                plot = '[discovery+] ' + plot
            else:  # Only one package in packages = Premium
                plot = '[discovery+] ' + plot

        episode_info = {
            'mediatype': 'episode',
            'title': video['attributes'].get('name').lstrip(),
            'tvshowtitle': show_title,
            'season': video['attributes'].get('seasonNumber'),
            'episode': video['attributes'].get('episodeNumber'),
            'plot': plot,
            'genre': g,
            'studio': primaryChannel,
            'duration': duration,
            'aired': video['attributes'].get('airDate')
        }

        # Watched status from discovery+
        if helper.get_setting('sync_playback'):
            if video['attributes']['viewingHistory']['viewed']:
                if video['attributes']['viewingHistory']['completed']:  # Watched video
                    episode_info['playcount'] = '1'
                    resume = 0
                    total = duration
                else:  # Partly watched video
                    episode_info['playcount'] = '0'
                    resume = video['attributes']['viewingHistory']['position'] / 1000.0
                    total = duration
            else:  # Unwatched video
                episode_info['playcount'] = '0'
                resume = 0
                total = 1
        else:  # Kodis resume data used
            resume = None
            total = None

        episode_art = {
            'fanart': show_fanart_image,
            'thumb': video_thumb_image,
            'clearlogo': show_logo_image,
            'poster': show_poster_image
        }

        if videoType:
            folder_name = helper.language(30017)
        else:
            folder_name = 'Watchlist'

        helper.add_item(video['attributes'].get('name').lstrip(), params=params,
                        info=episode_info,
                        art=episode_art,
                        content='episodes', playable=True, resume=resume, total=total,
                        folder_name=folder_name, sort_method='sort_episodes')

    helper.eod()

def list_collection(collection_id, page, mandatoryParams=None, parameter=None):
    if mandatoryParams is None and parameter is None:
        page_data = helper.d.get_collections(collection_id=collection_id, page=page)
    else:
        page_data = helper.d.get_collections(collection_id=collection_id, page=page, mandatoryParams=mandatoryParams,
                                             parameter=parameter)

    user_favorites = ",".join(
        [str(x['id']) for x in helper.d.get_favorites()['data']['relationships']['favorites']['data']])
    user_packages = ",".join([str(x) for x in helper.d.get_user_data()['attributes']['packages']])

    # Don't try to list empty collection
    if page_data['data'].get('relationships'):

        collections = list(filter(lambda x: x['type'] == 'collection', page_data['included']))
        collectionItems = list(filter(lambda x: x['type'] == 'collectionItem', page_data['included']))
        images = list(filter(lambda x: x['type'] == 'image', page_data['included']))
        shows = list(filter(lambda x: x['type'] == 'show', page_data['included']))
        videos = list(filter(lambda x: x['type'] == 'video', page_data['included']))
        channels = list(filter(lambda x: x['type'] == 'channel', page_data['included']))
        genres = list(filter(lambda x: x['type'] == 'genre', page_data['included']))
        links = list(filter(lambda x: x['type'] == 'link', page_data['included']))
        routes = list(filter(lambda x: x['type'] == 'route', page_data['included']))
        taxonomyNodes = list(filter(lambda x: x['type'] == 'taxonomyNode', page_data['included']))

        # Get order of content from page_data['data']
        for collection_relationship in page_data['data']['relationships']['items']['data']:
            for collectionItem in collectionItems:
                # Match collectionItem id's from collection listing to all collectionItems in data
                if collection_relationship['id'] == collectionItem['id']:
                    # List shows, used in discoveryplus.com (US)
                    if collectionItem['relationships'].get('show'):
                        for show in shows:
                            if collectionItem['relationships']['show']['data']['id'] == show['id']:

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

                                # Show genres in discoveryplus.com (US)
                                elif show['relationships'].get('txGenres'):
                                    for taxonomyNode in taxonomyNodes:
                                        for show_genre in show['relationships']['txGenres']['data']:
                                            if taxonomyNode['id'] == show_genre['id']:
                                                g.append(taxonomyNode['attributes']['name'])

                                if show['relationships'].get('primaryChannel'):
                                    for channel in channels:
                                        if channel['id'] == show['relationships']['primaryChannel']['data'][
                                            'id']:
                                            primaryChannel = channel['attributes']['name']
                                else:
                                    primaryChannel = None

                                info = {
                                    'mediatype': 'tvshow',
                                    'plot': show['attributes'].get('description'),
                                    'genre': g,
                                    'studio': primaryChannel,
                                    'season': len(show['attributes'].get('seasonNumbers')),
                                    'episode': show['attributes'].get('episodeCount')
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

                                fanart_image = None
                                thumb_image = None
                                logo_image = None
                                poster_image = None
                                if show['relationships'].get('images'):
                                    for image in images:
                                        for show_images in show['relationships']['images']['data']:
                                            if image['id'] == show_images['id']:
                                                if image['attributes']['kind'] == 'default':
                                                    fanart_image = image['attributes']['src']
                                                    thumb_image = image['attributes']['src']
                                                if image['attributes']['kind'] == 'logo':
                                                    logo_image = image['attributes']['src']
                                                if image['attributes']['kind'] == 'poster_with_logo':
                                                    poster_image = image['attributes']['src']

                                show_art = {
                                    'fanart': fanart_image,
                                    'thumb': thumb_image,
                                    'clearlogo': logo_image,
                                    'poster': poster_image
                                }

                                helper.add_item(title, params, info=info, art=show_art, content='tvshows',
                                                menu=menu, folder_name=page_data['data']['attributes'].get('title'),
                                                sort_method='unsorted')

                    # List videos
                    if collectionItem['relationships'].get('video'):
                        for video in videos:
                            # Match collectionItem's video id to all video id's in data
                            if collectionItem['relationships']['video']['data']['id'] == video['id']:

                                params = {
                                    'action': 'play',
                                    'video_id': video['id'],
                                    'video_type': video['attributes']['videoType']
                                }

                                show_fanart_image = None
                                show_logo_image = None
                                show_poster_image = None
                                for show in shows:
                                    if show['id'] == video['relationships']['show']['data']['id']:
                                        show_title = show['attributes']['name']

                                        if show['relationships'].get('images'):
                                            for image in images:
                                                for show_images in show['relationships']['images']['data']:
                                                    if image['id'] == show_images['id']:
                                                        if image['attributes']['kind'] == 'default':
                                                            show_fanart_image = image['attributes']['src']
                                                        if image['attributes']['kind'] == 'logo':
                                                            show_logo_image = image['attributes']['src']
                                                        if image['attributes']['kind'] == 'poster_with_logo':
                                                            show_poster_image = image['attributes']['src']

                                g = []
                                if video['relationships'].get('genres'):
                                    for genre in genres:
                                        for video_genre in video['relationships']['genres']['data']:
                                            if genre['id'] == video_genre['id']:
                                                g.append(genre['attributes']['name'])
                                # Show genres in discoveryplus.com (US)
                                elif video['relationships'].get('txGenres'):
                                    for taxonomyNode in taxonomyNodes:
                                        for video_genre in video['relationships']['txGenres']['data']:
                                            if taxonomyNode['id'] == video_genre['id']:
                                                g.append(taxonomyNode['attributes']['name'])

                                if video['relationships'].get('primaryChannel'):
                                    for channel in channels:
                                        if channel['id'] == video['relationships']['primaryChannel']['data']['id']:
                                            primaryChannel = channel['attributes']['name']
                                else:
                                    primaryChannel = None

                                if video['relationships'].get('images'):
                                    for image in images:
                                        if image['id'] == video['relationships']['images']['data'][0]['id']:
                                            video_thumb_image = image['attributes']['src']
                                else:
                                    video_thumb_image = None

                                duration = video['attributes']['videoDuration'] / 1000.0 if video['attributes'].get(
                                    'videoDuration') else None

                                # If episode is not yet playable, show playable time in plot
                                if video['attributes'].get('earliestPlayableStart'):
                                    if helper.d.parse_datetime(
                                            video['attributes']['earliestPlayableStart']) > helper.d.get_current_time():
                                        playable = str(
                                            helper.d.parse_datetime(
                                                video['attributes']['earliestPlayableStart']).strftime(
                                                '%d.%m.%Y %H:%M'))
                                        if video['attributes'].get('description'):
                                            plot = helper.language(30002) + playable + ' ' + video['attributes'].get(
                                                'description')
                                        else:
                                            plot = helper.language(30002) + playable
                                    else:
                                        plot = video['attributes'].get('description')
                                else:
                                    plot = video['attributes'].get('description')

                                # discovery+ subscription content check
                                # Check for discovery+ subscription content only if user doesn't have subscription
                                if 'Premium' not in user_packages:
                                    if len(video['attributes']['packages']) > 1:
                                        # Get all available packages in availabilityWindows
                                        for availabilityWindow in video['attributes']['availabilityWindows']:
                                            if availabilityWindow['package'] == 'Free':
                                                # Check if there is ending time for free availability
                                                if availabilityWindow.get('playableEnd'):
                                                    # Check if video is still available for free
                                                    if helper.d.parse_datetime(availabilityWindow[
                                                                                   'playableStart']) < helper.d.get_current_time() < helper.d.parse_datetime(
                                                        availabilityWindow['playableEnd']):
                                                        plot = plot

                                                    else:  # Video is not anymore available for free
                                                        plot = '[discovery+] ' + plot
                                    else:  # Only one package in packages = Premium
                                        plot = '[discovery+] ' + plot

                                episode_info = {
                                    'mediatype': 'episode',
                                    'title': video['attributes'].get('name').lstrip(),
                                    'tvshowtitle': show_title,
                                    'season': video['attributes'].get('seasonNumber'),
                                    'episode': video['attributes'].get('episodeNumber'),
                                    'plot': plot,
                                    'genre': g,
                                    'studio': primaryChannel,
                                    'duration': duration,
                                    'aired': video['attributes'].get('airDate')
                                }

                                # Watched status from discovery+
                                if helper.get_setting('sync_playback'):
                                    if video['attributes']['viewingHistory']['viewed']:
                                        if video['attributes']['viewingHistory']['completed']:  # Watched video
                                            episode_info['playcount'] = '1'
                                            resume = 0
                                            total = duration
                                        else:  # Partly watched video
                                            episode_info['playcount'] = '0'
                                            resume = video['attributes']['viewingHistory']['position'] / 1000.0
                                            total = duration
                                    else:  # Unwatched video
                                        episode_info['playcount'] = '0'
                                        resume = 0
                                        total = 1
                                else:  # Kodis resume data used
                                    resume = None
                                    total = None

                                episode_art = {
                                    'fanart': show_fanart_image,
                                    'thumb': video_thumb_image,
                                    'clearlogo': show_logo_image,
                                    'poster': show_poster_image
                                }

                                # mandatoryParams and no paramerer = list search result videos (Episodes, Specials, Extras)
                                if mandatoryParams and parameter is None:
                                    folder_name = page_data['data']['attributes'].get('title')
                                # parameter = list season
                                elif parameter:
                                    folder_name = show_title + ' / ' + helper.language(30011) + ' ' + str(
                                        video['attributes'].get('seasonNumber'))
                                else:
                                    folder_name = show_title

                                helper.add_item(video['attributes'].get('name').lstrip(), params=params,
                                                info=episode_info,
                                                art=episode_art,
                                                content='episodes', playable=True, resume=resume, total=total,
                                                folder_name=folder_name, sort_method='sort_episodes')

                    # List collections in discoveryplus.com (US) and discoveryplus.in
                    # Browse -> Channel or genre -> Category listing (A-Z, Trending...)
                    if collectionItem['relationships'].get('collection'):
                        for collection in collections:
                            if collection['id'] == collectionItem['relationships']['collection']['data']['id']:
                                if collection['attributes']['component']['id'] == 'content-grid':
                                    if collection['attributes'].get('title') or collection['attributes'].get('name'):

                                        # content-grid name can be title or name
                                        if collection['attributes'].get('title'):
                                            title = collection['attributes']['title']
                                        elif collection['attributes'].get('name'):
                                            title = collection['attributes']['name']
                                        else:
                                            title = ''

                                        params = {
                                            'action': 'list_collection',
                                            'collection_id': collection['id']
                                        }

                                        helper.add_item(title, params,
                                                        content='videos')

                                # discoveryplus.in
                                if collection['attributes']['component']['id'] == 'taxonomy-replica':
                                    # Don't list empty category
                                    if collection.get('relationships'):
                                        # Genres in discoveryplus.in
                                        if collection['relationships'].get('cmpContextLink'):
                                            for link in links:
                                                if collection['relationships']['cmpContextLink']['data']['id'] == link[
                                                    'id']:
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

                                                    for collectionItem2 in collectionItems:
                                                        if collection['relationships']['items']['data'][0]['id'] == \
                                                                collectionItem2['id']:
                                                            if collectionItem2['relationships'].get('image'):
                                                                for image in images:
                                                                    if image['id'] == \
                                                                            collectionItem2['relationships'][
                                                                                'image'][
                                                                                'data'][
                                                                                'id']:
                                                                        thumb_image = image['attributes']['src']
                                                            else:
                                                                thumb_image = None

                                                    category_art = {
                                                        'fanart': thumb_image,
                                                        'thumb': thumb_image
                                                    }

                                                    # Category titles have stored in different places
                                                    if collection['attributes'].get('title'):
                                                        link_title = collection['attributes']['title']
                                                    elif link['attributes'].get('title'):
                                                        link_title = link['attributes']['title']
                                                    elif link['attributes'].get('name'):
                                                        link_title = link['attributes']['name']
                                                    else:
                                                        link_title = None

                                                    helper.add_item(link_title, params, content='videos',
                                                                    art=category_art,
                                                                    folder_name=collection['attributes'].get(
                                                                        'title'))

                    # discoveryplus.com (US) search result 'collections' folder content
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

                                if link['relationships'].get('images'):
                                    for image in images:
                                        if image['id'] == \
                                                link['relationships']['images']['data'][0][
                                                    'id']:
                                            thumb_image = image['attributes']['src']
                                else:
                                    thumb_image = None

                                link_info = {
                                    'plot': link['attributes'].get('description')
                                }

                                link_art = {
                                    'fanart': thumb_image,
                                    'thumb': thumb_image
                                }

                                helper.add_item(link['attributes']['title'], params, info=link_info, content='videos',
                                                art=link_art,
                                                folder_name=page_data['data']['attributes'].get('title'))

        try:
            if page_data['data']['meta']['itemsCurrentPage'] != page_data['data']['meta']['itemsTotalPages']:
                nextPage = page_data['data']['meta']['itemsCurrentPage'] + 1
                params = {
                    'action': 'list_collection',
                    'collection_id': collection_id,
                    'page': nextPage,
                    'parameter': parameter,
                    'mandatoryParams': mandatoryParams
                }
                helper.add_item(helper.language(30019), params, content='tvshows', sort_method='bottom')
        except KeyError:
            pass

    helper.eod()

def search():
    search_query = helper.get_user_input(helper.language(30007))
    if search_query:
        # discoveryplus.com (US)
        if helper.d.locale_suffix == 'us':
            list_page_us('/search/result', search_query)
        else:
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
        if params['setting'] == 'reset_credentials':
            helper.reset_credentials()
        if params['setting'] == 'set_locale':
            helper.set_locale()
    elif 'iptv' in params:
        # Get new token
        helper.d.get_token()

        if params['iptv'] == 'channels':
            """Return JSON-STREAMS formatted data for all live channels"""
            from resources.lib.iptvmanager import IPTVManager
            port = int(params.get('port'))
            IPTVManager(port).send_channels()
        if params['iptv'] == 'epg':
            """Return JSON-EPG formatted data for all live channel EPG data"""
            from resources.lib.iptvmanager import IPTVManager
            port = int(params.get('port'))
            IPTVManager(port).send_epg()
    elif 'action' in params:
        # Get new token
        helper.d.get_token()

        if params['action'] == 'list_page':
            if helper.d.locale_suffix == 'us':
                list_page_us(page_path=params['page_path'])
            elif helper.d.locale_suffix == 'in':
                list_page_in(page_path=params['page_path'])
            else:
                list_page(page_path=params['page_path'])
        elif params['action'] == 'list_favorites':
            if helper.d.locale_suffix == 'in':
                list_favorites_in()
            else:
                list_favorites()
        elif params['action'] == 'list_favorite_watchlist_videos':
            list_favorite_watchlist_videos_in(videoType=params.get('videoType'), playlist=params.get('playlist'))
        elif params['action'] == 'list_collection':
            try:
                list_collection(collection_id=params['collection_id'], page=params['page'],
                                mandatoryParams=params.get('mandatoryParams'), parameter=params.get('parameter'))
            except KeyError:
                list_collection(collection_id=params['collection_id'], page=1,
                                mandatoryParams=params.get('mandatoryParams'), parameter=params.get('parameter'))
        elif params['action'] == 'list_collection_items':
            list_collection_items(collection_id=params['collection_id'], page_path=params['page_path'])
        elif params['action'] == 'play':
            # Play a video from a provided URL.
            helper.play_item(params['video_id'], params['video_type'])
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
            if error.value == 'unauthorized':  # Login error, wrong email or password
                helper.dialog('ok', helper.language(30006), helper.language(30012))
            else:
                helper.dialog('ok', helper.language(30006), error.value)

if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])
