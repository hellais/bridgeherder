#!/usr/bin/env python


from twisted.application.service import Application
from twisted.application import internet

from cyclone import web

from bridgeherder import log, api

application = Application('BridgeHerder')
bridgeHerderAPIFactory = web.Application(api.spec, debug=True)
bridgeHerderAPI = internet.TCPServer(31337, bridgeHerderAPIFactory)
bridgeHerderAPI.setServiceParent(application)

# instantiate an interface manager and configure addresses
# using auto=True will automatically manage networks attached
# to this computer
#ai = AutoInterfaceManager(auto=True)

# given some configuration options, and an interface manager, map
# addresses and ports into a set of bridge config files

#m = BridgeManager(config=hc, interface_manager=ai)
#m = addWebServer(hc, ai)
#m.start()


