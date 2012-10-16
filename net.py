#!/usr/bin/env python
"""
Contains helper functions for managing network interfaces
"""

import re
from ipaddr import IPNetwork, IPv4Network, IPv6Network, IPAddress, IPv6Address

import time
from math import log
from subprocess import Popen, PIPE
from random import getrandbits

class InterfaceManager(object):
    """ base class for implementing
        address allocating policies.
    """
    def __init__(self):
        raise NotImplementedError
    def add_network_manager(self):
        raise NotImplementedError
    def remove_network_manager(self):
        raise NotImplementedError

    @property
    def addresses(self):
        """
        return addresses managed
        by this InterfaceManager
        """
        raise NotImplementedError

    @property
    def networks(self):
        """
        return the set of networks managed by
        this InterfaceManager
        """
        raise NotImplementedError

    def save(self):
        """
        """
        raise NotImplementedError

    def restore(self):
        raise NotImplementedError

class AutoInterfaceManager(InterfaceManager):
    def __init__(self, auto=False):
        self.network_managers = []
        if auto:
            print "AutoInterfaceManager launched with auto=True"
            all_networks = get_configured_networks()
            public_networks = filter(public_network, all_networks)
            self.network_managers = [ NetworkManager(network) \
                    for network in public_networks ]
            self.save()

    @property
    def addresses(self):
        #XXX flatten the array?
        return [ n.addresses for n in self.network_managers ]

    @property
    def networks(self):
        return [ n.network for n in self.network_managers ]

    def add_network_manager(self, network_manager):
        self.network_managers.append(network_manager)

    def remove_network_manager(self, network_manager, restore=False):
        if restore: network_manager.restore()
        self.network_managers.remove(network_manager)

    def save(self):
        """
        save network state when instantiated
        we just track which addresses were there before
        """
        print "AutoInterfaceManager called save()" 
        return [ n.save() for n in self.network_managers ]

    def restore(self):
        """
        put network state back the way it was
        """
        return [ n.restore() for n in self.network_managers ]

class NetworkManager(object):
    """
    track and allocate addresses within a network
    """
    def __init__(self, network):
        #XXX: overload type?
        self.network = IPNetwork(network)
        self.managed_addresses = []
        self.unmanaged_addresses = self.addresses
        #XXX: should auto call save?
        print "Instantiated NetworkManager for %s" % self.network

    @property
    def addresses(self):
        """ get the currently configured addresses (address and prefix) as a list of IPNetwork objects """
        system_addresses = get_configured_addresses()
        #print "system addresses: %s" % system_addresses
        # exclude addresses not in the managed network
        excluded = filter(self.network.__contains__, system_addresses)
        #print "the excluded set of addresses: %s" % excluded
        return excluded

    @property
    def numhosts(self):
        if self.network:
            return self.network.numhosts
        return 0

    @property
    def numfree(self):
        if self.network:
            return (self.network.numhosts - 2) - (len(self.unmanaged_addresses) + len(self.managed_addresses))
        return 0

    def _test_add_address(self, address):
        """
        returns True if address may be added to
        the managed_addresses of this NetworkManager.
        """
        if address in self.network and \
                address not in self.unmanaged_addresses and \
                address not in self.managed_addresses and \
                address != self.network.network and \
                address != self.network.broadcast:
                    return True
        return False

    def _test_remove_address(self, address):
        """
        returns True if address is managed and may be removed
        by this NetworkManager
        """
        if address in self.managed_addresses: return True
        return False

    def add_address(self, address):
        """
        add an address to this NetworkManager, and bring it up
        """
        addr = IPAddress(address) 
        if not self._test_add_address(addr): return None
        up_address(addr, self.network.prefixlen)
        assert (addr in self.addresses)
        self.managed_addresses.append(addr)
        return addr

    def remove_address(self, address):
        """
        removes an address from this NetworkManager and the system
        """
        addr = IPAddress(address)
        if not self._test_remove_address(addr): return None
        IPNetwork
        down_address(addr, self.network.prefixlen)
        self.managed_addresses.remove(addr)
        return addr

    def get_random_address(self):
        """
        bring up a random address in the managed network
        """
        while True:
            addr = IPAddress(self.network.network._ip +\
                getrandbits(int(log(self.network.numhosts, 2))))
            attempt = self.add_address(addr)
            if attempt: return attempt
            if self.numfree <= 0: return None
            #XXX: running time?

    def get_all_addresses(self):
        """
        bring up all addresses not currently used
        """
        addresses = []
        for address in self.network:
            a = self.add_address(address)
            if a: addresses.append(a)
        return addresses

    def save(self):
        """
        save network state when instantiated
        we just track which addresses were there before
        """
        self.saved = self.addresses

    def restore(self):
        """
        put it back the way it was <3
        """
        for address in self.addresses:
            if address not in self.saved:
                self.remove_address(address)

def get_configured_addresses():
    """
    parses output of "$ ip addr" for configured addresses.
    returns a list of IPAddress objects.
    """
    inet = Popen(["/bin/ip", "addr"], stdin=PIPE, stdout=PIPE).communicate()
    m = re.finditer("inet6?\s(?P<addr>\S*?)\/\d+\s.*?(?P<mode>secondary)?\s(?P<dev>\S*)\n", inet[0])
    #XXX: pretty annoying, but should probably be IPAddress
    return [IPAddress(net['addr']) for net in [net.groupdict() for net in m]]

def get_configured_networks():
    """
    parses output of  "$ ip addr" for attached networks.
    Ignores secondary interfaces.
    """
    # get attached, configured networks
    networks = []
    inet = Popen(["/bin/ip", "addr"], stdin=PIPE, stdout=PIPE).communicate()
    # get both ipv4 and ipv6 networks
    m = re.finditer("inet6?\s(?P<addr>\S*?)\s.*?(?P<mode>secondary)?\s(?P<dev>\S*)\n", inet[0])
    for net in [net.groupdict() for net in m]:
        if net['mode'] == 'secondary': continue
        networks.append(IPNetwork(net['addr']))
    return networks

def public_network(net):
    """ returns true if the net is Internet read """
    if net.is_link_local or net.is_loopback or net.is_multicast or net.is_private or net.is_reserved or net.is_unspecified:
        return False
    return True

def get_random_addresses(net, desired):
    """ returns a list of ip network objects with random host bits """
    # Don't bother. host, network, broadcast are 3
    if net.numhosts < 4:
        print net
        print "not enough spare addresses... :("
        return []
    # Might take a while for big (ipv6) networks :-)
    if net.numhosts - 3 < desired:
        print "asked for more IPs than is possible for this network. Limiting to %d addresses" % (net.numhosts - 3)
        desired = min(net.numhosts - 3, desired)
    addresses = []
    conflicts = [repr(net)]
    while len(addresses) < desired:
        # ghetto, why can no specify netmask in constructor as kwarg?
        ip = IPAddress(net.network._ip + getrandbits(int(log(net.numhosts, 2))))
        ip = IPNetwork("%s/%s"%(ip,net.prefixlen))
        if ip != net.broadcast and ip != net.network and repr(ip) not in conflicts:
            conflicts.append(repr(ip))
            addresses.append(ip)
    return addresses

#XXX call to system as r00t, don't be dumb here...
# add the following to your sudoers file:
# YOUR_HERDER_USERNAME (ALL)=NOPASSWD: /sbin/ip
def up_address(address, prefixlen, interface="eth0"):
    address = str(IPNetwork("%s/%s"%(address,prefixlen)))
    print "Bringing up address %s" % address
    Popen(["sudo", "ip", "addr", "add", str(address), "dev", interface]).communicate()
    time.sleep(1)

def down_address(address, prefixlen, interface="eth0"):
    address = str(IPNetwork("%s/%s"%(address,prefixlen)))
    print "Bringing downaddress %s" % address
    Popen(["sudo", "ip", "addr", "del", str(address), "dev", interface]).communicate()
