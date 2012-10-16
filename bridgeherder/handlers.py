from cyclone.web import RequestHandler, HTTPError

class startBridges(RequestHandler):
    def get(self):
        print "Got a get request %s" % self.request.body

    def post(self):
        print "Got a post request %s" % self.request.body
