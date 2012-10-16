#!/usr/bin/env python

from txtorcon import TorConfig
import config as hc
from ipaddr import IPAddress, IPNetwork
from ipaddr import IPv4Address, IPv4Network
from ipaddr import IPv6Address, IPv6Network
from twisted.python import log
from twisted.internet import reactor, defer
from twisted.web.resource import Resource 
from twisted.web.server import Site
import random
import socket
import config as hc
import txtorcon

import time
import psutil
import json

"""
contains the components for bridge manager and bridge classes
"""


class Bridge(object):
    """ a class for manipulating a tor process """
    #XXX: TODO: integrate txtorcon.torstate functionality
    # sadly ipv6 descriptors seem to break parsing
    # XXX: submit patch to fix this
    def __init__(self, config=None):
        # tor binary path?
        self.config = config
        self.status = "Stopped"
        if config: assert isinstance(txtorcon.TorConfig, self.config)
        #XXX: 
        #raise NotImplementedError # not done yet, do more stuff here

    #XXX:  broken
    def running(fn):
        def f(*args):
            if args[0].status != "Running": return None
            return fn(*args)
        return f


    def _setup_failed(self):
        self.status = "Failed"

    def _setup_updates(self, prog, tag, summary):
        """ callback for updates of startup, write to stdout """
        print "%d%%: %s" % (prog, summary)

    def _start(self):
        self.status = "Starting" # should more tightly follow state of tor process, see the txtrocon.torstate. sadly it doesn't yet parse ipv6 descriptors #XXX TODO: fix this
        #XXX: I really don't know if we should catch Exceptions this way
        try:
            tp = txtorcon.launch_tor(self.config, reactor, tor_binary=hc.TOR_BINARY, progress_updates=self._setup_updates) # calls reactor.run()
            def _setup_complete(self):
                self.status = "Running"
            tp.addCallback(reactor.fireSystemEvent, 'bootstrap', self) #XXX: can we do like this ?
            #XXX: is this post bootstrap or what?
            tp.addErrback(self._setup_failed)
            def _bootstrap_complete():
                # do some things after bootstrap
                # e.g. provide a way to alert the BridgeManager
                # that this bridge has completed bootstrap
                reactor.fireSystemEvent('bootstrap')
                # figure out how to pass reference to instance in systemEvent
            tp.post_bootstrap = _bootstrap_complete
        except Exception: #XXX: must catch specifc exceptions!!!
            self.status = "Failed" # could we get the process exit status?
            raise
            return None

        return tp

    def start(self):
        """ start the bridge """
        if not self.config:
            print "Bridge Not Configured!"
            return

        if self.status == "Running":
            print "Already Started"
            return self.tp

        if self.status == "Failed":
            print "Starting from previous state 'Failed'"
            self.status = "Starting"

        print "Starting bridge %s" % "Unnamed"

        self.tp = self._start()
        return self.tp

    def reload(self):
        """ HUP this bridge """
        self.tp.signal("RELOAD")

    def stop(self):
        """ kill this bridge """
        pass #self.tp.quit() #XXX: DOES NOT WORK

    def restart(self):
        """ restart this bridge """
        self.stop()
        self.start()

    @property
    @running
    def process(self):
        if self.status != "Running": return None
        if not self.tp: return None
        if "transport" not in self.tp.keys(): return None
        print dir(self.tp)
        if not self.tp.transport: return None #XXX: not available yet?
        return psutil.Process(self.tp.transport.pid)

    #XXX: if this does not work, we could do self.tp.get_info("process/pid")

    #XXX: write a map of property names to get-info keys
    @property
    @running
    def clients_seen(self): return self.tp.get_info("status/clients-seen")

    @property
    @running
    def addresses(self): 
        or_addresses = [ x.strip('"') for x in self.tp.get_info("net/listeners/or").split() ]
        for line in or_addresses:
            a,port = x.split(':')
            address = a.replace('[','').replace(']','') # strip any [] from IPv6 address
            yield IPAddress(address)#,port #XXX: what function queries for both?

    @property
    @running
    def controlport(self): return self.tp.get_info("net/listeners/control")

    @property 
    @running
    def trafficWritten(self): return self.tp.get_info("traffic/written")

    @property
    @running
    def trafficRead(self): return self.tp.get_info("traffic/read")

    @property 
    @running
    def cpu_load(self): return self.process.get_cpu_percent(interval=1.0)

    @property
    @running
    def memory_info(self): return self.process.get_memory_info()

    def get_network_io(self):
        pass

    def ports(self):
        # see above: should this be accessed directly through the bridge
        # config?
        # have an accurate view?
        pass

class BridgeManager(Resource):
    """ implements a bridge manager with a web frontend
    """
    isLeaf = True
    def __init__(self, bridges=None, config=None, interface_manager=None):
        if bridges: self.bridges = bridges
        else: self.bridges = []
        if not config: return #XXX: log an INFO?

        if not interface_manager: return
        #XXX: kind of sketchy
        confs = get_bridge_configs(configure_interfaces(interface_manager))

        # mo bridges?
        while len(self.bridges) < config.NUM_BRIDGES:
            self.bridges.append(Bridge())

        assert len(self.bridges) == len(confs)
        for b in self.bridges:
            b.config = confs.pop()

        # set up the web resource
        Resource.__init__(self)

    def render_GET(self, request):
        return json.dumps([ b.cpu_load for b in self.bridges ])

    def render_POST(self, request):
        pass

    def start(self):
        """ start managed bridges """
        return [ b.start() for b in self.bridges ]

    def reload(self):
        """ HUP managed bridges """
        return [ b.reload() for b in self.bridges ]

    def add(self, bridge, start=False):
        if not isinstance(bridge, Bridge): return None
        self.bridges.append(bridge)
        if start: bridge.start()

    def add_from_config(self, config, start=False):
        """ add a bridge from a config file
            does not start the bridge
        """
        b = Bridge(config)
        if not b:
            return None
        self.bridges.append(b)
        if start: b.start()
        return b # does not return a torprotocol instance

    def stop(self):
        """ stop running bridges """
        return [ b.stop() for b in self.bridges ]

    def restart(self):
        """ restart running bridges """
        [ b.stop() for b in self.bridges ] #XXX: do we want to return exitcodes?
        return [ b.start() for b in self.bridges ]

    def status(self):
        return [ b.status for b in self.bridges ]

def port_available(host, port):
    """
    test to see if a port is available.
    """
    if isinstance(IPAddress(host), IPv6Address):
        addrclass = socket.AF_INET6
    else: addrclass = socket.AF_INET
    s = socket.socket(addrclass)
    try:
        s.bind((str(host), port))
    except socket.error, e:
        return False
    finally:
        s.close()
    return True

def get_available_port(address):
    """
    returns a random port number available on 'address'
    address must be a local address.
    """
    port = random.randint(1,65535)
    #XXX needs root for ports < 1024
    while not port_available(address, port): port = random.randint(1,65535)
    return port 

def get_port_list(address, num_ports, defaults=None):
    """
    generates a list of ports
    accepts a list of default ports
    """
    ports = set()
    if isinstance(defaults,list):
        for port in defaults: # create a copy of ports?
            if port_available(address, port): ports.update([port])

    while len(ports) < num_ports:
        ports.update([get_available_port(address)])
    return ports

def get_bridge_config(addresses, ports=None):
    #XXX: how we do pluggable transports? which ports they get?
    torconfig = txtorcon.TorConfig()
    for address in addresses:
        if not ports: ports = get_port_list(address, [9001, 443, 80])
        torconfig.OrPort = ["%s:%s"%(address, str(port)) for port in ports]
    torconfig.ControlPort = get_available_port('localhost')
    torconfig.BridgeRelay = 1
    torconfig.ExitPolicy = "reject *:*"
    torconfig.SocksPort = 0
    return torconfig

def get_bridge_configs(allocatable):
    """
    produces a set of bridge configs, distributing the addresses
    round-robin style
    """
    #XXX: how we do obfsproxy?
    #XXX: how we do make sure we listen on ports 443, 80, etc??
    # round-robin allocate address:port to bridges
    #XXX: might want to try and keep 1 ip per bridge, rather than
    # round robin ip:port across several bridges?
    #XXX: if we come up with several different allocator types, there
    # should be a more general way to express the concept of an allocator
    configs = []
    for bridge in xrange(hc.NUM_BRIDGES):
        configs.append(txtorcon.TorConfig())

    #XXX: ghetto, need to fix something with _ListWrapper in txtorcon
    fuckthis = dict()
    # set up the defaults
    for config in configs:
        config.ControlPort = get_available_port('127.0.0.1')
        config.BridgeRelay = 1
        config.ExitPolicy = "reject *:*"
        config.SocksPort = 0
        #XXX: ok great, this is fucking broken.
        # why the fuck can't append be called?
        # fuck fuck fuck
        config.OrPort = []
        fuckthis[config] = []

    # allocate those ports!
    i = 0
    for address,ports in allocatable:
        for port in ports:
            if isinstance(address, IPv6Address): orport = "[%s]:%s"%(address, port)
            else: orport = "%s:%s" % (address, port)
            config = configs[i%len(configs)]
            fuckthis[config].append(orport)
            i+=1
    #XXX: fucking ghetto hack
    for config in configs:
        config.OrPort = fuckthis[config]
    return configs

def ipv4_network(x):
    return isinstance(x.network, IPv4Network)

def ipv6_network(x):
    return isinstance(x.network, IPv6Network)

def configure_interfaces(ai):
    """
    discovers what public (see public_network()) networks are available,
    and bring up NUM_ADDRESSES

    """

    print "Number of Bridges to spawn: %d" % hc.NUM_BRIDGES

    total_ports = hc.NUM_BRIDGES * hc.MAX_OR_ADDRESSES_PER_BRIDGE

    # figure out what networks are attached
    ipv4_nms = filter(ipv4_network, ai.network_managers)
    ipv6_nms = filter(ipv6_network, ai.network_managers)

    #XXX -2 or -3, don't we include the primary address?
    num_ipv4_addresses = sum([x.numfree for x in ipv4_nms ])
    num_ipv6_addresses = sum([x.numfree for x in ipv6_nms ])

    print "Number of IPv4 addresses available: %d" % num_ipv4_addresses
    print "Number of IPv6 addresses available: %d" % num_ipv6_addresses

    # Tor requires at least one IPv4 address
    if num_ipv4_addresses == 0:
        exit("Exiting... no IPv4 Addresses available")

    # if there are ipv6 nets, what mixture should we use?
    percent_ipv4_ports = 1
    percent_ipv6_ports = 0
    if len(ipv6_nms) > 0:
        percent_ipv4_ports = hc.PERCENT_IPV4_PORTS # 0.5
        percent_ipv6_ports = 1 - percent_ipv4_ports

    # determine hard counts for the number of ipv4 and ipv6 listening sockets
    num_ipv6_ports = total_ports - percent_ipv4_ports * total_ports
    num_ipv4_ports = total_ports - num_ipv6_ports

    print "%d IPv4 ports (%d %%) | %d IPv6 ports (%d %%)" %\
            (num_ipv4_ports, 100*percent_ipv4_ports,\
            num_ipv6_ports, 100*percent_ipv6_ports )

    num_required_ipv6_addresses = num_ipv6_ports / hc.NUM_PORTS_PER_ADDRESS
    num_required_ipv4_addresses = num_ipv4_ports / hc.NUM_PORTS_PER_ADDRESS

    #track of all the networks and ports
    allocatable = []

    #XXX: this is pretty nasty and should be refactored, lots of repitition

    # If there aren't enough IPv4 addresses to go around, share addresses
    # amongst bridges by allocating unique address:port pairs
    if num_required_ipv4_addresses > num_ipv4_addresses:
        num_required_ipv4_addresses = num_ipv4_addresses
        print "Using %d IPv4 addresses" % num_ipv4_addresses
        num_ports_per_ipv4_address = num_ipv4_ports / num_ipv4_addresses
        assert (num_ports_per_ipv4_address < 40000) # XXX: better limit
    else:
        print "Using %d IPv4 addresses" % num_required_ipv4_addresses
        num_ports_per_ipv4_address = hc.NUM_PORTS_PER_ADDRESS

    allocatable.extend(get_allocatable(num_required_ipv4_addresses,
        num_ports_per_ipv4_address, ipv4_nms))
    if num_required_ipv6_addresses > num_ipv6_addresses: #lol
        exit("Insufficient IPv6 addresses???")
    if num_required_ipv6_addresses > 0:
        print "Using %d IPv6 addresses" % num_required_ipv6_addresses
        allocatable.extend(get_allocatable(num_required_ipv6_addresses,
            num_ports_per_ipv6_address, ipv6_nms))
    return allocatable

def get_allocatable(num_required_addresses, num_ports_per_address, nmlist):
    if isinstance(nmlist[0].network, IPv6Network): ipclass = "IPv6"
    if isinstance(nmlist[0].network, IPv4Network): ipclass = "IPv4"
    else: ipclass = "Unknown. Error?"
    num_addresses = 0
    allocatable = []
    while num_addresses < num_required_addresses:
        # round robin
        nm = nmlist.pop(0)
        nmlist.append(nm)
        a = nm.get_random_address()
        if a:
            ports = get_port_list(str(a), num_ports_per_address)
            allocatable.append((a,ports))
            num_addresses += 1
        else:
            if sum([x.numfree for x in nmlist]) <= 0:
                print "Unable to obtain required addresses."
                break
    print "Allocated %d %s addresses" % (num_addresses, ipclass)
    return allocatable

def addWebServer(config=None, interface_manager=None):
    resource = BridgeManager(config=config,
            interface_manager=interface_manager)
    site = Site(resource)
    reactor.listenTCP(8080, site, interface='127.0.0.1')
    return resource
