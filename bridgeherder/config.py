# The BridgeHerder config!
# 
# Warning, by default BridgeHerder will pick random addresses from the
# same subnet as existing addresses. This is probably what you want if
# this script is run on a vm or dedicated server with some IP space assigned
# to it, but you may need to manually configure the attached networks if this
# is not the case.
#XXX: how do we indicate which addresses are unavailable?
#XXX: doesn't do anything
#MY_NETWORKS = ["1.2.3.4/29", "fe80::dead:beef/64"]

# Here you can limit the number of bridges that will be run
# You may need to experiment to find a good value for your system
NUM_BRIDGES =  2

# number of ports bound to each address; the default is to use the max.
# Tor's descriptor format supports 8 or-address lines with 16 portspec entries
# each. That means we can have 8 different addresses, each with 16 ports.
# By default, we use the maximum number of ports.
NUM_PORTS_PER_ADDRESS =  4 # max is 16

NUM_ADDRESSES_PER_BRIDGE = 3 # max is 8, I think.

#8 or-address lines with 16 portspec entries per line: 128
MAX_OR_ADDRESSES_PER_BRIDGE = NUM_ADDRESSES_PER_BRIDGE * NUM_PORTS_PER_ADDRESS

# the ratio of IPv4 to IPv6 listening sockets
PERCENT_IPV4_PORTS = 0.5

# let the bridge herder manage addresses for you, will require root privileges.
#MANAGE_ADDRESSES = True
#XXX: doesn't do anything

# uses iptables to redirect connections on advertised ports to the port bridgedb
# is actually listening on. Will probably mean that we can steal ports that are
# bound to other applications. :-)
#USE_IPTABLES = True # False is not supported :-)
#XXX: doesn't do anything

# Set the path to your tor binary here.
TOR_BINARY = '/home/user/bridgeherder/tor'
