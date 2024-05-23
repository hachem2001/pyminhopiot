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
		- whether it is an ACK or not.
		The last_in_path 
	"""
	packet_id = 1
	
	def __init__(self, packet_id, source_id: int, ack = False)
		"""
		Re-insisting : "source_id" would be the gateway's ID if the
		gateway is sending a message back to a source.
		"""
		data = {
			packet_id = packet_id,
			source_id = source_id, 
			last_in_path = source_id,
			ack = ack,
		}
		
		super().__init__(data, source_id)
		self.packet_id = packet_id; packet_id += 1
		self.source_id = source_id
		self.last_in_path = source_id 
	
	

class GatewayLP(Gateway):
	def receive_packet(self, simulator: 'Simulator', packet: 'PacketLP')
		
	def send_ack(self, simulator: 'Simulator', in_packet: 'PacketLP')
		""" Send the ACK message corresponding to the in_packet """
