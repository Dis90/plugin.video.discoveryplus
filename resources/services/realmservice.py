import xbmc, xbmcaddon
import xbmcvfs
import os
import json
import requests

try: # Python 3
    from urllib.parse import quote_plus
except ImportError: # Python 2
    from urllib import quote_plus

# Plugin Info
addon = xbmcaddon.Addon(id='plugin.video.discoveryplus')
settings_folder = xbmcvfs.translatePath(addon.getAddonInfo('profile'))

def get_realm_config():
    # Get realm config
    # India uses old realmservice
    # Get redirected url of discoveryplus.com. Example https://www.discoveryplus.com/fi
    r = requests.get('https://www.discoveryplus.com')
    if r.url == 'https://www.discoveryplus.in/':
        url = 'https://prod-realmservice.mercury.dnitv.com/realm-config/www.discoveryplus.in'
        data = requests.get(url).json()
    else:
        url = 'https://global-prod.disco-api.com/bootstrapInfo'
        data = requests.get(url, headers={"x-disco-client": "WEB:dplus_us:dplus_us:2.2.2",
                                          "x-disco-params": "bid=dplus,hn=www.discoveryplus.com"}).json()

    return data

def write_realm_config(config):
    # Create settings folder if it doesn't exists
    if not xbmcvfs.exists(settings_folder):
        xbmcvfs.mkdir(settings_folder)

    config_file = os.path.join(settings_folder, 'realm_config')
    f = open(config_file, "w")
    f.write(config)
    f.close()

def main():
    monitor = xbmc.Monitor()

    while not monitor.abortRequested():
        # Download realm config on add-on startup
        config = get_realm_config()
        write_realm_config(json.dumps(config))
        break

if __name__ == '__main__': main()