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
import AddonSignals

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
        AddonSignals.registerSlot('upnextprovider', self.addon_name + '_play_action', self.play_upnext)

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

        return self.set_locale(self.get_setting('locale')) and self.set_login_credentials() and self.check_for_credentials()

    def set_login_credentials(self):
        username = self.get_setting('username')
        password = self.get_setting('password')

        if not username or not password:
            self.dialog('ok', self.language(30003), self.language(30004))
            self.get_addon().openSettings()
            return False
        else:
            return True

    def check_for_credentials(self):
        self.d.get_token() # Get new token before checking credentials
        if self.d.get_user_data()['attributes']['anonymous'] == True:
            self.login_process()
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

    def login_process(self):
        username = self.get_setting('username')
        password = self.get_setting('password')
        self.d.login(username, password)

    def reset_credentials(self):
        self.set_setting('username', '')
        self.set_setting('password', '')

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

    def play_upnext(self, data):
        self.log('Start playing from UpNext')
        self.log('Video id: ' + str(data['video_id']))

        xbmc.executebuiltin('PlayerControl(Stop)')
        media = 'plugin://' + self.addon_name + '/?action=play&video_id=' + data['video_id'] + '&video_type=video'
        xbmc.executebuiltin('PlayMedia({})'.format(media))

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

                # Do POST to playback progress when playback starts
                self.d.update_playback_progress('post', video_id, position)

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
        next_ep = self.helper.d.get_nextepisode_info(self.video_id)


        if next_ep['meta']['totalPages'] == 1:
            self.helper.log('Next episode name: ' + next_ep['data'][0]['attributes'].get('name').lstrip())

            next_show_title = json.loads(self.helper.d.get_metadata(json.dumps(next_ep['included']),
                                                                    next_ep['data'][0]['relationships']['show']['data'][
                                                                        'id']))['name']

            next_fanart_image = json.loads(self.helper.d.get_metadata(json.dumps(next_ep['included']),
                                                                      next_ep['data'][0]['relationships']['images'][
                                                                          'data'][0]['id']))['src'] if \
            next_ep['data'][0]['relationships'].get('images') else None

            self.helper.log('Current episode name: ' + self.current_episode_info['title'])

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
            current_episode["firstaired"] = self.current_episode_info['aired']

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
            next_episode["firstaired"] = next_ep['data'][0]['attributes'].get('airDate')

            play_info = {}
            play_info['video_id'] = next_ep['data'][0]['id']

            next_info = {
                'current_episode': current_episode,
                'next_episode': next_episode,
                'play_info': play_info,
                'notification_time': ''
            }

            AddonSignals.sendSignal("upnext_data", next_info, source_id=self.helper.addon_name)

        else:
            self.helper.log('No next episode available')

    def onPlayBackEnded(self):
        if self.running:
            self.running = False
            self.helper.log('Playback ended')
            video_totaltime = format(self.video_totaltime, '.0f')
            video_totaltime_msec = int(video_totaltime) * 1000

            self.helper.d.update_playback_progress('put', self.video_id, video_totaltime_msec)
            return xbmc.executebuiltin('Container.Refresh')

    def onPlayBackStopped(self):
        if self.running:
            self.running = False
            video_lastpos = format(self.video_lastpos, '.0f')
            video_totaltime = format(self.video_totaltime, '.0f')

            # Convert to milliseconds
            video_lastpos_msec = int(video_lastpos) * 1000
            video_totaltime_msec = int(video_totaltime) * 1000

            self.helper.log('totaltime_msec: ' + str(video_totaltime_msec))
            self.helper.log('lastpos_msec: ' + str(video_lastpos_msec))

            self.helper.d.update_playback_progress('put', self.video_id, video_lastpos_msec)

            return xbmc.executebuiltin('Container.Refresh')