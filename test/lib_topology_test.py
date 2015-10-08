# Copyright 2015 ETH Zurich
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
:mod:`lib_topology_test` --- SCION topology tests
=================================================
"""
# Stdlib
from unittest.mock import patch, MagicMock

# External packages
import nose
import nose.tools as ntools

# SCION
from lib.defines import (
    BEACON_SERVICE,
    CERTIFICATE_SERVICE,
    DNS_SERVICE,
    PATH_SERVICE,
    ROUTER_SERVICE,
)
from lib.topology import (
    Element,
    InterfaceElement,
    RouterElement,
    ServerElement,
    Topology
)


class TestElementInit(object):
    """
    Unit tests for lib.topology.Element.__init__
    """
    def test_basic(self):
        elem = Element()
        ntools.assert_is_none(elem.addr)
        ntools.assert_is_none(elem.name)

    @patch("lib.topology.haddr_parse", autospec=True)
    def test_ip_addr(self, parse):
        element = Element(("addrtype", "addr"))
        parse.assert_called_with("addrtype", "addr")
        ntools.eq_(element.addr, parse.return_value)

    def test_name_basic(self):
        elem = Element(name='localhost')
        ntools.assert_equal(elem.name, 'localhost')

    def test_name_numeric(self):
        elem = Element(name=42)
        ntools.assert_equal(elem.name, '42')


class TestServerElementInit(object):
    """
    Unit tests for lib.topology.ServerElement.__init__
    """
    @patch("lib.topology.Element.__init__", autospec=True)
    def test_basic(self, element_init):
        server_dict = {'AddrType': "addrtype", 'Addr': 123}
        server = ServerElement(server_dict, 'name')
        element_init.assert_called_once_with(server, ("addrtype", 123), 'name')

    @patch("lib.topology.Element.__init__", autospec=True)
    def test_no_name(self, element_init):
        server_dict = {'AddrType': "addrtype", 'Addr': 123}
        server = ServerElement(server_dict)
        element_init.assert_called_once_with(server, ("addrtype", 123), None)


class TestInterfaceElementInit(object):
    """
    Unit tests for lib.topology.InterfaceElement.__init__
    """
    def setUp(self):
        self.interface_dict = {
            'AddrType': 'atype', 'Addr': 'addr', 'IFID': 1, 'NeighborAD': 2,
            'NeighborISD': 3, 'NeighborType': 4, 'ToUdpPort': 5, 'UdpPort': 6,
            'ToAddr': None,
        }

    def tearDown(self):
        del self.interface_dict

    @patch("lib.topology.Element.__init__", autospec=True)
    def test_to_addr_none(self, element_init):
        interface = InterfaceElement(self.interface_dict, 'name')
        element_init.assert_called_once_with(
            interface, ('atype', 'addr'), 'name')
        ntools.eq_(interface.if_id, 1)
        ntools.eq_(interface.neighbor_ad, 2)
        ntools.eq_(interface.neighbor_isd, 3)
        ntools.eq_(interface.neighbor_type, 4)
        ntools.eq_(interface.to_udp_port, 5)
        ntools.eq_(interface.udp_port, 6)
        ntools.assert_is_none(interface.to_addr)

    @patch("lib.topology.Element.__init__", autospec=True)
    def test_name_none(self, element_init):
        interface = InterfaceElement(self.interface_dict)
        element_init.assert_called_once_with(
            interface, ('atype', 'addr'), None)

    @patch("lib.topology.haddr_parse", autospec=True)
    @patch("lib.topology.Element.__init__", autospec=True)
    def test_to_addr(self, element_init, parse):
        self.interface_dict['ToAddr'] = 'toaddr'
        interface = InterfaceElement(self.interface_dict)
        parse.assert_called_once_with('atype', 'toaddr')
        ntools.eq_(interface.to_addr, parse.return_value)


class TestRouterElementInit(object):
    """
    Unit tests for lib.topology.RouterElement.__init__
    """
    def setUp(self):
        self.router_dict = {'AddrType': 'atype', 'Addr': 'addr', 'Interface': 2}

    def tearDown(self):
        del self.router_dict

    @patch("lib.topology.InterfaceElement", autospec=True)
    @patch("lib.topology.Element.__init__", autospec=True)
    def test_basic(self, element_init, interface):
        interface.return_value = 'interface'
        router = RouterElement(self.router_dict, 'name')
        element_init.assert_called_once_with(router, ('atype', 'addr'), 'name')
        interface.assert_called_once_with(2)
        ntools.eq_(router.interface, 'interface')

    @patch("lib.topology.InterfaceElement", autospec=True)
    @patch("lib.topology.Element.__init__", autospec=True)
    def test_name_none(self, element_init, interface):
        router = RouterElement(self.router_dict)
        element_init.assert_called_once_with(router, ('atype', 'addr'), None)


class TestTopologyInit(object):
    """
    Unit tests for lib.topology.Topology.__init__
    """
    def test(self):
        topology = Topology()
        ntools.assert_false(topology.is_core_ad)
        ntools.eq_(topology.isd_id, 0)
        ntools.eq_(topology.ad_id, 0)
        ntools.eq_(topology.dns_domain, "")
        ntools.eq_(topology.beacon_servers, [])
        ntools.eq_(topology.certificate_servers, [])
        ntools.eq_(topology.dns_servers, [])
        ntools.eq_(topology.path_servers, [])
        ntools.eq_(topology.parent_edge_routers, [])
        ntools.eq_(topology.child_edge_routers, [])
        ntools.eq_(topology.peer_edge_routers, [])
        ntools.eq_(topology.routing_edge_routers, [])


class TestTopologyFromFile(object):
    """
    Unit tests for lib.topology.Topology.from_file
    """
    @patch("lib.topology.Topology.from_dict", spec_set=[],
           new_callable=MagicMock)
    @patch("lib.topology.load_json_file", autospec=True)
    def test(self, load, from_dict):
        load.return_value = 'topo_dict'
        from_dict.return_value = 'topology'
        ntools.eq_(Topology.from_file('filename'), 'topology')
        load.assert_called_once_with('filename')
        from_dict.assert_called_once_with('topo_dict')


class TestTopologyFromDict(object):
    """
    Unit tests for lib.topology.Topology.from_dict
    """
    @patch("lib.topology.Topology.parse_dict", autospec=True)
    def test(self, parse_dict):
        topology = Topology.from_dict('dict')
        parse_dict.assert_called_once_with(topology, 'dict')
        ntools.assert_is_instance(topology, Topology)


class TestTopologyParseDict(object):
    """
    Unit tests for lib.topology.Topology.parse_dict
    """
    @patch("lib.topology.logging.warning", autospec=True)
    @patch("lib.topology.RouterElement", autospec=True)
    @patch("lib.topology.ServerElement", autospec=True)
    def test(self, server_elem, router_elem, log_warning):
        bs = {'a': 'b', 'c': 'd'}
        cs = {'e': 'f', 'g': 'h'}
        ds = {'i': 'j', 'k': 'l'}
        ps = {'m': 'n', 'o': 'p'}
        er = {ROUTER_SERVICE + str(i): 'router' + str(i) for i in range(5)}
        zk = {
            'zk0': {
                'AddrType': "IPV4", 'Addr': 'zkv4', 'ClientPort': 2181,
            },
            'zk1': {
                'AddrType': "IPV6", 'Addr': 'zkv6', 'ClientPort': 2182,
            }
        }
        topo_dict = {
            'Core': 0, 'ISDID': 1, 'ADID': 2,
            'DnsDomain': 3, 'BeaconServers': bs,
            'CertificateServers': cs, 'DNSServers': ds,
            'PathServers': ps, 'EdgeRouters': er,
            'Zookeepers': zk,
        }
        server_elem.side_effect = ['bs0', 'bs1', 'cs0', 'cs1', 'ds0', 'ds1',
                                   'ps0', 'ps1']
        routers = [MagicMock(spec_set=['interface']) for i in range(5)]
        for router in routers:
            router.interface = MagicMock(spec_set=['neighbor_type'])
        routers[0].interface.neighbor_type = 'PARENT'
        routers[1].interface.neighbor_type = 'CHILD'
        routers[2].interface.neighbor_type = 'PEER'
        routers[3].interface.neighbor_type = 'ROUTING'
        router_elem.side_effect = routers
        topology = Topology()
        topology.beacon_servers = [1]
        topology.certificate_servers = [2]
        topology.dns_servers = [3]
        topology.path_servers = [4]
        topology.parent_edge_routers = [5]
        topology.child_edge_routers = [6]
        topology.peer_edge_routers = [7]
        topology.routing_edge_routers = [8]
        # Call
        topology.parse_dict(topo_dict)
        # Tests
        ntools.assert_false(topology.is_core_ad)
        ntools.eq_(topology.isd_id, 1)
        ntools.eq_(topology.ad_id, 2)
        ntools.eq_(topology.dns_domain, 3)
        ntools.eq_(topology.beacon_servers, [1, 'bs0', 'bs1'])
        ntools.eq_(topology.certificate_servers, [2, 'cs0', 'cs1'])
        ntools.eq_(topology.dns_servers, [3, 'ds0', 'ds1'])
        ntools.eq_(topology.path_servers, [4, 'ps0', 'ps1'])
        ntools.eq_(topology.parent_edge_routers, [5, routers[0]])
        ntools.eq_(topology.child_edge_routers, [6, routers[1]])
        ntools.eq_(topology.peer_edge_routers, [7, routers[2]])
        ntools.eq_(topology.routing_edge_routers, [8, routers[3]])
        ntools.eq_(sorted(topology.zookeepers),
                   sorted([('zkv4:2181'), ('[zkv6]:2182')]))
        ntools.eq_(log_warning.call_count, 1)


class TestTopologyGetAllEdgeRouters(object):
    """
    Unit tests for lib.topology.Topology.get_all_edge_routers
    """
    def test(self):
        topology = Topology()
        topology.parent_edge_routers = [0, 1]
        topology.child_edge_routers = [2]
        topology.peer_edge_routers = [3, 4, 5]
        topology.routing_edge_routers = [6, 7]
        ntools.eq_(topology.get_all_edge_routers(), list(range(8)))


class TestTopologyGetOwnConfig(object):
    """
    Unit tests for lib.topology.Topology.get_own_config
    """
    @patch("lib.topology.logging.error", autospec=True)
    def _check(self, topology, server_type, server_id, server, log_error):
        ntools.eq_(topology.get_own_config(server_type, server_id), server)
        if server is None:
            ntools.eq_(log_error.call_count, 1)

    def test(self):
        topology = Topology()
        topology.beacon_servers = [MagicMock(spec_set=['name']) for i in
                                   range(4)]
        topology.beacon_servers[2].name = 'name'
        topology.certificate_servers = [MagicMock(spec_set=['name']) for i in
                                        range(4)]
        topology.certificate_servers[2].name = 'name'
        topology.dns_servers = [MagicMock(spec_set=['name']) for i in range(4)]
        topology.dns_servers[2].name = 'name'
        topology.path_servers = [MagicMock(spec_set=['name']) for i in range(4)]
        topology.path_servers[2].name = 'name'
        server_types = [BEACON_SERVICE, CERTIFICATE_SERVICE, DNS_SERVICE,
                        PATH_SERVICE] * 2
        server_ids = ['name'] * 4 + ['bad_name'] * 4
        servers = [topology.beacon_servers[2],
                   topology.certificate_servers[2],
                   topology.dns_servers[2],
                   topology.path_servers[2]] + [None] * 4
        for type, id, server in zip(server_types, server_ids, servers):
            yield self._check, topology, type, id, server

    @patch("lib.topology.Topology.get_all_edge_routers", autospec=True)
    def test_er(self, get_edge_routers):
        topology = Topology()
        edge_routers = [MagicMock(spec_set=['name']) for i in range(4)]
        edge_routers[2].name = 'name'
        get_edge_routers.return_value = edge_routers
        ntools.eq_(topology.get_own_config(ROUTER_SERVICE, 'name'),
                   edge_routers[2])
        get_edge_routers.assert_called_once_with(topology)

    @patch("lib.topology.logging.error", autospec=True)
    @patch("lib.topology.Topology.get_all_edge_routers", autospec=True)
    def test_er_fail(self, get_edge_routers, log_error):
        topology = Topology()
        edge_routers = [MagicMock(spec_set=['name']) for i in range(4)]
        get_edge_routers.return_value = edge_routers
        ntools.assert_is_none(topology.get_own_config(ROUTER_SERVICE, 'name'))
        ntools.eq_(log_error.call_count, 1)

    @patch("lib.topology.logging.error", autospec=True)
    def test_bad_server_type(self, log_error):
        topology = Topology()
        ntools.assert_is_none(topology.get_own_config('blah', 'blah'))
        ntools.eq_(log_error.call_count, 1)


if __name__ == "__main__":
    nose.run(defaultTest=__name__)
