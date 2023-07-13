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
import xbmcvfs

try: # Python 3
    import http.cookiejar as cookielib
except ImportError: # Python 2
    import cookielib

try: # Python 3
    from urllib.parse import urlparse, urljoin, quote_plus
except ImportError: # Python 2
    from urlparse import urlparse, urljoin
    from urllib import quote_plus

def slugify(text):
    non_url_safe = [' ','"', '#', '$', '%', '&', '+',',', '/', ':', ';', '=', '?','@', '[', '\\', ']', '^', '`','{', '|', '}', '~', "'"]
    non_url_safe_regex = re.compile(r'[{}]'.format(''.join(re.escape(x) for x in non_url_safe)))
    text = non_url_safe_regex.sub('', text).strip()
    text = u'_'.join(re.split(r'\s+', text))
    return text

class Dplay(object):
    def __init__(self, settings_folder, logging_prefix, numresults, cookiestxt, cookiestxt_file, us_uhd, drm_supported, kodi_version):
        self.logging_prefix = logging_prefix
        self.numResults = numresults
        self.client_id = str(uuid.uuid1())
        self.device_id = self.client_id.replace("-", "")
        self.us_uhd = us_uhd
        self.drm_supported = drm_supported

        self.http_session = requests.Session()
        self.settings_folder = settings_folder
        self.unwanted_menu_items = ('epg')
        self.log_userdata_requests = False
        self.proxy_url = 'http://127.0.0.1:48201/'

        # Realm config
        if self.load_realm_config().get('data'):
            realm_config    = self.load_realm_config()['data']['attributes']
        # Old realm config format
        else:
            realm_config = self.load_realm_config()

        if realm_config['realm'] == 'dplusindia':
            disco_params = 'realm=dplusindia,hn=www.discoveryplus.in'
            disco_client = 'WEB:UNKNOWN:dplus-india:prod'
            self.contentRatingSystem = 'DMEC'
            self.linkDevice_url = 'discoveryplus.in/activate'
            self.api_url = 'https://' + realm_config['domain']
        else:
            disco_params = 'realm=' + realm_config['realm'] + ',bid=dplus,hn=www.discoveryplus.com,hth=' + realm_config.get('mainTerritoryCode') + ',features=ar'
            disco_client = 'WEB:UNKNOWN:dplus_us:2.2.2'
            self.linkDevice_url = 'discoveryplus.com/link'
            self.api_url = realm_config['baseApiUrl']

            if realm_config.get('mainTerritoryCode'):

                # Content rating systems
                # Great Britain = Ofcom
                if realm_config['mainTerritoryCode'] == 'gb':
                    self.contentRatingSystem = 'Ofcom'
                # Canada and USA = BLM
                elif realm_config['mainTerritoryCode'] in ['ca', 'us']:
                    self.contentRatingSystem = 'BLM'
                # EU = NICAM
                else:
                    self.contentRatingSystem = 'NICAM'

            # mainTerritoryCode empty = use BLM
            else:
                self.contentRatingSystem = 'BLM'

        self.realm = realm_config['realm']

        self.site_headers = {
            'x-disco-params': disco_params,
            'x-disco-client': disco_client
        }

        # client_name/client_version (manufacturer/model; operating system/version)
        client = disco_client.split(':')
        system, system_version = self.get_system()
        self.device_info = \
            '{client_name}/{client_version} (Kodi Foundation/Kodi {kodi_version}; {os_name}/{os_version}; {device_id})'\
                .format(client_name=client[2], client_version=client[3], kodi_version=kodi_version,
                        os_name=system, os_version=system_version, device_id=self.device_id)

        # Use exported cookies.txt
        if cookiestxt:
            self.cookie_jar = cookielib.MozillaCookieJar(cookiestxt_file)
        # Code login cookies and user defined cookie
        else:
            self.cookie_jar = cookielib.LWPCookieJar(os.path.join(self.settings_folder, 'cookie_file'))

        try:
            self.cookie_jar.load(ignore_discard=True, ignore_expires=True)
        except IOError:
            pass
        self.http_session.cookies = self.cookie_jar

    class DplusError(Exception):
        def __init__(self, value, code=None):
            self.value = value
            self.code = code

        def __str__(self):
            return repr(self.value)

    def log(self, string):
        msg = '%s: %s' % (self.logging_prefix, string)
        xbmc.log(msg=msg, level=xbmc.LOGDEBUG)

    def make_request(self, url, method, params=None, payload=None, headers=None):
        """Make an HTTP request. Return the response."""
        try:
            return self._make_request(url, method, params=params, payload=payload, headers=headers)
        except self.DplusError as error:
            if error.code == 'invalid.token':
                # Get new token and reload data
                self.get_token()
                return self._make_request(url, method, params=params, payload=payload, headers=headers)
            else:
                raise

    def _make_request(self, url, method, params=None, payload=None, headers=None):
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

            # For security reasons we don't want to log responses from these pages if status code is 200
            if ('/users/me' in url or '/token' in url) and self.log_userdata_requests is False and req.status_code == 200:
                self.log('Response: %s' % 'HIDDEN RESPONSE')
            else:
                self.log('Response: %s' % req.content)

            try:
                self.cookie_jar.save(ignore_discard=True, ignore_expires=True)
            except IOError:
                pass

            # Check for errors only if status code is 400 or 403
            if req.status_code in [400, 403]:
                self.raise_dplus_error(req.content)

            return req.content

        except requests.exceptions.ConnectionError as error:
            self.log('Connection Error: - %s' % error)
            raise
        except requests.exceptions.RequestException as error:
            self.log('Error: - %s' % error)
            raise

    def raise_dplus_error(self, response):
        try:
            response = json.loads(response)
            if 'errors' in response:
                for error in response['errors']:
                    # raise DplusError when 'errors' in response
                    raise self.DplusError(error['detail'], error['code'])

        except KeyError:
            pass
        except ValueError:  # when response is not in json
            pass

    def get_system(self):
        import platform
        system = 'unknown'
        if xbmc.getCondVisibility('system.platform.linux') and not xbmc.getCondVisibility('system.platform.android'):
            system = 'Linux'
        elif xbmc.getCondVisibility('system.platform.linux') and xbmc.getCondVisibility('system.platform.android'):
            system = 'Android'
        elif xbmc.getCondVisibility('system.platform.uwp'):
            system = 'UWP'
        elif xbmc.getCondVisibility('system.platform.windows'):
            system = 'Windows'
        elif xbmc.getCondVisibility('system.platform.osx'):
            system = 'macOS'
        elif xbmc.getCondVisibility('system.platform.ios'):
            system = 'iOS'
        elif xbmc.getCondVisibility('system.platform.tvos'):
            system = 'tvOS'

        system_version = 'unknown'
        if system == 'Windows':
            system_version = platform.win32_ver()[0]
        elif system == 'macOS':
            system_version = platform.mac_ver()[0]
        elif system == 'Android':
            import subprocess
            system_version = subprocess.check_output( ['/system/bin/getprop', 'ro.build.version.release'])

        return system, system_version

    def get_token(self, token=None):
        url = '{api_url}/token'.format(api_url=self.api_url)

        params = {
            'realm': self.realm,
            'deviceId': self.device_id,
            'shortlived': 'true'
        }

        headers = self.site_headers
        # Register used device to discovery+. Only works when code login is used.
        headers['x-device-info'] = self.device_info
        # Use provided token to get new cookie
        if token:
            headers['cookie'] = 'st=' + token

        return self._make_request(url, 'get', params=params, headers=headers)

    def linkDevice_initiate(self):
        url = '{api_url}/authentication/linkDevice/initiate'.format(api_url=self.api_url)

        return json.loads(self.make_request(url, 'post', headers=self.site_headers))

    def linkDevice_login(self):
        url = '{api_url}/authentication/linkDevice/login'.format(api_url=self.api_url)
        data = self.make_request(url, 'post', headers=self.site_headers)

        if data:
            return json.loads(data)['data']['attributes']['token']
        # Return is empty if code is not entered on discoveryplus.com/link
        else:
            return None

    def get_user_data(self):
        url = '{api_url}/users/me'.format(api_url=self.api_url)

        data = self.make_request(url, 'get')
        return json.loads(data)['data']

    def load_realm_config(self):
        # Download realm config if it doesn't exists
        if not xbmcvfs.exists(os.path.join(self.settings_folder, 'realm_config')):
            import resources.services.realmservice as realmservice
            realmservice.main()

        config_file = os.path.join(self.settings_folder, 'realm_config')
        f = open(config_file, "r")
        return json.loads(f.read())

    def get_avatars(self):
        url = '{api_url}/avatars'.format(api_url=self.api_url)

        data = self.make_request(url, 'get', headers=self.site_headers)
        return json.loads(data)['data']

    def get_profiles(self):
        url = '{api_url}/users/me/profiles'.format(api_url=self.api_url)

        data = json.loads(self.make_request(url, 'get', headers=self.site_headers))
        return data

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

    def logout(self):
        url = '{api_url}/logout'.format(api_url=self.api_url)
        return self.make_request(url, 'post', headers=self.site_headers)

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

        if self.realm == 'dplusindia':
            params['decorators'] = 'viewingHistory,isFavorite'
        else:
            params['decorators'] = 'viewingHistory,isFavorite,playbackAllowed'

        # discoveryplus.com (US and EU)
        if search_query:
            params['contentFilter[query]'] = search_query

        data = json.loads(self.make_request(url, 'get', params=params, headers=self.site_headers))
        return data

    def get_collections(self, collection_id, page, mandatoryParams=None, parameter=None, itemsSize=None):
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

        # itemsSize is used to force displayed items count to 100
        # This is needed for marking seasons watched/unwatched
        params = {
            'include': 'default',
            'page[items.number]': page,
            'page[items.size]': itemsSize if itemsSize else self.numResults
        }

        if self.realm == 'dplusindia':
            params['decorators'] = 'viewingHistory,isFavorite'
        else:
            params['decorators'] = 'viewingHistory,isFavorite,playbackAllowed'

        data = json.loads(self.make_request(url, 'get', params=params, headers=self.site_headers))
        return data

    def get_favorite_search_shows_in(self, search_query=None):
        url = '{api_url}/content/shows'.format(api_url=self.api_url)
        params = {
            'decorators': 'isFavorite',
            'include': 'images,contentPackages,taxonomyNodes',
            'page[size]': 100,
        }

        # Search shows
        if search_query:
            params['query'] = search_query
        # Favorite shows
        else:
            params['filter[isFavorite]'] = 'true'
            params['page[number]'] = 1

        data = json.loads(self.make_request(url, 'get', params=params, headers=self.site_headers))
        return data

    def get_favorite_watchlist_videos_in(self, videoType=None, playlist=None):
        url = '{api_url}/content/videos'.format(api_url=self.api_url)
        params = {
            'decorators': 'viewingHistory,isFavorite',
            'include': 'images,contentPackages,show,genres,primaryChannel,taxonomyNodes',
            'page[size]': 100,
            'page[number]': 1,
        }

        # Favorite videos
        if videoType:
            params['filter[videoType]'] = videoType
            params['filter[isFavorite]'] = 'true'
        # Watchlist videos
        else:
            params['filter[playlist]'] = playlist

        data = json.loads(self.make_request(url, 'get', params=params, headers=self.site_headers))
        return data

    def update_playback_progress(self, video_id, position):
        url = '{api_url}/playback/v2/report/video/{video_id}'.format(api_url=self.api_url, video_id=video_id)

        params = {
            'position': position
        }

        # d+ website doesn't offer option to set video as unwatched but API seems to support it
        if position == '0':
            return self.make_request(url, 'delete', headers=self.site_headers)
        else:
            return self.make_request(url, 'post', params=params, headers=self.site_headers)

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

    def parse_artwork(self, image_list, images, video_thumb=None, type=None):
        fanart_image = None
        logo_image = None
        poster_image = None
        poster_nologo_image = None
        landscape_image = None

        if image_list:
            for item in image_list['data']:
                image = [x for x in images if x['id'] == item['id']][0]
                if image['attributes']['kind'] == 'default':
                    fanart_image = image['attributes']['src']
                if image['attributes']['kind'] == 'logo':
                    logo_image = image['attributes']['src']
                if image['attributes']['kind'] == 'cover_artwork_horizontal':
                    landscape_image = image['attributes']['src']
                # discoveryplus.in has logos in poster
                if self.realm == 'dplusindia':
                    if image['attributes']['kind'] == 'poster':
                        poster_image = image['attributes']['src']
                else:
                    # Alternate is used as poster in Home -> Coming soon (US and EU)
                    # We will overwrite alternate image if poster exists
                    if image['attributes']['kind'] == 'alternate':
                        poster_image = image['attributes']['src']
                    if image['attributes']['kind'] == 'poster_with_logo':
                        poster_image = image['attributes']['src']
                    if image['attributes']['kind'] == 'poster':
                        poster_nologo_image = image['attributes']['src']

        if type and type in ['channel', 'category']:
            thumb = logo_image if logo_image else fanart_image
            logo_image = None
        else:
            thumb = video_thumb if video_thumb else fanart_image

        # Load images using proxy because Kodi curl doesn't like HEAD response 404
        # Image quality is same as website. Without these parameters images can be almost 10mb and with these 200kb
        fanart_image = self.proxy_url + fanart_image + '?bf=0&f=jpg&p=true&q=70&w=2200' if fanart_image else None
        thumb = self.proxy_url + thumb + '?w=800&f=JPG&p=true&q=60' if thumb else None
        logo_image = self.proxy_url + logo_image + '?bf=0&f=png&p=true&q=60&w=700' if logo_image else None
        poster_image = self.proxy_url + poster_image + '?w=800&f=JPG&p=true&q=60' if poster_image else None
        poster_nologo_image = self.proxy_url + poster_nologo_image + '?w=800&f=JPG&p=true&q=60' if poster_nologo_image else None
        landscape_image = self.proxy_url + landscape_image + '?w=800&f=JPG&p=true&q=60' if landscape_image else None

        art = {
            'fanart': fanart_image,
            'thumb': thumb,
            'clearlogo': logo_image,
            'poster': poster_image,
            'landscape': landscape_image,
            'keyart': poster_nologo_image
        }

        return art

    def get_channels(self):
        page_data = self.get_page('/epg')

        collections = list(filter(lambda x: x['type'] == 'collection', page_data['included']))
        collectionItems = list(filter(lambda x: x['type'] == 'collectionItem', page_data['included']))

        channels_list = []

        current_day = datetime.today().strftime('%Y-%m-%d')

        collection = [x for x in collections if x['attributes']['alias'] == 'epg-listing-wrapper'][0]
        for collection_relationships in collection['relationships']['items']['data']:
            collectionItem = [x for x in collectionItems if x['id'] == collection_relationships['id']][0]

            epg_page_data = self.get_collections(
                collection_id=collectionItem['relationships']['collection']['data']['id'], page=1,
                parameter='pf[day]={current_day}'.format(current_day=current_day))

            # It is possible that there's empty channel
            if epg_page_data.get('included'):

                channels = list(filter(lambda x: x['type'] == 'channel', epg_page_data['included']))
                images = list(filter(lambda x: x['type'] == 'image', epg_page_data['included']))

                for channel in channels:
                    if channel['attributes']['hasLiveStream']:
                        url = 'plugin://plugin.video.discoveryplus/play/channel/{channel_id}'.format(
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

                            channel_logo = self.proxy_url + channel_logo + '?bf=0&f=png&p=true&q=60&w=700' if channel_logo else None
                            fanart_image = self.proxy_url + fanart_image + '?bf=0&f=jpg&p=true&q=70&w=2200' if fanart_image else None

                        channels_list.append(dict(
                            id='%s@%s' % (channel['id'], slugify(
                                xbmcaddon.Addon(id='plugin.video.discoveryplus').getAddonInfo('name'))),
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

        # Introducing discovery+ Channels - Category
        collection = [x for x in collections if x['attributes']['alias'] == 'home-rail-jip-channels'][0]
        for collection_relationship in collection['relationships']['items']['data']:
            collectionItem = [x for x in collectionItems if x['id'] == collection_relationship['id']][0]

            if collectionItem['relationships'].get('channel'):
                channel = [x for x in channels if x['id'] == collectionItem['relationships']['channel']['data']['id']][0]

                if channel['attributes']['hasLiveStream']:
                    url = 'plugin://plugin.video.discoveryplus/play/channel/{channel_id}'.format(
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

                        channel_logo = self.proxy_url + channel_logo + '?bf=0&f=png&p=true&q=60&w=700' if channel_logo else None
                        fanart_image = self.proxy_url + fanart_image + '?bf=0&f=jpg&p=true&q=70&w=2200' if fanart_image else None

                    channels_list.append(dict(
                        id='%s@%s' % (channel['id'], slugify(
                            xbmcaddon.Addon(id='plugin.video.discoveryplus').getAddonInfo('name'))),
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

        collection = [x for x in collections if x['attributes']['alias'] == 'explore-national-live-channels-list'][0]
        for collection_relationship in collection['relationships']['items']['data']:
            collectionItem = [x for x in collectionItems if x['id'] == collection_relationship['id']][0]

            if collectionItem['relationships'].get('channel'):
                channel = [x for x in channels if x['id'] == collectionItem['relationships']['channel']['data']['id']][0]

                if channel['attributes']['hasLiveStream']:
                    url = 'plugin://plugin.video.discoveryplus/play/channel/{channel_id}'.format(
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

                        channel_logo = self.proxy_url + channel_logo + '?bf=0&f=png&p=true&q=60&w=700' if channel_logo else None
                        fanart_image = self.proxy_url + fanart_image + '?bf=0&f=jpg&p=true&q=70&w=2200' if fanart_image else None

                    channels_list.append(dict(
                        id='%s@%s' % (channel['id'], slugify(
                            xbmcaddon.Addon(id='plugin.video.discoveryplus').getAddonInfo('name'))),
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

        collection = [x for x in collections if x['attributes']['alias'] == 'epg-listing-wrapper'][0]
        for collection_relationships in collection['relationships']['items']['data']:
            collectionItem = [x for x in collectionItems if x['id'] == collection_relationships['id']][0]
            if collectionItem['relationships'].get('collection'):

                # Get daily epg per channel
                for option in collection['attributes']['component']['filters'][0]['options']:

                    # Grab EPG only for current day and later
                    if option['id'] >= \
                            collection['attributes']['component']['filters'][0]['initiallySelectedOptionIds'][0]:

                        epg_page_data = self.get_collections(
                            collection_id=collectionItem['relationships']['collection']['data']['id'],
                            page=1,
                            parameter=option['parameter'])

                        # It is possible that channel doesn't have EPG for requested day
                        if epg_page_data.get('included'):

                            collectionItems2 = list(filter(lambda x: x['type'] == 'collectionItem', epg_page_data['included']))
                            channels = list(filter(lambda x: x['type'] == 'channel', epg_page_data['included']))
                            images = list(filter(lambda x: x['type'] == 'image', epg_page_data['included']))
                            videos = list(filter(lambda x: x['type'] == 'video', epg_page_data['included']))
                            taxonomyNodes = list(filter(lambda x: x['type'] == 'taxonomyNode', epg_page_data['included']))

                            for channel in channels:
                                if channel['attributes']['hasLiveStream']:
                                    for collectionItem2 in collectionItems2:
                                        video = [x for x in videos if
                                                 x['id'] == collectionItem2['relationships']['video']['data']['id']][0]

                                        fanart_image = None
                                        if video['relationships'].get('images'):
                                            for image in images:
                                                for video_images in video['relationships']['images']['data']:
                                                    if image['id'] == video_images['id']:
                                                        if image['attributes']['kind'] == 'default':
                                                            fanart_image = image['attributes']['src']

                                            fanart_image = self.proxy_url + fanart_image + '?bf=0&f=jpg&p=true&q=70&w=2200' if fanart_image else None

                                        channel_id = '%s@%s' % (channel['id'], slugify(
                                            xbmcaddon.Addon(id='plugin.video.discoveryplus').getAddonInfo('name')))

                                        # Sport events
                                        if video['relationships'].get('txSports'):
                                            subtitle = video['attributes'].get('secondaryTitle')
                                            for taxonomyNode in taxonomyNodes:
                                                if taxonomyNode['id'] == \
                                                        video['relationships']['txSports']['data'][0]['id']:
                                                    if video['attributes'].get('secondaryTitle'):
                                                        subtitle = taxonomyNode['attributes']['name'] + ' - ' + \
                                                                   video['attributes']['secondaryTitle']
                                                    else:
                                                        subtitle = taxonomyNode['attributes']['name']

                                            epg[channel_id].append(dict(
                                                start=video['attributes'].get('scheduleStart'),
                                                stop=video['attributes'].get('scheduleEnd'),
                                                title=video['attributes'].get('name'),
                                                description=video['attributes'].get('description'),
                                                subtitle=subtitle,
                                                image=fanart_image
                                            ))
                                        # TV shows
                                        else:
                                            if video['attributes']['customAttributes'].get('listingSeasonNumber') and \
                                                    video['attributes']['customAttributes'].get('listingEpisodeNumber'):
                                                episode = 'S' + str(video['attributes']['customAttributes']['listingSeasonNumber']) + \
                                                          'E' + str(video['attributes']['customAttributes']['listingEpisodeNumber'])
                                            else:
                                                episode = None

                                            subtitle = video['attributes'].get('name')
                                            # Don't add name to subtitle if it same as listingShowName
                                            if video['attributes']['customAttributes'].get(
                                                    'listingShowName') and video['attributes'].get('name'):
                                                if video['attributes']['customAttributes']['listingShowName'] == \
                                                        video['attributes']['name']:
                                                    subtitle = None

                                            # At least discovery+ UK doesn't always have show name on data
                                            if video['attributes']['customAttributes'].get('listingShowName') is None:
                                                title = subtitle
                                                subtitle = None
                                            else:
                                                title = video['attributes']['customAttributes']['listingShowName']

                                            epg[channel_id].append(dict(
                                                start=video['attributes'].get('scheduleStart'),
                                                stop=video['attributes'].get('scheduleEnd'),
                                                title=title,
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

        # This will output window size if Kodi is in windowed mode
        #screenHeight = xbmc.getInfoLabel('System.ScreenHeight')
        #screenWidth = xbmc.getInfoLabel('System.ScreenWidth')

        # Use drmSupported:false for UHD streams. For now playback is only tested to kinda work when drm and
        # InputStreamAdaptive is disabled from add-on settings. It is possible that drm/mpd stream also works on Android devices.
        # Change drmSupported to false from add-on settings if you want to play videos without drm.
        if self.us_uhd:
            hwDecoding = ['H264','H265']
            platform = 'firetv'
            drmSupported = 'false'
            screenWidth = 3840
            screenHeight = 2160
        else:
            hwDecoding = []
            platform = 'desktop'
            screenWidth = 1920
            screenHeight = 1080
            if self.drm_supported:
                drmSupported = 'true'
            else:
                drmSupported = 'false'

        # discoveryplus.com (go=US and Canada)
        if self.realm == 'go':
            product = 'dplus_us'
        elif self.realm == 'dplusindia':
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

        if data_dict['attributes'].get('markers'):
            stream['videoAboutToEnd'] = data_dict['attributes']['markers']['videoAboutToEnd']

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