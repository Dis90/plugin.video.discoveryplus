# -*- coding: utf-8 -*-

import sys
import routing

from resources.lib.kodihelper import KodiHelper

base_url = sys.argv[0]
handle = int(sys.argv[1])
helper = KodiHelper(base_url, handle)
plugin = routing.Plugin()

def run():
    try:
        plugin.run()
    except helper.d.DplayError as error:
        if error.value == 'unauthorized':  # Login error, wrong email or password
            helper.dialog('ok', helper.language(30006), helper.language(30012))
        else:
            helper.dialog('ok', helper.language(30006), error.value)

@plugin.route('/')
def list_menu():
    update_setting_defaults()
    helper.check_for_credentials()

    # List menu items (Shows, Categories)
    if helper.d.realm == 'dplusindia':
        helper.add_item(helper.language(30017), url=plugin.url_for(list_page, '/liked-videos'))
        helper.add_item('Watchlist', url=plugin.url_for(list_page, '/watch-later'))
        helper.add_item('Kids', url=plugin.url_for(list_page, '/kids/home'))
        page_data = helper.d.get_menu('/bottom-menu-v3')
    else:
        page_data = helper.d.get_menu('/web-menubar-v2')

    collections = list(filter(lambda x: x['type'] == 'collection', page_data['included']))
    collectionItems = list(filter(lambda x: x['type'] == 'collectionItem', page_data['included']))
    images = list(filter(lambda x: x['type'] == 'image', page_data['included']))
    links = list(filter(lambda x: x['type'] == 'link', page_data['included']))
    routes = list(filter(lambda x: x['type'] == 'route', page_data['included']))

    for data_collection in page_data['data']['relationships']['items']['data']:
        for collectionItem in collectionItems:
            if data_collection['id'] == collectionItem['id']:
                # discoveryplus.com (EU and US) uses links after collectionItems
                # Get only links
                if collectionItem['relationships'].get('link'):
                    for link in links:
                        # Hide unwanted menu links
                        if collectionItem['relationships']['link']['data']['id'] == link['id'] and \
                                link['attributes'][
                                    'kind'] == 'Internal Link' and link['attributes']['name'] not in helper.d.unwanted_menu_items:

                            # Find page path from routes
                            for route in routes:
                                if route['id'] == \
                                        link['relationships']['linkedContentRoutes']['data'][0][
                                            'id']:
                                    next_page_path = route['attributes']['url']

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
                                'icon': thumb_image
                            }

                            # Replace search button url
                            if link['attributes']['name'].startswith('search'):
                                helper.add_item(link['attributes']['title'], url=plugin.url_for(search),
                                                info=link_info, art=link_art)
                            else:
                                helper.add_item(link['attributes']['title'], url=plugin.url_for(list_page, next_page_path),
                                                info=link_info, art=link_art)

                # discovery+ India uses collections after collectionItems
                if collectionItem['relationships'].get('collection'):
                    for collection in collections:
                        if collectionItem['relationships']['collection']['data']['id'] == collection['id']:

                            if collection['attributes']['component']['id'] == 'menu-item':
                                for collectionItem2 in collectionItems:
                                    if collection['relationships']['items']['data'][0]['id'] == collectionItem2['id']:
                                        # Get only links
                                        if collectionItem2['relationships'].get('link'):
                                            for link in links:
                                                # Hide unwanted menu links
                                                if collectionItem2['relationships']['link']['data']['id'] == link[
                                                    'id'] and \
                                                        link['attributes']['kind'] == 'Internal Link' and \
                                                        collection['attributes'][ 'title'] not in helper.d.unwanted_menu_items:

                                                    # Find page path from routes
                                                    for route in routes:
                                                        if route['id'] == \
                                                                link['relationships']['linkedContentRoutes']['data'][0][
                                                                    'id']:
                                                            next_page_path = route['attributes']['url']

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
                                                        'icon': thumb_image
                                                    }
                                                    # Have to use collection title instead link title because some links doesn't have title
                                                    helper.add_item(collection['attributes']['title'],
                                                                    url=plugin.url_for(list_page, next_page_path),
                                                                    info=link_info, art=link_art)

    # Search discoveryplus.in
    if helper.d.realm == 'dplusindia':
        helper.add_item(helper.language(30007), url=plugin.url_for(search))

    # Profiles
    if helper.d.realm != 'dplusindia':
        helper.add_item(helper.language(30036), url=plugin.url_for(list_profiles))

    helper.eod()

@plugin.route('/page<path:page_path>')
def list_page(page_path):
    if helper.d.realm == 'dplusindia':
        list_page_in(page_path=page_path)
    else:
        list_page_us(page_path=page_path)

# discoveryplus.com (US and EU)
def list_page_us(page_path, search_query=None):
    page_data = helper.d.get_page(page_path, search_query=search_query)

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

                        # Browse -> All (EU)
                        if pageItem['relationships'].get('link'):
                            for link in links:
                                if pageItem['relationships']['link']['data']['id'] == link['id']:
                                    list_collection(collection_id=link['relationships']['linkedContent']['data']['id'], page=1)

                        if pageItem['relationships'].get('collection'):
                            for collection in collections:
                                if pageItem['relationships']['collection']['data']['id'] == collection['id']:
                                    # Some collections doesn't have component
                                    if collection['attributes'].get('component'):

                                        # if content-grid after pageItem -> list content (My List)
                                        if collection['attributes']['component']['id'] == 'content-grid':
                                            list_collection(collection_id=collection['id'], page=1)

                                        # discoveryplus.com (US and EU) search result categories (Shows, Episodes, Specials, Collections, Extras)
                                        if collection['attributes']['component']['id'] == 'tabbed-component':
                                            for c in collection['relationships']['items']['data']:
                                                for collectionItem in collectionItems:
                                                    if c['id'] == collectionItem['id']:
                                                        for c2 in collections:
                                                            if collectionItem['relationships']['collection']['data'][
                                                                'id'] == c2['id']:
                                                                if c2['attributes']['component'][
                                                                    'id'] == 'content-grid':
                                                                    # Hide empty collections
                                                                    if c2.get('relationships'):

                                                                        folder_name = helper.language(
                                                                            30007) + ' / ' + search_query

                                                                        # mandatoryParams = pf[query]=mythbusters
                                                                        plugin_url = plugin.url_for(
                                                                            list_collection,
                                                                            collection_id=c2['id'],
                                                                            mandatoryParams=c2['attributes']['component'].get('mandatoryParams'))

                                                                        helper.add_item(c2['attributes']['title'],
                                                                                        url=plugin_url,
                                                                                        content='videos',
                                                                                        folder_name=folder_name)

                                        # Channel livestream when it is only item in page
                                        # discoveryplus.com (US) -> Introducing discovery+ Channels -> channel page live stream
                                        # discoveryplus.com (EU) Network Rail -> Channel -> livestream
                                        if collection['attributes']['component']['id'] == 'player':
                                            if collection.get('relationships'):
                                                for c in collection['relationships']['items']['data']:
                                                    for collectionItem in collectionItems:
                                                        if c['id'] == collectionItem['id']:
                                                            if collectionItem['relationships'].get('channel'):
                                                                for channel in channels:
                                                                    if collectionItem['relationships']['channel'][
                                                                        'data']['id'] == channel['id']:

                                                                        if channel['attributes'].get('hasLiveStream'):

                                                                            channel_info = {
                                                                                'mediatype': 'video',
                                                                                'title': channel['attributes'].get(
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
                                                                                            channel[
                                                                                                'relationships'][
                                                                                                'images']['data']:
                                                                                        if image['id'] == \
                                                                                                channel_images[
                                                                                                    'id']:
                                                                                            if image['attributes'][
                                                                                                'kind'] == 'logo':
                                                                                                channel_logo = \
                                                                                                    image[
                                                                                                        'attributes'][
                                                                                                        'src']
                                                                                            if image['attributes'][
                                                                                                'kind'] == 'default':
                                                                                                fanart_image = \
                                                                                                    image[
                                                                                                        'attributes'][
                                                                                                        'src']

                                                                            channel_art = {
                                                                                'fanart': fanart_image,
                                                                                'thumb': channel_logo if channel_logo else fanart_image
                                                                            }

                                                                            plugin_url = plugin.url_for(play, video_id=channel['id'], video_type='channel')

                                                                            helper.add_item(
                                                                                helper.language(30014) + ' ' +
                                                                                channel['attributes'].get('name'),
                                                                                url=plugin_url,
                                                                                info=channel_info, content='videos',
                                                                                art=channel_art,
                                                                                playable=True,
                                                                                folder_name=collection[
                                                                                    'attributes'].get('title'))

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

                                                plugin_url = plugin.url_for(list_page, next_page_path)

                                                link_art = {}

                                            # All, Channel pages listing (discovery+ Originals, HGTV...)
                                            else:

                                                plugin_url = plugin.url_for(
                                                    list_collection,
                                                    collection_id=link['relationships']['linkedContent']['data']['id'])

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

                                            # Hide Sports -> Schedule link (sports-schedule-link) and
                                            # Olympics -> Schedule link (olympics-schedule-page-link)
                                            if '-schedule-' not in link['attributes']['alias']:

                                                if link['attributes'].get('title'):
                                                    link_title = link['attributes']['title']
                                                elif link['attributes'].get('name'):
                                                    link_title = link['attributes']['name']
                                                else:
                                                    link_title = None

                                                helper.add_item(link_title, url=plugin_url, content='videos', art=link_art,
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
                                                                if taxonomyNode['id'] == \
                                                                        collectionItem['relationships']['taxonomyNode'][
                                                                            'data']['id']:
                                                                    # Find page path from routes
                                                                    for route in routes:
                                                                        if route['id'] == \
                                                                                taxonomyNode['relationships']['routes'][
                                                                                    'data'][0]['id']:
                                                                            next_page_path = route['attributes']['url']

                                                                    plugin_url = plugin.url_for(list_page, next_page_path)

                                                                    helper.add_item(taxonomyNode['attributes']['name'],
                                                                                    url=plugin_url,
                                                                                    content='videos',
                                                                                    folder_name=page['attributes'].get(
                                                                                        'pageMetadataTitle'))

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

                                            # Home -> For You -> categories
                                            # TV Channel -> categories
                                            if collection['attributes']['component']['id'] == 'content-grid':
                                                # Hide empty grids but allow continue watching.
                                                # For unknown reason d+ returns it empty when add-on loads homepage.
                                                if collection.get('relationships') or \
                                                        collection['attributes']['alias'] == 'continue-watching':

                                                    if collection['attributes'].get('title'):

                                                        # mandatoryParams = pf[channel.id]=292&pf[recs.id]=292&pf[recs.type]=channel
                                                        plugin_url = plugin.url_for(
                                                            list_collection,
                                                            collection_id=collection['id'],
                                                            mandatoryParams=collection['attributes']['component'].get('mandatoryParams'))

                                                        helper.add_item(collection['attributes']['title'],
                                                                        url=plugin_url,
                                                                        content='videos',
                                                                        folder_name=page['attributes'].get('pageMetadataTitle'))

                                                    # Home -> For You -> Network logo rail category link
                                                    if collection['attributes']['component'].get('templateId') == 'circle' and \
                                                            collection['attributes']['component'].get('customAttributes') and \
                                                            collection['attributes'].get('title') is None:
                                                        if collection['attributes']['component']['customAttributes'].get('isBroadcastTile') is True:

                                                            plugin_url = plugin.url_for(list_collection, collection_id=collection['id'])

                                                            helper.add_item(helper.language(30040),
                                                                            url=plugin_url,
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

                                                                    # User setting for listing only seasons in shows page
                                                                    if helper.get_setting('seasonsonly') and \
                                                                            c2['attributes']['component'].get('filters') and \
                                                                                        len(c2['attributes']['component']['filters'][0].get('options')) >= 0:
                                                                        list_collection(collection_id=c2['id'],
                                                                                        mandatoryParams=c2['attributes']['component'].get('mandatoryParams'),
                                                                                        page=1)

                                                                    else:
                                                                        # Episodes and Extras (tabbed-content)
                                                                        # You May Also Like (content-grid)
                                                                        # Channel category (d+ US) and Extras on shows that doesn't have episodes (content-grid)
                                                                        if c2['attributes']['component']['id'] == 'tabbed-content' or \
                                                                                c2['attributes']['component']['id'] == 'content-grid':
                                                                            # Hide empty folders
                                                                            if c2.get('relationships'):

                                                                                # mandatoryParams = pf[show.id]=12423
                                                                                plugin_url = plugin.url_for(
                                                                                                    list_collection,
                                                                                                    collection_id=c2['id'],
                                                                                                    mandatoryParams=c2['attributes']['component'].get('mandatoryParams'))

                                                                                helper.add_item(c2['attributes']['title'],
                                                                                                url=plugin_url,
                                                                                                content='videos',
                                                                                                folder_name=page['attributes'].get('pageMetadataTitle'))

                                            # discoveryplus.com (US) -> search -> collections -> list content of collection
                                            if collection['attributes']['component']['id'] == 'playlist':
                                                list_collection(collection_id=collection['id'], page=1)

                                            # discoveryplus.com (US) -> Introducing discovery+ Channels -> channel page live stream
                                            # discoveryplus.com (EU) Network Rail -> Channel -> livestream
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

                                                                                channel_info = {
                                                                                    'mediatype': 'video',
                                                                                    'title': channel['attributes'].get(
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
                                                                                                channel[
                                                                                                    'relationships'][
                                                                                                    'images']['data']:
                                                                                            if image['id'] == \
                                                                                                    channel_images[
                                                                                                        'id']:
                                                                                                if image['attributes'][
                                                                                                    'kind'] == 'logo':
                                                                                                    channel_logo = \
                                                                                                        image[
                                                                                                            'attributes'][
                                                                                                            'src']
                                                                                                if image['attributes'][
                                                                                                    'kind'] == 'default':
                                                                                                    fanart_image = \
                                                                                                        image[
                                                                                                            'attributes'][
                                                                                                            'src']

                                                                                channel_art = {
                                                                                    'fanart': fanart_image,
                                                                                    'thumb': channel_logo if channel_logo else fanart_image
                                                                                }

                                                                                plugin_url = plugin.url_for(play,
                                                                                                            video_id=channel['id'],
                                                                                                            video_type='channel')

                                                                                helper.add_item(
                                                                                    helper.language(30014) + ' ' +
                                                                                    channel['attributes'].get('name'),
                                                                                    url=plugin_url,
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
                    collection = helper.d.get_collections(collection_id=home_collection, page=1)['data']
                except:
                    continue
                if collection['attributes']['component']['id'] == 'carousel':

                    if collection['attributes'].get('title'):
                        title = collection['attributes']['title']
                    else:
                        title = collection['attributes']['name']

                    plugin_url = plugin.url_for(list_collection, collection_id=collection['id'])
                    helper.add_item(title, url=plugin_url, content='videos')

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
                                        list_collection(collection_id=collection['id'], page=1)

                                    if collection['attributes']['component']['id'] == 'mindblown-composite' or \
                                            collection['attributes']['component']['id'] == 'tab-bar':
                                        for collection_relationship in collection['relationships']['items']['data']:
                                            for collectionItem in collectionItems:
                                                if collection_relationship['id'] == collectionItem['id']:
                                                    for c2 in collections:
                                                        if c2['id'] == \
                                                                collectionItem['relationships']['collection']['data'][
                                                                    'id']:

                                                            if c2['attributes']['component'][
                                                                'id'] == 'mindblown-videos-list':
                                                                list_collection(collection_id=c2['id'], page=1)

                                                            # Favorites (Episodes, Shorts, Shows) and Watchlist (Episodes, Shorts)
                                                            if c2['attributes']['component']['id'] == 'tab-bar-item':
                                                                if c2['attributes']['component'].get(
                                                                        'customAttributes'):
                                                                    contentType = \
                                                                        c2['attributes']['component']['customAttributes'][
                                                                            'contentType']
                                                                    if contentType == 'watchlistVideos':
                                                                        plugin_url = plugin.url_for(list_favorite_watchlist_videos_in, playlist='dplus-watchlist-videos')
                                                                    elif contentType == 'watchlistShorts':
                                                                        plugin_url = plugin.url_for(list_favorite_watchlist_videos_in, playlist='dplus-watchlist-shorts')
                                                                    elif contentType == 'favoriteEpisodes':
                                                                        plugin_url = plugin.url_for(list_favorite_watchlist_videos_in, videoType='EPISODE')
                                                                    elif contentType == 'favoriteShorts':
                                                                        plugin_url = plugin.url_for(list_favorite_watchlist_videos_in, videoType='CLIP')
                                                                    elif contentType == 'favoriteShows':
                                                                        plugin_url = plugin.url_for(list_favorite_search_shows_in)

                                                                if c2['attributes'].get('title'):
                                                                    title = c2['attributes']['title']
                                                                else:
                                                                    title = c2['attributes']['name']

                                                                helper.add_item(title, url=plugin_url, content='videos',
                                                                                folder_name=collection['attributes'].get('title'))

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
                                                if collection['attributes'].get('title') or \
                                                        collection['attributes'].get('name'):

                                                    if collection['attributes'].get('title'):
                                                        title = collection['attributes']['title']
                                                    else:
                                                        title = collection['attributes']['name']

                                                    plugin_url = plugin.url_for(list_collection,
                                                                                collection_id=collection['attributes']['alias'])

                                                    helper.add_item(title, url=plugin_url, content='videos',
                                                                    folder_name=page['attributes'].get('pageMetadataTitle') )

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
                                                                            c2['relationships']['items']['data'][0]['id']:

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

                                                                        info = {
                                                                            'title': c2['attributes'].get('title'),
                                                                            'plot': c2['attributes'].get('description')
                                                                        }

                                                                        category_art = {
                                                                            'fanart': thumb_image,
                                                                            'thumb': thumb_image
                                                                        }

                                                                        plugin_url = plugin.url_for(list_page, next_page_path)

                                                                        helper.add_item(c2['attributes']['title'],
                                                                                        url=plugin_url,
                                                                                        info=info,
                                                                                        content='videos',
                                                                                        art=category_art,
                                                                                        folder_name=page[
                                                                                            'attributes'].get(
                                                                                            'pageMetadataTitle') )

                                        # Shows page in discoveryplus.in (Episodes, Shorts)
                                        if collection['attributes']['component']['id'] == 'show-container':
                                            for collection_relationship in collection['relationships']['items']['data']:
                                                for collectionItem in collectionItems:
                                                    if collection_relationship['id'] == collectionItem['id']:
                                                        for c2 in collections:
                                                            if collectionItem['relationships']['collection']['data']['id'] == c2['id']:

                                                                # Don't list empty category
                                                                if c2.get('relationships'):

                                                                    if c2['attributes'].get('name'):
                                                                        if c2['attributes']['name'] == 'blueprint-show-seasons-grid':

                                                                            # mandatoryParams = pf[show.id]=6613
                                                                            plugin_url = plugin.url_for(
                                                                                list_collection,
                                                                                collection_id=c2['id'],
                                                                                mandatoryParams=c2['attributes']['component'].get('mandatoryParams'))

                                                                            helper.add_item('Episodes', url=plugin_url,
                                                                                            content='videos',
                                                                                    folder_name=pages[0]['attributes'].get('title'))

                                                                        if c2['attributes']['name'] == 'blueprint-show-shorts':

                                                                            plugin_url = plugin.url_for(list_collection_items,
                                                                                                        page_path=page_path,
                                                                                                        collection_id=c2['id'])

                                                                            helper.add_item('Shorts', url=plugin_url,
                                                                                            content='videos',
                                                                                            folder_name=pages[0][
                                                                                                'attributes'].get('title') )

                                        # Channels page category links (example Discovery -> Discovery Shows) and 'Explore Shows and Full Episodes' -> BBC
                                        if collection['attributes']['component']['id'] == 'content-grid':
                                            # Hide empty grids (example upcoming events when there is no upcoming events).
                                            if collection.get('relationships'):
                                                if collection['attributes'].get('title'):

                                                    plugin_url = plugin.url_for(list_collection, collection_id=collection['id'])
                                                    helper.add_item(collection['attributes']['title'], url=plugin_url,
                                                                    content='videos',
                                                                    folder_name=page['attributes'].get('pageMetadataTitle'))
                                                # Explore Shows and Full Episodes -> BBC
                                                else:
                                                    list_collection(collection_id=collection['id'],
                                                                    mandatoryParams=collection['attributes'][
                                                                        'component'].get('mandatoryParams'), page=1)

                                        # Channel livestream
                                        if collection['attributes']['component']['id'] == 'channel-hero-player':
                                            for collectionItem in collectionItems:
                                                if collection['relationships']['items']['data'][0]['id'] == \
                                                        collectionItem['id']:
                                                    if collectionItem['relationships'].get('channel'):

                                                        # Channel livestream
                                                        for channel in channels:
                                                            if collectionItem['relationships']['channel']['data']['id'] == \
                                                                            channel['id']:

                                                                channel_info = {
                                                                    'mediatype': 'video',
                                                                    'title': channel['attributes'].get('name'),
                                                                    'plot': channel['attributes'].get('description'),
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

                                                                channel_art = {
                                                                    'fanart': fanart_image,
                                                                    'thumb': channel_logo if channel_logo else fanart_image
                                                                }

                                                                plugin_url = plugin.url_for(play, video_id=channel['id'],
                                                                                            video_type='channel')
                                                                helper.add_item(
                                                                    helper.language(30014) + ' ' + channel[
                                                                        'attributes'].get('name'),
                                                                    url=plugin_url,
                                                                    art=channel_art, info=channel_info,
                                                                    content='videos',
                                                                    playable=True)

                                        # Used in Premium page, Home (Category and OMG Moments!) and Shorts genres content
                                        if collection['attributes']['component']['id'] == 'carousel':

                                            if collection['attributes'].get('title'):
                                                title = collection['attributes']['title']
                                            else:
                                                title = collection['attributes']['name']

                                            plugin_url = plugin.url_for(list_collection, collection_id=collection['id'])
                                            helper.add_item(title, url=plugin_url, content='videos',
                                                            folder_name=page['attributes'].get('pageMetadataTitle'))

                                        # Shorts page categories
                                        if collection['attributes']['component']['id'] == 'all-taxonomies':
                                            for collectionItem in collectionItems:
                                                for collection_relationship in collection['relationships']['items']['data']:
                                                    if collectionItem['id'] == collection_relationship['id']:
                                                        if collectionItem['relationships'].get('collection'):
                                                            for c2 in collections:
                                                                if c2['id'] == \
                                                                        collectionItem['relationships']['collection'][
                                                                            'data']['id']:
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

                                                                                                plugin_url = plugin.url_for(list_page, next_page_path)

                                                                                                helper.add_item(
                                                                                                    taxonomyNode[
                                                                                                        'attributes'][
                                                                                                        'name'],
                                                                                                    content='videos',
                                                                                                    url = plugin_url)

    helper.eod()

@plugin.route('/collection_items<path:page_path>/<collection_id>')
def list_collection_items(page_path, collection_id):
    page_data = helper.d.get_page(page_path)

    collections = list(filter(lambda x: x['type'] == 'collection', page_data['included']))
    collectionItems = list(filter(lambda x: x['type'] == 'collectionItem', page_data['included']))
    images = list(filter(lambda x: x['type'] == 'image', page_data['included']))
    shows = list(filter(lambda x: x['type'] == 'show', page_data['included']))
    videos = list(filter(lambda x: x['type'] == 'video', page_data['included']))
    channels = list(filter(lambda x: x['type'] == 'channel', page_data['included']))
    taxonomyNodes = list(filter(lambda x: x['type'] == 'taxonomyNode', page_data['included']))

    for collection in collections:
        if collection['id'] == collection_id:
            for collection_relationship in collection['relationships']['items']['data']:
                for collectionItem in collectionItems:
                    if collection_relationship['id'] == collectionItem['id']:

                        # List videos (Show -> Shorts in d+ India) can't use list_collection because of missing mandatoryParams
                        if collectionItem['relationships'].get('video'):
                            for video in videos:
                                if collectionItem['relationships']['video']['data']['id'] == video['id']:

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
                                                            # discoveryplus.in has logos in poster
                                                            if helper.d.realm == 'dplusindia':
                                                                if image['attributes']['kind'] == 'poster':
                                                                    show_poster_image = image['attributes']['src']
                                                            else:
                                                                if image['attributes'][
                                                                    'kind'] == 'poster_with_logo':
                                                                    show_poster_image = image['attributes']['src']

                                    g = []
                                    if video['relationships'].get('txGenres'):
                                        for taxonomyNode in taxonomyNodes:
                                            for video_genre in video['relationships']['txGenres']['data']:
                                                if taxonomyNode['id'] == video_genre['id']:
                                                    g.append(taxonomyNode['attributes']['name'])

                                    mpaa = None
                                    if video['attributes'].get('contentRatings'):
                                        for contentRating in video['attributes']['contentRatings']:
                                            if contentRating['system'] == helper.d.contentRatingSystem:
                                                mpaa = contentRating['code']

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

                                    # discovery+ subscription check
                                    # First check if video is available for free
                                    if len(video['attributes']['packages']) > 1:
                                        # Get all available packages in availabilityWindows
                                        for availabilityWindow in video['attributes']['availabilityWindows']:
                                            if availabilityWindow['package'] == 'Free' or availabilityWindow[
                                                'package'] == 'Registered':
                                                # Check if there is ending time for free availability
                                                if availabilityWindow.get('playableEnd'):
                                                    # Check if video is still available for free
                                                    if helper.d.parse_datetime(availabilityWindow[
                                                                                   'playableStart']) < helper.d.get_current_time() < helper.d.parse_datetime(
                                                        availabilityWindow['playableEnd']):
                                                        subscription_needed = False

                                                    else:  # Video is not anymore available for free
                                                        subscription_needed = True
                                    else:  # Only one package in packages = Subscription needed
                                        subscription_needed = True

                                    # Check if user has needed subscription
                                    check = any(x in video['attributes']['packages'] for x in
                                                helper.d.get_user_data()['attributes']['packages'])
                                    if check is True:
                                        subscription_needed = False
                                    else:
                                        subscription_needed = True

                                    if subscription_needed is True:
                                        if plot:
                                            plot = helper.language(30034) + ' ' + plot
                                        else:
                                            plot = helper.language(30034)

                                    # secondaryTitle used in sport events
                                    if video['attributes'].get('secondaryTitle'):
                                        video_title = video['attributes'].get('name').lstrip() + ' - ' + \
                                                      video['attributes']['secondaryTitle'].lstrip()
                                    else:
                                        video_title = video['attributes'].get('name').lstrip()

                                    aired = None
                                    if video['attributes'].get('earliestPlayableStart'):
                                        aired = str(helper.d.parse_datetime(video['attributes']['earliestPlayableStart']))

                                    episode_info = {
                                        'mediatype': 'episode',
                                        'title': video_title,
                                        'tvshowtitle': show_title,
                                        'season': video['attributes'].get('seasonNumber'),
                                        'episode': video['attributes'].get('episodeNumber'),
                                        'plot': plot,
                                        'genre': g,
                                        'studio': primaryChannel,
                                        'duration': duration,
                                        'aired': aired,
                                        'mpaa': mpaa
                                    }

                                    # Watched status from discovery+
                                    menu = []
                                    if helper.get_setting('sync_playback'):
                                        if video['attributes']['viewingHistory']['viewed']:
                                            #if video['attributes']['viewingHistory'].get('completed'):
                                            if 'completed' in video['attributes']['viewingHistory']:
                                                if video['attributes']['viewingHistory']['completed']:  # Watched video
                                                    episode_info['playcount'] = '1'
                                                    resume = 0
                                                    total = duration
                                                    # Mark as unwatched
                                                    menu.append((helper.language(30042),
                                                                 'RunPlugin(plugin://' + helper.addon_name +
                                                                 '/update_playback_progress/' + str(
                                                                     video['id']) + '?position=0' + ')',))
                                                else:  # Partly watched video
                                                    episode_info['playcount'] = '0'
                                                    resume = video['attributes']['viewingHistory']['position'] / 1000.0
                                                    total = duration
                                                    # Reset resume position
                                                    menu.append((helper.language(30044),
                                                                 'RunPlugin(plugin://' + helper.addon_name +
                                                                 '/update_playback_progress/' + str(
                                                                     video['id']) + '?position=0' + ')',))
                                                    # Mark as watched
                                                    menu.append((helper.language(30043),
                                                                 'RunPlugin(plugin://' + helper.addon_name +
                                                                 '/update_playback_progress/' + str(
                                                                     video['id']) + '?position=' + str(video['attributes'][
                                                                     'videoDuration']) + ')',))
                                            else:  # Sometimes 'viewed' is True but 'completed' is missing. Example some Live sports
                                                episode_info['playcount'] = '0'
                                                resume = 0
                                                total = 1
                                        else:  # Unwatched video
                                            episode_info['playcount'] = '0'
                                            resume = 0
                                            total = 1
                                            # Live sport doesn't have videoDuration
                                            if video['attributes'].get('videoDuration'):
                                                # Mark as watched
                                                menu.append((helper.language(30043),
                                                         'RunPlugin(plugin://' + helper.addon_name +
                                                             '/update_playback_progress/' + str(
                                                             video['id']) + '?position=' + str(video['attributes'][
                                                             'videoDuration']) + ')',))
                                    else:  # Kodis resume data used
                                        resume = None
                                        total = None

                                    episode_art = {
                                        'fanart': show_fanart_image,
                                        'thumb': video_thumb_image,
                                        'clearlogo': show_logo_image,
                                        'poster': show_poster_image
                                    }

                                    plugin_url = plugin.url_for(play, video_id=video['id'], video_type=video['attributes']['videoType'])

                                    helper.add_item(video_title, url=plugin_url, info=episode_info, art=episode_art,
                                                    content='episodes', menu=menu, playable=True, resume=resume, total=total,
                                                    folder_name=collection['attributes'].get('title'),
                                                    sort_method='sort_episodes')

    helper.eod()

# Favorite and search shows in discoveryplus.in
@plugin.route('/favorite_shows_in')
def list_favorite_search_shows_in(search_query=None):
    page_data = helper.d.get_favorite_search_shows_in(search_query=search_query)

    images = list(filter(lambda x: x['type'] == 'image', page_data['included']))
    routes = list(filter(lambda x: x['type'] == 'route', page_data['included']))
    taxonomyNodes = list(filter(lambda x: x['type'] == 'taxonomyNode', page_data['included']))

    for show in page_data['data']:
        title = show['attributes']['name'].encode('utf-8')

        # Find page path from routes
        for route in routes:
            if route['id'] == show['relationships']['routes']['data'][0]['id']:
                next_page_path = route['attributes']['url']

        g = []
        if show['relationships'].get('txGenres'):
            for taxonomyNode in taxonomyNodes:
                for show_genre in show['relationships']['txGenres']['data']:
                    if taxonomyNode['id'] == show_genre['id']:
                        g.append(taxonomyNode['attributes']['name'])

        mpaa = None
        if show['attributes'].get('contentRatings'):
            for contentRating in show['attributes']['contentRatings']:
                if contentRating['system'] == helper.d.contentRatingSystem:
                    mpaa = contentRating['code']

        info = {
            'mediatype': 'tvshow',
            'plot': show['attributes'].get('description'),
            'genre': g,
            'season': len(show['attributes'].get('seasonNumbers')),
            'episode': show['attributes'].get('episodeCount'),
            'mpaa': mpaa
        }

        # Add or delete favorite context menu
        if show['attributes']['isFavorite']:
            menu = []
            menu.append((helper.language(30010),
                         'RunPlugin(plugin://' + helper.addon_name + '/delete_favorite/' + str(show['id']) + ')',))
        else:
            menu = []
            menu.append((helper.language(30009),
                         'RunPlugin(plugin://' + helper.addon_name + '/add_favorite/' + str(show['id']) + ')',))

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
                        # discoveryplus.in has logos in poster
                        if helper.d.realm == 'dplusindia':
                            if image['attributes']['kind'] == 'poster':
                                poster_image = image['attributes']['src']
                        else:
                            if image['attributes'][
                                'kind'] == 'poster_with_logo':
                                poster_image = image['attributes']['src']

        show_art = {
            'fanart': fanart_image,
            'thumb': thumb_image,
            'clearlogo': logo_image,
            'poster': poster_image
        }

        if search_query:
            folder_name = helper.language(30007) + ' / ' + search_query
        else:
            folder_name = helper.language(30017) + ' / Shows'

        plugin_url = plugin.url_for(list_page, next_page_path)

        helper.add_item(title, url=plugin_url, info=info, art=show_art, content='tvshows', menu=menu, folder_name=folder_name,
                        sort_method='unsorted')

    helper.eod()

# Favorite and watchlist videos in discoveryplus.in
@plugin.route('/favorite_watchlist_videos_in')
def list_favorite_watchlist_videos_in():
    if plugin.args.get('videoType'):
        page_data = helper.d.get_favorite_watchlist_videos_in(videoType=plugin.args['videoType'][0])
    else:
        page_data = helper.d.get_favorite_watchlist_videos_in(playlist=plugin.args['playlist'][0])

    images = list(filter(lambda x: x['type'] == 'image', page_data['included']))
    shows = list(filter(lambda x: x['type'] == 'show', page_data['included']))
    channels = list(filter(lambda x: x['type'] == 'channel', page_data['included']))
    taxonomyNodes = list(filter(lambda x: x['type'] == 'taxonomyNode', page_data['included']))

    for video in page_data['data']:

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
                            # discoveryplus.in has logos in poster
                            if helper.d.realm == 'dplusindia':
                                if image['attributes']['kind'] == 'poster':
                                    show_poster_image = image['attributes']['src']
                            else:
                                if image['attributes'][
                                    'kind'] == 'poster_with_logo':
                                    show_poster_image = image['attributes']['src']

        g = []
        if video['relationships'].get('txGenres'):
            for taxonomyNode in taxonomyNodes:
                for video_genre in video['relationships']['txGenres']['data']:
                    if taxonomyNode['id'] == video_genre['id']:
                        g.append(taxonomyNode['attributes']['name'])

        mpaa = None
        if video['attributes'].get('contentRatings'):
            for contentRating in video['attributes']['contentRatings']:
                if contentRating['system'] == helper.d.contentRatingSystem:
                    mpaa = contentRating['code']

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

        # discovery+ subscription check
        # First check if video is available for free
        if len(video['attributes']['packages']) > 1:
            # Get all available packages in availabilityWindows
            for availabilityWindow in video['attributes']['availabilityWindows']:
                if availabilityWindow['package'] == 'Free' or availabilityWindow['package'] == 'Registered':
                    # Check if there is ending time for free availability
                    if availabilityWindow.get('playableEnd'):
                        # Check if video is still available for free
                        if helper.d.parse_datetime(availabilityWindow[
                                                       'playableStart']) < helper.d.get_current_time() < helper.d.parse_datetime(
                            availabilityWindow['playableEnd']):
                            subscription_needed = False

                        else:  # Video is not anymore available for free
                            subscription_needed = True
        else:  # Only one package in packages = Subscription needed
            subscription_needed = True

        # Check if user has needed subscription
        check = any(x in video['attributes']['packages'] for x in helper.d.get_user_data()['attributes']['packages'])
        if check is True:
            subscription_needed = False
        else:
            subscription_needed = True

        if subscription_needed is True:
            if plot:
                plot = helper.language(30034) + ' ' + plot
            else:
                plot = helper.language(30034)

        aired = None
        if video['attributes'].get('earliestPlayableStart'):
            aired = str(helper.d.parse_datetime(video['attributes']['earliestPlayableStart']))

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
            'aired': aired,
            'mpaa': mpaa
        }

        # Watched status from discovery+
        menu = []
        if helper.get_setting('sync_playback'):
            if video['attributes']['viewingHistory']['viewed']:
                # if video['attributes']['viewingHistory'].get('completed'):
                if 'completed' in video['attributes']['viewingHistory']:
                    if video['attributes']['viewingHistory']['completed']:  # Watched video
                        episode_info['playcount'] = '1'
                        resume = 0
                        total = duration
                        # Mark as unwatched
                        menu.append((helper.language(30042),
                                     'RunPlugin(plugin://' + helper.addon_name + '/update_playback_progress/' + str(
                                         video['id']) + '?position=0' + ')',))
                    else:  # Partly watched video
                        episode_info['playcount'] = '0'
                        resume = video['attributes']['viewingHistory']['position'] / 1000.0
                        total = duration
                        # Reset resume position
                        menu.append((helper.language(30044),
                                     'RunPlugin(plugin://' + helper.addon_name + '/update_playback_progress/' + str(
                                         video['id']) + '?position=0' + ')',))
                        # Mark as watched
                        menu.append((helper.language(30043),
                                     'RunPlugin(plugin://' + helper.addon_name + '/update_playback_progress/' + str(
                                         video['id']) + '?position=' + str(video['attributes']['videoDuration']) + ')',))
                else:  # Sometimes 'viewed' is True but 'completed' is missing. Example some Live sports
                    episode_info['playcount'] = '0'
                    resume = 0
                    total = 1
            else:  # Unwatched video
                episode_info['playcount'] = '0'
                resume = 0
                total = 1
                # Live sport doesn't have videoDuration
                if video['attributes'].get('videoDuration'):
                    # Mark as watched
                    menu.append((helper.language(30043),
                                 'RunPlugin(plugin://' + helper.addon_name + '/update_playback_progress/' + str(
                                     video['id']) + '?position=' + str(video['attributes']['videoDuration']) + ')',))
        else:  # Kodis resume data used
            resume = None
            total = None

        episode_art = {
            'fanart': show_fanart_image,
            'thumb': video_thumb_image,
            'clearlogo': show_logo_image,
            'poster': show_poster_image
        }

        if plugin.args.get('videoType'):
            folder_name = helper.language(30017)
        else:
            folder_name = 'Watchlist'

        plugin_url = plugin.url_for(play, video_id=video['id'], video_type=video['attributes']['videoType'])

        helper.add_item(video['attributes'].get('name').lstrip(), url=plugin_url, info=episode_info, art=episode_art,
                        content='episodes', menu=menu, playable=True, resume=resume, total=total,
                        folder_name=folder_name, sort_method='sort_episodes')

    helper.eod()

@plugin.route('/collection/<collection_id>')
def list_collection(collection_id, page=1, mandatoryParams=None, parameter=None):
    mandatoryParams = plugin.args['mandatoryParams'][0] if plugin.args.get('mandatoryParams') else mandatoryParams
    parameter = plugin.args['parameter'][0] if plugin.args.get('parameter') else parameter
    page = plugin.args['page'][0] if plugin.args.get('page') else page

    page_data = helper.d.get_collections(collection_id=collection_id, page=page, mandatoryParams=mandatoryParams,
                                         parameter=parameter)

    # Don't try to list empty collection
    if page_data['data'].get('relationships'):

        collections = list(filter(lambda x: x['type'] == 'collection', page_data['included']))
        collectionItems = list(filter(lambda x: x['type'] == 'collectionItem', page_data['included']))
        images = list(filter(lambda x: x['type'] == 'image', page_data['included']))
        shows = list(filter(lambda x: x['type'] == 'show', page_data['included']))
        videos = list(filter(lambda x: x['type'] == 'video', page_data['included']))
        channels = list(filter(lambda x: x['type'] == 'channel', page_data['included']))
        links = list(filter(lambda x: x['type'] == 'link', page_data['included']))
        routes = list(filter(lambda x: x['type'] == 'route', page_data['included']))
        taxonomyNodes = list(filter(lambda x: x['type'] == 'taxonomyNode', page_data['included']))

        # dicoveryplus.com (US and EU) and discoveryplus.in list series season grid
        # Parameter is missing for season listing and shows without seasons (movies, documentaries)
        # So we check that there's seasons listed in data (['filters'][0]['options'])
        if page_data['data']['attributes'].get('component') and \
                page_data['data']['attributes']['component']['id'] == 'tabbed-content' and \
                page_data['data']['attributes']['component'].get('filters') and \
                parameter is None and \
                len(page_data['data']['attributes']['component']['filters'][0].get('options')) > 0:

            # If there's only one season and setting flattentvshows is true -> list videos
            if helper.get_setting('flattentvshows') and \
                    len(page_data['data']['attributes']['component']['filters'][0]['options']) == 1:
                list_collection(collection_id=page_data['data']['id'],
                                page=1,
                                mandatoryParams=page_data['data']['attributes']['component'].get('mandatoryParams'),
                                parameter=page_data['data']['attributes']['component']['filters'][0]['options'][0][
                                    'id'])
            else:
                for option in page_data['data']['attributes']['component']['filters'][0]['options']:
                    title = helper.language(30011) + ' ' + str(option['id'])

                    g = []
                    # Show genres
                    if shows[0]['relationships'].get('txGenres'):
                        for taxonomyNode in taxonomyNodes:
                            for show_genre in shows[0]['relationships']['txGenres']['data']:
                                if taxonomyNode['id'] == show_genre['id']:
                                    g.append(taxonomyNode['attributes']['name'])

                    mpaa = None
                    if shows[0]['attributes'].get('contentRatings'):
                        for contentRating in shows[0]['attributes']['contentRatings']:
                            if contentRating['system'] == helper.d.contentRatingSystem:
                                mpaa = contentRating['code']

                    if shows[0]['relationships'].get('primaryChannel'):
                        for channel in channels:
                            if channel['id'] == shows[0]['relationships']['primaryChannel']['data']['id']:
                                primaryChannel = channel['attributes']['name']
                    else:
                        primaryChannel = None

                    info = {
                        'mediatype': 'season',
                        'tvshowtitle': shows[0]['attributes'].get('name'),
                        'plotoutline': shows[0]['attributes'].get('description'),
                        'plot': shows[0]['attributes'].get('longDescription'),
                        'genre': g,
                        'studio': primaryChannel,
                        'season': len(shows[0]['attributes'].get('seasonNumbers')),
                        'episode': shows[0]['attributes'].get('episodeCount'),
                        'mpaa': mpaa
                    }

                    fanart_image = None
                    thumb_image = None
                    logo_image = None
                    poster_image = None
                    if shows[0]['relationships'].get('images'):
                        for image in images:
                            for show_images in shows[0]['relationships']['images']['data']:
                                if image['id'] == show_images['id']:
                                    if image['attributes']['kind'] == 'default':
                                        fanart_image = image['attributes']['src']
                                        thumb_image = image['attributes']['src']
                                    if image['attributes']['kind'] == 'logo':
                                        logo_image = image['attributes']['src']
                                    # discoveryplus.in has logos in poster
                                    if helper.d.realm == 'dplusindia':
                                        if image['attributes']['kind'] == 'poster':
                                            poster_image = image['attributes']['src']
                                    else:
                                        if image['attributes'][
                                            'kind'] == 'poster_with_logo':
                                            poster_image = image['attributes']['src']

                    show_art = {
                        'fanart': fanart_image,
                        'thumb': thumb_image,
                        'clearlogo': logo_image,
                        'poster': poster_image
                    }

                    if page_data['data']['attributes'].get('title'):
                        folder_name = shows[0]['attributes'].get('name') + ' / ' + page_data['data'][
                            'attributes'].get(
                            'title')
                    else:
                        folder_name = shows[0]['attributes'].get('name')

                    # mandatoryParams = pf[show.id]=12423, parameter = # pf[seasonNumber]=1
                    plugin_url = plugin.url_for(list_collection,
                                                collection_id=page_data['data']['id'],
                                                mandatoryParams=page_data['data']['attributes']['component'].get('mandatoryParams'),
                                                parameter=option['parameter'])

                    helper.add_item(title, url=plugin_url, content='seasons', info=info, art=show_art, folder_name=folder_name,
                                    sort_method='sort_label')

        # content-grid, content-hero etc
        else:

            # Get order of content from page_data['data']
            for collection_relationship in page_data['data']['relationships']['items']['data']:
                for collectionItem in collectionItems:
                    # Match collectionItem id's from collection listing to all collectionItems in data
                    if collection_relationship['id'] == collectionItem['id']:
                        # List shows
                        if collectionItem['relationships'].get('show'):
                            for show in shows:
                                if collectionItem['relationships']['show']['data']['id'] == show['id']:

                                    title = show['attributes']['name'].encode('utf-8')

                                    # Find page path from routes
                                    for route in routes:
                                        if route['id'] == show['relationships']['routes']['data'][0]['id']:
                                            next_page_path = route['attributes']['url']

                                    g = []
                                    # Show genres
                                    if show['relationships'].get('txGenres'):
                                        for taxonomyNode in taxonomyNodes:
                                            for show_genre in show['relationships']['txGenres']['data']:
                                                if taxonomyNode['id'] == show_genre['id']:
                                                    g.append(taxonomyNode['attributes']['name'])

                                    mpaa = None
                                    if show['attributes'].get('contentRatings'):
                                        for contentRating in show['attributes']['contentRatings']:
                                            if contentRating['system'] == helper.d.contentRatingSystem:
                                                mpaa = contentRating['code']

                                    if show['relationships'].get('primaryChannel'):
                                        for channel in channels:
                                            if channel['id'] == show['relationships']['primaryChannel']['data'][
                                                'id']:
                                                primaryChannel = channel['attributes']['name']
                                    else:
                                        primaryChannel = None

                                    info = {
                                        'mediatype': 'tvshow',
                                        'plotoutline': show['attributes'].get('description'),
                                        'plot': show['attributes'].get('longDescription'),
                                        'genre': g,
                                        'studio': primaryChannel,
                                        'season': len(show['attributes'].get('seasonNumbers')),
                                        'episode': show['attributes'].get('episodeCount'),
                                        'mpaa': mpaa
                                    }

                                    # Add or delete favorite context menu
                                    if show['attributes']['isFavorite']:
                                        menu = []
                                        menu.append((helper.language(30010),
                                                     'RunPlugin(plugin://' + helper.addon_name + '/delete_favorite/' + str(
                                                         show['id']) + ')',))
                                    else:
                                        menu = []
                                        menu.append((helper.language(30009),
                                                     'RunPlugin(plugin://' + helper.addon_name + '/add_favorite/' + str(
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
                                                    # discoveryplus.in has logos in poster
                                                    if helper.d.realm == 'dplusindia':
                                                        if image['attributes']['kind'] == 'poster':
                                                            poster_image = image['attributes']['src']
                                                    else:
                                                        if image['attributes']['kind'] == 'poster_with_logo':
                                                            poster_image = image['attributes']['src']

                                    show_art = {
                                        'fanart': fanart_image,
                                        'thumb': thumb_image,
                                        'clearlogo': logo_image,
                                        'poster': poster_image
                                    }

                                    plugin_url = plugin.url_for(list_page, next_page_path)

                                    helper.add_item(title, url=plugin_url, info=info, art=show_art, content='tvshows',
                                                    menu=menu, folder_name=page_data['data']['attributes'].get('title'),
                                                    sort_method='unsorted')

                        # List videos
                        if collectionItem['relationships'].get('video'):
                            for video in videos:
                                # Match collectionItem's video id to all video id's in data
                                if collectionItem['relationships']['video']['data']['id'] == video['id']:

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
                                                            # discoveryplus.in has logos in poster
                                                            if helper.d.realm == 'dplusindia':
                                                                if image['attributes']['kind'] == 'poster':
                                                                    show_poster_image = image['attributes']['src']
                                                            else:
                                                                if image['attributes'][
                                                                    'kind'] == 'poster_with_logo':
                                                                    show_poster_image = image['attributes']['src']

                                    g = []
                                    if video['relationships'].get('txGenres'):
                                        for taxonomyNode in taxonomyNodes:
                                            for video_genre in video['relationships']['txGenres']['data']:
                                                if taxonomyNode['id'] == video_genre['id']:
                                                    g.append(taxonomyNode['attributes']['name'])

                                    mpaa = None
                                    if video['attributes'].get('contentRatings'):
                                        for contentRating in video['attributes']['contentRatings']:
                                            if contentRating['system'] == helper.d.contentRatingSystem:
                                                mpaa = contentRating['code']

                                    # Sport example Tennis
                                    if video['relationships'].get('txSports'):
                                        for taxonomyNode in taxonomyNodes:
                                            if taxonomyNode['id'] == video['relationships']['txSports']['data'][0]['id']:
                                                sport = taxonomyNode['attributes']['name']
                                    # Olympics sport
                                    elif video['relationships'].get('txOlympicssport'):
                                        for taxonomyNode in taxonomyNodes:
                                            if taxonomyNode['id'] == \
                                                    video['relationships']['txOlympicssport']['data'][0]['id']:
                                                sport = taxonomyNode['attributes']['name']
                                    else:
                                        sport = None

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

                                    # discovery+ subscription check
                                    # First check if video is available for free
                                    if len(video['attributes']['packages']) > 1:
                                        # Get all available packages in availabilityWindows
                                        for availabilityWindow in video['attributes']['availabilityWindows']:
                                            if availabilityWindow['package'] == 'Free' or availabilityWindow[
                                                'package'] == 'Registered':
                                                # Check if there is ending time for free availability
                                                if availabilityWindow.get('playableEnd'):
                                                    # Check if video is still available for free
                                                    if helper.d.parse_datetime(availabilityWindow[
                                                                                   'playableStart']) < helper.d.get_current_time() < helper.d.parse_datetime(
                                                        availabilityWindow['playableEnd']):
                                                        subscription_needed = False

                                                    else:  # Video is not anymore available for free
                                                        subscription_needed = True
                                    else:  # Only one package in packages = Subscription needed
                                        subscription_needed = True

                                    # Check if user has needed subscription
                                    check = any(x in video['attributes']['packages'] for x in
                                                helper.d.get_user_data()['attributes']['packages'])
                                    if check is True:
                                        subscription_needed = False
                                    else:
                                        subscription_needed = True

                                    if subscription_needed is True:
                                        if plot:
                                            plot = helper.language(30034) + ' ' + plot
                                        else:
                                            plot = helper.language(30034)

                                    video_title = video['attributes'].get('name').lstrip()
                                    # Sport
                                    if sport:
                                        video_title = sport + ': ' + video_title
                                    # secondaryTitle used in sport events
                                    if video['attributes'].get('secondaryTitle'):
                                        video_title = video_title + ' - ' + \
                                                      video['attributes']['secondaryTitle'].lstrip()

                                    aired = None
                                    if video['attributes'].get('earliestPlayableStart'):
                                        aired = str(helper.d.parse_datetime(video['attributes']['earliestPlayableStart']))

                                    if video['attributes']['videoType'] == 'LIVE':
                                        episode_info = {
                                            'mediatype': 'video',
                                            'title': video_title,
                                            'plot': plot,
                                            'studio': primaryChannel,
                                            'duration': duration,
                                            'aired': aired
                                        }
                                    else:
                                        episode_info = {
                                            'mediatype': 'episode',
                                            'title': video_title,
                                            'tvshowtitle': show_title,
                                            'season': video['attributes'].get('seasonNumber'),
                                            'episode': video['attributes'].get('episodeNumber'),
                                            'plot': plot,
                                            'genre': g,
                                            'studio': primaryChannel,
                                            'duration': duration,
                                            'aired': aired,
                                            'mpaa': mpaa
                                        }

                                    # Watched status from discovery+
                                    menu = []
                                    if helper.get_setting('sync_playback'):
                                        if video['attributes']['viewingHistory']['viewed']:
                                            #if video['attributes']['viewingHistory'].get('completed'):
                                            if 'completed' in video['attributes']['viewingHistory']:
                                                if video['attributes']['viewingHistory']['completed']:  # Watched video
                                                    episode_info['playcount'] = '1'
                                                    resume = 0
                                                    total = duration
                                                    # Mark as unwatched
                                                    menu.append((helper.language(30042),
                                                                 'RunPlugin(plugin://' + helper.addon_name +
                                                                 '/update_playback_progress/' + str(
                                                                     video['id']) + '?position=0' + ')',))
                                                else:  # Partly watched video
                                                    episode_info['playcount'] = '0'
                                                    resume = video['attributes']['viewingHistory']['position'] / 1000.0
                                                    total = duration
                                                    # Reset resume position
                                                    menu.append((helper.language(30044),
                                                                 'RunPlugin(plugin://' + helper.addon_name +
                                                                 '/update_playback_progress/' + str(
                                                                     video['id']) + '?position=0' + ')',))
                                                    # Mark as watched
                                                    menu.append((helper.language(30043),
                                                                 'RunPlugin(plugin://' + helper.addon_name +
                                                                 '/update_playback_progress/' + str(
                                                                     video['id']) + '?position=' + str(video['attributes'][
                                                                    'videoDuration']) + ')',))
                                            else:  # Sometimes 'viewed' is True but 'completed' is missing. Example some Live sports
                                                episode_info['playcount'] = '0'
                                                resume = 0
                                                total = 1
                                        else:  # Unwatched video
                                            episode_info['playcount'] = '0'
                                            resume = 0
                                            total = 1
                                            # Live sport doesn't have videoDuration
                                            if video['attributes'].get('videoDuration'):
                                                # Mark as watched
                                                menu.append((helper.language(30043),
                                                         'RunPlugin(plugin://' + helper.addon_name +
                                                             '/update_playback_progress/' + str(
                                                             video['id']) + '?position=' + str(video['attributes'][
                                                             'videoDuration']) + ')',))
                                    else:  # Kodis resume data used
                                        resume = None
                                        total = None

                                    episode_art = {
                                        'fanart': show_fanart_image,
                                        'thumb': video_thumb_image,
                                        'clearlogo': show_logo_image,
                                        'poster': show_poster_image
                                    }

                                    # mandatoryParams and no parameter = list search result videos (Episodes, Specials, Extras)
                                    if mandatoryParams and parameter is None:
                                        folder_name = page_data['data']['attributes'].get('title')
                                    # parameter = list season
                                    elif parameter:
                                        folder_name = show_title + ' / ' + helper.language(30011) + ' ' + str(
                                            video['attributes'].get('seasonNumber'))
                                    else:
                                        folder_name = show_title

                                    # Use sort_episodes only when episodeNumber is available
                                    if video['attributes'].get('episodeNumber'):
                                        sort_method = 'sort_episodes'
                                    else:
                                        sort_method = 'unsorted'

                                    plugin_url = plugin.url_for(play, video_id=video['id'], video_type=video['attributes']['videoType'])

                                    helper.add_item(video_title, url=plugin_url, info=episode_info, art=episode_art,
                                                    content='episodes', menu=menu, playable=True, resume=resume, total=total,
                                                    folder_name=folder_name, sort_method=sort_method)

                        # Explore -> Live Channels & On Demand Shows, Explore Shows and Full Episodes content in d+ India
                        # Home -> For You -> Network logo rail content in discoveryplus.com (US and EU)
                        if collectionItem['relationships'].get('channel'):
                            for channel in channels:
                                if collectionItem['relationships']['channel']['data']['id'] == channel['id']:
                                    # List channel pages
                                    if channel['relationships'].get('routes'):
                                        # Find page path from routes
                                        for route in routes:
                                            if route['id'] == channel['relationships']['routes']['data'][0]['id']:
                                                next_page_path = route['attributes']['url']

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

                                        channel_art = {
                                            'fanart': fanart_image,
                                            'thumb': channel_logo if channel_logo else fanart_image
                                        }

                                        plugin_url = plugin.url_for(list_page, next_page_path)

                                        helper.add_item(channel['attributes'].get('name'), url=plugin_url, info=channel_info,
                                                        content='videos', art=channel_art,
                                                        folder_name=page_data['data']['attributes'].get('title'),
                                                        sort_method='unsorted')

                                    # List channel livestreams only if there's no route to channel page
                                    elif channel['attributes'].get('hasLiveStream'):

                                        channel_info = {
                                            'mediatype': 'video',
                                            'title': channel['attributes'].get('name'),
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

                                        channel_art = {
                                            'fanart': fanart_image,
                                            'thumb': channel_logo if channel_logo else fanart_image
                                        }

                                        plugin_url = plugin.url_for(play, video_id=channel['id'], video_type='channel')

                                        helper.add_item(
                                            helper.language(30014) + ' ' + channel['attributes'].get('name'),
                                            url=plugin_url, info=channel_info, content='videos', art=channel_art,
                                            playable=True, folder_name=collection['attributes'].get('title'))

                        # List collections in discoveryplus.com (US and EU) and discoveryplus.in

                        # Browse -> Channel or genre -> Category listing (A-Z, Trending...)
                        if collectionItem['relationships'].get('collection'):
                            for collection in collections:
                                if collection['id'] == collectionItem['relationships']['collection']['data']['id']:
                                    if collection['attributes']['component']['id'] == 'content-grid':
                                        if collection['attributes'].get('title') or collection['attributes'].get('name'):

                                            # content-grid name can be title or name
                                            if collection['attributes'].get('title'):
                                                title = collection['attributes']['title']
                                            else:
                                                title = collection['attributes']['name']

                                            plugin_url = plugin.url_for(list_collection, collection_id=collection['id'])

                                            helper.add_item(title, url=plugin_url, content='videos')

                                    # discoveryplus.in
                                    if collection['attributes']['component']['id'] == 'taxonomy-replica':
                                        # Don't list empty category
                                        if collection.get('relationships'):
                                            # Genres in discoveryplus.in
                                            if collection['relationships'].get('cmpContextLink'):
                                                for link in links:
                                                    if collection['relationships']['cmpContextLink']['data']['id'] == link['id']:
                                                        # Find page path from routes
                                                        for route in routes:
                                                            if route['id'] == \
                                                                    link['relationships']['linkedContentRoutes'][
                                                                        'data'][0]['id']:
                                                                next_page_path = route['attributes']['url']

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

                                                        plugin_url = plugin.url_for(list_page, next_page_path)

                                                        helper.add_item(link_title, url=plugin_url, content='videos',
                                                                        art=category_art,
                                                                        folder_name=collection['attributes'].get('title'))

                        # discoveryplus.com (US and EU) search result 'collections' folder content
                        if collectionItem['relationships'].get('link'):
                            for link in links:
                                if collectionItem['relationships']['link']['data']['id'] == link['id']:
                                    # Find page path from routes
                                    for route in routes:
                                        if route['id'] == \
                                                link['relationships']['linkedContentRoutes'][
                                                    'data'][0]['id']:
                                            next_page_path = route['attributes']['url']

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

                                    # Category titles have stored in different places
                                    if collectionItem.get('attributes') and collectionItem['attributes'].get('title'):
                                        link_title = collectionItem['attributes']['title']
                                    elif link['attributes'].get('title'):
                                        link_title = link['attributes']['title']
                                    elif link['attributes'].get('name'):
                                        link_title = link['attributes']['name']
                                    else:
                                        link_title = None

                                    plugin_url = plugin.url_for(list_page, next_page_path)

                                    helper.add_item(link_title, url=plugin_url, info=link_info, content='videos', art=link_art,
                                                    folder_name=page_data['data']['attributes'].get('title'))

                        # Kids -> Superheroes/Heroes We Love discoveryplus.in
                        # Sports -> All Sports discoveryplus.com (EU)
                        # Olympics -> All Sports discoveryplus.com (EU)
                        if collectionItem['relationships'].get('taxonomyNode'):
                            for taxonomyNode in taxonomyNodes:
                                if collectionItem['relationships']['taxonomyNode']['data']['id'] == taxonomyNode['id']:

                                    # Find page path from routes
                                    for route in routes:
                                        if route['id'] == taxonomyNode['relationships']['routes']['data'][0]['id']:
                                            next_page_path = route['attributes']['url']

                                    fanart_image = None
                                    logo_image = None
                                    poster_image = None
                                    if taxonomyNode['relationships'].get('images'):
                                        for image in images:
                                            for taxonomyNode_images in taxonomyNode['relationships']['images']['data']:
                                                if image['id'] == taxonomyNode_images['id']:
                                                    if image['attributes']['kind'] == 'default':
                                                        fanart_image = image['attributes']['src']
                                                    if image['attributes']['kind'] == 'logo':
                                                        logo_image = image['attributes']['src']
                                                    # discoveryplus.in has logos in poster
                                                    if helper.d.realm == 'dplusindia':
                                                        if image['attributes']['kind'] == 'poster':
                                                            poster_image = image['attributes']['src']
                                                    else:
                                                        if image['attributes'][
                                                            'kind'] == 'poster_with_logo':
                                                            poster_image = image['attributes']['src']

                                    art = {
                                        'fanart': fanart_image,
                                        'thumb': logo_image if logo_image else fanart_image,
                                        'poster': poster_image
                                    }

                                    info = {
                                        'plot': taxonomyNode['attributes'].get('description')
                                    }

                                    plugin_url = plugin.url_for(list_page, next_page_path)

                                    helper.add_item(taxonomyNode['attributes']['name'], url=plugin_url, info=info, art=art,
                                                    content='tvshows', sort_method='unsorted')

            try:
                if page_data['data']['meta']['itemsCurrentPage'] != page_data['data']['meta']['itemsTotalPages']:
                    nextPage = page_data['data']['meta']['itemsCurrentPage'] + 1
                    plugin_url = plugin.url_for(list_collection, collection_id=collection_id, page=nextPage,
                                                parameter=parameter, mandatoryParams=mandatoryParams)
                    helper.add_item(helper.language(30019), url=plugin_url, content='tvshows', sort_method='bottom')
            except KeyError:
                pass

    helper.eod()

@plugin.route('/search')
def search():
    search_query = helper.get_user_input(helper.language(30007))
    if search_query:
        if helper.d.realm == 'dplusindia':
            list_favorite_search_shows_in(search_query)
        # discoveryplus.com (US and EU)
        else:
            list_page_us('/search/result', search_query)
    else:
        helper.log('No search query provided.')
        return False

@plugin.route('/list_profiles')
def list_profiles():
    profiles = helper.d.get_profiles()
    avatars = helper.d.get_avatars()
    user_data = helper.d.get_user_data()

    for profile in profiles:

        image_url = None
        for avatar in avatars:
            if avatar['id'] == profile['attributes']['avatarName'].lower():
                image_url = avatar['attributes']['imageUrl']

        art = {
            'icon': image_url
        }

        plugin_url = plugin.url_for(switch_profile, profileId=profile['id'])

        if profile['id'] == user_data['attributes']['selectedProfileId']:
            profile_name = profile['attributes']['profileName'] + ' *'
        elif profile['attributes'].get('pinRestricted'):
            profile_name = profile['attributes']['profileName'] + ' ' + helper.language(30037)
            plugin_url = plugin.url_for(switch_profile,
                                        profileId=profile['id'],
                                        pinRestricted=profile['attributes']['pinRestricted'],
                                        profileName=profile['attributes']['profileName'])
        else:
            profile_name = profile['attributes']['profileName']

        helper.add_item(profile_name, url=plugin_url, art=art)

    helper.eod()

@plugin.route('/add_favorite/<show_id>')
def add_favorite(show_id):
    helper.d.add_or_delete_favorite(method='post', show_id=show_id)
    helper.refresh_list()

@plugin.route('/delete_favorite/<show_id>')
def delete_favorite(show_id):
    helper.d.add_or_delete_favorite(method='delete', show_id=show_id)
    helper.refresh_list()

@plugin.route('/play/<video_id>')
def play(video_id):
    helper.play_item(video_id, plugin.args['video_type'][0])

@plugin.route('/reset_settings')
def reset_settings():
    helper.reset_settings()

@plugin.route('/switch_profile')
def switch_profile():
    if plugin.args.get('pinRestricted'):
        pin = helper.dialog('numeric', helper.language(30006) + ' {}'.format(plugin.args['profileName'][0]))
        if pin:
            try:
                helper.d.switch_profile(plugin.args['profileId'][0], pin)
                # Invalid pin
            except helper.d.DplayError as error:
                helper.dialog('ok', helper.language(30006), error.value)
    else:
        helper.d.switch_profile(plugin.args['profileId'][0])
    helper.refresh_list()

@plugin.route('/update_playback_progress/<video_id>')
def update_playback_progress(video_id):
    helper.d.update_playback_progress(video_id=video_id, position=plugin.args['position'][0])
    helper.refresh_list()

@plugin.route('/iptv/channels')
def iptv_channels():
    helper.d.get_token()
    """Return JSON-STREAMS formatted data for all live channels"""
    from resources.lib.iptvmanager import IPTVManager
    port = int(plugin.args.get('port')[0])
    IPTVManager(port).send_channels()

@plugin.route('/iptv/epg')
def iptv_epg():
    helper.d.get_token()
    """Return JSON-EPG formatted data for all live channel EPG data"""
    from resources.lib.iptvmanager import IPTVManager
    port = int(plugin.args.get('port')[0])
    IPTVManager(port).send_epg()

def update_setting_defaults():
    iptv_channels_uri = helper.get_setting('iptv.channels_uri')
    iptv_epg_uri = helper.get_setting('iptv.epg_uri')

    if iptv_channels_uri != 'plugin://plugin.video.discoveryplus/iptv/channels':
        helper.set_setting('iptv.channels_uri', 'plugin://plugin.video.discoveryplus/iptv/channels')
    if iptv_epg_uri != 'plugin://plugin.video.discoveryplus/iptv/epg':
        helper.set_setting('iptv.epg_uri', 'plugin://plugin.video.discoveryplus/iptv/epg')