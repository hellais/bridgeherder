# -*- coding: UTF-8
#   api
#   ***
#   :copyright: 2012 Hermes No Profit Association - GlobaLeaks Project
#   :author: Arturo Filastò <art@globaleaks.org>
#   :license: see LICENSE file
#
#   Contains all the logic for handling tip related operations.
#   This contains the specification of the API.
#   Read this if you want to have an overall view of what API calls are handled
#   by what.

from cyclone.web import StaticFileHandler

from bridgeherder import handlers


spec = [
    ## Node Handler ##
    #  * /node U1
    (r'/startbridges', handlers.startBridges),
    ## Main Web app ##
    # XXX serves /tmp directory
    (r"/(.*)", StaticFileHandler, {'path': '/tmp'})
]

