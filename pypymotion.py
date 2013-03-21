#!/usr/bin/env python

import os, re, smtplib, subprocess, sys, time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from stat import S_ISREG, ST_CTIME, ST_MODE
from datetime import datetime
import ConfigParser
import findmyiphone

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
      return False
   result = subprocess.Popen( [ 'sudo', 'arp-scan', network ],
	 		      stdout=subprocess.PIPE,
			      stderr=subprocess.STDOUT ).stdout.readlines()
   for addr in result:
      for i in presenceMacs:
	 if i in addr:
	    return True
   return False

def findIphones():
   if not home:
      return False
   for fmiAccount in fmiAccounts:
      fmi = findmyiphone.FindMyIPhone( fmiAccount[ 'username' ],
      				       fmiAccount[ 'password' ] )
      for i, device in enumerate( fmi.devices ):
      	 if device.name in fmiAccount[ 'devices' ]:
	    location = None
	    try:
               location = fmi.locate( i, max_wait=90 )
	    except Exception:
	       print 'No location for', device.name
	    if location:
	       for x in [ 'latitude', 'longitude' ]:
	          distanceFromHome = abs( location[ x ] - home[ x ] ) * 10000000000
	          if distanceFromHome <= location[ 'accuracy' ]:
		     return True
	    else:
	       print 'No location for', device.name
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

def pictures( dirpath, baseName, all=False ):
   # Consider only the id (22) in 22-20130312074653-00
   baseName = baseName[ 0 : 2 ]
   pics = sorted( os.path.join( dirpath, fn ) for fn in os.listdir( dirpath ) \
   					      if fn.endswith( picturesExt ) and \
					         fn.startswith( baseName ) )
   if not all:
      return pics[ preCapture : preCapture + 5 ]
   return pics

def convertForIos( src, dst ):
   subprocess.Popen( [ 'ffmpeg', '-i', src, dst ], stdout=subprocess.PIPE,
	 	     stderr=subprocess.STDOUT ).stdout.readlines()
   os.remove( src )

def sendEmail( attachment ):
   msg = MIMEMultipart()
   msg[ 'Subject' ] = 'motion has a video for you'
   msg[ 'From' ] = emailFrom
   msg[ 'To' ] = emailTo

   originalAttachment = attachment
   if iosCompatible:
      attachmentDir, attachmentFile = os.path.split( attachment )
      baseName, _ = os.path.splitext( attachmentFile )
      iosVideo = attachmentDir + '/' + baseName + '.mov'
   duration = videoDuration( attachment )
   if iosCompatible:
      attachment = iosVideo
   pics = pictures( picturesDir, baseName )
   embeddedPics = ''
   html = '<html><head><meta http-equiv="Content-Type" content="text/html charset=us-ascii"></head>'
   html += '<body style="word-wrap: break-word; -webkit-nbsp-mode: space; -webkit-line-break: after-white-space; ">'
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

   if attachVideo:
      video = MIMEApplication( open( attachment, 'rb' ).read() )
      video.add_header( 'Content-Disposition', 'attachment', filename=os.path.basename( attachment ) )
      video.add_header( 'Content-ID', os.path.basename( attachment ) )
      msg.attach( video )

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
      print usage()
      sys.exit( 1 )
   video = sys.argv[ 1 ]
   # If someone's home delete everything
   if findIphones() or arpScan():
      baseName, _ = os.path.splitext( os.path.basename( video ) )
      files = [ video ] + pictures( picturesDir, baseName, all=True )
      for f in files:
   	 os.remove( f )
   else:
      sendEmail( video )

if __name__ == "__main__":
    main()
