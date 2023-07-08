# -*- coding: utf-8 -*-

import os
import sys
import json

from .dplay import Dplay

import xbmc
import xbmcvfs
import xbmcgui
import xbmcplugin
from xbmcaddon import Addon
import inputstreamhelper
from base64 import b64encode

try:  # Python 3
    from urllib.parse import urlencode
except ImportError:  # Python 2
    from urllib import urlencode


class KodiHelper(object):
    def __init__(self, base_url=None, handle=None):
        addon = self.get_addon()
        self.base_url = base_url
        self.handle = handle
        self.addon_path = xbmcvfs.translatePath(addon.getAddonInfo('path'))
        self.addon_profile = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
        self.addon_name = addon.getAddonInfo('id')
        self.addon_version = addon.getAddonInfo('version')
        self.language = addon.getLocalizedString
        self.logging_prefix = '[%s-%s]' % (self.addon_name, self.addon_version)
        if not xbmcvfs.exists(self.addon_profile):
            xbmcvfs.mkdir(self.addon_profile)
        self.d = Dplay(self.addon_profile, self.logging_prefix, self.get_setting('numresults'), self.get_setting('cookiestxt'),
                       self.get_setting('cookiestxt_file'), self.get_setting('us_uhd'), self.get_setting('drm_supported'), self.get_kodi_version())

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

    def get_kodi_version(self):
        version = xbmc.getInfoLabel('System.BuildVersion')
        return version.split('.')[0]

    def set_setting(self, key, value):
        return self.get_addon().setSetting(key, value)

    def log(self, string):
        msg = '%s: %s' % (self.logging_prefix, string)
        xbmc.log(msg=msg, level=xbmc.LOGDEBUG)

    def dialog(self, dialog_type, heading, message=None, options=None, nolabel=None, yeslabel=None, useDetails=False):
        dialog = xbmcgui.Dialog()
        if dialog_type == 'ok':
            dialog.ok(heading, message)
        elif dialog_type == 'yesno':
            return dialog.yesno(heading, message, nolabel=nolabel, yeslabel=yeslabel)
        elif dialog_type == 'select':
            ret = dialog.select(heading, options, useDetails=useDetails)
            if ret > -1:
                return ret
            else:
                return None
        elif dialog_type == 'numeric':
            ret = dialog.numeric(0, heading, '', 1)
            if ret:
                return ret
            else:
                return None

    def profiles_dialog(self):
        profiles_dict = self.d.get_profiles()
        avatars = self.d.get_avatars()
        user_data = self.d.get_user_data()

        profiles = []

        for profile in profiles_dict['data']:
            image_url = None
            for avatar in avatars:
                if avatar['id'] == profile['attributes']['avatarName'].lower():
                    image_url = avatar['attributes']['imageUrl']
                # Use default avatar if profile doesn't have avatar
                elif avatar['id'] == 'default':
                    image_url = avatar['attributes']['imageUrl']

            profile_name = profile['attributes']['profileName']
            info_line = ''
            if profile['id'] == user_data['attributes']['selectedProfileId']:
                profile_name = '[B]{}[/B]'.format(profile_name) # Bold current profile name
                info_line = self.language(30013) # Current profile
            elif profile['attributes'].get('pinRestricted'):
                info_line = self.language(30037)

            # Kids profiles
            if profile.get('relationships'):
                profile_restriction_level_id = profile['relationships']['contentRestrictionLevel']['data']['id']
                restriction_level = [x for x in profiles_dict['included'] if x['id'] == profile_restriction_level_id][0]
                # Restriction level name and description
                info_line += self.language(30008) + '[' + restriction_level['attributes']['name'] + '] ' + restriction_level['attributes']['description']

            li = xbmcgui.ListItem(
                label=profile_name,
                label2=info_line
            )
            li.setArt({
                'thumb': image_url
            })

            profiles.append(li)

        index = self.dialog('select', self.language(30036), options=profiles, useDetails=True)
        if index is not None:
            if profiles_dict['data'][index]['attributes'].get('pinRestricted'):
                self.profile_pin_dialog(profiles_dict['data'][index])
            else:
                self.d.switch_profile(profiles_dict['data'][index]['id'])
                self.set_setting('profileselected', 'true')
                self.refresh_list()

    def profile_pin_dialog(self, profile):
        pin = self.dialog('numeric', self.language(30038) + ' {}'.format(profile['attributes']['profileName']))
        if pin:
            try:
                self.d.switch_profile(profile['id'], pin)
                self.set_setting('profileselected', 'true')
                self.refresh_list()
            # Invalid pin
            except self.d.DplusError as error:
                self.dialog('ok', self.language(30006), error.value)
                self.set_setting('profileselected', 'false')

    def linkDevice_dialog(self):
        linkingCode = self.d.linkDevice_initiate()['data']['attributes']['linkingCode']

        dialog_text = self.language(30046).format(linkDevice_url=self.d.linkDevice_url, linkingCode=linkingCode)

        pDialog = xbmcgui.DialogProgress()
        pDialog.create(self.language(30030), dialog_text)

        not_logged = True
        while not_logged:
            if pDialog.iscanceled():
                break
            xbmc.sleep(5000)  # Check login every 5 seconds
            link_token = self.d.linkDevice_login()
            if link_token:
                pDialog.update(50)
                # Save cookie
                self.d.get_token(link_token)
                not_logged = False
        pDialog.update(100)
        pDialog.close()

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

    def reset_settings(self):
        self.set_setting('numresults', '100')
        self.set_setting('cookiestxt', 'true')
        self.set_setting('cookiestxt_file', '')
        self.set_setting('cookie', '')
        self.set_setting('sync_playback', 'true')
        self.set_setting('us_uhd', 'false')
        self.set_setting('use_isa', 'true')
        self.set_setting('seasonsonly', 'false')
        self.set_setting('flattentvshows', 'false')
        self.set_setting('iptv.enabled', 'false')
        self.set_setting('profileselected', 'false')
        self.set_setting('select_first_unwatched', '0')

        # Remove cookies file
        cookie_file = os.path.join(self.addon_profile, 'cookie_file')
        if os.path.exists(cookie_file):
            os.remove(cookie_file)

    def add_item(self, title, url, folder=True, playable=False, info=None, art=None, menu=None,
                 resume=None, total=None, position=None):
        addon = self.get_addon()
        listitem = xbmcgui.ListItem(label=title, offscreen=True)

        if playable:
            listitem.setProperty('IsPlayable', 'true')
            listitem.setProperty('get_stream_details_from_player', 'true')
            folder = False
        if resume is not None:
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
        if menu:
            listitem.addContextMenuItems(menu)
        # SpecialSort
        if position:
            listitem.setProperty("SpecialSort", position)

        xbmcplugin.addDirectoryItem(self.handle, url, listitem, folder)

    def add_sort_methods(self, sort_method):
        if sort_method == 'unsorted':
            xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_UNSORTED)
            xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
        if sort_method == 'sort_label':
            xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
        if sort_method == 'sort_episodes':
            xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_EPISODE)
            xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_VIDEO_TITLE)

    def finalize_directory(self, content_type=None, sort_method='unsorted', title=None):
        """Finalize a directory listing. Set title, available sort methods and content type"""
        if title:
            xbmcplugin.setPluginCategory(self.handle, title)
        if content_type:
            xbmcplugin.setContent(self.handle, content_type)
        self.add_sort_methods(sort_method)

    def eod(self, cache=True):
        """Tell Kodi that the end of the directory listing is reached."""
        xbmcplugin.endOfDirectory(self.handle, cacheToDisc=cache)

    def refresh_list(self):
        """Refresh listing"""
        return xbmc.executebuiltin('Container.Refresh')

    def autoSelect_precheck(self, contentType):
        totalUnwatched = int(xbmc.getInfoLabel("Container.TotalUnWatched"))
        content = xbmc.getInfoLabel('Container.Content')
        # Check if all items are already watched
        if totalUnwatched == 0:
            return False
        # If currently displayed content type is different than in loaded data we don't want to autoscroll
        # Example when using view Landscape Combined in seasons page on skin Arctic Horizon 2 and changing season
        # add-on will load episodes of season which will trigger autoscroll
        if content != contentType:
            return False
        # select_first_unwatched 1 = On first entry
        if self.get_setting('select_first_unwatched') == '1':
            if int(xbmc.getInfoLabel('ListItem.CurrentItem')) > 1:
                return False
        # If content is seasons but season markers is false
        if content == 'seasons' and self.get_setting('season_markers') is False:
            return False
        return True

    def autoSelect(self, contentType):
        # Auto select first unwatched season or episode. Kodi built in feature only works for Kodi library
        # Inspiration taken from here https://forum.kodi.tv/showthread.php?tid=373589
        # Wait list to complete
        xbmc.sleep(100)
        # Get sort direction
        sortOrderAsc = xbmc.getCondVisibility('Container.SortDirection(ascending)')
        try:
            totalItems = int(xbmc.getInfoLabel('Container.NumAllItems'))
        except:
            # totalItems = 0
            return
        if not self.autoSelect_precheck(contentType):
            return

        # Get current container ID
        window = xbmcgui.Window(xbmcgui.getCurrentWindowId())
        containerID = window.getFocusId()

        nextItemIndex = 0
        for itemIndex in range(totalItems):
            template = 'Container({id}).ListItemAbsolute({index}).'.format(id=containerID, index=itemIndex)
            label = xbmc.getInfoLabel(template + 'Label')
            # PlayCount infolabel:
            # A string that's either empty or a stringified number, the times the item
            # has been completely played ("", "1", "2" etc). This leaves that "watched"
            # checkmark on items that aren't partially played.
            playcount = xbmc.getInfoLabel(template + 'PlayCount')
            if playcount:
                # This ListItem has been completely played.
                pass
            # PercentPlayed infolabel:
            # A stringified number from 0 to 100, (eg "37"), which is how far the video has been played.
            # If the number is non-zero then the video can be resumed (that half-filled circle icon).
            percentPlayed = xbmc.getInfoLabel(template + 'PercentPlayed')
            if playcount == '' and percentPlayed == '0' and label != '..':
                # This ListItem is not watched
                nextItemIndex = itemIndex
                # Stop looping in first match if sort order is ascending
                if sortOrderAsc:
                    break
            if percentPlayed != '0' and label != '..':
                # This ListItem has been partially played.
                nextItemIndex = itemIndex
                # Stop looping in first match if sort order is ascending
                if sortOrderAsc:
                    break

        # Select the chosen item
        try:
            xbmc.executebuiltin(
                'SetFocus({id},{selectedIndex},absolute)'.format(id=containerID, selectedIndex=nextItemIndex))
        except:
            pass

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
            self.log('Failed to send notification: %s' % result.get('error').get('message'))
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

    # End of Up next integration

    def play_item(self, video_id, video_type):
        useIsa = self.get_setting('use_isa')
        try:
            stream = self.d.get_stream(video_id, video_type)
            playitem = xbmcgui.ListItem(path=stream['url'], offscreen=True)

            # at least d+ India has dash streams that are not drm protected
            # website uses hls stream for those videos but we are using first stream in PlaybackInfo and that can be dash
            # this is tested to work
            if stream['type'] == 'dash':
                # Kodi 19 Matrix or higher
                if self.get_kodi_version() >= '19':
                    playitem.setProperty('inputstream', 'inputstream.adaptive')
                # Kodi 18 Leia
                else:
                    playitem.setProperty('inputstreamaddon', 'inputstream.adaptive')

                playitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')

                # DRM enabled = use Widevine
                if stream['drm_enabled']:
                    is_helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
                    if is_helper.check_inputstream():
                        playitem.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
                        if stream['drm_token']:
                            header = 'PreAuthorization=' + stream['drm_token']
                            playitem.setProperty('inputstream.adaptive.license_key',
                                                stream['license_url'] + '|' + header + '|R{SSM}|')
                        else:
                            playitem.setProperty('inputstream.adaptive.license_key', stream['license_url'] + '||R{SSM}|')
            else:

                if useIsa:
                    # Kodi 19 Matrix or higher
                    if self.get_kodi_version() >= '19':
                        playitem.setProperty('inputstream', 'inputstream.adaptive')
                    # Kodi 18 Leia
                    else:
                        playitem.setProperty('inputstreamaddon', 'inputstream.adaptive')

                    playitem.setProperty('inputstream.adaptive.manifest_type', 'hls')

            # Live TV
            if video_type == 'channel':
                xbmcplugin.setResolvedUrl(self.handle, True, listitem=playitem)
            # Get metadata to use for Up next
            else:
                # Get current episode info
                current_episode = self.d.get_current_episode_info(video_id=video_id)

                images = list(filter(lambda x: x['type'] == 'image', current_episode['included']))
                shows = list(filter(lambda x: x['type'] == 'show', current_episode['included']))
                channels = list(filter(lambda x: x['type'] == 'channel', current_episode['included']))

                show = [x for x in shows if x['id'] == current_episode['data']['relationships']['show']['data']['id']][0]

                # Content rating
                mpaa = None
                if current_episode['data']['attributes'].get('contentRatings'):
                    for contentRating in current_episode['data']['attributes']['contentRatings']:
                        if contentRating['system'] == self.d.contentRatingSystem:
                            mpaa = contentRating['code']

                # Channel
                primaryChannel = None
                if current_episode['data']['relationships'].get('primaryChannel'):
                    primaryChannel = [x['attributes']['name'] for x in channels if
                                      x['id'] == current_episode['data']['relationships']['primaryChannel']['data']['id']][0]

                # Thumbnail
                video_thumb_image = None
                if current_episode['data']['relationships'].get('images'):
                    video_thumb_image = [x['attributes']['src'] for x in images if
                                         x['id'] == current_episode['data']['relationships']['images']['data'][0]['id']][0]

                duration = current_episode['data']['attributes']['videoDuration'] / 1000.0 if current_episode['data'][
                    'attributes'].get('videoDuration') else None

                aired = ''
                if current_episode['data']['attributes'].get('earliestPlayableStart'):
                    aired = str(self.d.parse_datetime(current_episode['data']['attributes']['earliestPlayableStart'])
                                .strftime('%d.%m.%Y'))

                if current_episode['data']['attributes']['videoType'] == 'LIVE':
                    info = {
                        'mediatype': 'video',
                        'title': current_episode['data']['attributes'].get('name').lstrip(),
                        'plot': current_episode['data']['attributes'].get('description'),
                        'studio': primaryChannel,
                        'duration': duration,
                        'aired': aired,
                    }
                else:
                    info = {
                        'mediatype': 'episode',
                        'title': current_episode['data']['attributes'].get('name').lstrip(),
                        'tvshowtitle': show['attributes']['name'],
                        'season': current_episode['data']['attributes'].get('seasonNumber'),
                        'episode': current_episode['data']['attributes'].get('episodeNumber'),
                        'plot': current_episode['data']['attributes'].get('description'),
                        'duration': duration,
                        'aired': current_episode['data']['attributes'].get('airDate'),
                        'mpaa': mpaa,
                        'studio': primaryChannel
                    }

                playitem.setInfo('video', info)

                art = self.d.parse_artwork(show['relationships'].get('images'), images, video_thumb=video_thumb_image)

                playitem.setArt(art)

                player = DplusPlayer()
                player.resolve(playitem)

                player.video_id = video_id
                player.video_notification_time = stream['videoAboutToEnd'] / 1000.0 if stream.get('videoAboutToEnd') else ''
                player.current_show_id = current_episode['data']['relationships']['show']['data']['id']
                player.current_episode_info = info
                player.current_episode_art = art

                monitor = xbmc.Monitor()
                while not monitor.abortRequested() and player.playing:
                    if player.isPlayingVideo():
                        player.video_totaltime = player.getTotalTime()
                        player.video_lastpos = player.getTime()

                    xbmc.sleep(1000)

        except self.d.DplusError as error:
            self.dialog('ok', self.language(30006), error.value)

class DplusPlayer(xbmc.Player):
    def __init__(self):
        base_url = sys.argv[0]
        handle = int(sys.argv[1])
        self.helper = KodiHelper(base_url, handle)
        #self.video_id = None
        #self.current_show_id = None
        #self.current_episode_info = ''
        #self.current_episode_art = ''
        #self.video_lastpos = 0
        #self.video_totaltime = 0
        self.playing = False
        self.paused = False
        self.ff_rw = False

    def resolve(self, li):
        xbmcplugin.setResolvedUrl(self.helper.handle, True, listitem=li)
        self.playing = True

    def onPlayBackStarted(self):  # pylint: disable=invalid-name
        """Called when user starts playing a file"""
        self.helper.log('[DplusPlayer] Event onPlayBackStarted')

        self.onAVStarted()

    def onAVStarted(self):  # pylint: disable=invalid-name
        """Called when Kodi has a video or audiostream"""
        self.helper.log('[DplusPlayer] Event onAVStarted')
        self.push_upnext()

    def onPlayBackSeek(self, time, seekOffset):  # pylint: disable=invalid-name
        """Called when user seeks to a time"""
        self.helper.log('[DplusPlayer] Event onPlayBackSeek time=' + str(time) + ' offset=' + str(seekOffset))
        self.video_lastpos = time // 1000

        # If we seek beyond the end, exit Player
        if self.video_lastpos >= self.video_totaltime:
            self.stop()

    def onPlayBackSpeedChanged(self, speed):
        """Called when players speed changes (eg. user FF/RW)."""
        self.helper.log('[DplusPlayer] Event onPlayBackSpeedChanged speed=' + str(speed))

        # 1 is normal playback speed
        if speed != 1:
            self.ff_rw = True

    def onPlayBackPaused(self):  # pylint: disable=invalid-name
        """Called when user pauses a playing file"""
        self.helper.log('[DplusPlayer] Event onPlayBackPaused')
        self.update_playback_progress()
        self.paused = True

    def onPlayBackEnded(self):  # pylint: disable=invalid-name
        """Called when Kodi has ended playing a file"""
        self.helper.log('[DplusPlayer] Event onPlayBackEnded')
        # Up Next/Kodi calls onPlayBackEnded two times if user doesn't select Watch Now and video_lastpos is not available on first time
        try:
            self.update_playback_progress()
        except AttributeError:
            return
        self.playing = False
        # Up Next calls onPlayBackEnded before onPlayBackStarted if user doesn't select Watch Now
        # Reset current video id
        self.video_id = None

    def onPlayBackStopped(self):  # pylint: disable=invalid-name
        """Called when user stops Kodi playing a file"""
        self.helper.log('[DplusPlayer] Event onPlayBackStopped')
        self.update_playback_progress()
        self.playing = False
        # Reset current video id
        self.video_id = None

    def onPlayerExit(self):  # pylint: disable=invalid-name
        """Called when player exits"""
        self.helper.log('[DplusPlayer] Event onPlayerExit')
        self.update_playback_progress()
        self.playing = False

    def onPlayBackResumed(self):  # pylint: disable=invalid-name
        """Called when user resumes a paused file or a next playlist item is started"""
        if self.paused:
            suffix = 'after pausing'
            self.paused = False
        elif self.ff_rw:
            suffix = 'after ff/rw'
            self.ff_rw = False
        # playlist change
        # Up Next uses this when user clicks Watch Now, only happens if user is watching first episode in row after
        # that onPlayBackEnded is used even if user clicks Watch Now
        else:
            suffix = 'after playlist change'
            self.paused = False
            self.update_playback_progress()
            # Reset current video id
            self.video_id = None
        log = '[DplusPlayer] Event onPlayBackResumed ' + suffix
        self.helper.log(log)

    def push_upnext(self):
        if not self.video_id:
            return
        self.helper.log('Getting next episode info')
        next_episode = self.helper.d.get_next_episode_info(current_video_id=self.video_id)

        if next_episode.get('data'):
            # discovery+ can recommend to watch episode from different TV show when all episodes are watched.
            # So we only send data to Up Next when episode is from same TV show what is currently playing.
            if self.current_show_id == next_episode['data'][0]['relationships']['show']['data']['id']:
                self.helper.log('Current episode name: %s' % self.current_episode_info['title'].encode('utf-8'))
                self.helper.log(
                    'Next episode name: %s' % next_episode['data'][0]['attributes'].get('name').encode('utf-8').lstrip())

                images = list(filter(lambda x: x['type'] == 'image', next_episode['included']))
                shows = list(filter(lambda x: x['type'] == 'show', next_episode['included']))

                show = [x for x in shows if x['id'] == next_episode['data'][0]['relationships']['show']['data']['id']][0]

                # Thumbnail
                next_episode_thumb_image = None
                if next_episode['data'][0]['relationships'].get('images'):
                    next_episode_thumb_image = [x['attributes']['src'] for x in images if
                                                x['id'] ==
                                                next_episode['data'][0]['relationships']['images']['data'][0]['id']][0]

                next_episode_aired = ''
                if next_episode['data'][0]['attributes'].get('earliestPlayableStart'):
                    next_episode_aired = str(
                        self.helper.d.parse_datetime(next_episode['data'][0]['attributes']['earliestPlayableStart']) \
                        .strftime('%d.%m.%Y'))

                next_episode_art = self.helper.d.parse_artwork(show['relationships'].get('images'), images,
                                                               video_thumb=next_episode_thumb_image)

                next_info = dict(
                    current_episode=dict(
                        episodeid=self.video_id,
                        tvshowid=self.current_show_id,
                        title=self.current_episode_info['title'],
                        art={
                            'thumb': self.current_episode_art['thumb'],
                            'tvshow.clearart': '',
                            'tvshow.clearlogo': self.current_episode_art['clearlogo'],
                            'tvshow.fanart': self.current_episode_art['fanart'],
                            'tvshow.landscape': self.current_episode_art['landscape'],
                            'tvshow.poster': self.current_episode_art['poster'],
                        },
                        season=self.current_episode_info['season'],
                        episode=self.current_episode_info['episode'],
                        showtitle=self.current_episode_info['tvshowtitle'],
                        plot=self.current_episode_info['title'],
                        playcount='',
                        rating=None,
                        firstaired=self.current_episode_info['aired'],
                        runtime=self.current_episode_info['duration'],
                    ),
                    next_episode=dict(
                        episodeid=next_episode['data'][0]['id'],
                        tvshowid=next_episode['data'][0]['relationships']['show']['data']['id'],
                        title=next_episode['data'][0]['attributes'].get('name').lstrip(),
                        art={
                            'thumb': next_episode_art['thumb'],
                            'tvshow.clearart': '',
                            'tvshow.clearlogo': next_episode_art['clearlogo'],
                            'tvshow.fanart': next_episode_art['fanart'],
                            'tvshow.landscape:': next_episode_art['landscape'],
                            'tvshow.poster': next_episode_art['poster'],
                        },
                        season=next_episode['data'][0]['attributes'].get('seasonNumber'),
                        episode=next_episode['data'][0]['attributes'].get('episodeNumber'),
                        showtitle=show['attributes']['name'],
                        plot=next_episode['data'][0]['attributes'].get('description'),
                        playcount='',
                        rating=None,
                        firstaired=next_episode_aired,
                        runtime=next_episode['data'][0]['attributes'].get('videoDuration') / 1000.0,
                    ),

                    play_url='plugin://' + self.helper.addon_name + '/play/' + next_episode['data'][0]['attributes'][
                                 'videoType'].lower() + '/' + next_episode['data'][0]['id'],
                    notification_offset=self.video_notification_time,
                )

                self.helper.upnext_signal(sender=self.helper.addon_name, next_info=next_info)

            else:
                self.helper.log('Next episode is not from same tvshow, skipping')

        else:
            self.helper.log('No next episode available')

    def update_playback_progress(self):
        if not self.video_id:
            return
        if not self.helper.get_setting('sync_playback'):
            return
        video_lastpos = format(self.video_lastpos, '.0f')
        video_totaltime = format(self.video_totaltime, '.0f')
        try:
            video_percentage = self.video_lastpos * 100 / self.video_totaltime
        except ZeroDivisionError:
            video_percentage = 0
        # Convert to milliseconds
        video_lastpos_msec = int(video_lastpos) * 1000
        video_totaltime_msec = int(video_totaltime) * 1000

        self.helper.log('Video totaltime msec: %s' % str(video_totaltime_msec))
        self.helper.log('Video lastpos msec: %s' % str(video_lastpos_msec))
        self.helper.log('Video percentage watched: %s' % str(video_percentage))

        # Over 92 percent watched = use totaltime
        if video_percentage > 92:
            self.helper.log('Marking episode completely watched')
            self.helper.d.update_playback_progress(self.video_id, video_totaltime_msec)
        elif video_percentage == 0:
            self.helper.log('Playback error. Not updating playback status.')
        else:
            self.helper.log('Marking episode partly watched')
            self.helper.d.update_playback_progress(self.video_id, video_lastpos_msec)