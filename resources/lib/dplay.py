# -*- coding: utf-8 -*-
"""
A Kodi-agnostic library for Discovery+
"""
import os
from io import open, StringIO
import xbmc
import re
import json
import codecs
import time
import calendar
from datetime import datetime, timedelta
import requests
import uuid

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

class Dplay(object):
    def __init__(self, settings_folder, site, locale, logging_prefix):
        self.logging_prefix = logging_prefix
        self.site_url = site
        self.locale = locale
        self.locale_suffix = self.locale.split('_')[1].lower()
        self.client_id = str(uuid.uuid1())
        self.device_id = self.client_id.replace("-", "")
        if self.locale_suffix == 'us':
            self.api_url = 'https://us1-prod-direct.' + self.site_url
        else:
            self.api_url = 'https://disco-api.' + self.site_url
        self.http_session = requests.Session()
        self.settings_folder = settings_folder
        self.tempdir = os.path.join(settings_folder, 'tmp')
        self.unwanted_menu_items = ('Hae mukaan', 'Info', 'Tablå', 'Live TV', 'TV-guide')
        if not os.path.exists(self.tempdir):
            os.makedirs(self.tempdir)
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
            self.cookie_jar.save(ignore_discard=True, ignore_expires=True)
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

        #dplayfi dplayse dplayno dplaydk dplaynl dplayes dplayit questuk go
        # .com uses go, co.uk uses questuk and others dplay+locale
        if self.locale_suffix == 'gb':
            realm = 'questuk'
        elif self.locale_suffix == 'us':
            realm = 'go'
        else:
            realm = 'dplay' + self.locale_suffix

        params = {
            'realm': realm,
            'deviceId': self.device_id,
            'shortlived': 'true'
        }

        return self.make_request(url, 'get', params=params)

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
            return False

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

    def get_menu(self):
        url = '{api_url}/cms/collections/web-menubar'.format(api_url=self.api_url)

        params = {
            'include': 'default'
        }

        data = json.loads(self.make_request(url, 'get', params=params))
        return data

    def get_page(self, path):
        url = '{api_url}/cms/routes{path}'.format(api_url=self.api_url, path=path)

        params = {
            'decorators': 'viewingHistory',
            'include': 'default'
        }

        data = json.loads(self.make_request(url, 'get', params=params))
        return data

    def get_collections(self, collection_id, mandatoryParams=None, parameter=None):
        if mandatoryParams and parameter:
            url = '{api_url}/cms/collections/{collection_id}?{mandatoryParams}&{parameter}'.format(api_url=self.api_url, collection_id=collection_id, mandatoryParams=mandatoryParams, parameter=parameter)
        elif mandatoryParams is None and parameter:
            url = '{api_url}/cms/collections/{collection_id}?{parameter}'.format(api_url=self.api_url, collection_id=collection_id, parameter=parameter)
        else:
            url = '{api_url}/cms/collections/{collection_id}?{mandatoryParams}'.format(api_url=self.api_url, collection_id=collection_id, mandatoryParams=mandatoryParams)

        params = {
            'decorators': 'viewingHistory',
            'include': 'default',
            'page[items.number]': 1,
            'page[items.size]': 100
        }

        data = json.loads(self.make_request(url, 'get', params=params))
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

        data = json.loads(self.make_request(url, 'get', params=params))
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
            'decorators': 'viewingHistory',
            'include': 'genres,images,primaryChannel,show,show.images'
        }

        data = json.loads(self.make_request(url, 'get', params=params))
        return data

    def get_next_episode_info(self, current_video_id):
        url = '{api_url}/content/videos/{video_id}/next'.format(api_url=self.api_url, video_id=current_video_id)

        params = {
            'algorithm': 'naturalOrder',
            'include': 'genres,images,primaryChannel,show,show.images,contentPackages'
        }

        data = json.loads(self.make_request(url, 'get', params=params))
        return data

    def add_or_delete_favorite(self, method, show_id):
        # POST for adding and DELETE for delete
        url = '{api_url}/users/me/favorites/shows/{show_id}'.format(api_url=self.api_url, show_id=show_id)

        return self.make_request(url, method)

    def decode_html_entities(self, s):
        s = s.strip()
        s = s.replace('&lt;', '<')
        s = s.replace('&gt;', '>')
        s = s.replace('&nbsp;', ' ')
        # Must do ampersand last
        s = s.replace('&amp;', '&')
        return s

    def webvtt_to_srt(self, subdata):
        # Modified from:
        # https://github.com/spaam/svtplay-dl/blob/master/lib/svtplay_dl/subtitle/__init__.py
        ssubdata = StringIO(subdata)
        srt = ""
        subtract = False
        number_b = 1
        number = 0
        block = 0
        subnr = False

        for i in ssubdata.readlines():
            match = re.search(r"^[\r\n]+", i)
            match2 = re.search(r"([\d:\.]+ --> [\d:\.]+)", i)
            match3 = re.search(r"^(\d+)\s", i)
            if i[:6] == "WEBVTT":
                continue
            elif "X-TIMESTAMP" in i:
                continue
            elif match and number_b > 1:
                block = 0
                srt += "\n"
            elif match2:
                if not subnr:
                    srt += "%s\n" % number_b
                matchx = re.search(r"(?P<h1>\d+):(?P<m1>\d+):(?P<s1>[\d\.]+) --> (?P<h2>\d+):(?P<m2>\d+):(?P<s2>[\d\.]+)", i)
                if matchx:
                    hour1 = int(matchx.group("h1"))
                    hour2 = int(matchx.group("h2"))
                    if int(number) == 1:
                        if hour1 > 9:
                            subtract = True
                    if subtract:
                        hour1 -= 10
                        hour2 -= 10
                else:
                    matchx = re.search(r"(?P<m1>\d+):(?P<s1>[\d\.]+) --> (?P<m2>\d+):(?P<s2>[\d\.]+)", i)
                    hour1 = 0
                    hour2 = 0
                time = "{:02d}:{}:{} --> {:02d}:{}:{}\n".format(
                    hour1, matchx.group("m1"), matchx.group("s1").replace(".", ","), hour2, matchx.group("m2"), matchx.group("s2").replace(".", ",")
                )
                srt += time
                block = 1
                subnr = False
                number_b += 1

            elif match3 and block == 0:
                number = match3.group(1)
                srt += "%s\n" % number
                subnr = True
            else:
                sub = re.sub("<[^>]*>", "", i)
                srt += sub.strip()
                srt += "\n"

        srt = self.decode_html_entities(srt)
        return srt

    # This is used for Inputstream Adaptive versions below 2.4.6 (Kodi 18) and versions below 2.6.1 (Kodi 19)
    def get_subtitles(self, video_url, video_id):
        playlist = self.make_request(video_url, 'get', headers=None, text=True)
        self.log('Video playlist url: %s' % video_url)

        line1 = urljoin(video_url, urlparse(video_url).path)
        url = line1.replace("playlist.m3u8", "")

        paths = []
        for line in playlist.splitlines():
            if "#EXT-X-MEDIA:TYPE=SUBTITLES" in line:
                line2 = line.split(',')[7] #URI line from file playlist.m3u8
                #URI="exp=1537779948~acl=%2f*~data=hdntl~hmac=f62bc6753397ac3837b7e173b688e7bd45b2d79c12c40d2adeab3b67bc74f839/1155354603-prog_index.m3u8?version_hash=299f6771"

                line3 = line2.split('"')[1] #URI content
                # Response option 1: exp=1537735286~acl=%2f*~data=hdntl~hmac=de7dacddbe65cc734725c836cc0ffd0f1c0b069bde3999fa084141112dc9f57f/1155354603-prog_index.m3u8?hdntl=exp=1537735286~acl=/*~data=hdntl~hmac=de7dacddbe65cc734725c836cc0ffd0f1c0b069bde3999fa084141112dc9f57f&version_hash=5a73e2ce
                # Response option 2: 1155354603-prog_index.m3u8?version_hash=299f6771
                line4 = line3.replace("prog_index.m3u8", "0.vtt") # Change prog_index.m3u8 -> 0.vtt to get subtitle file url
                # Output: exp=1537779948~acl=%2f*~data=hdntl~hmac=f62bc6753397ac3837b7e173b688e7bd45b2d79c12c40d2adeab3b67bc74f839/1155354603-0.vtt?version_hash=299f6771
                subtitle_url = url + line4 # Subtitle file full address
                self.log('Full subtitle url: %s' % subtitle_url)

                lang_code = line.split(',')[3].split('"')[1] # Subtitle language, returns fi, sv, da or no

                # Save subtitle files to addon temp folder
                path = os.path.join(self.tempdir, '{0}.{1}.srt'.format(video_id, lang_code))
                # Don't download subtitles if files already exist in addon temp folder
                if os.path.exists(path) is False:
                    with open(path, 'w', encoding='utf-8') as subfile:
                        # Download subtitles
                        sub_str = self.make_request(subtitle_url, 'get')

                        # Convert WEBVTT subtitles to SRT subtitles
                        sub_str = sub_str.decode('utf-8', 'ignore')
                        sub_str = self.webvtt_to_srt(sub_str)

                        subfile.write(sub_str)
                paths.append(path)

        return paths

    def get_stream(self, video_id, video_type):
        stream = {}

        params = {'usePreAuth': 'true'}

        if video_type == 'channel':
            url = '{api_url}/playback/v2/channelPlaybackInfo/{video_id}'.format(api_url=self.api_url, video_id=video_id)
        else:
            url = '{api_url}/playback/v2/videoPlaybackInfo/{video_id}'.format(api_url=self.api_url, video_id=video_id)

        data_dict = json.loads(self.make_request(url, 'get', params=params, headers=None))['data']

        stream['hls_url'] = data_dict['attributes']['streaming']['hls']['url']
        stream['mpd_url'] = data_dict['attributes']['streaming']['dash']['url']
        stream['license_url'] = data_dict['attributes']['protection']['key_servers']['widevine']
        stream['drm_token'] = data_dict['attributes']['protection']['drm_token']
        stream['drm_enabled'] = data_dict['attributes']['protection']['drm_enabled']

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
