#!/usr/bin/env python
from net import AutoInterfaceManager
from bridge import BridgeManager, addWebServer

from twisted.python import log # actually use me
from twisted.internet import reactor, defer

import config as hc
import signal

def main():
    # instantiate an interface manager and configure addresses
    # using auto=True will automatically manage networks attached
    # to this computer
    ai = AutoInterfaceManager(auto=True)

    # given some configuration options, and an interface manager, map
    # addresses and ports into a set of bridge config files

    #m = BridgeManager(config=hc, interface_manager=ai)
    m = addWebServer(hc, ai)
    m.start()

    def shutdown():
	    m.stop()
	    ai.restore

    reactor.addSystemEventTrigger('before', 'shutdown', shutdown)
    reactor.run()

def _handleSIGHUP(*args):
    """Called when we receive a SIGHUP; invokes _reloadFn."""
    reactor.callLater(0, _reloadFn)

def reload(self):
    #XXX: change the listening ports. will probably need to update firewall rules or the like...
    # re-read config file
    import config as hc
    print "reload"
    return True

if __name__ == '__main__':
    global _reloadFn
    _reloadFn = reload
    signal.signal(signal.SIGHUP, _handleSIGHUP)
    main()
