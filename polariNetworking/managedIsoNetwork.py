#-----  https://scapy.readthedocs.io/en/latest/installation.html  --------
#
#You need the following software in order to install Scapy on Windows:
#
#Python: Python 2.7.X or 3.4+. After installation, add the Python installation directory and its
#Scripts subdirectory to your PATH. Depending on your Python version, the defaults would
#be C:\Python27 and C:\Python27\Scripts respectively.
#Npcap: the latest version. Default values are recommended. Scapy will also work with Winpcap.
#Scapy: latest development version from the Git repository. Unzip the archive, open a
#command prompt in that directory and run python setup.py install.
#
#------------------------------------------------------------------------
#
import scapy.config
import scapy.route
import scapy.layers.l2
import scapy.all as spy
import getopt
import sys
import os
import math
import socket
import errno
#Referenced Github on neighborhood.py by bwaldvogel for developing code below.
#Defines an isolated network, which may or may not be a secure network.
class managedIsoNetwork():
    def __init__(self, name=None, networkRegisteredSystems=[], networkIPs = []):
        self.name = name
        self.hostNames = []
        self.networkIPs = networkIPs
        self.networkRegisteredSystems = networkRegisteredSystems
        #Creates a "Packet Capture" Interface, which can be used to analyze traffic on the
        #given network.  Should be Npcap for windows and libpcap interface for others.
        self.packetCaptureServiceActive = False

    def getNetworkInterfaces(self):
        ifaceList = spy.get_if_list()
        print("interface list: ", ifaceList)

    def getHostsOnCurrentWifi(self):
        try:
            scapy.config.Conf.sniff_promisc=False
            scapy.config.Conf.use_pcap()
            opts, args = getopt.getopt(sys.argv[1:], 'hi:', ['help', 'interface'])
        except getopt.GetoptError as err:
            print(str(err))
        interface_to_scan = None
        for o, a in opts:
            if o in ('-h', '--help'):
                interface_to_scan = a
            elif o in ('-i', '--interface'):
                interface_to_scan = a
        for network, netmask, _, interface, address, _ in scapy.config.conf.route.routes:
            if interface_to_scan and interface_to_scan != interface:
                continue
            #Skip loopback network and default gw
            if network == 0 or interface == 'lo' or address == '0.0.0.0':
                continue
            if(netmask <= 0 or netmask >= 0xFFFFFFFF):
                print("illegal netmask value", hex(netmask))
                continue
            if(interface != interface_to_scan and interface.startswith('docker') or interface.startswith('br-')):
                continue
            #Remaining networks are those we actually want to analyze.
            network = scapy.utils.ltoa(network)
            #Convert to CIDR notation
            netmask = 32 - int(round(math.log(0xFFFFFFFF - netmask, 2)))
            #Scan and print neighbors
            net = "%s/%s" % (network, netmask)
            #attempt to scan neighbors
            try:
                response, err = scapy.layers.l2.arping(net, iface=interface, timeout=5, verbose=True)
                for s, r in response.res:
                    line = r.sprintf("%Ether.src%  %ARP.psrc%")
                    try:
                        hostname = socket.gethostbyaddr(r.psrc)
                        if not hostname in self.hostNames:
                            self.hostNames.append(hostname)
                    except socket.herror:
                        #Failed to resolve
                        pass
            except socket.error as e:
                if e.errno == errno.EPERM:
                    print("Operation not Permitted: Must run from root.")
                else:
                    raise