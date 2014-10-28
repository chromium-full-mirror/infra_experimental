import webapp2
import urllib
import urllib2

FORWARD_TO = 'https://chromium-cq-status.appspot.com/'

class ForwardingHandler(webapp2.RequestHandler):
  def get(self, url):
    response = urllib2.urlopen(FORWARD_TO + url)
    self.response.headers['Content-Type'] = response.info().gettype()
    self.response.write(''.join([l for l in response]))

  def post(self, url):
    data = self.request.POST
    response = urllib2.urlopen(FORWARD_TO + url, data=urllib.urlencode(data))
    self.response.headers['Content-Type'] = response.info().gettype()
    self.response.write(''.join([l for l in response]))

application = webapp2.WSGIApplication([
    ('/(.*)', ForwardingHandler),
], debug=True)
