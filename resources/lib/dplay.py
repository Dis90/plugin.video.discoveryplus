# -*- coding: utf-8 -*-
"""
A Kodi-agnostic library for Discovery+
"""
import os
import xbmc
import re
import json
import time
import calendar
from datetime import datetime, timedelta, date
import requests
import uuid
import xbmcaddon
import xbmcgui

try: # Python 3
    import http.cookiejar as cookielib
except ImportError: # Python 2
    import cookielib

try: # Python 3
    from urllib.parse import urlparse, urljoin
except ImportError: # Python 2
    from urlparse import urlparse, urljoin

def slugify(text):
    non_url_safe = [' ','"', '#', '$', '%', '&', '+',',', '/', ':', ';', '=', '?','@', '[', '\\', ']', '^', '`','{', '|', '}', '~', "'"]
    non_url_safe_regex = re.compile(r'[{}]'.format(''.join(re.escape(x) for x in non_url_safe)))
    text = non_url_safe_regex.sub('', text).strip()
    text = u'_'.join(re.split(r'\s+', text))
    return text

class Dplay(object):
    def __init__(self, settings_folder, country, logging_prefix, numresults, cookiestxt_file, us_uhd):
        self.logging_prefix = logging_prefix
        self.numResults = numresults
        self.locale_suffix = country
        self.client_id = str(uuid.uuid1())
        self.device_id = self.client_id.replace("-", "")
        self.us_uhd = us_uhd

        if self.locale_suffix == 'gb':
            self.api_url = 'https://eu1-prod-direct.discoveryplus.com'
            self.realm = 'dplay'
            self.site_headers = {
                'x-disco-params': 'realm=dplay,siteLookupKey=dplus_uk,bid=dplus,hn=www.discoveryplus.com,hth=gb,features=ar',
                'x-disco-client': 'WEB:UNKNOWN:dplus_us:1.25.0'
            }
        elif self.locale_suffix == 'us':
            self.api_url = 'https://us1-prod-direct.discoveryplus.com'
            self.realm = 'go'
            self.site_headers = {
                'x-disco-params': 'realm=go,siteLookupKey=dplus_us,bid=dplus,hn=www.discoveryplus.com,features=ar',
                'x-disco-client': 'WEB:UNKNOWN:dplus_us:1.25.0'
            }
        elif self.locale_suffix == 'in':
            self.api_url = 'https://ap2-prod-direct.discoveryplus.in'
            self.realm = 'dplusindia'
            self.site_headers = {
                'x-disco-params': 'realm=dplusindia,hn=www.discoveryplus.in',
                'x-disco-client': 'WEB:UNKNOWN:dplus-india:prod'
            }
        else:
            self.api_url = 'https://eu1-prod-direct.discoveryplus.com'
            self.realm = 'dplay'
            self.site_headers = {
                'x-disco-params': 'realm=dplay,siteLookupKey=dplus_{locale},bid=dplus,hn=www.discoveryplus.com,hth={locale},features=ar'.format(locale=self.locale_suffix),
                'x-disco-client': 'WEB:UNKNOWN:dplus_us:1.25.0'
            }

        self.http_session = requests.Session()
        self.settings_folder = settings_folder
        self.tempdir = os.path.join(settings_folder, 'tmp')
        self.unwanted_menu_items = ('epg')
        if not os.path.exists(self.tempdir):
            os.makedirs(self.tempdir)

        self.cookie_jar = cookielib.MozillaCookieJar(cookiestxt_file)

        try:
            self.cookie_jar.load(ignore_discard=True, ignore_expires=True)
        except IOError:
            pass
        self.http_session.cookies = self.cookie_jar

    class DplayError(Exception):
        def __init__(self, value):
            self.value = value

        def __str__(self):
            return repr(self.value)

    def log(self, string):
        msg = '%s: %s' % (self.logging_prefix, string)
        xbmc.log(msg=msg, level=xbmc.LOGDEBUG)

    def make_request(self, url, method, params=None, payload=None, headers=None, text=False):
        """Make an HTTP request. Return the response."""
        self.log('Request URL: %s' % url)
        self.log('Method: %s' % method)
        self.log('Params: %s' % params)
        self.log('Payload: %s' % payload)
        self.log('Headers: %s' % headers)
        try:
            if method == 'get':
                req = self.http_session.get(url, params=params, headers=headers)
            elif method == 'put':
                req = self.http_session.put(url, params=params, data=payload, headers=headers)
            elif method == 'delete':
                req = self.http_session.delete(url, params=params, data=payload, headers=headers)
            elif method == 'patch':
                req = self.http_session.patch(url, params=params, data=payload, headers=headers)
            else:  # post
                req = self.http_session.post(url, params=params, data=payload, headers=headers)
            self.log('Response code: %s' % req.status_code)
            self.log('Response: %s' % req.content)
            try:
                self.cookie_jar.save(ignore_discard=True, ignore_expires=True)
            except IOError:
                pass
            self.raise_dplay_error(req.content)
            if text:
                return req.text
            return req.content

        except requests.exceptions.ConnectionError as error:
            self.log('Connection Error: - %s' % error)
            raise
        except requests.exceptions.RequestException as error:
            self.log('Error: - %s' % error)
            raise

    def raise_dplay_error(self, response):
        try:
            response = json.loads(response)
            #if isinstance(error, dict):
            if 'errors' in response:
                for error in response['errors']:
                    if 'code' in error.keys():
                        if error['code'] == 'unauthorized': # Login error, wrong email or password
                            raise self.DplayError(error['code']) # Detail is empty in login error
                        else:
                            raise self.DplayError(error['detail'])

        except KeyError:
            pass
        except ValueError:  # when response is not in json
            pass

    # Return users country
    def get_country(self):
        r = requests.get('https://www.discoveryplus.com')
        path = urlparse(r.url).path
        country = path.replace('/', '')

        if country is '':
            if r.url == 'https://www.discoveryplus.in/':
                country = 'in'
            elif r.url == 'https://www.discoveryplus.com/':
                country = 'us'

        return country

    def get_token(self):
        url = '{api_url}/token'.format(api_url=self.api_url)

        params = {
            'realm': self.realm,
            'deviceId': self.device_id,
            'shortlived': 'true'
        }

        return self.make_request(url, 'get', params=params, headers=self.site_headers)

    def get_user_data(self):
        url = '{api_url}/users/me'.format(api_url=self.api_url)

        data = self.make_request(url, 'get')
        return json.loads(data)['data']

    def get_avatars(self):
        url = '{api_url}/avatars'.format(api_url=self.api_url)

        data = self.make_request(url, 'get', headers=self.site_headers)
        return json.loads(data)['data']

    def get_profiles(self):
        url = '{api_url}/users/me/profiles'.format(api_url=self.api_url)

        data = self.make_request(url, 'get', headers=self.site_headers)
        return json.loads(data)['data']

    def switch_profile(self, profileId, pin=None):
        jsonPayload = {
                'data': {
                    'attributes': {
                        'selectedProfileId': profileId
                    },
                    'id': self.get_user_data()['id'],
                    'type': 'user'
                }
        }

        if pin:
            url = '{api_url}/users/me/profiles/switchProfile'.format(api_url=self.api_url)
            jsonPayload['data']['attributes']['profilePin'] = pin
            return self.make_request(url, 'post', payload=json.dumps(jsonPayload), headers=self.site_headers)
        else:
            url = '{api_url}/users/me'.format(api_url=self.api_url)
            return self.make_request(url, 'patch', payload=json.dumps(jsonPayload), headers=self.site_headers)

    def get_menu(self, menu):
        url = '{api_url}/cms/collections{menu}'.format(api_url=self.api_url, menu=menu)

        params = {
            'include': 'default'
        }

        data = json.loads(self.make_request(url, 'get', params=params, headers=self.site_headers))
        return data

    def get_config_in(self):
        url = '{api_url}/cms/configs/client-config-pwa'.format(api_url=self.api_url)

        data = json.loads(self.make_request(url, 'get', headers=self.site_headers))
        return data

    def get_page(self, path, search_query=None):
        url = '{api_url}/cms/routes{path}'.format(api_url=self.api_url, path=path)

        params = {
            'include': 'default'
        }

        # discoveryplus.com (US) and discoveryplus.in
        if self.locale_suffix == 'us' or self.locale_suffix == 'in':
            params['decorators'] = 'viewingHistory,isFavorite'
        else:
            params['decorators'] = 'viewingHistory,isFavorite,playbackAllowed'

        # discoveryplus.com (US and EU)
        if search_query:
            params['contentFilter[query]'] = search_query

        data = json.loads(self.make_request(url, 'get', params=params, headers=self.site_headers))
        return data

    def get_collections(self, collection_id, page, mandatoryParams=None, parameter=None):
        mandatoryParams = None if mandatoryParams == 'None' else mandatoryParams
        parameter = None if parameter == 'None' else parameter

        if mandatoryParams and parameter:
            url = '{api_url}/cms/collections/{collection_id}?{mandatoryParams}&{parameter}'.format(api_url=self.api_url, collection_id=collection_id, mandatoryParams=mandatoryParams, parameter=parameter)
        elif mandatoryParams is None and parameter:
            url = '{api_url}/cms/collections/{collection_id}?{parameter}'.format(api_url=self.api_url, collection_id=collection_id, parameter=parameter)
        elif mandatoryParams and parameter is None:
            url = '{api_url}/cms/collections/{collection_id}?{mandatoryParams}'.format(api_url=self.api_url, collection_id=collection_id, mandatoryParams=mandatoryParams)
        else:
            url = '{api_url}/cms/collections/{collection_id}'.format(api_url=self.api_url, collection_id=collection_id)

        params = {
            'include': 'default',
            'page[items.number]': page,
            'page[items.size]': self.numResults
        }

        if self.locale_suffix == 'us' or self.locale_suffix == 'in':
            params['decorators'] = 'viewingHistory,isFavorite'
        else:
            params['decorators'] = 'viewingHistory,isFavorite,playbackAllowed'

        data = json.loads(self.make_request(url, 'get', params=params, headers=self.site_headers))
        return data

    def get_search_shows_in(self, search_query):
        url = '{api_url}/content/shows'.format(api_url=self.api_url)

        params = {
            'decorators': 'isFavorite',
            'include': 'images,contentPackages,taxonomyNodes',
            'page[size]': 100,
            'query': search_query
        }

        data = json.loads(self.make_request(url, 'get', params=params))
        return data

    def get_watchlist_in(self, playlist):
        url = '{api_url}/content/videos'.format(api_url=self.api_url)
        params = {
            'decorators': 'viewingHistory,isFavorite',
            'include': 'images,contentPackages,show,genres,primaryChannel,taxonomyNodes',
            'filter[playlist]': playlist,
            'page[size]': 100,
            'page[number]': 1
        }

        data = json.loads(self.make_request(url, 'get', params=params, headers=self.site_headers))
        return data

    def get_favorites_in(self):
        url = '{api_url}/content/shows'.format(api_url=self.api_url)
        params = {
            'decorators': 'isFavorite',
            'include': 'images,contentPackages,taxonomyNodes',
            'filter[isFavorite]': 'true',
            'page[size]': 100,
            'page[number]': 1
        }

        data = json.loads(self.make_request(url, 'get', params=params, headers=self.site_headers))
        return data

    def get_favorite_videos_in(self, videoType):
        url = '{api_url}/content/videos'.format(api_url=self.api_url)
        params = {
            'decorators': 'viewingHistory,isFavorite',
            'include': 'images,contentPackages,show,genres,primaryChannel,taxonomyNodes',
            'filter[isFavorite]': 'true',
            'page[size]': 100,
            'page[number]': 1,
            'filter[videoType]': videoType
        }

        data = json.loads(self.make_request(url, 'get', params=params, headers=self.site_headers))
        return data

    def update_playback_progress(self, method, video_id, position):
        url = '{api_url}/playback/v2/report/video/{video_id}'.format(api_url=self.api_url, video_id=video_id)

        params = {
            'position': position
        }

        return self.make_request(url, method, params=params)

    def get_current_episode_info(self, video_id):
        url = '{api_url}/content/videos/{video_id}'.format(api_url=self.api_url, video_id=video_id)

        params = {
            'include': 'primaryChannel,ratingDescriptors,show.images,ratings.images,genres,ratings,images,show,ratingDescriptors.images'
        }

        data = json.loads(self.make_request(url, 'get', params=params, headers=self.site_headers))
        return data

    def get_next_episode_info(self, current_video_id):
        url = '{api_url}/cms/recommendations/nextVideos'.format(api_url=self.api_url)

        params = {
            'algorithm': 'naturalOrder',
            'include': 'images,primaryChannel,contentPackages,show,show.images,ratings,ratings.images,genres',
            'videoId': current_video_id
        }

        data = json.loads(self.make_request(url, 'get', params=params, headers=self.site_headers))
        return data

    def add_or_delete_favorite(self, method, show_id):
        # POST for adding and DELETE for delete
        url = '{api_url}/users/me/favorites/show/{show_id}'.format(api_url=self.api_url, show_id=show_id)

        return self.make_request(url, method, headers=self.site_headers)

    def get_channels(self):
        page_data = self.get_page('/epg')

        collections = list(filter(lambda x: x['type'] == 'collection', page_data['included']))
        collectionItems = list(filter(lambda x: x['type'] == 'collectionItem', page_data['included']))

        channels_list = []

        current_day = datetime.today().strftime('%Y-%m-%d')

        for collection in collections:
            if collection['attributes']['alias'] == 'epg-listing-wrapper':
                for collection_relationships in collection['relationships']['items']['data']:
                    for collectionItem in collectionItems:
                        if collection_relationships['id'] == collectionItem['id']:

                            epg_page_data = self.get_collections(
                                collection_id=collectionItem['relationships']['collection']['data']['id'], page=1,
                                parameter='pf[day]={current_day}'.format(current_day=current_day))
                            channels = list(filter(lambda x: x['type'] == 'channel', epg_page_data['included']))
                            images = list(filter(lambda x: x['type'] == 'image', epg_page_data['included']))

                            for channel in channels:
                                if channel['attributes']['hasLiveStream']:
                                    url = 'plugin://plugin.video.discoveryplus/?action=play&video_id={channel_id}&video_type=channel'.format(
                                        channel_id=channel['id'])

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

                                    channels_list.append(dict(
                                        id='%s@%s' % (channel['id'], slugify(
                                            xbmcaddon.Addon(id='plugin.video.discoveryplus').getAddonInfo(
                                                'name'))),
                                        name=channel['attributes']['name'],
                                        logo=channel_logo if channel_logo else fanart_image,
                                        stream=url
                                    ))


        return channels_list

    def get_channels_us(self):
        page_data = self.get_page('/home')

        collections = list(filter(lambda x: x['type'] == 'collection', page_data['included']))
        collectionItems = list(filter(lambda x: x['type'] == 'collectionItem', page_data['included']))
        channels = list(filter(lambda x: x['type'] == 'channel', page_data['included']))
        images = list(filter(lambda x: x['type'] == 'image', page_data['included']))

        channels_list = []

        for collection in collections:
            # Introducing discovery+ Channels - Category
            if collection['attributes']['alias'] == 'home-rail-jip-channels':
                for c in collection['relationships']['items']['data']:
                    for collectionItem in collectionItems:
                        if c['id'] == collectionItem['id']:
                            if collectionItem['relationships'].get('channel'):
                                for channel in channels:
                                    if \
                                            collectionItem['relationships']['channel']['data'][
                                                'id'] == channel['id']:

                                        if channel['attributes']['hasLiveStream']:
                                            url = 'plugin://plugin.video.discoveryplus/?action=play&video_id={channel_id}&video_type=channel'.format(
                                                channel_id=channel['id'])

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

                                            channels_list.append(dict(
                                                id='%s@%s' % (channel['id'], slugify(
                                                    xbmcaddon.Addon(id='plugin.video.discoveryplus').getAddonInfo(
                                                        'name'))),
                                                name=channel['attributes']['name'],
                                                logo=channel_logo if channel_logo else fanart_image,
                                                stream=url
                                            ))

        return channels_list

    def get_channels_in(self):
        page_data = self.get_page('/explore-v2')

        collections = list(filter(lambda x: x['type'] == 'collection', page_data['included']))
        collectionItems = list(filter(lambda x: x['type'] == 'collectionItem', page_data['included']))
        channels = list(filter(lambda x: x['type'] == 'channel', page_data['included']))
        images = list(filter(lambda x: x['type'] == 'image', page_data['included']))

        channels_list = []

        for collection in collections:
            if collection['attributes']['alias'] == 'explore-national-live-channels-list':
                for c in collection['relationships']['items']['data']:
                    for collectionItem in collectionItems:
                        if c['id'] == collectionItem['id']:
                            if collectionItem['relationships'].get('channel'):
                                for channel in channels:
                                    if \
                                            collectionItem['relationships']['channel']['data'][
                                                'id'] == channel['id']:

                                        if channel['attributes']['hasLiveStream']:
                                            url = 'plugin://plugin.video.discoveryplus/?action=play&video_id={channel_id}&video_type=channel'.format(
                                                channel_id=channel['id'])

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

                                            channels_list.append(dict(
                                                id='%s@%s' % (channel['id'], slugify(
                                                    xbmcaddon.Addon(id='plugin.video.discoveryplus').getAddonInfo(
                                                        'name'))),
                                                name=channel['attributes']['name'],
                                                logo=channel_logo if channel_logo else fanart_image,
                                                stream=url
                                            ))

        return channels_list

    def get_epg(self):
        from collections import defaultdict
        epg = defaultdict(list)

        page_data = self.get_page('/epg')

        collections = list(filter(lambda x: x['type'] == 'collection', page_data['included']))
        collectionItems = list(filter(lambda x: x['type'] == 'collectionItem', page_data['included']))

        for collection in collections:
            if collection['attributes']['alias'] == 'epg-listing-wrapper':
                for collection_relationships in collection['relationships']['items']['data']:
                    for collectionItem in collectionItems:
                        if collection_relationships['id'] == collectionItem['id']:
                            if collectionItem['relationships'].get('collection'):

                                # Get daily epg per channel
                                for option in collection['attributes']['component']['filters'][0]['options']:
                                    epg_page_data = self.get_collections(
                                        collection_id=collectionItem['relationships']['collection']['data']['id'],
                                        page=1,
                                        parameter=option['parameter'])

                                    # It is possible that channel doesn't have EPG for requested day
                                    if epg_page_data.get('included'):

                                        collectionItems2 = list(
                                            filter(lambda x: x['type'] == 'collectionItem', epg_page_data['included']))
                                        channels = list(
                                            filter(lambda x: x['type'] == 'channel', epg_page_data['included']))
                                        images = list(filter(lambda x: x['type'] == 'image', epg_page_data['included']))
                                        videos = list(filter(lambda x: x['type'] == 'video', epg_page_data['included']))
                                        taxonomyNodes = list(filter(lambda x: x['type'] == 'taxonomyNode', epg_page_data['included']))

                                        for channel in channels:
                                            if channel['attributes']['hasLiveStream']:
                                                for collectionItem2 in collectionItems2:
                                                    for video in videos:
                                                        if video['id'] == \
                                                                collectionItem2['relationships']['video']['data'][
                                                                    'id']:

                                                            fanart_image = None
                                                            if video['relationships'].get('images'):
                                                                for image in images:
                                                                    for video_images in \
                                                                    video['relationships']['images'][
                                                                        'data']:
                                                                        if image['id'] == video_images['id']:
                                                                            if image['attributes']['kind'] == 'default':
                                                                                fanart_image = image['attributes'][
                                                                                    'src']

                                                            channel_id = '%s@%s' % (channel['id'], slugify(
                                                                xbmcaddon.Addon(
                                                                    id='plugin.video.discoveryplus').getAddonInfo(
                                                                    'name')))

                                                            # Sport events
                                                            if video['relationships'].get('txSports'):
                                                                subtitle = video['attributes'].get('secondaryTitle')
                                                                for taxonomyNode in taxonomyNodes:
                                                                    if taxonomyNode['id'] == video['relationships']['txSports']['data'][0]['id']:
                                                                        if video['attributes'].get('secondaryTitle'):
                                                                            subtitle = taxonomyNode['attributes'][
                                                                                           'name'] + ' - ' + \
                                                                                       video['attributes']['secondaryTitle']
                                                                        else:
                                                                            subtitle = taxonomyNode['attributes'][
                                                                                'name']

                                                                epg[channel_id].append(dict(
                                                                    start=video['attributes'].get('scheduleStart'),
                                                                    stop=video['attributes'].get('scheduleEnd'),
                                                                    title=video['attributes'].get('name'),
                                                                    description=video['attributes'].get('description'),
                                                                    subtitle=subtitle,
                                                                    episode='',
                                                                    image=fanart_image
                                                                ))
                                                            # TV shows
                                                            else:
                                                                if video['attributes']['customAttributes'].get(
                                                                        'listingSeasonNumber') and video['attributes'][
                                                                    'customAttributes'].get('listingEpisodeNumber'):
                                                                    episode = 'S' + str(
                                                                        video['attributes']['customAttributes'][
                                                                            'listingSeasonNumber']) + 'E' + str(
                                                                        video['attributes']['customAttributes'][
                                                                            'listingEpisodeNumber'])
                                                                else:
                                                                    episode = ''

                                                                # Don't add name to subtitle if it same as listingShowName
                                                                if video['attributes']['customAttributes'].get(
                                                                        'listingShowName') and video['attributes'].get(
                                                                    'name'):
                                                                    if video['attributes']['customAttributes'][
                                                                        'listingShowName'] == \
                                                                            video['attributes']['name']:
                                                                        subtitle = ''
                                                                    else:
                                                                        subtitle = video['attributes']['name']
                                                                else:
                                                                    subtitle = ''

                                                                epg[channel_id].append(dict(
                                                                    start=video['attributes'].get('scheduleStart'),
                                                                    stop=video['attributes'].get('scheduleEnd'),
                                                                    title=video['attributes']['customAttributes'].get(
                                                                        'listingShowName'),
                                                                    description=video['attributes'].get('description'),
                                                                    subtitle=subtitle,
                                                                    episode=episode,
                                                                    image=fanart_image
                                                            ))


        return epg

    # discoveryplus.com (US) doesn't have EPG so we use channel name as show name
    def get_epg_us(self):
        from collections import defaultdict
        epg = defaultdict(list)

        today = datetime.utcnow().date()
        start = datetime(today.year, today.month, today.day).astimezone()
        end = start + timedelta(1)

        for channel in self.get_channels_us():
            epg[channel['id']].append(dict(
                start=start.isoformat(),
                stop=end.isoformat(),
                title=channel['name']
            ))
        return epg

    # discoveryplus.in doesn't have EPG so we use channel name as show name
    def get_epg_in(self):
        from collections import defaultdict
        epg = defaultdict(list)

        today = datetime.utcnow().date()
        start = datetime(today.year, today.month, today.day).astimezone()
        end = start + timedelta(1)

        for channel in self.get_channels_in():
            epg[channel['id']].append(dict(
                start=start.isoformat(),
                stop=end.isoformat(),
                title=channel['name']
            ))
        return epg

    def get_stream(self, video_id, video_type):
        stream = {}

        screenHeight = xbmcgui.getScreenHeight()
        screenWidth = xbmcgui.getScreenWidth()

        # Use drmSupported:false for UHD streams. For now playback is only tested to kinda work when drm and
        # InputStreamAdaptive is disabled from add-on settings. It is possible that drm/mpd stream also works on Android devices.
        # All videos doesn't work without drm/mpd stream. That is why drm is enabled if US UHD is not enabled.
        # Also subtitles seems to be broken in HLS or Kodi doesn't like them.
        # Change drmSupported:true to false if you want to play videos without drm.
        if self.us_uhd:
            hwDecoding = ['H264','H265']
            platform = 'firetv'
            drmSupported = 'false'
        else:
            hwDecoding = []
            platform = 'desktop'
            drmSupported = 'true'

        if self.locale_suffix == 'us':
            product = 'dplus_us'
        elif self.locale_suffix == 'in':
            # this is maybe wrong or not needed
            product = 'dplusindia'
        else:
            product = 'dplus_emea'

        jsonPayload = {
            'deviceInfo': {
                'adBlocker': 'true',
                'drmSupported': drmSupported,
                'hwDecodingCapabilities': hwDecoding,
                'screen':{
                    'width':screenWidth,
                    'height':screenHeight
                },
                'player':{
                    'width':screenWidth,
                    'height':screenHeight
                }
            },
            'wisteriaProperties':{
                'advertiser': {
                    'firstPlay': 0,
                    'fwIsLat': 0
                },
                'device':{
                    'browser':{
                        'name': 'chrome',
                        'version': '96.0.4664.55'
                    },
                    'type': platform
                },
                'platform': platform,
                'product': product,
                'sessionId': self.client_id,
                'streamProvider': {
                    'suspendBeaconing': 0,
                    'hlsVersion': 7,
                    'pingConfig': 1
                }
            }
        }

        if video_type == 'channel':
            jsonPayload['channelId'] = video_id
            url = '{api_url}/playback/v3/channelPlaybackInfo'.format(api_url=self.api_url)
        else:
            jsonPayload['videoId'] = video_id
            url = '{api_url}/playback/v3/videoPlaybackInfo'.format(api_url=self.api_url)

        data_dict = json.loads(self.make_request(url, 'post', headers=self.site_headers, payload=json.dumps(jsonPayload)))['data']

        stream['url'] = data_dict['attributes']['streaming'][0]['url']
        stream['type'] = data_dict['attributes']['streaming'][0]['type']

        if data_dict['attributes']['streaming'][0]['protection']['drmEnabled']:
            stream['license_url'] = data_dict['attributes']['streaming'][0]['protection']['schemes']['widevine']['licenseUrl']
            stream['drm_token'] = data_dict['attributes']['streaming'][0]['protection'].get('drmToken')
        stream['drm_enabled'] = data_dict['attributes']['streaming'][0]['protection']['drmEnabled']

        return stream

    def parse_datetime(self, date):
        """Parse date string to datetime object."""
        date_time_format = '%Y-%m-%dT%H:%M:%SZ'
        datetime_obj = datetime(*(time.strptime(date, date_time_format)[0:6]))

        return self.utc_to_local(datetime_obj)

    def get_current_time(self):
        """Return the current local time."""
        return datetime.now()

    def utc_to_local(self, utc_dt):
        # get integer timestamp to avoid precision lost
        timestamp = calendar.timegm(utc_dt.timetuple())
        local_dt = datetime.fromtimestamp(timestamp)
        assert utc_dt.resolution >= timedelta(microseconds=1)
        return local_dt.replace(microsecond=utc_dt.microsecond)