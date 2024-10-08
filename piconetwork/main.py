import heapq
import time
from io import StringIO
from math import sqrt
from typing import Callable, Any, Dict, List, Optional
import random
"""
OUERTANI Mohamed Hachem <omhx21@gmail.com>

Many simplifications are included, notably the lack of a Channel.
It is in nodes that the time of receiving the packet is encoded

This is naturally not representative of the real world
- To be improved with an ad-hoc Channel class taking-it-all

"""


# User made imports
from .packet import Packet
from .logger import Logger

NONE_LOGGER = Logger("none", verbose=False)
EVENT_LOGGER = Logger("event", verbose=False)
GATEWAY_LOGGER = Logger("gateway", verbose=False)
NODE_LOGGER = Logger("node", verbose=False)
SIMULATOR_LOGGER = Logger("simulator", verbose=False)
SOURCE_LOGGER = Logger("source", verbose=False)
CHANNEL_LOGGER = Logger("channel", verbose=True)

class Loggable:
    """ An object that ships with a logging unit. Useful for logging what is happening (event callbacks etc ...) """

    def __init__(self, logger=NONE_LOGGER, preamble='', active=True, verbose_overwrite=True, simulator: Optional['Simulator']=None):
        """
        :logger: Logger object associated
        :preamble: Preamble to prepend to every logged message
        :active: Whether the act of saving logs to the logs table of the logger object is enabled.
        :verbose: Whether this log is verbose or not.
        """
        self._logger = logger
        self._logger_preamble = preamble
        self._logger_active = active
        self._logger_verbose_overwrite = verbose_overwrite
        self._logger_simulator: Optional['Simulator'] = simulator

    def _reset_loggable_part(self):
        self._logger.reset_logs()
        self._logger_simulator = None

    def _log(self, *args, end='', verbose_overwrite = True, **kwargs):
        """ Adds message to log. """
        if self._logger_active:
            output = StringIO()
            print(*args, file=output, end=end, **kwargs)
            extra_prependor = self._logger_simulator != None and f'|{self._logger_simulator.get_current_time():0.2f}| ' or ''
            self._logger.log(f"{extra_prependor}{self._logger_preamble}"+output.getvalue(), verbose_overwrite and self._logger_verbose_overwrite)

    def set_logger_active(self, active:bool):
        """ Whether logs are saved (in memory) or not """
        self._logger_active = active

    def set_logger_verbose_overwrite(self, verbose_overwrite:bool):
        """ Whether the messages saved in memory are shown in stdout. """
        self._logger_verbose_overwrite = verbose_overwrite

    def set_logger_simulator(self, simulator:'Simulator'):
        """
        Sets the simulator associated with this logger
        Useful for adding timestamps to logs.
        """
        self._logger_simulator = simulator

class Event:
    def __init__(self, time: float, callback: Callable[['Simulator'], Any], *args, **kwargs):
        """
        An event to be executed. No re-scheduling possible, however cancellation IS possible.
        :param time: Float representing time in milliseconds.
        :param callback: Event callback when the time of execution of the event arrives.
        :param args: Ordered arguments of callback
        :param kwargs: Keyword arguments of callback
        """
        self.time = time
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        self.effective = True # Parameter allowing the cancellation of events.

    def __lt__(self, other: 'Event'):
        return self.time < other.time

    def execute(self, simulator: 'Simulator'):
        if self.effective:
            self.callback(simulator, *self.args, **self.kwargs)

    def cancel(self):
        self.effective = False

class Simulator:
    def __init__(self, simulation_length: float = 10.0, simulations_real_inertia: float = 0.01):
        """
        Simulator, to which pertains events.
        Holds an internal clock, and events get executed linearly in it.
        :simulation_length: How many time units corresponding to events will be treated.
        :simulations_real_inertia: How long (float) 1 simulation second corresponds to real execution time
        """
        assert (simulations_real_inertia >= 0.0)
        self.current_time = 0.0
        self.simulation_length = simulation_length
        self.event_queue = []
        self.running = False
        self.nodes: Dict[int, Node] = {}
        # How long to sleep before every event execution.
        self.simulations_real_inertia = simulations_real_inertia

    def get_current_time(self) -> float:
        """ Returns current time. Similar to NS3's Simulator::NOW()  """
        return self.current_time

    def schedule_event(self, delay: float, callback: Callable[['Simulator'], Any], *args, **kwargs) -> Event:
        """
        Schedules an event for execution.
        :returns: event object, allowing to cancel the event if needed
        """
        event_time = self.current_time + delay
        event = Event(event_time, callback, *args, **kwargs)
        heapq.heappush(self.event_queue, event)
        self.log(f"Event scheduled for time {event_time}")
        return event

    def run(self):
        self.running = True
        while self.event_queue and self.running:
            event = heapq.heappop(self.event_queue)
            assert event.time >= self.current_time, "Event scheduled in the past, not possible"
            time.sleep(self.simulations_real_inertia * ((self.simulation_length > 0.0 and min(event.time, self.simulation_length) or event.time) - self.current_time))
            self.current_time = event.time # MUST SET BEFORE EXECUTING THE EVENT

            if self.simulation_length > 0.0 and \
                    self.current_time > self.simulation_length:
                self.running = False
                break

            self.log(f"Executing event at time {self.current_time}")
            event.execute(self)
            # ^ Simulate some delay for each event execution

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

class Channel:
    def __init__(self, packet_delay_per_unit=0.1):
        """
        Each node will be registered with it's identifier.
        Would be in self.assigned_nodes (dict of node_id to Node)

        Each node would have his adjacency-list : nodes adjacent
        to it, in a list. Each adjacency is a tuple : (id, delay)

        A matrix would have been nice, but this would do.
        It's a graph structure either way.
        :packet_delay_per_unit: by default transmissions here are 0.01 second per time unit.
        """

        self.assigned_nodes = {}
        self.adjacencies_per_node = {}
        self.packet_delay_per_distance_unit = packet_delay_per_unit

    def set_delay_per_distance_unit(self, delay:float):
        """ Modifies delay per unit distance; or propagation slowness if you will """
        self.packet_delay_per_distance_unit = delay

    def assign_node(self, node: 'Node'):
        self.assigned_nodes[node.get_id()] = node  # Reference.
        node.set_channel(self)
        self.adjacencies_per_node[node.get_id()] = []

    def get_assigned_node(self, node_id: int) -> 'Node':
        """ Returns a node handle for given node_id. This assumes it is assigned to the channel """
        return self.assigned_nodes[node_id]

    def assign_isolated_nodes(self, *args: 'Node'):
        """
        It might feel counterintuitive here, but the instead of doing
        a NetDevice assigned to each Node, and NetDevice assigned to
        channels, here we assign the Nodes themselves to the channel
        (register them), and let each node be assigned a channel.
        """
        for i, node in enumerate(args):
            self.assign_node(node)

    def create_bidirectional_link(self, node_id_1: int, node_id_2: int,
                                  delay: float, reliability: float = 1.0):
        """
        Create bi-directional link
        """

        assert (self.assigned_nodes[node_id_1] != None)
        assert (self.assigned_nodes[node_id_2] != None)

        self.create_unidirectional_link(node_id_1, node_id_2, delay, reliability)
        self.create_unidirectional_link(node_id_2, node_id_1, delay, reliability)

    def create_unidirectional_link(self, node_id_1: int, node_id_2: int,
                                   delay: float, reliability: float = 1.0):
        """
        Create unidirectional link
        """

        assert (self.assigned_nodes[node_id_1] != None)
        assert (self.assigned_nodes[node_id_2] != None)

        self.adjacencies_per_node[node_id_1].append((node_id_2, delay, reliability))

    def check_link(self, node_id_1: int, node_id_2: int, unidirectional: bool = False) -> bool:
        """
        Check if node_id_1 is linked to node_id_2
        if unidirectional : only node_id_1 -> node_id_2
        """
        return_value = False
        for (id_, distance, _) in self.adjacencies_per_node[node_id_1]:
            if id_ == node_id_2:
                return_value = True

        if unidirectional and not return_value:
            return False

        if not unidirectional:
            for (id_, distance, _) in self.adjacencies_per_node[node_id_2]:
                if id_ == node_id_1:
                    return True

        return return_value

    def _get_link_list_index(self, node_id_1: int, node_id_2: int) -> int:
        """
        Internal function useful for returning the index in self.adjacencies_per_node of node_id_1 where we find node_id_2.
        Returns -1 if it doesn't exist.
        """
        id_to_return = -1

        for i in range(len(self.adjacencies_per_node[node_id_1])):
            (id_, distance, _) = self.adjacencies_per_node[node_id_1][i]
            if id_ == node_id_2:
                id_to_return = i
        return id_to_return

    def get_neighbour_ids(self, node_id) -> List[int]:
        """
        Return list of indices of connected neighbours.
        """
        result = set()
        for _id, distance, reliability in self.adjacencies_per_node[node_id]:
            result.add(_id)

        return list(result)

    def get_distance(self, node_id_1: int, node_id_2: int):
        """ Returns the distance for node_id_1 -> node_id_2 if it exists. """
        assert(self.check_link(node_id_1, node_id_2, unidirectional = True) == True) # Assert the link exists.
        id_in_list_of_node_2 = self._get_link_list_index(node_id_1, node_id_2)
        return self.adjacencies_per_node[node_id_1][id_in_list_of_node_2][1]

    def set_reliability_unidirectional(self, node_id_1: int, node_id_2: int, reliability: float):
        """ Sets the reliability of the transmission node_id_1 -> node_id_2. """
        assert(self.check_link(node_id_1, node_id_2, unidirectional = True) == True) # Assert the link exists.
        assert(reliability <= 1.0 and reliability >= 0.0) # Assert the link exists.
        id_in_list_of_node_2 = self._get_link_list_index(node_id_1, node_id_2)
        self.adjacencies_per_node[node_id_1][id_in_list_of_node_2] = (self.adjacencies_per_node[node_id_1][id_in_list_of_node_2][0], self.adjacencies_per_node[node_id_1][id_in_list_of_node_2][1], reliability)
        CHANNEL_LOGGER.log(f"Set reliability from {node_id_1} to {node_id_2} to {reliability}")

    def set_reliability(self, node_id_1: int, node_id_2: int, reliability: float, unidirectional:bool = False):
        """ Sets the reliability of the transmission node_id_1 <---> node_id_2. """
        self.set_reliability_unidirectional(node_id_1, node_id_2, reliability)
        if not unidirectional:
            self.set_reliability_unidirectional(node_id_2, node_id_1, reliability)

    def set_reliability_all(self, reliability:float):
        """ Sets the reliability of ALL links """
        for sender_id in self.adjacencies_per_node.keys():
            for (node_id, distance, _) in self.adjacencies_per_node[sender_id]:
                self.set_reliability_unidirectional(sender_id, node_id, reliability)

    def get_time_delay(self, node_id_1: int, node_id_2: int):
        """ Returns the time delay for node_id_1 -> node_id_2 if it exists. """
        return self.packet_delay_per_distance_unit * self.get_distance(node_id_1, node_id_2)

    def create_metric_mesh(self, distance_threshold: float, *args: 'Node', reliability:float = 1.0):
        """
        Assign the nodes, and creates the adjacenties using x,y distance
        between nodes.
        """
        for i, node in enumerate(args):
            self.assign_node(node)

        for i, node in enumerate(args):
            for j, other_node in enumerate(args):
                if node.get_id() != other_node.get_id() and \
                        not self.check_link(node.get_id(), other_node.get_id()) and \
                        node.distance_to(other_node) <= distance_threshold:
                    self.create_bidirectional_link(node.get_id(),
                                                   other_node.get_id(), node.distance_to(other_node), reliability)
                    CHANNEL_LOGGER.log(f"Created link ({node.get_id()}, {node.x:.2f}, {node.y:.2f}), ({other_node.get_id()}, {other_node.x:.2f}, {other_node.y:.2f}), {reliability}")

    def handle_transmission(self, simulator: 'Simulator',
                            packet: 'Packet', sender_id: int):
        """ As the name implies. It creates the appropriate events. """
        # Send packet to all adjacent points
        for (node_id, distance, reliability) in self.adjacencies_per_node[sender_id]:
            if random.random() < reliability:
                new_packet = packet.forward(sender_id)
                new_packet.add_to_path(node_id)  # Add ID of receiver to its path.
                delay = distance * self.packet_delay_per_distance_unit
                simulator.schedule_event(delay,
                    self.assigned_nodes[node_id].receive_packet, new_packet)
            #CHANNEL_LOGGER.log(f"channel registered packet from {sender_id} to {node_id}")

class Node(Loggable):
    next_id = 1

    def __init__(self, x: float, y: float, channel: 'Channel' = None, hearing_radius_capacity = -1):
        super(Node, self).__init__(logger=NODE_LOGGER, preamble=str(Node.next_id)+" - ")
        self.node_id = Node.next_id
        Node.next_id += 1
        self.x = x
        self.y = y
        self.channel = channel
        self.hearing_radius_capacity = hearing_radius_capacity # if -1, channel takes care of it.

    def set_channel(self, channel: 'Channel'):
        """ Assign said channel to node. Called by channel. """
        self.channel = channel

    def get_id(self):
        return self.node_id

    def receive_packet(self, simulator: Simulator, packet: Packet):
        """
        Registers receiving a packet, then processing it. Call back used
        by channels.
        """
        self.process_packet(simulator, packet)

    def process_packet(self, simulator: 'Simulator', packet: 'Packet'):
        """
        Process the packet : it is here where broadcasting it may be
        decided.
        """
        self.broadcast_packet(simulator, packet)

    def broadcast_packet(self, simulator: Simulator, packet: Packet):
        """
        Broadcast packet through channel.
        """
        assert (self.channel != None)
        self.channel.handle_transmission(simulator, packet, self.get_id())

    def broadcast_packet_schedule(self, simulator: Simulator, packet: Packet, delay:float = 0.0):
        """
        Schedule broadcasting the packet - so it won't be immediate.
        """
        # Remember : simulator is set as first argument by default in callback of schedule_event.
        simulator.schedule_event(delay, self.broadcast_packet, packet)

    def distance_to(self, other: 'Node') -> float:
        return sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

class Gateway(Node):
    def __init__(self, x: float, y: float, channel: 'Channel' = None):
        super(Gateway, self).__init__(x, y, channel)
        super(Node, self).__init__(logger=GATEWAY_LOGGER, preamble=str(Node.next_id)+" - ")

    def process_packet(self, simulator: Simulator, packet: Packet):
        # Gateways can also process packets like regular nodes if needed
        # self.process_packet(simulator, packet)
        pass

class Source(Node):
    def __init__(self, x: float, y: float, interval: float, channel: 'Channel' = None):
        super().__init__(x, y, channel)
        super(Node, self).__init__(logger=SOURCE_LOGGER, preamble=str(self.node_id)+" - ")
        self.interval = interval

    def start_sending(self, simulator: Simulator):
        self.send_packet(simulator)
        # simulator.schedule_event(self.interval, self.start_sending)
        # Don't add simulator as arg, added by default.

    def send_packet(self, simulator: Simulator):
        packet = Packet(data="Hello", source_id=self.node_id)
        self.broadcast_packet(simulator, packet)
