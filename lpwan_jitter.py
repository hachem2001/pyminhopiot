from main import *
from packet import Packet
from logger import Logger

from typing import Any

"""

OUERTANI Mohamed Hachem (omhx21@gmail.com)

Aim : simulate the conditions of the WIP paper.

Note to self :
- Only a handful of "source" nodes.
- They are the destination or source of packets, along side the gateways
- Intermediate nodes play the SOLE ROLE of facilitating these ping-pongs
- A source node, as for now, is not a 'ping_pong_facilitating' node.


Further constraints would include :
- A variable number N of nodes
- Source nodes can also be relay nodes
- All nodes can be source and relay nodes


Furrrther work :
- Clustering (academic 1st priority)
- Dead branches ( CF personal notes & personal preference )


"""

class PacketLP(Packet):
    """
            Our own specification for a packet, including the information
            that we deem necessary for the functioning of the protocol.
            In this case :
            - source_id of first emitter of the packet (The Source)
            - destination_id (Must be -1 for any gateway, or a source_id
            in the case of a message returning to a specific node)
            - last_in_path : id of last node transmitting the packet
            - packet_id : id of the packet itself.
            - whether it is an ACK or not (and which packet_id it acks if so.)
            The last_in_path
    """

    packet_id_counter = 1  # Static variable to the class

    class DataLP:
        def __init__(self, source_id: int, packet_id : int, ack : (bool, int)= (False, -1)):
            self.packet_id = packet_id
            self.source_id = source_id
            self.last_in_path = source_id
            self.ack = ack
        
        def __repr__(self) -> str:
            return f'<{type(self)}{{{self.packet_id},{self.source_id},{self.last_in_path},{self.ack}}}>'
        


    def __init__(self, source_id: int, ack : (bool, int)= (False, -1)):
        """
        Re-insisting : "source_id" would be the gateway's ID if the
        gateway is sending a message back to a source.
        """
        data = self.DataLP(source_id, PacketLP.packet_id_counter, ack)
        super().__init__(data, source_id)
        PacketLP.packet_id_counter += 1

    def get_id(self):
        return self.data.packet_id


class GatewayLP(Gateway):
    def process_packet(self, simulator: 'Simulator', packet: 'PacketLP'):
        """
        Processing of packets reaching the gateway.
        Invokes a send_ack
        """
        GATEWAY_LOGGER.log(f"Gateway {self.node_id} captured packet: {packet}")
        self.send_ack(simulator, packet)

    def send_ack(self, simulator: 'Simulator', in_packet: 'PacketLP'):
        """
        Send the ACK message corresponding to the in_packet
        Invokes the corresponding broadcast_packet
        :in_packet: Packet received for which an ACK will be created
        """
        ack_packet = PacketLP(self.get_id(), ack=(True, in_packet.get_id()))
        self.broadcast_packet(simulator, ack_packet)


class NodeLP(Node):
    """
    Implementation following paper
    """

    def __init__(self, x: float, y: float, channel: 'Channel' = None):
        super().__init__(x, y, channel)
        self.last_packets = []  # Stores list of last heard packet ids
        # A packet_id is removed from the list when the node hears back its echo
        # This way, a packet never gets retransmitted twice by the same node.

    def process_packet(self, simulator: 'Simulator', packet: 'PacketLP'):
        # How to trigger a computer scientist/programmer
        if packet.data.last_in_path in self.last_packets:
            # Remove id from the list
            self.last_packets.remove(packet.data.last_in_path)
            # And do nothing. Drop the packet
            # TODO : Fixed size of how many IDs to keep track of
            # Remember : extreme LPWAN here.
            return

        # If packet not yet seen
        packet.data.last_in_path = self.get_id()  # Set last-in-path
        self.broadcast_packet(simulator, packet)


class SourceLP(NodeLP):
    def start_sending(self, simulator: Simulator):
        self.send_packet(simulator)

        # UNCOMMENT FOR PERIODIC SENDING

        # simulator.schedule_event(self.interval, self.start_sending)
        # Don't add simulator as arg, added by default.

    def process_packet(self, simulator: Simulator, packet: PacketLP):
        # Drop packets.
        if packet.data.ack:
            SOURCE_LOGGER.log(f"Source {self.node_id} received ack for packet_id: {packet.data.ack[1]}")

        return

    def send_packet(self, simulator: Simulator):
        packet = PacketLP(self.get_id(), False)
        SOURCE_LOGGER.log(f"Source {self.node_id} sending packet: {packet}")
        self.broadcast_packet(simulator, packet)
