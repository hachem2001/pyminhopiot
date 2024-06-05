from main import *

class ChannelGeneric(Channel):
    def handle_transmission(self, simulator: 'Simulator',
                            packet: 'Packet', sender_id: int):
        """ As the name implies. It creates the appropriate events. """
        # Send packet to all adjacent points
        for (node_id, distance) in self.adjacencies_per_node[sender_id]:
            new_packet = packet.forward(sender_id)
            new_packet.add_to_path(node_id)  # Add ID of receiver to its path.
            delay = distance * self.packet_delay_per_distance_unit
            simulator.schedule_event(delay,
                                     self.assigned_nodes[node_id].receive_packet, new_packet)
            CHANNEL_LOGGER.log(
                f"channel registered packet from {sender_id} to {node_id}")

class NodeGeneric(Node):
    next_id = 1

    def receive_packet(self, simulator: Simulator, packet: Packet):
        """
        Registers receiving a packet, then processing it. Call back used
        by channels.
        """
        self._log(f"received packet: {packet}")
        super().receive_packet(simulator, packet)

    def broadcast_packet(self, simulator: Simulator, packet: Packet):
        """
        Broadcast packet through channel. 
        """
        self._log(f"broadcast packet: {packet}")
        super().broadcast_packet(simulator, packet)

class GatewayGeneric(Gateway):
    def process_packet(self, simulator: Simulator, packet: Packet):
        self._log(f"captured packet: {packet}")
        # Gateways can also process packets like regular nodes if needed
        # self.process_packet(simulator, packet)

class SourceGeneric(Source):
    def start_sending(self, simulator: Simulator):
        self.send_packet(simulator)
        # simulator.schedule_event(self.interval, self.start_sending)
        # Don't add simulator as arg, added by default.

    def send_packet(self, simulator: Simulator):
        packet = Packet(data="Hello", source_id=self.node_id, first_emission_time=simulator.get_current_time())
        self._log(f"sending packet: {packet}")
        self.broadcast_packet(simulator, packet)
