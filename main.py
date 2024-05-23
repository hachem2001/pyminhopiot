import heapq
import time
from math import sqrt
from typing import Callable, Any, Dict, List

"""
OUERTANI Mohamed Hachem <omhx21@gmail.com>

Many simplifications are included, notably the lack of a Channel.
It is in nodes that the time of receiving the packet is encoded

This is naturally not representative of the real world
- To be improved with an ad-hoc Channel class taking-it-all 

"""


# User made imports
from packet import Packet
from logger import Logger

EVENT_LOGGER = Logger("event", verbose = False)
GATEWAY_LOGGER = Logger("gateway", verbose = False)
NODE_LOGGER = Logger("node", verbose = False)
SIMULATOR_LOGGER = Logger("simulator", verbose = False)
SOURCE_LOGGER = Logger("source", verbose = False)

class Event:
	def __init__(self, time: float, callback: Callable[['Simulator'], Any], *args, **kwargs):
		"""
		An event to be executed.
		:param time: Float representing time in milliseconds.
		:param callback: Event callback when the time of execution of the event arrives.
		:param args: Ordered arguments of callback
		:param kwargs: Keyword arguments of callback
		"""
		self.time = time
		self.callback = callback
		self.args = args
		self.kwargs = kwargs

	def __lt__(self, other: 'Event'):
		return self.time < other.time

	def execute(self, simulator: 'Simulator'):
		self.callback(simulator, *self.args, **self.kwargs)


class Simulator:
	def __init__(self, simulation_length : float = 10.0):
		"""
		Simulator, to which pertains events.
		Holds an internal clock, and events get executed linearly in it.
		"""
		self.current_time = 0.0
		self.simulation_length = simulation_length
		self.event_queue = []
		self.running = False
		self.nodes: Dict[int, Node] = {}

	def schedule_event(self, delay: float, callback: Callable[['Simulator'], Any], *args, **kwargs):
		event_time = self.current_time + delay
		event = Event(event_time, callback, *args, **kwargs)
		heapq.heappush(self.event_queue, event)
		self.log(f"Event scheduled for time {event_time}")

	def run(self):
		self.running = True
		while self.event_queue and self.running:
			event = heapq.heappop(self.event_queue)
			self.current_time = event.time
			self.log(f"Executing event at time {self.current_time}")
			event.execute(self)
			time.sleep(0.01)  # Simulate some delay for each event execution
			if self.simulation_length > 0.0 and self.current_time > self.simulation_length:
				self.running = False

	def stop(self):
		"""
		Generally this function is useless unless the simulation of queues is running batches by batches.
		Do not use this function after a non-ending .run(), use when you know what you're doing.
		:return: None
		"""
		self.running = False
		self.log("Simulator stopped")

	def log(self, message):
		if SIMULATOR_LOGGER:
			SIMULATOR_LOGGER.log(message)

	def add_node(self, node: 'Node'):
		self.nodes[node.node_id] = node

	def add_nodes(self, *args):
		for node in args:
			self.add_node(node)

	def send_packet(self, packet: Packet, current_node: 'Node'):
		current_node.receive_packet(self, packet)


class Node:
	next_id = 1

	def __init__(self, x: float, y: float):
		self.node_id = Node.next_id
		Node.next_id += 1
		self.x = x
		self.y = y
		self.neighbors: List['Node'] = []

	def add_neighbor(self, neighbor: 'Node'):
		self.neighbors.append(neighbor)

	def receive_packet(self, simulator: Simulator, packet: Packet):
		packet.add_to_path(self.node_id)
		NODE_LOGGER.log(f"Node {self.node_id} received packet: {packet}")
		self.process_packet(simulator, packet)

	def process_packet(self, simulator: Simulator, packet: Packet):
		for neighbor in self.neighbors:
			if neighbor.node_id not in packet.path:
				simulator.schedule_event(1, neighbor.receive_packet, packet)

	def distance_to(self, other: 'Node') -> float:
		return sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)
 

class Gateway(Node):
	def receive_packet(self, simulator: Simulator, packet: Packet):
		packet.add_to_path(self.node_id)
		GATEWAY_LOGGER.log(f"Gateway {self.node_id} captured packet: {packet}")
		# Gateways can also process packets like regular nodes if needed
		# self.process_packet(simulator, packet)


class Source(Node):
	def __init__(self, x: float, y: float, interval: float):
		super().__init__(x, y)
		self.interval = interval

	def start_sending(self, simulator: Simulator):
		self.send_packet(simulator)
		simulator.schedule_event(self.interval, self.start_sending) # Don't add simulator as arg, added by default.
	def send_packet(self, simulator: Simulator):
		packet = Packet(data="Hello", source_id=self.node_id)
		SOURCE_LOGGER.log(f"Source {self.node_id} sending packet: {packet}")
		self.process_packet(simulator, packet)

# Function to add neighbors based on distance
def add_neighbors_within_distance(nodes: List[Node], distance_threshold: float):
	for i, node in enumerate(nodes):
		for j, other_node in enumerate(nodes):
			if i != j and node.distance_to(other_node) <= distance_threshold:
				node.add_neighbor(other_node)
