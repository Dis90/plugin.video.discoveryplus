# plugin.video.discoveryplus
discovery+ add-on for Kodi

# Disclaimer
This add-on is unofficial and it is not supported by Discovery Networks and because of that it can break at anytime.

# Supported platforms
- Linux
- Mac
- Windows
- Android

# Tested countries
- Brazil
- Canada
- Denmark
- Finland
- Germany
- India
- Italy
- Netherlands
- Norway
- Spain
- Sweden
- United Kingdom
- United States

# Features
- Supports: <a href="https://forum.kodi.tv/showthread.php?tid=336747">Up Next</a>, <a href="https://github.com/add-ons/service.iptv.manager">IPTV Manager</a> and <a href="https://forum.kodi.tv/forumdisplay.php?fid=231">PseudoTV Live</a> (Kodi 19 ->)
- Playback progress is same in discovery+ site and on Kodi add-on (you can start video on site and continue it on Kodi or other way round)
- Live TV channels
- Videos
- Favorites/My List
- Profiles

# Repository
Install add-on via repository and you get automatic updates.

Repository for Kodi 19 and higher: https://github.com/Dis90/repository.dis90/raw/matrix/repo/repository.dis90-1.0.1.zip

# How do I login?
There are three ways to login.
1. If cookies aren't set add-on will show you PIN code which you then type to <a href=https://discoveryplus.com/link>https://discoveryplus.com/link</a> (USA and EU) or <a href=https://discoveryplus.in/activate>https://discoveryplus.in/activate</a> (India)
2. Export cookies from Chrome. Go to discovery+ website and login. After that use <a href="https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc">Get cookies.txt</a> to export cookies and from add-on settings specify location of cookies.txt.
3. Find cookie named st from your browser. Example in Chrome you can use this link chrome://settings/siteData?searchSubpage=prod-direct.discoveryplus and add value of st cookie to add-on settings.

# FAQ

### Video playback has irregularly short black interruptions during live streams or VODs, the sound is normal

The reason is probably the use of InputStream Adaptive. Depending on the avaiable bandwidth, the resolution of the stream is automatically increased and decreased when using the ‘Adaptive (default)’ setting.  
The same happens in the official Discovery+ app, but without a black image.

Solution: Change the setting in the InputStream Adaptive add-on, e.g. to ‘Fixed resolution’ and set ‘Max resolution’ as well as ‘Max resoltion for DRM videos’ to a value that is possible with the available bandwidth.  
Hint: 1080p can use up to 10 Mbit/s.
