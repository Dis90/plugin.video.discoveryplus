# -*- coding: utf-8 -*-
"""
A Kodi-agnostic library for Dplay
"""
import os
from io import open
import json
import codecs
import cookielib
import time
from datetime import datetime
from pycaption import WebVTTReader, SRTWriter

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

    def get_homepage(self):
        url = 'https://disco-api.dplay.{locale_suffix}/cms/collections/home-page'.format(locale_suffix=self.locale_suffix)

        params = {
            'decorators': 'viewingHistory',
            'include': 'default'
        }

        data = json.loads(self.make_request(url, 'get', params=params))
        return data

    def get_shows(self, search_query=None, letter=None):
        url = 'https://disco-api.dplay.{locale_suffix}/content/shows'.format(locale_suffix=self.locale_suffix)

        if search_query:
            params = {
                'include': 'genres,images,primaryChannel.images,contentPackages',
                'page[size]': 20,
                'query': search_query
            }
        elif letter:
            params = {
                'include': 'genres,images,primaryChannel.images,contentPackages',
                'filter[name.startsWith]': letter,
                'page[size]': 100,
                'page[number]': '1'
            }
        else: # Get popular shows
            params = {
                'include': 'genres,images,primaryChannel.images,contentPackages',
                'page[size]': 100,
                'page[number]': '1',
                'sort': 'views.lastMonth'
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

    def get_metadata(self, data, id):
        for i in json.loads(data):
            if i['id'] == id:
                return json.dumps(i['attributes'])

    def get_channels(self):
        url = 'https://disco-api.dplay.{locale_suffix}/cms/collections/kanaler'.format(locale_suffix=self.locale_suffix)

        params = {
            'include': 'default'
        }

        data = json.loads(self.make_request(url, 'get', params=params))
        return data

    def get_channel_shows(self, channel_id):
        url = 'https://disco-api.dplay.{locale_suffix}/cms/collections/channel/{channel_id}'.format(locale_suffix=self.locale_suffix, channel_id=channel_id)

        params = {
            'include': 'default'
        }

        data = json.loads(self.make_request(url, 'get', params=params))
        return data

    def get_videos(self, show_id, season_number):
        url = 'https://disco-api.dplay.{locale_suffix}/content/videos'.format(locale_suffix=self.locale_suffix)

        params = {
            'decorators': 'viewingHistory',
            'include': 'images,primaryChannel,show,contentPackages',
            'filter[videoType]': 'EPISODE, LIVE, FOLLOW_UP',
            'filter[show.id]': show_id,
            'filter[seasonNumber]': season_number,
            'page[size]': 100,
            'page[number]': '1',
            'sort': 'episodeNumber'
        }

        data = json.loads(self.make_request(url, 'get', params=params))
        return data

    def update_playback_progress(self, method, video_id, position):
        url = 'https://disco-api.dplay.{locale_suffix}/playback/report/video/{video_id}'.format(locale_suffix=self.locale_suffix, video_id=video_id)

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

    def get_nextepisode_info(self, current_video_id):
        url = 'https://disco-api.dplay.{locale_suffix}/content/videos/{video_id}/next'.format(locale_suffix=self.locale_suffix, video_id=current_video_id)

        params = {
            'algorithm': 'naturalOrder',
            'include': 'genres,images,primaryChannel,show,show.images,contentPackages'
        }

        data = json.loads(self.make_request(url, 'get', params=params))
        return data

    def webvtt_to_srt_conversion(self, sub_webvtt):
        caption_set = WebVTTReader().read(sub_webvtt)
        output = SRTWriter().write(caption_set)

        return output

    # Delete this when Kodi starts to support webvtt subtitles over .m3u8 hls stream
    def get_subtitles(self, video_url):
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
                # Download subtitles
                sub_str = self.make_request(subtitle_url, 'get')
                # Convert WEBVTT subtitles to SRT subtitles
                sub_str = sub_str.decode('utf-8', 'ignore')
                sub_str = self.webvtt_to_srt_conversion(sub_str)
                # Save subtitle files to addon tmp dir
                path = os.path.join(self.tempdir, '{0}.srt'.format(lang_code))
                with open(path, 'w', encoding='utf-8') as subfile:
                    subfile.write(sub_str)
                paths.append(path)

        return paths

    def get_stream(self, video_id, video_type):
        stream = {}

        params = {'usePreAuth': 'true'}

        url = 'https://disco-api.dplay.{locale_suffix}/playback/{video_type}PlaybackInfo/{video_id}'.format(locale_suffix=self.locale_suffix, video_type=video_type, video_id=video_id)

        data_dict = json.loads(self.make_request(url, 'get', params=params, headers=None))['data']

        stream['hls_url'] = data_dict['attributes']['streaming']['hls']['url']
        stream['mpd_url'] = data_dict['attributes']['streaming']['dash']['url']
        stream['license_url'] = data_dict['attributes']['protection']['key_servers']['widevine']
        stream['drm_token'] = data_dict['attributes']['protection']['drm_token']

        return stream

    def parse_datetime(self, date):
        """Parse date string to datetime object."""
        date_time_format = '%Y-%m-%dT%H:%M:%SZ'
        datetime_obj = datetime(*(time.strptime(date, date_time_format)[0:6]))

        return datetime_obj

    def get_current_time(self):
        """Return the current local time."""
        return datetime.now()
