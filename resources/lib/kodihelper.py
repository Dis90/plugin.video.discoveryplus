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
            return None
        else:
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

    def add_item(self, title, params, items=False, folder=True, playable=False, info=None, art=None, content=False, menu=None, resume=None, total=None, folder_name=None, sort_method=None):
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
        if folder_name:
            xbmcplugin.setPluginCategory(self.handle, folder_name)
        if sort_method:
            if sort_method == 'unsorted':
                xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_UNSORTED)
                xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
            if sort_method == 'sort_label':
                xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
            if sort_method == 'sort_episodes':
                xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_EPISODE)
                xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_VIDEO_TITLE)

        recursive_url = self.base_url + '?' + urllib.urlencode(params)

        if items is False:
            xbmcplugin.addDirectoryItem(self.handle, recursive_url, listitem, folder)
        else:
            items.append((recursive_url, listitem, folder))
            return items

    def eod(self):
        """Tell Kodi that the end of the directory listing is reached."""
        xbmcplugin.endOfDirectory(self.handle)

    def refresh_list(self):
        """Refresh listing after adding or deleting favorites"""
        return xbmc.executebuiltin('Container.Refresh')

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

    def play_item(self, video_id, video_type):
        try:
            stream = self.d.get_stream(video_id, video_type)

            if video_type == 'video':
                playitem = xbmcgui.ListItem(path=stream['hls_url'])
                playitem.setProperty('inputstreamaddon', 'inputstream.adaptive')
                # Have to use hls for shows because mpd encryption type 'clearkey' is not supported by inputstream.adaptive
                playitem.setProperty('inputstream.adaptive.manifest_type', 'hls')
                playitem.setSubtitles(self.d.get_subtitles(stream['hls_url'], video_id))

                # Get current episode info
                current_episode = self.d.parse_page(video_id=video_id)

                images = current_episode['images']
                shows = current_episode['shows']

                for s in shows:
                    if s['id'] == current_episode['data']['relationships']['show']['data']['id']:
                        show_title = s['attributes']['name']

                if current_episode['data']['relationships'].get('images'):
                    for i in images:
                        if i['id'] == current_episode['data']['relationships']['images']['data'][0]['id']:
                            fanart_image = i['attributes']['src']
                else:
                    fanart_image = None


                duration = current_episode['data']['attributes']['videoDuration'] / 1000.0 if current_episode['data'][
                    'attributes'].get('videoDuration') else None

                info = {
                    'mediatype': 'episode',
                    'title': current_episode['data']['attributes'].get('name').lstrip(),
                    'tvshowtitle': show_title,
                    'season': current_episode['data']['attributes'].get('seasonNumber'),
                    'episode': current_episode['data']['attributes'].get('episodeNumber'),
                    'plot': current_episode['data']['attributes'].get('description'),
                    'duration': duration,
                    'aired': current_episode['data']['attributes'].get('airDate')
                }

                playitem.setInfo('video', info)

                art = {
                    'fanart': fanart_image,
                    'thumb': fanart_image
                }

                playitem.setArt(art)

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
        next_episode = self.helper.d.parse_page(current_video_id=self.video_id)

        if next_episode.get('data'):
            self.helper.log('Current episode name: ' + self.current_episode_info['title'].encode('utf-8'))
            self.helper.log('Next episode name: ' + next_episode['data'][0]['attributes'].get('name').encode('utf-8').lstrip())

            images = next_episode['images']
            shows = next_episode['shows']

            for s in shows:
                if s['id'] == next_episode['data'][0]['relationships']['show']['data']['id']:
                    next_episode_show_title = s['attributes']['name']

            if next_episode['data'][0]['relationships'].get('images'):
                for i in images:
                    if i['id'] == next_episode['data'][0]['relationships']['images']['data'][0]['id']:
                        next_episode_fanart_image = i['attributes']['src']
            else:
                next_episode_fanart_image = None

            next_info = dict(
                current_episode=dict(
                    episodeid=self.video_id,
                    tvshowid='',
                    title=self.current_episode_info['title'],
                    art={
                        'thumb': self.current_episode_art['thumb'],
                        'tvshow.clearart': '',
                        'tvshow.clearlogo': '',
                        'tvshow.fanart': self.current_episode_art['fanart'],
                        'tvshow.landscape': '',
                        'tvshow.poster': '',
                    },
                    season=self.current_episode_info['season'],
                    episode=self.current_episode_info['episode'],
                    showtitle=self.current_episode_info['tvshowtitle'],
                    plot=self.current_episode_info['title'],
                    playcount='',
                    rating=None,
                    firstaired=self.helper.d.parse_datetime(self.current_episode_info['aired']).strftime('%d.%m.%Y'),
                    runtime=self.current_episode_info['duration'],
                ),
                next_episode=dict(
                    episodeid=next_episode['data'][0]['id'],
                    tvshowid='',
                    title=next_episode['data'][0]['attributes'].get('name').lstrip(),
                    art={
                        'thumb': next_episode_fanart_image,
                        'tvshow.clearart': '',
                        'tvshow.clearlogo': '',
                        'tvshow.fanart': next_episode_fanart_image,
                        'tvshow.landscape:': '',
                        'tvshow.poster': '',
                    },
                    season=next_episode['data'][0]['attributes'].get('seasonNumber'),
                    episode=next_episode['data'][0]['attributes'].get('episodeNumber'),
                    showtitle=next_episode_show_title,
                    plot=next_episode['data'][0]['attributes'].get('description'),
                    playcount='',
                    rating=None,
                    firstaired=self.helper.d.parse_datetime(next_episode['data'][0]['attributes'].get('airDate')).strftime('%d.%m.%Y'),
                    runtime=next_episode['data'][0]['attributes'].get('videoDuration') / 1000.0,
                ),

                play_url='plugin://' + self.helper.addon_name + '/?action=play_upnext&next_video_id=' + next_episode['data'][0]['id'],
                notification_time='',
            )

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