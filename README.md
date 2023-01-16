# iTunesJukebox
Applescript, Python, Arduino to interface an old Jukebox with iTunes.

My step-father purchased a 1970's era jukebox which was used in a Waffle House restaurant (from what we can tell, a number of years.)

The jukebox was cleaned, its electromechanical components, lights, and speakers were removed and replaced with a early 90's Sony receiver, 
6x9 car speakers, and powered subwoofer, and a Raspberry Pi computer. The Pi is running the fantastic shairport-sync software. 
The jukebox is now accessible via iPhones and Macs.

The jukebox was looking and sounding great, however the 7 segment displays and the 12 button keypad were just begging to be used again.

This repo is the hacked code allows the jukebox to command iTunes to queue up music to play. This is accomplished via custom software 
running on the Raspberry Pi, the Mac running iTunes, and of course an Arduino. 

iTunes has a playlist named "Jukebox" with 200 songs, the maximum the jukebox can display. Entering the 3 digit number of a song
causes the Raspberry Pi to request iTunes to queue that song number from the "Jukebox" playlist to play next.

There are several programming languages in use.

Python: Custom code to communicate with iTunes.
Arduino: Handle communication between the Jukebox keypad/display and the Pi.
Applescript: Additional control of iTunes.

This is a complete and total hack. I look forward to improving this code in the (hopefully) near future.
