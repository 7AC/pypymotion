pypymotion
==========

Python [Motion](http://www.lavrsen.dk/foswiki/bin/view/Motion/WebHome) event handler. It allows Motion to send emails with a preview of the pictures and a link to the corresponding video.
It can also disable itself when you're home if you want it to, by detecting the MAC addresses of some devices (e.g., your cell phones).


Dependencies
------------
* motion
* sendmail
* arp-scan (optional)


Installation
------------
```bash
mkdir /etc/pypymotion
cp pypymotion.cfg /etc/pypymotion
$EDITOR /etc/pypymotion/pypymotion.cfg # customize the settings
echo 'on_movie_end /path/to/pypymotion.py %f' >> /etc/motion/motion.conf
/etc/init.d/motion restart```
