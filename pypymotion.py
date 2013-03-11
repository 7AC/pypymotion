#!/usr/bin/env python

import os, re, smtplib, subprocess, sys, time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from stat import S_ISREG, ST_CTIME, ST_MODE
from datetime import datetime
import ConfigParser

configFile = '/etc/pypymotion/pypymotion.cfg'
config = ConfigParser.ConfigParser( allow_no_value=True )
config.read( os.path.expanduser( configFile ) )
attachVideo = config.getint( 'General', 'attach_video' )
picturesDir = config.get( 'General', 'pictures_dir' )
picturesExt = config.get( 'General', 'pictures_ext' )
postCapture = config.getint( 'General', 'post_capture' )
emailFrom = config.get( 'Email', 'email_from' )
emailTo = config.get( 'Email', 'email_to' )
videoUrl = None
try:
   videoUrl = config.get( 'Email', 'video_url' )
except ConfigParser.NoOptionError:
   pass
playIcon = None
try:
   playIcon = config.get( 'Email', 'play_icon' )
except ConfigParser.NoOptionError:
   pass
presenceMacs = []
network = None
try:
   presenceMacs = config.get( 'Presence', 'presence_macs' ).split( ',' )
   network = config.get( 'Presence', 'network' )
except ConfigParser.NoOptionError:
   pass

def usage():
   return 'usage: %s <file>\n' % os.path.basename( sys.argv[ 0 ] )

def userIsHome():
   if not network or not presenceMacs:
      return False
   result = subprocess.Popen( [ 'sudo', 'arp-scan', network ],
	 		      stdout=subprocess.PIPE,
			      stderr=subprocess.STDOUT ).stdout.readlines()
   for addr in result:
      for i in presenceMacs:
	 if i in addr:
	    return True
   return False

def df():
   result = subprocess.Popen( [ 'df', '-h', '-P', picturesDir ],
	 		      stdout=subprocess.PIPE,
			      stderr=subprocess.STDOUT ).stdout.readlines()[ 1 ]
   return re.split( ' +', result )[ 3 ]

def videoDuration( video ):
   result = subprocess.Popen( [ 'ffprobe', video ],
	 		      stdout = subprocess.PIPE,
			      stderr = subprocess.STDOUT )
   try:
      duration = [ x for x in result.stdout.readlines() if "Duration" in x ]
      duration = duration[ 0 ].split( ',' )[ 0 ].split( 'Duration: ' )[ 1 ].split( '.' )[ 0 ].split( ':' )
      return str( int( duration[ 0 ] ) * 3600 + int( duration[ 1 ] ) * 60 + int( duration[ 2 ] ) )
   except IndexError:
      sys.stderr.write( '%s not found\n' % video )
      sys.exit( 1 )

def pictures( dirpath ):
   # get all entries in the directory w/ stats
   entries = ( os.path.join( dirpath, fn ) for fn in os.listdir( dirpath ) if fn.endswith( picturesExt ) )
   entries = ( ( os.stat( path )[ ST_CTIME ], path ) for path in entries )

   # return the last N pictures before the postCapture ones
   return [ path for _, path in sorted( entries )[ - postCapture - 5 : - postCapture ] ]

def sendEmail( attachment ):
   #print '[%s] %s\n' % ( datetime.now(), attachment )
   msg = MIMEMultipart( 'alternative' )
   msg[ 'Subject' ] = 'motion has a video for you'
   msg[ 'From' ] = emailFrom
   msg[ 'To' ] = emailTo

   duration = videoDuration( attachment )
   pics = pictures( picturesDir )
   embeddedPics = ''
   for p in pics:
      embeddedPics += '<img src="cid:%s" width="640">' % os.path.basename( p )
   html = '<html><head><title>motion</title></head><body>'
   if videoUrl and playIcon:
      html += '<a href="%s/%s"><img src="cid:%s" height="70" align="left"></a>' \
	      % ( videoUrl, os.path.basename( attachment ), os.path.basename( playIcon ) )
   html += '<p>&nbsp;&nbsp;&nbsp;Duration: %ss</p>' % duration
   html += '<p>&nbsp;&nbsp;&nbsp;Available space: %s</p>' % df()
   html += '<br>%s</body></html>' % embeddedPics

   body = MIMEText( html, 'html' )

   if playIcon:
      pics.append( playIcon )
   for p in pics:
      fp = open( p, 'rb' )
      img = MIMEImage( fp.read() )
      fp.close()
      img.add_header( 'Content-ID', '<%s>' % os.path.basename( p ) )
      msg.attach( img )

   msg.attach( body )

   if attachVideo:
      video = MIMEApplication( open( attachment, 'rb' ).read() )
      video.add_header( 'Content-Disposition', 'attachment', filename=os.path.basename( attachment ) )
      video.add_header( 'Content-ID', os.path.basename( attachment ) )
      msg.attach( video )

   smtp = smtplib.SMTP( "localhost" )
   smtp.sendmail( msg[ 'From' ], msg[ 'To' ], msg.as_string() )
   smtp.quit()

def main():
   if len( sys.argv ) != 2:
      print usage()
      sys.exit( 1 )
   if not userIsHome():
      sendEmail( sys.argv[ 1 ] )

if __name__ == "__main__":
    main()
