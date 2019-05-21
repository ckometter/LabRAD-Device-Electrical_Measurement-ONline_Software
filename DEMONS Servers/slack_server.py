# Copyright []
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
### BEGIN NODE INFO
[info]
name = Slack Server
version = 0.0
description = Send message/figures to Slack  

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""


from labrad.server import LabradServer, setting
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet import reactor, defer
import labrad.units as units
from labrad.types import Value
import time
import sys
import slackweb
import requests

class SlackServer(LabradServer):
    name = "Slack Server"    # Will be labrad name of server
 
#------------------------------------------------------------------------------------------------------------------------------------------#
    """
    To initialize this server, slackweb needed to be installed, add incoming webhook to the target channel, add result_send app to channel.
    """

# incoming_webhook_url is the url for the incoming webhook app, input_channel is the last part of the url string
    @setting(104,incoming_webhook_url = 's: incoming webhook url', input_channel = 's: input channel identifier', returns = '')
    def initializeServer(self, c, incoming_webhook_url, input_channel):  # Do initialization here
        try: 
            self.slack = yield slackweb.Slack(url = incoming_webhook_url) 
            self.token = 'xoxb-30076933861-621785695825-bDllX5iMrc4bMIt8Y2l2ie6A' # Young Lab token
            self.channel = input_channel
            print "Server initialization complete"
        except Exception as inst:
            print 'Error Initializing Server: ', inst
            
    @setting(101,line = 's: message', returns = '')        
    def message(self, c, line):
        try:
            yield self.slack.notify(text = line)
        except Exception:
            print 'Error when sending message to slack'
    
    @setting(102,filelocale = 's: location of the file to upload', comment = 's: comment', title = 's: title', returns = '')    
    def image(self, c, filelocale, comment='', title=''):
        try:
            files = {'file': open(filelocale, 'rb')}
            param = {
                    'token':self.token,
                    'channels':self.channel,
                    'initial_comment': comment,
                    'title': title
                    }
            yield requests.post(url="https://slack.com/api/files.upload", params=param, files=files)
        except Exception as inst:
            print 'Error Uploading Pictures to Slack: ', inst
        
 
#------------------------------------------------------------------------------------------------------------------------------------------#
    """
    Additional functions that may be useful for programming the server. 
    """

    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = defer.Deferred()
        reactor.callLater(secs,d.callback,'Sleeping')
        return d

__server__ = SlackServer()
  
if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)