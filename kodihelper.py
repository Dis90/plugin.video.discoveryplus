# -*- coding: utf-8 -*-

import os
import urllib
import re
import sys
import json

from dplay import Dplay

import xbmc
import xbmcvfs
import xbmcgui
import xbmcplugin
from xbmcaddon import Addon
import inputstreamhelper
from base64 import b64encode
import time
from datetime import datetime, timedelta

class KodiHelper(object):
    def __init__(self, base_url=None, handle=None):
        addon = self.get_addon()
        self.base_url = base_url
        self.handle = handle
        self.addon_path = xbmc.translatePath(addon.getAddonInfo('path'))
        self.addon_profile = xbmc.translatePath(addon.getAddonInfo('profile'))
        self.addon_name = addon.getAddonInfo('id')
        self.addon_version = addon.getAddonInfo('version')
        self.language = addon.getLocalizedString
        self.logging_prefix = '[%s-%s]' % (self.addon_name, self.addon_version)
        if not xbmcvfs.exists(self.addon_profile):
            xbmcvfs.mkdir(self.addon_profile)
        self.d = Dplay(self.addon_profile, self.get_setting('locale'), True)

    def get_addon(self):
        """Returns a fresh addon instance."""
        return Addon()

    def get_setting(self, setting_id):
        addon = self.get_addon()
        setting = addon.getSetting(setting_id)
        if setting == 'true':
            return True
        elif setting == 'false':
            return False
        else:
            return setting

    def set_setting(self, key, value):
        return self.get_addon().setSetting(key, value)

    def log(self, string):
        msg = '%s: %s' % (self.logging_prefix, string)
        xbmc.log(msg=msg, level=xbmc.LOGDEBUG)

    def dialog(self, dialog_type, heading, message=None, options=None, nolabel=None, yeslabel=None):
        dialog = xbmcgui.Dialog()
        if dialog_type == 'ok':
            dialog.ok(heading, message)
        elif dialog_type == 'yesno':
            return dialog.yesno(heading, message, nolabel=nolabel, yeslabel=yeslabel)
        elif dialog_type == 'select':
            ret = dialog.select(heading, options)
            if ret > -1:
                return ret
            else:
                return None

    def get_user_input(self, heading, hidden=False):
        keyboard = xbmc.Keyboard('', heading, hidden)
        keyboard.doModal()
        if keyboard.isConfirmed():
            query = keyboard.getText()
            self.log('User input string: %s' % query)
        else:
            query = None

        if query and len(query) > 0:
            return query
        else:
            return None

    def check_for_prerequisites(self):
        return self.set_locale(self.get_setting('locale')) and self.check_for_credentials()

    def check_for_credentials(self):
        self.d.get_token() # Get new token before checking credentials
        if self.d.get_user_data()['attributes']['anonymous'] == True:
            self.dialog('ok', self.language(30006), self.language(30015)) # Request to use Firefox to login
        return True

    def set_locale(self, locale=None):
        countries = ['fi_FI', 'sv_SE', 'da_DK', 'nb_NO']
        if not locale:
            options = ['dplay.fi', 'dplay.se', 'dplay.dk', 'dplay.no']
            selected_locale = self.dialog('select', self.language(30013), options=options)
            if selected_locale is None:
                selected_locale = 0  # default to .fi
            self.set_setting('locale_title', options[selected_locale])
            self.set_setting('locale', countries[selected_locale])

        return True

    def add_item(self, title, params, items=False, folder=True, playable=False, info=None, art=None, content=False, menu=None, resume=None, total=None):
        addon = self.get_addon()
        listitem = xbmcgui.ListItem(label=title)

        if playable:
            listitem.setProperty('IsPlayable', 'true')
            folder = False
        if resume:
            listitem.setProperty("ResumeTime", str(resume))
            listitem.setProperty("TotalTime", str(total))
        if art:
            listitem.setArt(art)
        else:
            art = {
                'icon': addon.getAddonInfo('icon'),
                'fanart': addon.getAddonInfo('fanart')
            }
            listitem.setArt(art)
        if info:
            listitem.setInfo('video', info)
        if content:
            xbmcplugin.setContent(self.handle, content)
        if menu:
            listitem.addContextMenuItems(menu)

        recursive_url = self.base_url + '?' + urllib.urlencode(params)

        if items is False:
            xbmcplugin.addDirectoryItem(self.handle, recursive_url, listitem, folder)
        else:
            items.append((recursive_url, listitem, folder))
            return items

    def eod(self):
        """Tell Kodi that the end of the directory listing is reached."""
        xbmcplugin.endOfDirectory(self.handle)

    # Up Next integration
    def upnext_signal(self, sender, next_info):
        """Send a signal to Kodi using JSON RPC"""
        self.log("Sending Up Next data: %s" % next_info)
        data = [self.to_unicode(b64encode(json.dumps(next_info).encode()))]
        self.notify(sender=sender + '.SIGNAL', message='upnext_data', data=data)

    def notify(self, sender, message, data):
        """Send a notification to Kodi using JSON RPC"""
        result = self.jsonrpc(method='JSONRPC.NotifyAll', params=dict(
            sender=sender,
            message=message,
            data=data,
        ))
        if result.get('result') != 'OK':
            self.log('Failed to send notification: ' + result.get('error').get('message'))
            return False
        self.log('Succesfully sent notification')
        return True

    def jsonrpc(self, **kwargs):
        """ Perform JSONRPC calls """
        if kwargs.get('id') is None:
            kwargs.update(id=0)
        if kwargs.get('jsonrpc') is None:
            kwargs.update(jsonrpc='2.0')

        self.log("Sending notification event data: %s" % kwargs)
        return json.loads(xbmc.executeJSONRPC(json.dumps(kwargs)))

    def to_unicode(self, text, encoding='utf-8', errors='strict'):
        """Force text to unicode"""
        if isinstance(text, bytes):
            return text.decode(encoding, errors=errors)
        return text

    def play_upnext(self, next_video_id):
        self.log('Start playing from Up Next')
        self.log('Next video id: ' + str(next_video_id))

        # Stop playback before playing next episode otherwise episode is not marked as watched
        xbmc.executebuiltin('PlayerControl(Stop)')

        media = 'plugin://' + self.addon_name + '/?action=play&video_id=' + next_video_id + '&video_type=video'
        xbmc.executebuiltin('PlayMedia({})'.format(media))
    # End of Up next integration

    def parse_datetime(self, date):
        """Parse date string to datetime object."""
        date_time_format = '%Y-%m-%dT%H:%M:%SZ'
        datetime_obj = datetime(*(time.strptime(date, date_time_format)[0:6]))
        return datetime_obj

    def play_item(self, video_id, video_type):
        try:
            stream = self.d.get_stream(video_id, video_type)

            if video_type == 'video':
                playitem = xbmcgui.ListItem(path=stream['hls_url'])
                playitem.setProperty('inputstreamaddon', 'inputstream.adaptive')
                # Have to use hls for shows because mpd encryption type 'clearkey' is not supported by inputstream.adaptive
                playitem.setProperty('inputstream.adaptive.manifest_type', 'hls')
                playitem.setSubtitles(self.d.get_subtitles(stream['hls_url']))

                # Get current episode info
                current_ep = self.d.get_current_episode_info(video_id)

                show_title = json.loads(self.d.get_metadata(json.dumps(current_ep['included']),
                                                                   current_ep['data']['relationships']['show']['data'][
                                                                       'id']))['name']

                fanart_image = json.loads(self.d.get_metadata(json.dumps(current_ep['included']),
                                                                     current_ep['data']['relationships']['images'][
                                                                         'data'][0]['id']))['src'] if \
                current_ep['data']['relationships'].get('images') else None

                duration = current_ep['data']['attributes']['videoDuration'] / 1000.0 if current_ep['data'][
                    'attributes'].get('videoDuration') else None

                info = {
                    'mediatype': 'episode',
                    'title': current_ep['data']['attributes'].get('name').lstrip(),
                    'tvshowtitle': show_title,
                    'season': current_ep['data']['attributes'].get('seasonNumber'),
                    'episode': current_ep['data']['attributes'].get('episodeNumber'),
                    'plot': current_ep['data']['attributes'].get('description'),
                    'duration': duration,
                    'aired': current_ep['data']['attributes'].get('airDate')
                }

                playitem.setInfo('video', info)

                art = {
                    'fanart': fanart_image,
                    'thumb': fanart_image
                }

                playitem.setArt(art)

                if current_ep['data']['attributes']['viewingHistory'].get('position'):
                    position = current_ep['data']['attributes']['viewingHistory']['position']
                else:
                    position = 0

                resume = position / 1000.0
                playitem.setProperty("ResumeTime", str(resume))
                playitem.setProperty("TotalTime", str(duration))

            elif video_type == 'channel':
                is_helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
                if is_helper.check_inputstream():
                    playitem = xbmcgui.ListItem(path=stream['mpd_url'])
                    playitem.setProperty('inputstreamaddon', 'inputstream.adaptive')
                    playitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')
                    playitem.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
                    header = 'PreAuthorization=' + stream['drm_token']
                    playitem.setProperty('inputstream.adaptive.license_key', stream['license_url'] + '|' + header + '|R{SSM}|')

            player = DplayPlayer()
            player.resolve(playitem)

            if video_type == 'video':
                player.video_id = video_id
                player.current_episode_info = info
                player.current_episode_art = art

                while not xbmc.abortRequested and player.running:
                    if player.isPlayingVideo():
                        player.video_totaltime = player.getTotalTime()
                        player.video_lastpos = player.getTime()

                    xbmc.sleep(1000)

        except self.d.DplayError as error:
            self.dialog('ok', self.language(30006), error.value)

class DplayPlayer(xbmc.Player):
    def __init__(self):
        base_url = sys.argv[0]
        handle = int(sys.argv[1])
        self.helper = KodiHelper(base_url, handle)
        self.video_id = 0
        self.current_episode_info = ''
        self.current_episode_art = ''
        self.video_lastpos = 0
        self.video_totaltime = 0
        self.running = False

    def resolve(self, li):
        xbmcplugin.setResolvedUrl(self.helper.handle, True, listitem=li)
        self.running = True

    def onPlayBackStarted(self):
        self.helper.log('Getting next episode info')
        next_ep = self.helper.d.get_next_episode_info(self.video_id)

        if next_ep['meta']['totalPages'] == 1:
            self.helper.log('Next episode name: ' + next_ep['data'][0]['attributes'].get('name').encode('utf-8').lstrip())

            next_show_title = json.loads(self.helper.d.get_metadata(json.dumps(next_ep['included']),
                                                                    next_ep['data'][0]['relationships']['show']['data'][
                                                                        'id']))['name']

            next_fanart_image = json.loads(self.helper.d.get_metadata(json.dumps(next_ep['included']),
                                                                      next_ep['data'][0]['relationships']['images'][
                                                                          'data'][0]['id']))['src'] if \
            next_ep['data'][0]['relationships'].get('images') else None

            self.helper.log('Current episode name: ' + self.current_episode_info['title'].encode('utf-8'))

            current_episode = {}
            current_episode["episodeid"] = self.video_id
            current_episode["tvshowid"] = ''
            current_episode["title"] = self.current_episode_info['title']
            current_episode["art"] = {}
            current_episode["art"]["tvshow.poster"] = ''
            current_episode["art"]["thumb"] = self.current_episode_art['thumb']
            current_episode["art"]["tvshow.fanart"] = self.current_episode_art['fanart']
            current_episode["art"]["tvshow.landscape"] = ''
            current_episode["art"]["tvshow.clearart"] = ''
            current_episode["art"]["tvshow.clearlogo"] = ''
            current_episode["plot"] = self.current_episode_info['title']
            current_episode["showtitle"] = self.current_episode_info['tvshowtitle']
            current_episode["playcount"] = ''
            current_episode["season"] = self.current_episode_info['season']
            current_episode["episode"] = self.current_episode_info['episode']
            current_episode["rating"] = None
            current_episode["firstaired"] = self.helper.parse_datetime(self.current_episode_info['aired']).strftime('%d.%m.%Y')
            current_episode["runtime"] = self.current_episode_info['duration']

            next_episode = {}
            next_episode["episodeid"] = next_ep['data'][0]['id']
            next_episode["tvshowid"] = ''
            next_episode["title"] = next_ep['data'][0]['attributes'].get('name').lstrip()
            next_episode["art"] = {}
            next_episode["art"]["tvshow.poster"] = ''
            next_episode["art"]["thumb"] = next_fanart_image
            next_episode["art"]["tvshow.fanart"] = next_fanart_image
            next_episode["art"]["tvshow.landscape"] = ''
            next_episode["art"]["tvshow.clearart"] = ''
            next_episode["art"]["tvshow.clearlogo"] = ''
            next_episode["plot"] = next_ep['data'][0]['attributes'].get('description')
            next_episode["showtitle"] = next_show_title
            next_episode["playcount"] = ''
            next_episode["season"] = next_ep['data'][0]['attributes'].get('seasonNumber')
            next_episode["episode"] = next_ep['data'][0]['attributes'].get('episodeNumber')
            next_episode["rating"] = None
            next_episode["firstaired"] = self.helper.parse_datetime(next_ep['data'][0]['attributes'].get('airDate')).strftime('%d.%m.%Y')
            next_episode["runtime"] = next_ep['data'][0]['attributes'].get('videoDuration') / 1000.0

            next_info = {
                'current_episode': current_episode,
                'next_episode': next_episode,
                'play_url': 'plugin://' + self.helper.addon_name + '/?action=play_upnext&next_video_id=' + next_ep['data'][0]['id'],
                'notification_time': ''
            }

            self.helper.upnext_signal(sender=self.helper.addon_name, next_info=next_info)

        else:
            self.helper.log('No next episode available')

    def onPlayBackEnded(self):
        if self.running:
            self.running = False
            self.helper.log('Playback ended')
            video_totaltime = format(self.video_totaltime, '.0f')
            video_totaltime_msec = int(video_totaltime) * 1000

            # Get new token before updating playback progress
            self.helper.d.get_token()

            # Dplay wants POST before PUT
            self.helper.d.update_playback_progress('post', self.video_id, video_totaltime_msec)
            self.helper.d.update_playback_progress('put', self.video_id, video_totaltime_msec)
            return xbmc.executebuiltin('Container.Update')

    def onPlayBackStopped(self):
        if self.running:
            self.running = False
            video_lastpos = format(self.video_lastpos, '.0f')
            video_totaltime = format(self.video_totaltime, '.0f')

            # Convert to milliseconds
            video_lastpos_msec = int(video_lastpos) * 1000
            video_totaltime_msec = int(video_totaltime) * 1000

            self.helper.log('Video totaltime msec: ' + str(video_totaltime_msec))
            self.helper.log('Video lastpos msec: ' + str(video_lastpos_msec))

            # Get new token before updating playback progress
            self.helper.d.get_token()

            # Dplay wants POST before PUT
            self.helper.d.update_playback_progress('post', self.video_id, video_lastpos_msec)
            self.helper.d.update_playback_progress('put', self.video_id, video_lastpos_msec)

            return xbmc.executebuiltin('Container.Update')