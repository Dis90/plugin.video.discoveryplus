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
    from urllib.parse import urlparse, urljoin, quote
except ImportError: # Python 2
    from urlparse import urlparse, urljoin
    from urllib import quote

try:  # Python 2
    unicode
except NameError:  # Python 3
    unicode = str  # pylint: disable=redefined-builtin,invalid-name

def slugify(text):
    non_url_safe = [' ','"', '#', '$', '%', '&', '+',',', '/', ':', ';', '=', '?','@', '[', '\\', ']', '^', '`','{', '|', '}', '~', "'"]
    non_url_safe_regex = re.compile(r'[{}]'.format(''.join(re.escape(x) for x in non_url_safe)))
    text = non_url_safe_regex.sub('', text).strip()
    text = u'_'.join(re.split(r'\s+', text))
    return text

class Dplay(object):
    def __init__(self, settings_folder, site, locale, logging_prefix, numresults, cookiestxt, cookiestxt_file, sync_playback, us_uhd):
        self.logging_prefix = logging_prefix
        self.site_url = site
        self.locale = locale
        self.numResults = numresults
        self.locale_suffix = self.locale.split('_')[1].lower()
        self.client_id = str(uuid.uuid1())
        self.device_id = self.client_id.replace("-", "")
        self.sync_playback = sync_playback
        self.us_uhd = us_uhd

        if self.locale_suffix == 'gb':
            self.api_url = 'https://disco-api.' + self.site_url
            self.realm = 'questuk'
            self.site_headers = {'x-disco-params': 'realm='+self.realm}
        elif self.locale_suffix == 'us':
            self.api_url = 'https://us1-prod-direct.' + self.site_url
            self.realm = 'go'
            self.site_headers = {'x-disco-params': 'realm=go,siteLookupKey=dplus_us', 'x-disco-client': 'WEB:UNKNOWN:dplus_us:0.0.1'}
        elif self.locale_suffix == 'in':
            self.api_url = 'https://ap2-prod-direct.' + self.site_url
            self.realm = 'dplusindia'
            self.site_headers = {'x-disco-params': 'realm=dplusindia', 'x-disco-client': 'WEB:UNKNOWN:dplus-india:prod'}
        else:
            self.api_url = 'https://disco-api.' + self.site_url
            self.realm = 'dplay' + self.locale_suffix
            self.site_headers = {'x-disco-params': 'realm='+self.realm}

        self.http_session = requests.Session()
        self.settings_folder = settings_folder
        self.tempdir = os.path.join(settings_folder, 'tmp')
        self.unwanted_menu_items = ('Hae mukaan', 'Info', 'Tablå', 'Live TV', 'TV-guide')
        if not os.path.exists(self.tempdir):
            os.makedirs(self.tempdir)

        # If cookiestxt setting is true use users cookies file
        if cookiestxt:
            self.cookie_jar = cookielib.MozillaCookieJar(cookiestxt_file)
        else:
            self.cookie_jar = cookielib.LWPCookieJar(os.path.join(self.settings_folder, 'cookie_file'))

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
            self.log('Connection Error: - %s' % error.message)
            raise
        except requests.exceptions.RequestException as error:
            self.log('Error: - %s' % error.value)
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

    def get_token(self):
        url = '{api_url}/token'.format(api_url=self.api_url)

        params = {
            'realm': self.realm,
            'deviceId': self.device_id,
            'shortlived': 'true'
        }

        return self.make_request(url, 'get', params=params, headers=self.site_headers)

    def url_encode(self, url):
        """Converts an URL in url encode characters
        :param str url: The data to URL encode.
        :return: Encoded URL like this. Example: '/~connolly/' yields '/%7econnolly/'.
        :rtype: str
        """

        # noinspection PyUnresolvedReferences
        if isinstance(url, unicode):
            # noinspection PyUnresolvedReferences
            return quote(url.encode())
        else:
            # this is the main time waster
            # noinspection PyUnresolvedReferences
            return quote(url)

    def login(self, username=None, password=None):
        # Modified from:
        # https://github.com/retrospect-addon/plugin.video.retrospect/blob/master/channels/channel.se/sbs/chn_sbs.py

        # Local import to not slow down any other stuff
        import binascii
        try:
            # If running on Leia
            import pyaes
        except:
            # If running on Pre-Leia
            from resources.lib import pyaes
        import random

        now = int(time.time())
        b64_now = binascii.b2a_base64(str(now).encode()).decode().strip()

        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
                     "(KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36"
        window_id = "{}|{}".format(
            binascii.hexlify(os.urandom(16)).decode(), binascii.hexlify(os.urandom(16)).decode())

        fe = ["DNT:unknown", "L:en-US", "D:24", "PR:1", "S:1920,975", "AS:1920,935", "TO:-120",
              "SS:true", "LS:true", "IDB:true", "B:false", "ODB:true", "CPUC:unknown",
              "PK:Win32", "CFP:990181251", "FR:false", "FOS:false", "FB:false", "JSF:Arial",
              "P:Chrome PDF Plugin", "T:0,false,false", "H:4", "SWF:false"]
        fs_murmur_hash = '48bf49e1796939175b0406859d00baec'

        data = [
            {"key": "api_type", "value": "js"},
            {"key": "p", "value": 1},                       # constant
            {"key": "f", "value": self.device_id},               # browser instance ID
            {"key": "n", "value": b64_now},                 # base64 encoding of time.now()
            {"key": "wh", "value": window_id},              # WindowHandle ID
            {"key": "fe", "value": fe},                     # browser properties
            {"key": "ife_hash", "value": fs_murmur_hash},   # hash of browser properties
            {"key": "cs", "value": 1},                      # canvas supported 0/1
            {"key": "jsbd", "value": "{\"HL\":41,\"NCE\":true,\"DMTO\":1,\"DOTO\":1}"}
        ]
        data_value = json.dumps(data)

        stamp = now - (now % (60 * 60 * 6))
        key_password = "{}{}".format(user_agent, stamp)

        salt_bytes = os.urandom(8)
        key_iv = self.__evp_kdf(key_password.encode(), salt_bytes, key_size=8, iv_size=4,
                                iterations=1, hash_algorithm="md5")
        key = key_iv["key"]
        iv = key_iv["iv"]

        encrypter = pyaes.Encrypter(pyaes.AESModeOfOperationCBC(key, iv))
        encrypted = encrypter.feed(data_value)
        # Again, make a final call to flush any remaining bytes and strip padding
        encrypted += encrypter.feed()

        salt_hex = binascii.hexlify(salt_bytes)
        iv_hex = binascii.hexlify(iv)
        encrypted_b64 = binascii.b2a_base64(encrypted)
        bda = {
            "ct": encrypted_b64.decode(),
            "iv": iv_hex.decode(),
            "s": salt_hex.decode()
        }
        bda_str = json.dumps(bda)
        bda_base64 = binascii.b2a_base64(bda_str.encode())

        req_dict = {
            "bda": bda_base64.decode(),
            "public_key": "FE296399-FDEA-2EA2-8CD5-50F6E3157ECA",
            "site": "https://client-api.arkoselabs.com",
            "userbrowser": user_agent,
            "simulate_rate_limit": "0",
            "simulated": "0",
            "rnd": "{}".format(random.random())
        }

        req_data = ""
        for k, v in req_dict.items():
            req_data = "{}{}={}&".format(req_data, k, self.url_encode(v))
        req_data = req_data.rstrip("&")

        arkose_headers = {"user-agent": user_agent}

        arkose_data = self.make_request('https://client-api.arkoselabs.com/fc/gt2/public_key/FE296399-FDEA-2EA2-8CD5-50F6E3157ECA', 'get', params=req_data, headers=arkose_headers)
        arkose_json = json.loads(arkose_data)
        arkose_token = arkose_json.get("token")

        if "rid=" not in arkose_token:
            self.log("Error logging in. Invalid Arkose token.")
            self.log(arkose_token)
            raise self.DplayError('Error logging in. Invalid Arkose token.')

        self.log("Succesfully required a login token from Arkose.")

        # Get new token
        self.get_token()

        discoveryplus_username = username
        discoveryplus_password = password
        creds = {"credentials": {"username": discoveryplus_username, "password": discoveryplus_password}}
        headers = {
                "x-disco-arkose-token": arkose_token,
                "x-disco-arkose-sitekey": "FE296399-FDEA-2EA2-8CD5-50F6E3157ECA",
                "Origin": "https://www.{site_url}".format(site_url=self.site_url),
                "x-disco-client": "WEB:10.16.0:AUTH_DPLAY_V1:4.0.1-rc2-gi1",
                # is not specified a captcha is required
                # "Sec-Fetch-Site": "same-site",
                # "Sec-Fetch-Mode": "cors",
                # "Sec-Fetch-Dest": "empty",
                "Referer": "https://www.{site_url}/myaccount/login".format(site_url=self.site_url),
                "User-Agent": user_agent
            }

        login_url = '{api_url}/login'.format(api_url=self.api_url)
        return self.make_request(login_url, 'post', payload=json.dumps(creds), headers=headers)

    def __evp_kdf(self, passwd, salt, key_size=8, iv_size=4, iterations=1, hash_algorithm="md5"):
        """
        https://gist.github.com/adrianlzt/d5c9657e205b57f687f528a5ac59fe0e
        :param byte passwd:
        :param byte salt:
        :param int key_size:
        :param int iv_size:
        :param int iterations:
        :param str hash_algorithm:
        :return:
        """

        import hashlib

        target_key_size = key_size + iv_size
        derived_bytes = b""
        number_of_derived_words = 0
        block = None
        hasher = hashlib.new(hash_algorithm)

        while number_of_derived_words < target_key_size:
            if block is not None:
                hasher.update(block)

            hasher.update(passwd)
            hasher.update(salt)
            block = hasher.digest()

            hasher = hashlib.new(hash_algorithm)

            for _ in range(1, iterations):
                hasher.update(block)
                block = hasher.digest()
                hasher = hashlib.new(hash_algorithm)

            derived_bytes += block[0: min(len(block), (target_key_size - number_of_derived_words) * 4)]

            number_of_derived_words += len(block)/4

        return {
            "key": derived_bytes[0: key_size * 4],
            "iv": derived_bytes[key_size * 4:]
        }

    def get_user_data(self):
        url = '{api_url}/users/me'.format(api_url=self.api_url)

        data = self.make_request(url, 'get')
        return json.loads(data)['data']

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
            params['decorators'] = 'viewingHistory'

        # discoveryplus.com (US)
        if search_query:
            params['contentFilter[query]'] = search_query

        data = json.loads(self.make_request(url, 'get', params=params, headers=self.site_headers))
        return data

    def get_collections(self, collection_id, page, mandatoryParams=None, parameter=None):
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
            params['decorators'] = 'viewingHistory'

        data = json.loads(self.make_request(url, 'get', params=params, headers=self.site_headers))
        return data

    def get_search_shows(self, search_query):
        url = '{api_url}/content/shows'.format(api_url=self.api_url)

        params = {
            'include': 'genres,images,primaryChannel.images,contentPackages',
            'page[size]': 100,
            'query': search_query
        }

        data = json.loads(self.make_request(url, 'get', params=params))
        return data

    def get_favorites(self):
        url = '{api_url}/users/me/favorites'.format(api_url=self.api_url)
        params = {
            'include': 'default'
        }

        data = json.loads(self.make_request(url, 'get', params=params, headers=self.site_headers))
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
        if not self.sync_playback:
            return

        url = '{api_url}/playback/v2/report/video/{video_id}'.format(api_url=self.api_url, video_id=video_id)

        params = {
            'position': position
        }

        return self.make_request(url, method, params=params)

    def get_current_episode_info(self, video_id):
        url = '{api_url}/content/videos/{video_id}'.format(api_url=self.api_url, video_id=video_id)

        params = {
            'decorators': 'viewingHistory',
            'include': 'genres,images,primaryChannel,show,show.images'
        }

        data = json.loads(self.make_request(url, 'get', params=params, headers=self.site_headers))
        return data

    def get_next_episode_info(self, current_video_id):
        url = '{api_url}/content/videos/{video_id}/next'.format(api_url=self.api_url, video_id=current_video_id)

        params = {
            'algorithm': 'naturalOrder',
            'include': 'genres,images,primaryChannel,show,show.images,contentPackages'
        }

        data = json.loads(self.make_request(url, 'get', params=params, headers=self.site_headers))
        return data

    def add_or_delete_favorite(self, method, show_id):
        # POST for adding and DELETE for delete
        url = '{api_url}/users/me/favorites/shows/{show_id}'.format(api_url=self.api_url, show_id=show_id)

        return self.make_request(url, method, headers=self.site_headers)

    def get_channels(self):
        url = '{api_url}/cms/configs/web-prod'.format(api_url=self.api_url)
        epg_channels = json.loads(self.make_request(url, 'get', headers=self.site_headers))['data']['attributes']['config']['epg']['channels']

        channels_list = []

        for key, value in epg_channels.items():
            url = 'plugin://plugin.video.discoveryplus/?action=play&video_id={channel_id}&video_type=channel'.format(channel_id=value['id'])

            channels_list.append(dict(
                id='%s@%s'%(key,slugify(xbmcaddon.Addon(id='plugin.video.discoveryplus').getAddonInfo('name'))),
                name=value['logo']['title'],
                logo=value['logo']['src'],
                stream=url,
                preset=value['order']

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

            # Not available at the moment
            # Normal channels
            # if collection['attributes']['alias'] == 'networks':
            #     for c in collection['relationships']['items']['data']:
            #         for collectionItem in collectionItems:
            #             if c['id'] == collectionItem['id']:
            #                 if collectionItem['relationships'].get('channel'):
            #                     for channel in channels:
            #                         if \
            #                                 collectionItem['relationships']['channel']['data'][
            #                                     'id'] == channel['id']:
            #
            #                             if channel['attributes']['hasLiveStream']:
            #                                 url = 'plugin://plugin.video.discoveryplus/?action=play&video_id={channel_id}&video_type=channel'.format(
            #                                     channel_id=channel['id'])
            #
            #                                 channel_logo = None
            #                                 fanart_image = None
            #                                 if channel['relationships'].get('images'):
            #                                     for image in images:
            #                                         for channel_images in \
            #                                                 channel['relationships']['images'][
            #                                                     'data']:
            #                                             if image['id'] == channel_images[
            #                                                 'id']:
            #                                                 if image['attributes'][
            #                                                     'kind'] == 'logo':
            #                                                     channel_logo = \
            #                                                         image['attributes']['src']
            #                                                 if image['attributes'][
            #                                                     'kind'] == 'default':
            #                                                     fanart_image = \
            #                                                         image['attributes']['src']
            #
            #                                 channels_list.append(dict(
            #                                     id='%s@%s' % (channel['id'], slugify(
            #                                         xbmcaddon.Addon(id='plugin.video.discoveryplus').getAddonInfo(
            #                                             'name'))),
            #                                     name=channel['attributes']['name'],
            #                                     logo=channel_logo if channel_logo else fanart_image,
            #                                     stream=url
            #
            #                                 ))

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
        url = '{api_url}/cms/configs/web-prod'.format(api_url=self.api_url)
        epg_channels = json.loads(self.make_request(url, 'get', headers=self.site_headers))['data']['attributes']['config']['epg']['channels']

        from collections import defaultdict
        epg = defaultdict(list)

        for key in epg_channels.keys():
            # discovery+ website TV guide displays +- 8 days
            startDate = date.today() - timedelta(days=8)
            endDate = date.today() + timedelta(days=8)

            url = '{api_url}/tvlistings/v2/channels/{tvguide_id}?startDate={startDate}T04:00:00.000Z&endDate={endDate}T03:59:59.000Z'.format(api_url=self.api_url, tvguide_id=key, startDate=startDate, endDate=endDate)
            data = json.loads(self.make_request(url, 'get', headers=self.site_headers))

            for epg_data in data['data']:
                start_time = epg_data['attributes'].get('utcStart')
                duration = epg_data['attributes'].get('duration')

                # Convert UTC datetime to seconds since the Epoch
                date_time_format = '%Y-%m-%dT%H:%M:%SZ'
                datetime_obj = datetime(*(time.strptime(start_time, date_time_format)[0:6]))
                start_time_unix = (datetime_obj - datetime(1970, 1, 1)).total_seconds()
                # Add episode duration to start time
                stop_time = start_time_unix + duration
                # Convert to ISO-8601
                stop_time_iso = datetime.utcfromtimestamp(stop_time).isoformat()

                if epg_data['attributes'].get('season') and epg_data['attributes'].get('episode'):
                    episode = 'S' + str(epg_data['attributes']['season']) + 'E' + str(epg_data['attributes']['episode'])
                else:
                    episode = ''

                # Don't add eventName to subtitle if it same as showName
                if epg_data['attributes'].get('showName') and epg_data['attributes'].get('eventName'):
                    if epg_data['attributes']['showName'] == epg_data['attributes']['eventName']:
                        subtitle = ''
                    else:
                        subtitle = epg_data['attributes']['eventName']
                else:
                    subtitle = ''

                channel_id = '%s@%s'%(key,slugify(xbmcaddon.Addon(id='plugin.video.discoveryplus').getAddonInfo('name')))

                epg[channel_id].append(dict(
                    start=epg_data['attributes'].get('utcStart'),
                    stop=stop_time_iso,
                    title=epg_data['attributes'].get('showName'),
                    description=epg_data['attributes']['description'] if epg_data['attributes'].get('description') else '',
                    subtitle=subtitle,
                    episode=episode
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

        if self.us_uhd:
            hwDecoding = ['H264','H265']
            platform = 'firetv'
        else:
            hwDecoding = []
            platform = 'desktop'

        params = {'usePreAuth': 'true'}
        # discoveryplus.com (US)
        if self.locale_suffix == 'us':
            if video_type == 'channel':
                jsonPayload = {
                    'deviceInfo': {
                        'adBlocker': 'true'
                    },
                    'channelId': video_id,
                               'wisteriaProperties': {
                                   'advertiser': {
                                       'firstPlay': 0,
                                       'fwIsLat': 0
                                   },
                                   'device': {
                                       'type': 'desktop'
                                    },
                                   'platform': 'desktop',
                                   'product': 'dplus_us',
                                   'sessionId': self.client_id,
                                   'streamProvider': {
                                       'suspendBeaconing': 0,
                                       'hlsVersion': 7,
                                       'pingConfig': 1
                                   }
                               }
                }

                url = '{api_url}/playback/v3/channelPlaybackInfo'.format(api_url=self.api_url)

            else:
                jsonPayload = {
                    'deviceInfo': {
                        'adBlocker': 'true',
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
                    'videoId': video_id,
                    'wisteriaProperties':{
                        'platform': platform,
                        'product': 'dplus_us'
                    }
                }
                url = '{api_url}/playback/v3/videoPlaybackInfo'.format(api_url=self.api_url)

            data_dict = json.loads(self.make_request(url, 'post', params=params, headers=self.site_headers, payload=json.dumps(jsonPayload)))['data']
        else:
            if video_type == 'channel':
                url = '{api_url}/playback/v2/channelPlaybackInfo/{video_id}'.format(api_url=self.api_url, video_id=video_id)
            else:
                url = '{api_url}/playback/v2/videoPlaybackInfo/{video_id}'.format(api_url=self.api_url, video_id=video_id)

            data_dict = json.loads(self.make_request(url, 'get', params=params, headers=self.site_headers))['data']

        # discoveryplus.com (US)
        if self.locale_suffix == 'us':
            stream['hls_url'] = data_dict['attributes']['streaming'][0]['url']
            stream['drm_enabled'] = data_dict['attributes']['streaming'][0]['protection']['drmEnabled']
        else:
            stream['hls_url'] = data_dict['attributes']['streaming']['hls']['url']
            stream['mpd_url'] = data_dict['attributes']['streaming']['dash']['url']
            if data_dict['attributes']['protection']['schemes'].get('widevine'):
                stream['license_url'] = data_dict['attributes']['protection']['schemes']['widevine']['licenseUrl']
                stream['drm_token'] = data_dict['attributes']['protection']['drmToken']
            stream['drm_enabled'] = data_dict['attributes']['protection']['drmEnabled']

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