pypymotion
==========

Python [Motion](http://www.lavrsen.dk/foswiki/bin/view/Motion/WebHome) event handler. It allows Motion to send emails with a preview of the pictures and a link to the corresponding video.
It can also disable itself when you're home, it can use a couple of methods to detect your presence:
* if you have an Apple device it can use [Find My iPhone](http://www.apple.com/iphone/icloud/#find)
* it can scan for ARP entries for selected MAC addresses
* 
Take a look at the [config file](https://github.com/7AC/pypymotion/blob/master/pypymotion.cfg) for more details on the features and tweaks.

Dependencies
------------
* motion
* [findmyiphone](https://github.com/7AC/recordmylatitude/tree/master/findmyiphone) (for Apple-based presence detection)
* arp-scan (for ARP-based presence detection)


Installation
------------
```bash
mkdir /etc/pypymotion
cp *.cfg /etc/pypymotion
$EDITOR /etc/pypymotion/pypymotion.cfg # customize the settings
echo 'on_movie_end /path/to/pypymotion.py %f' >> /etc/motion/motion.conf
/etc/init.d/motion restart
