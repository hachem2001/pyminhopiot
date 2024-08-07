import heapq

from .main import *
from .packet import Packet
from .logger import Logger

from typing import Any, Tuple, ClassVar, Type, Optional
from enum import Enum, auto

import random
import math

"""
OUERTANI Mohamed Hachem (omhx21@gmail.com)

Aim : simulate the conditions of the WIP paper.

Assumptions :
- Nodes have homogenous (speed-wise) internal clocks : all of them have the same tick rate.
    This is important to handle jitter - can we do better? The code implementation seems to assume we can do that,
    and the paper assumes we can use it to find ToA and jitter.
    This also adds another internal variable : record time of reception of the packet.

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
        def __init__(self, source_id: int, packet_id : int, ack : tuple[bool, int]= (False, -1), before_last_in_path = -1):
            self.packet_id = packet_id
            self.source_id = source_id
            self.last_in_path = source_id
            self.before_last_in_path = before_last_in_path # TODO : TEMPORARY FIX FOR "FORWARDED PACKET" DETERMINISTIC DETECTION. TO BE FIXED LATER
            self.ack = ack

        def __repr__(self) -> str:
            return f'<{self.packet_id},{self.source_id},{self.last_in_path},{self.before_last_in_path},{self.ack}>'

    def __init__(self, source_id: int, first_emission_time:float = -1, ack : Tuple[bool, int]= (False, -1), before_last_in_path = -1):
        """
        Re-insisting : "source_id" would be the gateway's ID if the
        gateway is sending a message back to a source.
        """
        data : self.DataLP = self.DataLP(source_id, PacketLP.packet_id_counter, ack, before_last_in_path)
        super().__init__(data, source_id, first_emission_time=first_emission_time)
        PacketLP.packet_id_counter += 1

    def get_id(self):
        return self.data.packet_id

    def get_source_id(self):
        return self.data.source_id

    def get_antecessor_id(self):
        return self.data.last_in_path

class NodeLP_BaseState_Handler():
    """
    For simplicity, this is an abstract class for some "handler" of packets in a NodeLP.
    Meaning : IDLE would have its handler would derive from this. Same for RETX_PENDING, etc.
    NOTE : A NodeLP must be able to switch between handlers when switching between states.
    Therefore information on the packet is not stored here, but in its seperate class definition, and passed everytime in here for treatment.

    A NodeLP packet handler _must_ define these states by default.
    """
    @staticmethod
    def process_packet(simulator: 'Simulator', node: 'NodeLP', packet: 'PacketLP', packet_jitter_info: 'NodeLP_Jitter_Configuration'):
        """ Process first-arriving packet """
        raise NotImplementedError("Handle method not implemented")

class NodeLP_Idle_Handler(NodeLP_BaseState_Handler):
    @staticmethod
    def process_packet(simulator: 'Simulator', node: 'NodeLP', packet: 'PacketLP', packet_jitter_info: 'NodeLP_Jitter_Configuration'):
    # Schedule retransmission.
        if packet.data.ack:
            # TODO : Treat acks properly? For now paper says reduce jitter. To be explained I suppose.
            packet_jitter_info.step_reduce_jitter()
            if not node.RETRANSMIT_BACK_ACKS:
                return

        # Schedule transmission. Save event handle should the event be cancelled (e.g ack received)
        packet_jitter_info.set_internal_state(NodeLP_Packet_State.RETX_PENDING) # USE NodeLP_Packet_State.RETX_PENDING.value below, or else "self" wouldn't be passed.
        event = simulator.schedule_event(packet_jitter_info.get_jitter_random(), NodeLP_Packet_State.RETX_PENDING.value.transmit_packet_lp_schedulable, node, packet, packet_jitter_info)
        packet_jitter_info.event_handle = event

class NodeLP_Retxpending_Handler(NodeLP_BaseState_Handler):
    @staticmethod
    def process_packet(simulator: 'Simulator', node: 'NodeLP', packet: 'PacketLP', packet_jitter_info: 'NodeLP_Jitter_Configuration'):
        # Count neighbours or cancel scheduled retransmission
        possibility_1 = packet.data.ack and packet_jitter_info.packet_message_id == node.get_packet_message_id(packet) and packet_jitter_info.packet_id != packet.get_id() # Overhearing gateway acknowledgement (from gateway!) (for current packet/message id!) : suppress transmission, as well as reduce jitter
        possibility_2 = packet_jitter_info.suppression_mode == NodeLP_Suppression_Mode.BOLD and packet.data.before_last_in_path == packet_jitter_info.id_node_antecessor_of_last_packet_forwarded # A n+1 retransmission of the message already occurred

        if packet_jitter_info.packet_message_id == node.get_packet_message_id(packet):
            # "Overheard neighbour" count increase!
            packet_jitter_info.register_neighbour(packet.data.last_in_path)

        if possibility_1: # Reduce jitter
            packet_jitter_info.step_reduce_jitter()

        if possibility_1 or possibility_2: # Cancel retransmission event and go back to IDLE. (can't believe I missed this.)
            packet_jitter_info.event_handle.cancel()
            packet_jitter_info.handle_possible_suppression_set_or_unset()
            packet_jitter_info.set_internal_state(NodeLP_Packet_State.IDLE)

    @staticmethod
    def transmit_packet_lp_schedulable(simulator: 'Simulator', node: 'NodeLP', packet: 'PacketLP', packet_jitter_info: 'NodeLP_Jitter_Configuration'):
        """
        Schedulable immediate transmission. It checks current state, but its aim is to initite immediate transmission
        Suppression is decided here.
        TODO : If the transmission takes time, the node would no longer be able to receive packets, and collision can happen etc etc.
        TODO : add safeguard mecanism should packet window not be assigned (for whatever coding error there was) allowing to verify this quickly.
        """
        # Expected state. Proceed as per the paper. This is the "jitter timeout" situation.
        # Two possibilities, depending on random probability outcome : allowed to send, or not allowed to send.
        if packet_jitter_info.get_internal_state() != NodeLP_Packet_State.RETX_PENDING:
            raise AssertionError("State not expected in scheduled transmission. Event of retransmission should be _canceled_ in the case packet treatment halted")

        random_decisive_variable = random.random()
        if random_decisive_variable < packet_jitter_info.get_transmission_probability():
            # Forward packet, and go to followup state.
            packet_jitter_info.retransmission_time = simulator.get_current_time()
            node.transmit_packet_lp_effective(simulator, packet)
            # And go to follow-up-state, as well as set its appropriate triggers
            packet_jitter_info.set_internal_state(NodeLP_Packet_State.FOLLOWUP_PENDING) # Same thing : use value from enum to have 'self' defined, here below.
            event = simulator.schedule_event(packet_jitter_info._FOLLOWUP_PENDING_DONE_TIMEOUT(), NodeLP_Packet_State.FOLLOWUP_PENDING.value.end_of_followup_pending_schedulable, node, packet, packet_jitter_info, any_type_of_followup_received=False)
            packet_jitter_info.event_handle = event
        else:
            # Drop packet and get to DONE state (Idle)
            packet_jitter_info.set_internal_state(NodeLP_Packet_State.IDLE)
            packet_jitter_info.event_handle = None
            packet_jitter_info.handle_possible_suppression_set_or_unset()
            node.packet_window_free(packet_jitter_info.packet_id_index)
            node._log(f"dropped packet {packet} on suppression state")

class NodeLP_Followuppending_Handler(NodeLP_BaseState_Handler):
    @staticmethod
    def process_packet(simulator: 'Simulator', node: 'NodeLP', packet: 'PacketLP', packet_jitter_info: 'NodeLP_Jitter_Configuration'):
        # If we hear a packet that is forwarding our message (last_in_path is this node) : move to Done.
        if packet.data.before_last_in_path == node.get_id():
            # Hear a forward retransmission? Treat it here
            # Acknowledgement based delay reduction : an ACK recevied DIRECTLY FROM A GATEWAY (previous message in internal state was not an ACK)
            if packet.data.ack and packet_jitter_info.packet_id != packet.get_id():
                # TODO : Overwrite current state and focus on forwarding the ack?? Not clear - opted AGAINST (Juan Antonio specified we treat the simple case here, source receives no acks)
                packet_jitter_info.half_reduce_jitter_with_minimize()

                # For now : do that, as it means we are connected to Gateway.
                # Remove all planned events,
                packet_jitter_info.event_handle.cancel()
                packet_jitter_info.set_internal_state(NodeLP_Packet_State.FOLLOWUP_PENDING) # Below can be scheduled as an immediate event, or just executed now.
                NodeLP_Followuppending_Handler.end_of_followup_pending_schedulable(simulator, node, packet, packet_jitter_info, any_type_of_followup_received=True, direct_ack_from_gateway = True)

                # and treat this packet immediately, starting fresh.
                if node.RETRANSMIT_BACK_ACKS:
                    node.process_packet(simulator, packet)
            else:
                # "Overheard neighbour" count increase!
                # packet_jitter_info.register_neighbour(packet.data.last_in_path)

                # Forward Delay Adaptation
                packet_jitter_info.adapt_jitter(node.estimate_jitter_of_next_forwarding_node_within_channel(simulator, node.channel, packet_jitter_info, packet))

                # Then remove all planned events,
                packet_jitter_info.event_handle.cancel()

                # decrease jitter and move to DONE(IDLE) state. Note : jitter decrease NOT handled by the function, however jitter increase is.
                packet_jitter_info.set_internal_state(NodeLP_Packet_State.FOLLOWUP_PENDING) # Below can be scheduled as an immediate event, or just executed now.
                NodeLP_Followuppending_Handler.end_of_followup_pending_schedulable(simulator, node, packet, packet_jitter_info, any_type_of_followup_received=True, direct_ack_from_gateway = False)

        else:
            # Hear a retransmission of said packet but by someone else? Treat it here.
            # For now, until we understand better how to treat packet retransmissions, just increase neighbour count.
            # NOTE : neighbour count is increased at the TOP of the function.
            pass

    @staticmethod
    def end_of_followup_pending_schedulable(simulator: 'Simulator', node: 'NodeLP', packet: 'PacketLP', packet_jitter_info: 'NodeLP_Jitter_Configuration', any_type_of_followup_received:bool = False, direct_ack_from_gateway:bool = False):
        """
        Schedules timeout of followup-pending.
        It automatically sets event callback to null.
        :any_type_of_followup_received: means this node was the before-last-in-path of the packet, whether it's an ACK or a message forwarding.
        TODO : add safeguard mecanism should packet window not be assigned (for whatever coding error there was) allowing to verify this quickly.
        """
        if packet_jitter_info.get_internal_state() != NodeLP_Packet_State.FOLLOWUP_PENDING:
            raise AssertionError("State not expected in scheduled transmission. Event of retransmission should be _canceled_ in the case packet treatment halted")

        if any_type_of_followup_received:
            # Depending on suppression mode, some value reset is due here. Changed in the future
            packet_jitter_info.handle_possible_suppression_set_or_unset(direct_ack_from_gateway_unset=direct_ack_from_gateway)
        else:
            packet_jitter_info.step_increase_jitter()
            packet_jitter_info.handle_possible_suppression_set_or_unset(no_followup_heard_set=True)

        packet_jitter_info.set_internal_state(NodeLP_Packet_State.IDLE)
        packet_jitter_info.event_handle = None
        packet_jitter_info.handle_possible_suppression_set_or_unset()
        node.packet_window_free(packet_jitter_info.packet_id_index)

class NodeLP_Done_Handler(NodeLP_BaseState_Handler):
    @staticmethod
    def process_packet(simulator: 'Simulator', node: 'NodeLP', packet: 'PacketLP', packet_jitter_info: 'NodeLP_Jitter_Configuration'):
        raise AssertionError("Current implementation assumes DONE and IDLE are the same state for simplicity")

# When we are on "flooding" , "fastflooding" or "slowflooding" mode, which can be considered as disjoint one-cell "States" but oh well.

class NodeLP_Flooding_Handler(NodeLP_BaseState_Handler):
    @staticmethod
    def process_packet(simulator: 'Simulator', node: 'NodeLP', packet: 'PacketLP', packet_jitter_info: 'NodeLP_Jitter_Configuration'):
        # Immediate retransmission.
        if not packet.data.ack:
            node.transmit_packet_lp_effective(simulator, packet)
            node.packet_window_free(packet_jitter_info.packet_id_index)

class NodeLP_Fastflooding_Handler(NodeLP_BaseState_Handler):
    @staticmethod
    def process_packet(simulator: 'Simulator', node: 'NodeLP', packet: 'PacketLP', packet_jitter_info: 'NodeLP_Jitter_Configuration'):
        # Add fast delay
        if not packet.data.ack:
            event = simulator.schedule_event(random.random() * packet_jitter_info._JITTER_INTERVAL_DURATION(), NodeLP_Packet_State.FASTFLOODING.value.transmit_packet_lp_schedulable,  node, packet, packet_jitter_info)
            packet_jitter_info.event_handle = event

    @staticmethod
    def transmit_packet_lp_schedulable(simulator: 'Simulator', node: 'NodeLP', packet: 'PacketLP', packet_jitter_info: 'NodeLP_Jitter_Configuration'):
        node.transmit_packet_lp_effective(simulator, packet)
        node.packet_window_free(packet_jitter_info.packet_id_index)

class NodeLP_Slowflooding_Handler(NodeLP_BaseState_Handler):
    @staticmethod
    def process_packet(simulator: 'Simulator', node: 'NodeLP', packet: 'PacketLP', packet_jitter_info: 'NodeLP_Jitter_Configuration'):
    # Schedule retransmission.
        if not packet.data.ack:
            event = simulator.schedule_event(random.random() * packet_jitter_info.JITTER_MAX_VALUE, NodeLP_Packet_State.SLOWFLOODING.value.transmit_packet_lp_schedulable, node, packet, packet_jitter_info)
            packet_jitter_info.event_handle = event

    @staticmethod
    def transmit_packet_lp_schedulable(simulator: 'Simulator', node: 'NodeLP', packet: 'PacketLP', packet_jitter_info: 'NodeLP_Jitter_Configuration'):
        node.transmit_packet_lp_effective(simulator, packet)
        node.packet_window_free(packet_jitter_info.packet_id_index)

class NodeLP_Packet_State(Enum):
    """
    The various internam finite state machine states described in the paper
    For a NodeLP.

    They are per PACKET.
    """
    IDLE = NodeLP_Idle_Handler
    RETX_PENDING = NodeLP_Retxpending_Handler
    FOLLOWUP_PENDING = NodeLP_Followuppending_Handler
    DONE = NodeLP_Done_Handler # Redundant to be honest. If done, just turn back to Idle immediately after done.
    # The above 4 are CONNECTED.
    # The two below are not. They are monads if you wish.

    FLOODING = NodeLP_Flooding_Handler
    FASTFLOODING = NodeLP_Fastflooding_Handler
    SLOWFLOODING = NodeLP_Slowflooding_Handler

class NodeLP_Suppression_Mode(Enum):
    """
    Different suppression modes that can be used by a node
    """
    NEVER_ENGAGED = auto() # Fake state to take note of nodes that never received a message.
    REGULAR = auto() # No suppressions
    CONSERVATIVE = auto() # Conservative suppression depending on number of overheard neighbours
    AGGRESSIVE = auto() # Aggressive suppression with fixed probability.
    BOLD = auto() # I call it bold because it retransmits-not so long as it does not hear a retransmitter.

    DEFAULT_START = NEVER_ENGAGED # START MODE OF NODES.
    DEFAULT_SUPPRESSION = AGGRESSIVE # DEFINE DEFAULT SUPPRESSION MODE HERE!
    PROBABILISTIC_SUPPRESSIONS = [CONSERVATIVE, AGGRESSIVE] # List all probabilistic suppressions

class NodeLP_Jitter_Configuration:
    """
    This would be valid for every packet in the node's capacity.
    Therefore, it makes sense that this class regroups all relevant state variables per packet.
    TODO : different state variables per packet?? Or is this to be used for multiple sources?
    """

    MAX_NUMBER_OF_NEIGHBOUR_IDS_STORABLE: int = 10 # Really big assumption here.
    # NOTE : technically, some less deterministic but good enough methods of estimating the number of neighbours can be used
    # Nonetheless, it would require some number of bytes of storage in all cases.
    # Also: this doesn't treat the case of where neighbours can get lost due to weather situation/etc ...

    ADAPTATION_FACTOR: float = 0.5 # Value in interval (0,1]
    JITTER_MIN_VALUE: float = 0.2
    JITTER_MAX_VALUE: float = 1.2
    JITTER_INTERVALS: int = 10 # Number of intervals to divide the jitter to.
    # This corresponds to [0.2, 0.3], [0.3, 0.4], ... [1.1, 1.2]

    # Suppression default values
    SUPPRESSION_AGGRESSIVE_PROBABILITY = 0.2 # p_min as described in the paper
    SUPPRESSION_MODE_SWITCH : ClassVar[NodeLP_Suppression_Mode] = NodeLP_Suppression_Mode.DEFAULT_SUPPRESSION

    def _JITTER_INTERVAL_DURATION(self): return (self.JITTER_MAX_VALUE - self.JITTER_MIN_VALUE)/self.JITTER_INTERVALS

    def _FOLLOWUP_PENDING_DONE_TIMEOUT(self): return 2 * self.JITTER_MAX_VALUE

    def __init__(self, packet_message_id = -1, source_id = -1, antecessor_id = -1, packet_id = -1, packet_id_index = -1, mode : NodeLP_Suppression_Mode = NodeLP_Suppression_Mode.DEFAULT_SUPPRESSION, handler:Type[NodeLP_BaseState_Handler] = NodeLP_Idle_Handler ):
        """
        :packet_message_id: Packet Message ID (same one for M or ack of M).
        :packet_id: Packet ID (M and ack of M don't have same ID).
        :source_id: 0 for "any gateway", > 0 for a specific source
        :packet_id_index: position in the node's internal table. Must be set by the node!
        :mode: Suppression mode that we switch to when we reach maximum jitter.
        """
        # Redundant id tracking for easier coding - not truly an internal state variable, code can be rewritten to omit it.
        self.packet_id_index = packet_id_index
        self.internal_state_for_packet_handler: Type[NodeLP_BaseState_Handler] = handler

        # Packet tracking related information
        self.packet_message_id = packet_message_id
        self.packet_id = packet_id
        self.source_id = source_id

        # Jitter adaptation internal state
        self.min_jitter = self.max_jitter = -1 # self.JITTER_INTERVALS-1 # MUST BE A NUMBER BETWEEN 0 and min(self.max_jitter,JITTER_INTERVALS)-1
        # self.JITTER_INTERVALS # MUST BE A NUMBER max(self.min_jitter,0)+1 and JITTER_INTERVALS

        self.reset_jitter() # To keep the implementation self-coherent, we define default values/behavior HERE. IN THIS FUNCTION.

        self._reset_value_jitter = [self.min_jitter, self.max_jitter] # In case of a reset, revert to this old "random" value.

        self.id_node_antecessor_of_last_packet_forwarded = antecessor_id

        # Overhead suppression internal state
        self.neighbours_noted = set() # Number of recorded neighbours is in here.
        self.suppression_mode : NodeLP_Suppression_Mode = NodeLP_Suppression_Mode.DEFAULT_START
        self.suppression_switch : NodeLP_Suppression_Mode = mode
        self.probability_of_forwarding = 1.0 # between 0.0 and 1.0

        # State of packet
        self.internal_state_for_packet = NodeLP_Packet_State.IDLE

        # For cancelling event of schedulered transmission or scheduled followup if necessary. It can be thought of as a time internal state variable.
        self.event_handle : Optional[Event] = None

        # For time-based calculations :
        self.retransmission_time : Optional[float] = None # None if not retransmitted yet, >0 otherwise.

    def reset_mode_to(self, mode : NodeLP_Suppression_Mode, handler: Type[NodeLP_BaseState_Handler]):
        """ Resets the jitter configuration to initial random value, and sets its mode to given mode with handler """
        self.packet_message_id = self.packet_id = self.source_id = -1
        self.id_node_antecessor_of_last_packet_forwarded = -1
        self.internal_state_for_packet_handler: Type[NodeLP_BaseState_Handler] = handler
        self.probability_of_forwarding = 1.0 # between 0.0 and 1.0
        self.neighbours_noted = set() # Number of recorded neighbours is in here.
        self.suppression_switch = mode
        self.set_suppression_mode(NodeLP_Suppression_Mode.DEFAULT_START)
        self.internal_state_for_packet = NodeLP_Packet_State.IDLE
        self.min_jitter = self._reset_value_jitter[0]; self.max_jitter = self._reset_value_jitter[1]

    def soft_switch_to(self, packet_message_id, packet_id, source_id = False, antecessor_id = False):
        """
        Keeps the jitter parameters, and merely changes the IDs treated by the jitter parameter.
        packet_id_index does not change here, because it is a soft switch working on the same slot.
        """

        if source_id != False:
            self.source_id = source_id
        if antecessor_id != False:
            self.id_node_antecessor_of_last_packet_forwarded = antecessor_id

        # Reset event handle
        self.event_handle = None

        # Reset retransmission time : new packet, we didn't retransmit it yet
        self.retransmission_time : Optional[float] = None

        # Reset neighbour heard retransmission count if packet_id is different. TODO : is this correct ?
        if self.packet_id != packet_id:
            self.neighbours_noted.clear()
            if self.suppression_mode == NodeLP_Suppression_Mode.CONSERVATIVE: # Reset probability associated with it.
                self.set_suppression_mode(NodeLP_Suppression_Mode.CONSERVATIVE)

        # Change the IDs
        self.packet_id = packet_id
        self.packet_message_id = packet_message_id

        # If NEVER ENGAGED, SWITCH TO REGULAR MODE
        if self.suppression_mode == NodeLP_Suppression_Mode.NEVER_ENGAGED:
            self.set_suppression_mode(NodeLP_Suppression_Mode.REGULAR)

    def register_neighbour(self, neighbour_id: int) -> bool:
        if neighbour_id in self.neighbours_noted and self.get_neighbours_count() < self.MAX_NUMBER_OF_NEIGHBOUR_IDS_STORABLE:
            return False

        self.neighbours_noted.add(neighbour_id)
        return True

    def get_neighbours_count(self) -> int:
        return len(self.neighbours_noted)

    def get_transmission_probability(self):
        if self.suppression_mode == NodeLP_Suppression_Mode.CONSERVATIVE:
            self.probability_of_forwarding = 1.0 / (1 + self.get_neighbours_count())
        return self.probability_of_forwarding

    def set_internal_state(self, state: NodeLP_Packet_State):
        """ Sets the packet state (IDLE, RETXPENDING, ...) """
        self.internal_state_for_packet = state
        self.internal_state_for_packet_handler = state.value

    def get_internal_state(self) -> NodeLP_Packet_State:
        """ Returns the enum internal state of packet """
        return self.internal_state_for_packet

    def get_internal_state_handler(self) -> Type[NodeLP_BaseState_Handler]:
        """ Returns handler for state (IDLE, RETXPENDING, ...) """
        return self.internal_state_for_packet_handler

    def get_max_jitter(self) -> float:
        """ Get the maximum jitter of the state. """
        return self.max_jitter * self._JITTER_INTERVAL_DURATION() + self.JITTER_MIN_VALUE

    def get_min_jitter(self) -> float:
        """ Get the minimum jitter of the state. """
        return self.min_jitter * self._JITTER_INTERVAL_DURATION() + self.JITTER_MIN_VALUE

    def get_jitter_random(self) -> float:
        """
        Return a random variable between jitter min and jitter max, as per the paper description.
        Though I'm slightly surprised it works this way, instead of updating a jitter value directly, it's kept randomized.
        Reason : avoid collisions of packets IRL - for packets collide and cause jumble when well synchronized.
        """
        min_j = self.get_min_jitter()
        jitter = random.random() * (self.get_max_jitter() - min_j) + min_j
        return jitter

    def get_jitter_average(self) -> float:
        """ Returns the estimated average of the jitter used by this node """
        jitter = (self.get_max_jitter() + self.get_min_jitter())/2
        return jitter

    def set_jitter_interval_around(self, jitter):
        """ Sets jitter to a narrow interval around the given value. """
        # TODO : clip jitter instead
        assert jitter >= self.JITTER_MIN_VALUE and jitter <= self.JITTER_MAX_VALUE, "Jitter set outside of allowed values"
        jitter_min_index = min(int(math.floor((jitter-self.JITTER_MIN_VALUE)/self._JITTER_INTERVAL_DURATION())), self.JITTER_INTERVALS-1)
        jitter_max_index = max(int(math.ceil((jitter-self.JITTER_MIN_VALUE)/self._JITTER_INTERVAL_DURATION())), 1)
        self.min_jitter = jitter_min_index
        self.max_jitter = jitter_max_index

    def clip_jitter(self, jitter):
        """ Returns a cliped jitter in the appropriate interval """
        return max(self.JITTER_MIN_VALUE, min(self.JITTER_MAX_VALUE, jitter))

    def half_reduce_jitter_with_minimize(self):
        """ Sets jitter to minimal interval around half the average current value """
        self.set_jitter_interval_around(self.clip_jitter(self.get_jitter_average()/2))

    def step_reduce_jitter(self):
        """ Decreases jitter interval indexes of both min and max by 1 """
        self.min_jitter = max(0, self.min_jitter - 1) # The order is important
        self.max_jitter = max(self.min_jitter + 1, self.max_jitter - 1)

    def step_increase_jitter(self):
        """ Increases jitter interval indexes of both min and max by 1 """
        self.max_jitter = min(self.max_jitter + 1, self.JITTER_INTERVALS) # The order is important
        self.min_jitter = min(self.min_jitter + 1, self.max_jitter - 1)

    def double_increase_jitter_with_minimize(self):
        """ Sets jitter to minimal interval around double the average current value """
        self.set_jitter_interval_around(self.clip_jitter(self.get_jitter_average()*2))

    def adapt_jitter(self, other_jitter):
        """ Paper-described bellman-equation-type jitter adaptation """
        # NOTE : this differs from the Jiazi Yi's code, which itself isn't compatible with the paper's note.
        # To make the technique functional, we render the adaptation probabilistic : instead of adding the difference, we switch to the new value with a probability
        old_jitter_average = self.get_jitter_average()
        new_jitter_average = (1 - self.ADAPTATION_FACTOR) * old_jitter_average + self.ADAPTATION_FACTOR * other_jitter
        self.set_jitter_interval_around(self.clip_jitter(new_jitter_average))

    def minimize_jitter_interval(self):
        """ Makes it so that the jitter interval is set to the smallest possible interval around the average value. """
        self.set_jitter_interval_around(self.clip_jitter(self.get_jitter_average()))

    def reset_jitter(self):
        """
        Makes jitter random over the full range.
        This is different from having an assigned jitter interval.
        """
        self.min_jitter = random.randint(0, self.JITTER_INTERVALS - 1) # MUST BE A NUMBER BETWEEN 0 and min(self.max_jitter,JITTER_INTERVALS)-1
        self.max_jitter = self.min_jitter + 1 # MUST BE A NUMBER max(self.min_jitter,0)+1 and JITTER_INTERVALS

    def set_suppression_mode(self, mode):
        """
        Switch suppression mode to the one specified.
        """
        if mode == NodeLP_Suppression_Mode.REGULAR:
            self.probability_of_forwarding = 1.0
        elif mode == NodeLP_Suppression_Mode.CONSERVATIVE:
            self.probability_of_forwarding = 1.0 / (1 + self.get_neighbours_count())
        elif mode == NodeLP_Suppression_Mode.AGGRESSIVE:
            self.probability_of_forwarding = self.SUPPRESSION_AGGRESSIVE_PROBABILITY
        elif mode == NodeLP_Suppression_Mode.BOLD:
            self.probability_of_forwarding = 1.0

        self.suppression_mode = mode

    def handle_possible_suppression_set_or_unset(self, no_followup_heard_set : bool = False, direct_ack_from_gateway_unset : bool = False):
        """
        For simplicity, suppression is set or unset at the end of every packet cycle. This way, it is consistent (compared to the current way that it is dealt with)
        Also for simplicity, for now, setting or unsetting suppression mode has the same condition.
        """
        if self.max_jitter != self.JITTER_INTERVALS or direct_ack_from_gateway_unset:
            self.set_suppression_mode(NodeLP_Suppression_Mode.REGULAR)
        elif self.max_jitter == self.JITTER_INTERVALS or no_followup_heard_set:
            self.set_suppression_mode(self.suppression_switch)
        else:
            pass # Do nothing I guess! Keep it as it is. Although this is impossible to reach, self.max_jitter can't not be == or != at the same time

class NodeLP_Receiver_State(Enum):
    READY_TO_RECEIVE = auto()
    NOT_READY_TO_RECEIVING = auto() # If a NodeLP receives a packet while it's receiving another, it considers that there is a collision and both packets get dropped.

class NodeLP(Node):
    """
    Implementation following paper.
    We will assume that a NodeLP will only retain a state machine for
    ONE packet. If it receives a packet of a different identifier at that point : drop

    The paper currently discusses work per packet.
    Incidentally we are obliged to define a fixed size.
    """

    PACKETS_STATE_CAPACITY = 1 # Can only keep track of one.

    PACKETS_REMEMBER_CAPACITY = 5 # Amount of packet ids that the node remembers in order not to retreat the same packet twice.

    RETRANSMIT_BACK_ACKS = False # If we try to send the Ack back to source.

    DISSALLOW_MULTIPLE_RETRANSMISSIONS = True # If the same packet_id can be reassigned to the same window as before. can happen in some "ping pong" situations

    NODE_RECEPTION_OF_PACKET_DURATION = NodeLP_Jitter_Configuration._JITTER_INTERVAL_DURATION(NodeLP_Jitter_Configuration) / 6.0 # Here we hard-code it per-packet. Normally, this would depend on the packet length among other things.
    # Here we set it to be the minimal jitter value divided by 4 (ARBITRARY CHOICE)

    # Default entry points depending on the mode of the node
    MODE_TO_SUPPRESSION_DICTIONARY = {
        'REGULAR': NodeLP_Suppression_Mode.REGULAR,
        'CONSERVATIVE': NodeLP_Suppression_Mode.CONSERVATIVE,
        'AGGRESSIVE': NodeLP_Suppression_Mode.AGGRESSIVE,
        'BOLD': NodeLP_Suppression_Mode.BOLD,
        'FLOODING': NodeLP_Suppression_Mode.NEVER_ENGAGED,
        'SLOWFLOODING': NodeLP_Suppression_Mode.NEVER_ENGAGED,
        'FASTFLOODING': NodeLP_Suppression_Mode.NEVER_ENGAGED
    }

    MODE_TO_STATE_DICTIONARY : Dict[str, NodeLP_Packet_State]= {
        'REGULAR': NodeLP_Packet_State.IDLE,
        'CONSERVATIVE': NodeLP_Packet_State.IDLE,
        'AGGRESSIVE': NodeLP_Packet_State.IDLE,
        'BOLD': NodeLP_Packet_State.IDLE,
        'FLOODING': NodeLP_Packet_State.FLOODING,
        'SLOWFLOODING': NodeLP_Packet_State.SLOWFLOODING,
        'FASTFLOODING': NodeLP_Packet_State.FASTFLOODING,
    }

    def __init__(self, x: float, y: float, channel: 'Channel' = None, mode = "REGULAR"):
        super().__init__(x, y, channel)
        # Stores list of last heard packet ids, with respect to the capacity
        # A packet_id is removed (set to -1) from the list when the node hears back its echo
        # This way, a packet never gets retransmitted twice by the same node (w/r to capacity)
        self.last_packets_treated = [-1 for i in range(NodeLP.PACKETS_STATE_CAPACITY)]

        # Record the set mode
        assert mode in self.MODE_TO_STATE_DICTIONARY.keys(), f"Unrecognized mode {mode}"
        self.mode = mode

        # Internal state variables for each packet in capacity of being treated.
        self.last_packets_informations = [NodeLP_Jitter_Configuration(packet_id_index=i, mode=self.MODE_TO_SUPPRESSION_DICTIONARY[mode], handler=self.MODE_TO_STATE_DICTIONARY[mode].value) for i in range(NodeLP.PACKETS_STATE_CAPACITY)]

        # Cycling stack or heap for last treated packets
        self.last_packets_remembered = [] # USED WITH heapq MODULE : retains just the packet IDs of the last

        # A node cannot receive packets instantaneously : it takes time. So we define some variable to be the "packet reception duration"
        # If we receive another packet whilst we're receiving another, we drop both!
        self.ready_to_receive = NodeLP_Receiver_State.READY_TO_RECEIVE
        self.reception_event = None # This is an event handler so we can cancel it in case.

        # For logging purposes :
        self._jitter_interval_before = 0
        self._jitter_interval_after = 0
        self._suppression_mode_before = 0
        self._suppression_mode_after = 0

        # NOTE : Assignment to whichever internal state is kind of random here. It should therefore depend on something fixed, like the source_id for example.

        # Keeps track of how many more packets can be treated further.
        self.remaining_capacity = NodeLP.PACKETS_STATE_CAPACITY

        # 'Enabled' parameter allowing to disable or enable the node. Used only for testing 'dissapearing' nodes.
        self.enabled = True

    def reset_mode_to(self, mode):
        """ Switches node's mode, useful for rerunning experiments over the same topology without regenerating the whole network """
        assert mode in self.MODE_TO_STATE_DICTIONARY.keys(), f"Unrecognized mode {mode}"
        self.mode = mode
        self.last_packets_informations[0].reset_mode_to(mode=self.MODE_TO_SUPPRESSION_DICTIONARY[mode], handler=self.MODE_TO_STATE_DICTIONARY[mode].value)

    def reset_node(self):
        """ Resets the node's parameters. """
        self.reset_mode_to(self.mode)

    def set_enabled(self, bl: bool):
        self.enabled = bl

    def get_enabled(self) -> bool:
        return self.enabled

    def estimate_jitter_of_next_forwarding_node_within_channel(self, simulator: 'Simulator', channel: 'Channel', internal_state : NodeLP_Jitter_Configuration , packet: 'PacketLP'):
        """
        Attempts to estimate the jitter of the node from which the packet was received, assuming the node transmitted the packet and heard back its echo
        This unfortunately relies on a functional internal clock within each device. We'll assume it is the case, and cheat using Simulator's time.
        Here we also cheat by asking the channel how long it takes to get to said node.
        TODO: Fix this cheaty case?
        """

        twottimestimeofarrivalplusjitter = simulator.get_current_time() - internal_state.retransmission_time
        channelestimatedtimeofarrival = channel.get_time_delay(self.get_id(), packet.data.last_in_path)
        return twottimestimeofarrivalplusjitter - 2 * channelestimatedtimeofarrival

    def get_packet_message_id(self, packet:'PacketLP'):
        """
        A packet ID changes when the content of the message is not different.
        Say, an ack to a message M does not have the same ID as M.
        This function returns the message ID.
        Meaning, for a packet M, if it's a message it returns its ID, if it's an ACK to M it returns the same ID as M.
        """
        packet_id = packet.data.ack != False and packet.data.ack[1] or packet.get_id()
        return packet_id

    def get_packet_window_index(self, packet:'PacketLP'):
        """
        If the packet is part of the node's processing, it will return the appropriate index
        Otherwise, it will return -1
        """
        packet_id = self.get_packet_message_id(packet)
        packet_id_index = -1

        try:
            packet_id_index = self.last_packets_treated.index(packet_id)
        except ValueError:
            packet_id_index = -1

        return packet_id_index

    def packet_window_register(self, packet:'PacketLP') -> Tuple[bool, int]:
        """
        If the packet is part of one of the node's processing windows, it will return the appropriate index with (True, packet_id_index)
        Else, it will assign a window to it if the capacity allows it, returning the tuple (True, packet_id_index)
        Else, it will return (False, -1)
        :returns: (Whether the packet has a dedicated window or not, packet_id if assigned, otherwise -1)
        """
        packet_id = self.get_packet_message_id(packet)
        packet_id_index = self.get_packet_window_index(packet)

        if packet_id_index == -1:
            if self.remaining_capacity <= 0:
                # Three possibilities :
                # either we indiscriminately drop the packet
                # or we indiscriminately immediately forward the packet
                # Not Opted Yet : To maybe do ?
                # or we decide to use one of the last packets' internal state for simulation
                # Not Opted Yet : TODO
                return (False, -1)
            else:
                # Assign the packet to the first slot
                packet_id_index = self.last_packets_treated.index(-1) # If error arises, it shouldn't. So there is a problem with the code.

                if NodeLP.DISSALLOW_MULTIPLE_RETRANSMISSIONS:
                    if self.last_packets_informations[packet_id_index].packet_message_id == packet_id:
                        return (False, packet_id_index)

                    if packet_id in self.last_packets_remembered:
                        return (False, packet_id_index)
                    else:
                        if len(self.last_packets_remembered) == self.PACKETS_REMEMBER_CAPACITY:
                            heapq.heappop(self.last_packets_remembered)
                        heapq.heappush(self.last_packets_remembered, packet_id)

                    # To disallow "PING-PONG situations". TODO : be careful about packet_message_id and packet_id

                self.last_packets_treated[packet_id_index] = packet_id

                # Here it is a soft switch : keep all the jitter and suppression configurations as they are.
                self.last_packets_informations[packet_id_index].soft_switch_to(packet_message_id=packet_id, packet_id=packet.get_id(), source_id=packet.get_source_id(), antecessor_id=packet.get_antecessor_id())
                self.remaining_capacity -= 1
                return (True, packet_id_index)

                # Different jitter per packet in packet capacity? TODO : TBS + assign packet depending on source in the list.
        else:
            return (True, packet_id_index)

    def packet_window_free(self, window_id_index):
        """
        Marks the window as free, allowing it to be used. Does not remove the internal state parameters, should they be re-used.
        """

        assert(window_id_index>=0 and window_id_index<self.PACKETS_STATE_CAPACITY)
        if self.last_packets_treated[window_id_index] != -1:
            self.remaining_capacity += 1
            self.last_packets_treated[window_id_index] = -1

    def set_receive_availability(self, simulator: 'Simulator', to_set: NodeLP_Receiver_State):
        """

        :param simulator: Not needed, but we keep it here so we can schedule this as an event.
        :param to_set: State of reception availability to set.
        :return: None.
        """
        self.ready_to_receive = to_set

    def receive_packet(self, simulator: Simulator, packet: Packet):
        """
        Registers receiving a packet, then processing it. Call back used
        by channels. Overwrites higher class method
        """
        assert(isinstance(packet, PacketLP))
        self._log("received packet",packet)
        self.process_packet(simulator, packet)

    def process_packet(self, simulator: 'Simulator', packet: 'PacketLP', do_not_schedule_reception : bool = False):
        """
        First entry point when processing a packet fully received by the node.

        If possible, it'll treat it within the appropriate finite state that corresponds to it.

        :do_not_schedule_reception: By default when processing a packet we "delay" it's actual processing to mimic the delay it takes to receive the packet
        This is to allow simulating collision between packets from the point of view of the node (not in air).
        It is set to true when we actually effectively process the packet.
        """

        # If disabled node : do not process
        if not self.enabled:
            return

        if not do_not_schedule_reception:
            if self.ready_to_receive == NodeLP_Receiver_State.READY_TO_RECEIVE: # If ready to receive:
                self.reception_event = simulator.schedule_event(self.NODE_RECEPTION_OF_PACKET_DURATION, self.process_packet, packet, do_not_schedule_reception=True)
                self.ready_to_receive = NodeLP_Receiver_State.NOT_READY_TO_RECEIVING
            else:
                # Drop the current event, and schedule the setting of ready_to_receive to being ready (assume the packet keeps coming through
                # This means consecutive collisions can happen
                self._log("packets collided.")
                self.reception_event.cancel()
                self.reception_event = simulator.schedule_event(self.NODE_RECEPTION_OF_PACKET_DURATION, self.set_receive_availability, NodeLP_Receiver_State.READY_TO_RECEIVE)
            return
        else:
            # We waited long enough, and no other packet came through : we become able to receive again!
            self.ready_to_receive = NodeLP_Receiver_State.READY_TO_RECEIVE


        # First : is packet in list of being_treated_packets ?
        packet_id = self.get_packet_message_id(packet)
        packet_id_index = self.get_packet_window_index(packet)
        register_result = self.packet_window_register(packet)
        packet_id_index = register_result[1]

        if register_result[0] == False:
            # What to do if packet couldn't get assigned a window ? Fow now, just drop and do nothing.
            return

        # Packet is assigned somewhere with packet_id_index in our list of packet ids that we can treat.
        internal_state = self.last_packets_informations[packet_id_index]
        state_handler = internal_state.get_internal_state_handler()
        self._log("state when received:", internal_state.internal_state_for_packet)

        self._jitter_interval_before = internal_state.min_jitter
        self._suppression_mode_before = internal_state.suppression_mode

        state_handler.process_packet(simulator, self, packet, internal_state) # IDLE, RETX, ...

        self._suppression_mode_after = internal_state.suppression_mode
        self._jitter_interval_after = internal_state.min_jitter

        if self._jitter_interval_after != self._jitter_interval_before:
            self._log(f"jitter updated to {self._jitter_interval_after}")
        if self._jitter_interval_after != self._jitter_interval_before:
            self._log(f"suppression set to {internal_state.suppression_mode}")

    def transmit_packet_lp_effective(self, simulator: 'Simulator', packet: 'PacketLP'):
        """
        Effectively starts transmitting the packet. Any side effects are to be treated outside of this function (changing states etc ...)
        TODO : The node must become blocked and unable to do further calculations for a set amount of time to simulate packet sending
        NOTE : Real world situation is more complicated, where collisions can happen and the node can detect this more or less with CSMA.
        This introduces more time delays.
        ABOLUTE TODO : Estimate order of magnitude for EVERY impactful parameter.
        """
        self._log("retransmitted packet",packet)
        packet.data.before_last_in_path = packet.data.last_in_path # Set the before-last-in-path.
        packet.data.last_in_path = self.get_id()  # Set last-in-path
        self.broadcast_packet(simulator, packet) # Broadcast the packet.

class GatewayLP(NodeLP):

    def __init__(self, x: float, y: float, channel: 'Channel' = None ):
        super().__init__(x, y, channel)
        super(Node, self).__init__(logger=GATEWAY_LOGGER, preamble=str(self.node_id)+" - ")
        self.acknowledged_packets = set()

    def arrival_successful_callback(self, simulator: 'Simulator', packet: 'PacketLP'):
        # A function to be modified if in scripts should we want to log something specific at packet arrival.
        pass

    def receive_packet(self, simulator: Simulator, packet: Packet):
        """
        Registers receiving a packet, then processing it. Call back used
        by channels. Overwrites higher class method
        """
        assert(isinstance(packet, PacketLP))
        self.process_packet(simulator, packet)

    def process_packet(self, simulator: 'Simulator', packet: 'PacketLP'):
        """
        Processing of packets reaching the gateway.
        Invokes a send_ack
        """
        # GATEWAY_LOGGER.log(f"Gateway {self.node_id} captured packet: {packet}")
        # Schedule ACK message
        # NOTE : Here it is not scheduled but immediate ...
        # Log time it took the packet to
        if self.enabled and not packet.get_id() in self.acknowledged_packets:
            self.acknowledged_packets.add(packet.get_id()) # Only acknowledge packets once
            self._log(f"captured packet: {packet}")
            self._log(f"source-to-gateway time for packet {packet.data.packet_id} is {(simulator.get_current_time() - packet.first_emission_time):.2f}, passing through {len(packet.path)-1} intermediate hops.")
            self.arrival_successful_callback(simulator, packet) # User-defined callback, if ever

            if not packet.data.ack:
                self.send_ack(simulator, packet)

    def send_ack(self, simulator: 'Simulator', in_packet: 'PacketLP'):
        """
        Send the ACK message corresponding to the in_packet
        Invokes the corresponding broadcast_packet
        :in_packet: Packet received for which an ACK will be created
        """
        # Source ID set to 0 because gateway. TODO (not yet set)
        ack_packet = PacketLP(self.get_id(), first_emission_time=simulator.get_current_time(), ack=(True, in_packet.get_id()), before_last_in_path=in_packet.data.last_in_path)
        self.broadcast_packet(simulator, ack_packet)

class SourceLP(NodeLP):

    def __init__(self, x: float, y: float, interval: float, channel: 'Channel' = None ):
        """
        :interval: Interval between each message retransmission
        """
        super().__init__(x, y, channel)
        super(Node, self).__init__(logger=SOURCE_LOGGER, preamble=str(self.node_id)+" - ")
        self.interval = interval

    def start_sending(self, simulator: Simulator):
        self.send_packet(simulator)

        simulator.schedule_event(self.interval, self.start_sending)
        # Don't add simulator as arg, added by default.

    def receive_packet(self, simulator: Simulator, packet: Packet):
        """
        Registers receiving a packet, then processing it. Call back used
        by channels. Overwrites higher class method
        """
        assert(isinstance(packet, PacketLP))
        self.process_packet(simulator, packet)

    def process_packet(self, simulator: Simulator, packet: PacketLP):
        if self.enabled:
            # Drop packets.
            if packet.data.ack:
                self._log(f"received ack for packet_id: {packet.data.ack[1]}, packet: {packet}")
            return

    def send_packet(self, simulator: Simulator):
        if self.enabled:
            packet = PacketLP(self.get_id(), first_emission_time=simulator.get_current_time(), ack = False)
            self._log(f"sending packet: {packet}")
            self.broadcast_packet(simulator, packet)
