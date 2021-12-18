# -*- coding: utf-8 -*-
"""PseudoTV Live / IPTV Manager Integration module"""
import os, re, json
import xbmc, xbmcaddon, xbmcgui

# Plugin Info
ADDON_ID      = 'plugin.video.discoveryplus'
PROP_KEY      = 'PseudoTV_Recommended.%s'%(ADDON_ID)
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
MONITOR       = xbmc.Monitor()

def slugify(text):
    non_url_safe = [' ','"', '#', '$', '%', '&', '+',',', '/', ':', ';', '=', '?','@', '[', '\\', ']', '^', '`','{', '|', '}', '~', "'"]
    non_url_safe_regex = re.compile(r'[{}]'.format(''.join(re.escape(x) for x in non_url_safe)))
    text = non_url_safe_regex.sub('', text).strip()
    text = u'_'.join(re.split(r'\s+', text))
    return text

def regPseudoTV():
    while not MONITOR.abortRequested():
        WAIT_TIME = 60
        if (xbmc.getCondVisibility('System.HasAddon(service.iptv.manager)') and xbmc.getCondVisibility('System.HasAddon(plugin.video.pseudotv.live)')):
            try:
                # Manager Info
                IPTV_MANAGER = xbmcaddon.Addon(id='service.iptv.manager')
                IPTV_PATH    = IPTV_MANAGER.getAddonInfo('profile')
                IPTV_M3U     = os.path.join(IPTV_PATH,'playlist.m3u8')
                IPTV_XMLTV   = os.path.join(IPTV_PATH,'epg.xml')
            except Exception as e:
                xbmc.log('%s-%s-regPseudoTV failed! %s'%(ADDON_ID,ADDON_VERSION,e),xbmc.LOGERROR)
                break
            
            if REAL_SETTINGS.getSettingBool('iptv.enabled'):
                asset = {'iptv':{'type':'iptv','name':ADDON_NAME,'path':ADDON_PATH,'icon':ICON.replace(ADDON_PATH,'special://home/addons/%s/'%(ADDON_ID)).replace('\\','/'),'m3u':{'path':IPTV_M3U,'slug':'@%s'%(slugify(ADDON_NAME))},'xmltv':{'path':IPTV_XMLTV},'id':ADDON_ID}}
                xbmcgui.Window(10000).setProperty(PROP_KEY, json.dumps(asset))
                WAIT_TIME = 900
            else:
                xbmcgui.Window(10000).clearProperty(PROP_KEY)
                WAIT_TIME = 300
        if MONITOR.waitForAbort(WAIT_TIME): break
        
if __name__ == '__main__': regPseudoTV()
