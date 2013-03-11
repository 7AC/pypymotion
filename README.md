pypymotion
==========

[Motion](http://www.lavrsen.dk/foswiki/bin/view/Motion/WebHome) python event handler. It allows Motion to send emails with a preview of the pictures and a link to the corresponding video.
It can also disable itself when you're home if you want it to, by detecting the MAC addresses of some devices (e.g., your cell phones).


Dependencies
------------
* motion
* sendmail
* arp-scan


Installation
------------
Add the following to your motion.conf:
```on_movie_end /path/to/pypymotion.py %f```

Create /etc/pypymotion and copy pypymotion.cfg to it, edit the settings.

Restart motion.
