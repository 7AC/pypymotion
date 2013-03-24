pypymotion
==========

Python [Motion](http://www.lavrsen.dk/foswiki/bin/view/Motion/WebHome) event handler. It allows Motion to send emails with a preview of the pictures and a link to the corresponding video.
It can also disable itself when you're home, it can use a couple of methods to detect your presence:
* if you have an Apple device it can use [Find My iPhone](http://www.apple.com/iphone/icloud/#find)
* it can scan for ARP entries for selected MAC addresses

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
```

Demo
----
```bash
2013-03-24 11:27:05,032 INFO New video event: /tmp/motion/video/119-20130324112546.avi (20s)
2013-03-24 11:27:05,916 INFO 3 devices for appleuser@gmail.com
2013-03-24 11:27:05,918 INFO Skipping John Doe’s iPad
2013-03-24 11:27:05,919 INFO Found John’s iPhone in configuration, locating
2013-03-24 11:27:05,940 INFO John’s iPhone is at 37.7700000000,-122.42000000
2013-03-24 11:27:05,951 INFO John’s iPhone is far (5.785795 km)
2013-03-24 11:27:05,959 INFO Selected 5 pic(s) (119-20130324112544-01.jpg to 119-20130324112546-01.jpg) (5/40)
2013-03-24 11:27:06,106 INFO Emailing 5 pics
2013-03-24 11:27:12,893 INFO Converting video to /tmp/motion/video/119-20130324112546.mov
```
