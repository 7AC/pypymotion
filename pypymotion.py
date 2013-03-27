#!/usr/bin/env python
#
# This file is part of pypymotion.
#
# pypymotion is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pypymotion is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pypymotion.  If not, see <http://www.gnu.org/licenses/>.

import math, os, re, smtplib, subprocess, sys, time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from stat import S_ISREG, ST_CTIME, ST_MODE
from datetime import datetime
import ConfigParser
import findmyiphone
import logging, traceback

logger = logging.getLogger( 'pypymotion' )
hdlr = logging.FileHandler( '/var/tmp/pypymotion.log' )
formatter = logging.Formatter( '%(asctime)s %(levelname)s %(message)s' )
hdlr.setFormatter( formatter )
logger.addHandler( hdlr ) 
logger.setLevel( logging.INFO )

def loggerExceptHook( t, v, tb ):
   logger.error( traceback.format_exception( t, v, tb ) )

sys.excepthook = loggerExceptHook

configFile = '/etc/pypymotion/pypymotion.cfg'
config = ConfigParser.ConfigParser( allow_no_value=True )
config.read( configFile )
attachVideo = config.getint( 'General', 'attach_video' )
picturesDir = config.get( 'General', 'pictures_dir' )
picturesExt = config.get( 'General', 'pictures_ext' )
preCapture = config.getint( 'General', 'pre_capture' )
postCapture = config.getint( 'General', 'post_capture' )
emailFrom = config.get( 'Email', 'email_from' )
emailPassword = config.get( 'Email', 'email_password' )
emailTo = config.get( 'Email', 'email_to' )
smtpAddress = config.get( 'Email', 'smtp_address' )
smtpPort = config.getint( 'Email', 'smtp_port' )
# TODO: get rid of these try blocks
home = None
try:
   home = { 'latitude' : config.getfloat( 'General', 'home_lat' ),
   	    'longitude' : config.getfloat( 'General', 'home_lon' ) }
except ConfigParser.NoOptionError:
   pass
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
iosCompatible = False
try:
   iosCompatible = config.getint( 'Email', 'ios_compatible' )
except ConfigParser.NoOptionError:
   pass
presenceMacs = []
network = None
try:
   presenceMacs = config.get( 'ARP', 'presence_macs' ).split( ',' )
   network = config.get( 'ARP', 'network' )
except ConfigParser.NoSectionError, ConfigParser.NoOptionError:
   pass
iCloudSettings = []
try:
   iCloudSettings = config.options( 'iCloud' )
except ConfigParser.NoSectionError:
   pass
fmiAccounts = []
for i in iCloudSettings:
   subConfig = ConfigParser.ConfigParser( allow_no_value=True )
   subConfig.optionxform = str
   subConfig.read( i )
   account = { 'username' : subConfig.get( 'Account', 'username' ),
   	       'password' : subConfig.get( 'Account', 'password' ),
	       'devices' : [] }
   for device in subConfig.options( 'Devices' ):
      account[ 'devices' ].append( device.strip() )
   fmiAccounts.append( account )
   
def usage():
   return 'usage: %s <file>\n' % os.path.basename( sys.argv[ 0 ] )

def arpScan():
   if not network or not presenceMacs:
      return None
   result = subprocess.Popen( [ 'sudo', 'arp-scan', network ],
	 		      stdout=subprocess.PIPE,
			      stderr=subprocess.STDOUT ).stdout.readlines()
   for addr in result:
      for i in presenceMacs:
	 if i in addr:
	    return i
   return None

def distance( origin, destination ):
   # Author: Wayne Dyck
   lat1, lon1 = origin
   lat2, lon2 = destination
   radius = 6371 # km
   dlat = math.radians( lat2 - lat1 )
   dlon = math.radians( lon2 - lon1 )
   a = math.sin( dlat / 2 ) * math.sin( dlat / 2 ) + \
       math.cos( math.radians( lat1 ) ) * math.cos( math.radians( lat2 ) ) * \
       math.sin( dlon / 2 ) * math.sin( dlon / 2 )
   c = 2 * math.atan2( math.sqrt( a ), math.sqrt( 1 - a ) )
   d = radius * c
   return d

def findIphones():
   if not home:
      return False
   for fmiAccount in fmiAccounts:
      fmi = findmyiphone.FindMyIPhone( fmiAccount[ 'username' ],
      				       fmiAccount[ 'password' ] )
      logger.info( '%d devices for %s' % ( len( fmi.devices ),
					   fmiAccount[ 'username' ] ) )
      for i, device in enumerate( fmi.devices ):
      	 if device.name in fmiAccount[ 'devices' ]:
	    logger.info( 'Found %s in configuration, locating' % device.name )
	    location = None
	    try:
               location = fmi.locate( i, max_wait=90 )
	    except Exception:
	       logger.error( 'No location for ' + device.name )
	       continue
	    logger.info( '%s is at %f,%f' % ( device.name, location[ 'latitude' ],
					      location[ 'longitude' ] ) )
	    distanceFromHome = distance( ( home[ 'latitude' ],
					   home[ 'longitude' ] ),
					 ( location[ 'latitude' ],
					   location[ 'longitude' ] ) )
	    if distanceFromHome < 0.1:
	       logger.info( '%s is close (%f m)' % ( device.name,
						     distanceFromHome * 1000 ) )
	       return device.name
	    logger.info( '%s is far (%f km)' % ( device.name,
						 distanceFromHome ) )
	 else:
	    logger.info( 'Skipping ' + device.name )
   return None

def df():
   result = subprocess.Popen( [ 'df', '-h', '-P', picturesDir ],
	 		      stdout=subprocess.PIPE,
			      stderr=subprocess.STDOUT ).stdout.readlines()[ 1 ]
   return re.split( ' +', result )[ 3 ]

def videoDuration( video ):
   result = subprocess.Popen( [ 'ffprobe', video ],
	 		      stdout = subprocess.PIPE,
			      stderr = subprocess.STDOUT )
   duration = [ x for x in result.stdout.readlines() if "Duration" in x ]
   duration = duration[ 0 ].split( ',' )[ 0 ].split( 'Duration: ' )[ 1 ].\
	      split( '.' )[ 0 ].split( ':' )
   return str( int( duration[ 0 ] ) * 3600 + int( duration[ 1 ] ) * 60 + \
	       int( duration[ 2 ] ) )

def logFiles( files, typeName='file(s)', prefix='', suffix='',
	      level=logging.INFO, detail=False ):
   # <prefix> <count> <typeName> [(<first> to <last>)] <suffix>
   if not files:
      return
   log = prefix + '%d %s' % ( len( files ), typeName )
   if detail:
      log += ' (' + os.path.basename( files[ 0 ] )
      if len( files ) > 1:
	 log += ' to ' + os.path.basename( files[ -1 ] )
      log += ')'
   log += suffix
   logger.info( log )

def pictures( dirpath, baseName, all=False ):
   # Consider only the id (22) in 22-20130312074653-00
   baseName = baseNamei.split( '-' )[ 0 ]
   pics = sorted( os.path.join( dirpath, fn ) for fn in os.listdir( dirpath ) \
   					      if fn.endswith( picturesExt ) and \
					         fn.startswith( baseName ) )
   picsLen = len( pics )
   if not all:
      pics = pics[ preCapture : preCapture + 5 ]
      logFiles( pics, typeName='pic(s)', prefix='Selected ',
		suffix=' (%d/%d)' % ( len( pics ), picsLen ), detail=True )
   return pics

def convertForIos( src, dst ):
   logger.info( 'Converting video to %s' % dst )
   subprocess.Popen( [ 'ffmpeg', '-i', src, dst ], stdout=subprocess.PIPE,
	 	     stderr=subprocess.STDOUT ).stdout.readlines()
   os.remove( src )

def sendEmail( attachment, duration ):
   msg = MIMEMultipart()
   msg[ 'Subject' ] = 'motion has a video for you'
   msg[ 'From' ] = emailFrom
   msg[ 'To' ] = emailTo

   originalAttachment = attachment
   if iosCompatible:
      attachmentDir, attachmentFile = os.path.split( attachment )
      baseName, _ = os.path.splitext( attachmentFile )
      iosVideo = attachmentDir + '/' + baseName + '.mov'
   if iosCompatible:
      attachment = iosVideo
   pics = pictures( picturesDir, baseName )
   embeddedPics = ''
   html = '''
<html>
<head><meta http-equiv="Content-Type" content="text/html charset=us-ascii"></head>
<body style="word-wrap: break-word; -webkit-nbsp-mode: space; 
             -webkit-line-break: after-white-space; ">'''
   if videoUrl:
      html += '<a href="%s/%s"><img src="%s/%s" ' % ( videoUrl,
      						      os.path.basename( attachment ),
						      videoUrl,
						      os.path.basename( playIcon ) )
      html += 'alt="play video" height="48" width="48"></a>'
   html += '<div>Duration: %ss</div>' % duration
   html += '<div>Available space: %s</div>' % df()
   html += '</body></html>'

   body = MIMEText( html, 'html' )
   msg.attach( body )

   for p in pics:
      fp = open( p, 'rb' )
      img = MIMEImage( fp.read() )
      fp.close()
      img.add_header( 'Content-ID', '<%s>' % os.path.basename( p ) )
      msg.attach( img )
   logger.info( 'Emailing %d pics' % len( pics ) )

   if attachVideo:
      video = MIMEApplication( open( attachment, 'rb' ).read() )
      video.add_header( 'Content-Disposition', 'attachment',
			filename=os.path.basename( attachment ) )
      video.add_header( 'Content-ID', os.path.basename( attachment ) )
      msg.attach( video )
      logger.info( 'Attaching video' )

   # Add an option for this
   mailServer = smtplib.SMTP( smtpAddress, smtpPort )
   mailServer.ehlo()
   mailServer.starttls()
   mailServer.ehlo()
   mailServer.login( emailFrom, emailPassword )
   mailServer.sendmail( emailFrom, emailTo, msg.as_string() )
   mailServer.close()

# This worked with sendmail
#   smtp = smtplib.SMTP( "localhost" )
#   print 'Sending email'
#   smtp.sendmail( msg[ 'From' ], msg[ 'To' ], msg.as_string() )
#   smtp.quit()
   if iosCompatible:
      convertForIos( originalAttachment, iosVideo )

def main():
   if len( sys.argv ) != 2:
      logger.error( sys.argv )
      print usage()
      sys.exit( 1 )
   video = sys.argv[ 1 ]
   duration = videoDuration( video )
   logger.info( 'New video event: %s (%ss)' % ( video, duration ) )
   iphones = findIphones()
   macs = arpScan()
   # If someone's home delete everything
   if iphones or macs:
      baseName, _ = os.path.splitext( os.path.basename( video ) )
      pics = pictures( picturesDir, baseName, all=True )
      logFiles( pics, typeName='pic(s)', prefix='Removing ' )
      logFiles( [ video ], typeName='video', prefix='Removing ' )
      for f in [ video ] + pics:
	 try:
	    os.remove( f )
	 except OSError, e:
	    logFiles( [ f ], prefix='Failed to remove ', level=logging.ERROR )
   # If noone's home notify
   else:
      sendEmail( video, duration )

if __name__ == "__main__":
   main()
