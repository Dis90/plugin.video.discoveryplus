# -*- coding: utf-8 -*-
"""
A Kodi-agnostic library for Dplay
"""
import os
from io import open, StringIO
import re
import json
import codecs
import cookielib
import time
import calendar
from datetime import datetime, timedelta

import requests
import urlparse
import sqlite3
import glob
import sys

class Dplay(object):
    def __init__(self, settings_folder, locale, debug=False):
        self.debug = debug
        self.locale = locale
        self.locale_suffix = self.locale.split('_')[1].lower()
        self.http_session = requests.Session()
        self.settings_folder = settings_folder
        self.tempdir = os.path.join(settings_folder, 'tmp')
        self.unwanted_menu_items = ('Hae mukaan', 'Info', 'Tablå', 'Live TV', 'TV-guide')
        if not os.path.exists(self.tempdir):
            os.makedirs(self.tempdir)

        cj = cookielib.CookieJar()

        self.get_firefox_cookies(cj, self.find_cookie_files()[0], 'dplay')
        self.http_session.cookies = cj

    def find_cookie_files(self):
        if sys.platform == 'darwin':
            cookie_files = glob.glob(
                os.path.expanduser('~/Library/Application Support/Firefox/Profiles/*default*/cookies.sqlite'))
        elif sys.platform.startswith('linux'):
            cookie_files = glob.glob(os.path.expanduser('~/.mozilla/firefox/*default*/cookies.sqlite'))
        elif sys.platform == 'win32':
            cookie_files = glob.glob(os.path.join(os.environ.get('APPDATA', ''),
                                                    'Mozilla/Firefox/Profiles/*default*/cookies.sqlite'))
        else:
            self.log('Unsupported operating system: ' + sys.platform)

        if cookie_files:
            return cookie_files
        else:
            raise self.log('Failed to find Firefox cookies')

    # From https://stackoverflow.com/questions/49502254/how-to-import-firefox-cookies-to-python-requests
    def get_firefox_cookies(self, cj, ff_cookies_file, domain_name):
        # Create local copy of cookies sqlite database. This is necessary in case this database is still being written
        # to while the user browses to avoid sqlite locking errors.
        tmp_cookies_file = os.path.join(self.tempdir, 'ff_cookies.sqlite')
        open(tmp_cookies_file, 'wb').write(open(ff_cookies_file, 'rb').read())

        con = sqlite3.connect(tmp_cookies_file)
        cur = con.cursor()

        cur.execute('select host, path, isSecure, expiry, name, value from moz_cookies '
                    'where host like "%{}%"'.format(domain_name))

        for item in cur.fetchall():
            c = cookielib.Cookie(0, item[4], item[5],
                                 None, False,
                                 item[0], item[0].startswith('.'), item[0].startswith('.'),
                                 item[1], False,
                                 item[2],
                                 item[3], item[3] == "",
                                 None, None, {})
            self.log(c)
            cj.set_cookie(c)
        con.close()

    class DplayError(Exception):
        def __init__(self, value):
            self.value = value

        def __str__(self):
            return repr(self.value)

    def log(self, string):
        if self.debug:
            try:
                print '[Dplay]: %s' % string
            except UnicodeEncodeError:
                # we can't anticipate everything in unicode they might throw at
                # us, but we can handle a simple BOM
                bom = unicode(codecs.BOM_UTF8, 'utf8')
                print '[Dplay]: %s' % string.replace(bom, '')
            except:
                pass

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
                        raise self.DplayError(error['detail'])

        except KeyError:
            pass
        except ValueError:  # when response is not in json
            pass

    def get_token(self):
        url = 'https://disco-api.dplay.{locale_suffix}/token'.format(locale_suffix=self.locale_suffix)

        #dplayfi dplayse dplayno dplaydk
        realm = 'dplay' + self.locale_suffix

        params = {
            'realm': realm
        }

        return self.make_request(url, 'get', params=params)

    def get_user_data(self):
        url = 'https://disco-api.dplay.{locale_suffix}/users/me'.format(locale_suffix=self.locale_suffix)

        data = self.make_request(url, 'get')
        return json.loads(data)['data']

    def get_menu(self):
        url = 'https://disco-api.dplay.{locale_suffix}/cms/collections/web-menubar'.format(locale_suffix=self.locale_suffix)

        params = {
            'include': 'default'
        }

        data = json.loads(self.make_request(url, 'get', params=params))
        return data

    def parse_page(self, page_path=None, collection_id=None, search_query=None, mandatoryParams=None, parameter=None, video_id=None, current_video_id=None):
        if page_path == 'menu':
            page = self.get_menu()
        elif page_path == 'favorites':
            page = self.get_favorites()
        elif page_path == 'search':
            page = self.get_search_shows(search_query)
        elif collection_id:
            if parameter:
                page = self.get_collections(collection_id, mandatoryParams, parameter)
            else:
                page = self.get_collections(collection_id, mandatoryParams)
        # Current episode info
        elif video_id:
            page = self.get_current_episode_info(video_id)
        elif current_video_id:
            page = self.get_next_episode_info(current_video_id)
        else:
            page = self.get_page(page_path)

        pages = []
        pageItems = []
        collections = []
        collectionItems = []
        images = []
        links = []
        shows = []
        videos = []
        channels = []
        routes = []
        genres = []

        # page['data'] is dict or list
        if isinstance(page['data'], dict):
            data = {
                'type': page['data']['type'],
                'attributes': page['data'].get('attributes'),
                'relationships': page['data'].get('relationships')
            }
        else:
            data = []
            for d in page['data']:
                data.append(d)

        if page.get('included'):
            for p in page['included']:

                # Pages
                if p['type'] == 'page':
                    pages.append({
                        'id': p['id'],
                        'attributes': p['attributes'],
                        'relationships': p['relationships']
                    })

                # PageItems
                if p['type'] == 'pageItem':
                    pageItems.append({
                        'id': p['id'],
                        'relationships': p['relationships']
                    })

                # Collections
                if p['type'] == 'collection':
                    collections.append({
                        'id': p['id'],
                        'attributes': p['attributes'],
                        'relationships': p.get('relationships')
                    })

                # CollectionItems
                if p['type'] == 'collectionItem':
                    collectionItems.append({
                        'id': p['id'],
                        'attributes': p.get('attributes'),
                        'relationships': p['relationships']
                    })

                # Images
                if p['type'] == 'image':
                    images.append({
                        'id': p['id'],
                        'attributes': p['attributes']
                    })

                # Shows
                if p['type'] == 'show':
                    shows.append({
                        'id': p['id'],
                        'attributes': p['attributes'],
                        'relationships': p['relationships']
                    })

                # Videos
                if p['type'] == 'video':
                    videos.append({
                        'id': p['id'],
                        'attributes': p['attributes'],
                        'relationships': p['relationships']
                    })

                # Channels
                if p['type'] == 'channel':
                    channels.append({
                        'id': p['id'],
                        'attributes': p['attributes'],
                        'relationships': p['relationships']
                    })

                # Genres
                if p['type'] == 'genre':
                    genres.append({
                        'id': p['id'],
                        'attributes': p['attributes']
                    })

                # Links (menu, categories)
                if p['type'] == 'link':
                    links.append({
                        'id': p['id'],
                        'attributes': p['attributes'],
                        'relationships': p.get('relationships')
                    })

                # Routes
                if p['type'] == 'route':
                    routes.append({
                        'id': p['id'],
                        'attributes': p['attributes']
                    })

        page_sorted = ({'data': data, 'pages': pages, 'pageItems': pageItems, 'collections': collections, 'collectionItems': collectionItems, 'images': images, 'shows': shows, 'videos': videos, 'channels': channels, 'genres': genres, 'links': links, 'routes': routes})

        return page_sorted

    def get_page(self, path):
        url = 'https://disco-api.dplay.{locale_suffix}/cms/routes{path}'.format(locale_suffix=self.locale_suffix, path=path)

        params = {
            'decorators': 'viewingHistory',
            'include': 'default'
        }

        data = json.loads(self.make_request(url, 'get', params=params))
        return data

    def get_collections(self, collection_id, mandatoryParams=None, parameter=None):
        if mandatoryParams and parameter:
            url = 'https://disco-api.dplay.{locale_suffix}/cms/collections/{collection_id}?{mandatoryParams}&{parameter}'.format(locale_suffix=self.locale_suffix, collection_id=collection_id, mandatoryParams=mandatoryParams, parameter=parameter)
        elif mandatoryParams is None and parameter:
            url = 'https://disco-api.dplay.{locale_suffix}/cms/collections/{collection_id}?{parameter}'.format(locale_suffix=self.locale_suffix, collection_id=collection_id, parameter=parameter)
        else:
            url = 'https://disco-api.dplay.{locale_suffix}/cms/collections/{collection_id}?{mandatoryParams}'.format(locale_suffix=self.locale_suffix, collection_id=collection_id, mandatoryParams=mandatoryParams)

        params = {
            'decorators': 'viewingHistory',
            'include': 'default',
            'page[items.number]': 1,
            'page[items.size]': 100
        }

        data = json.loads(self.make_request(url, 'get', params=params))
        return data

    def get_search_shows(self, search_query):
        url = 'https://disco-api.dplay.{locale_suffix}/content/shows'.format(locale_suffix=self.locale_suffix)

        params = {
            'include': 'genres,images,primaryChannel.images,contentPackages',
            'page[size]': 100,
            'query': search_query
        }

        data = json.loads(self.make_request(url, 'get', params=params))
        return data

    def get_favorites(self):
        url = 'https://disco-api.dplay.{locale_suffix}/users/me/favorites'.format(locale_suffix=self.locale_suffix)
        params = {
            'include': 'default'
        }

        data = json.loads(self.make_request(url, 'get', params=params))
        return data

    def update_playback_progress(self, method, video_id, position):
        url = 'https://disco-api.dplay.{locale_suffix}/playback/v2/report/video/{video_id}'.format(locale_suffix=self.locale_suffix, video_id=video_id)

        params = {
            'position': position
        }

        return self.make_request(url, method, params=params)

    def get_current_episode_info(self, video_id):
        url = 'https://disco-api.dplay.{locale_suffix}/content/videos/{video_id}'.format(locale_suffix=self.locale_suffix, video_id=video_id)

        params = {
            'decorators': 'viewingHistory',
            'include': 'genres,images,primaryChannel,show,show.images'
        }

        data = json.loads(self.make_request(url, 'get', params=params))
        return data

    def get_next_episode_info(self, current_video_id):
        url = 'https://disco-api.dplay.{locale_suffix}/content/videos/{video_id}/next'.format(locale_suffix=self.locale_suffix, video_id=current_video_id)

        params = {
            'algorithm': 'naturalOrder',
            'include': 'genres,images,primaryChannel,show,show.images,contentPackages'
        }

        data = json.loads(self.make_request(url, 'get', params=params))
        return data

    def add_or_delete_favorite(self, method, show_id):
        # POST for adding and DELETE for delete
        url = 'https://disco-api.dplay.{locale_suffix}/users/me/favorites/shows/{show_id}'.format(locale_suffix=self.locale_suffix, show_id=show_id)

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

    # Delete this when Kodi starts to support webvtt subtitles over .m3u8 hls stream
    def get_subtitles(self, video_url, video_id):
        playlist = self.make_request(video_url, 'get', headers=None, text=True)
        self.log('Video playlist url: ' + video_url)

        line1 = urlparse.urljoin(video_url, urlparse.urlparse(video_url).path)
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
                self.log('Full subtitle url: ' + subtitle_url)

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
            url = 'https://disco-api.dplay.{locale_suffix}/playback/v2/channelPlaybackInfo/{video_id}'.format(locale_suffix=self.locale_suffix, video_id=video_id)
        else:
            url = 'https://disco-api.dplay.{locale_suffix}/playback/v2/videoPlaybackInfo/{video_id}'.format(locale_suffix=self.locale_suffix, video_id=video_id)

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
