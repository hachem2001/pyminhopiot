from main import *
from packet import Packet
from logger import Logger

from typing import Any, Tuple
from enum import Enum, auto

import random

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
        def __init__(self, source_id: int, packet_id : int, timestamp : float, ack : (bool, int)= (False, -1)):
            self.packet_id = packet_id
            self.source_id = source_id
            self.last_in_path = source_id
            self.before_last_in_path = -1 # TODO : TEMPORARY FIX FOR "FORWARDED PACKET" DETERMINISTIC DETECTION. TO BE FIXED LATER 
            self.ack = ack
            self.timestamp = self.timestamp # Not noted with the internal variables, but certainly is another one both in packets and nodes.
        
        def __repr__(self) -> str:
            return f'<{type(self)}{{{self.packet_id},{self.source_id},{self.last_in_path},{self.ack}}}>'
        


    def __init__(self, source_id: int, ack : (bool, int)= (False, -1)):
        """
        Re-insisting : "source_id" would be the gateway's ID if the
        gateway is sending a message back to a source.
        """
        data : self.DataLP = self.DataLP(source_id, PacketLP.packet_id_counter, ack)
        super().__init__(data, source_id)
        PacketLP.packet_id_counter += 1

    def get_id(self):
        return self.data.packet_id
    
    def get_source_id(self):
        return self.data.source_id

    def get_antecessor_id(self):
        return self.data.last_in_path

class NodeLP(Node):
    """
    Implementation following paper.
    We will assume that a NodeLP will only retain a state machine for
    ONE packet. If it receives a packet of a different identifier at that point : drop
    
    The paper currently discusses work per packet.
    Incidentally we are obliged to define a fixed size.
    """

    PACKETS_STATE_CAPACITY = 1 # Can only keep track of one.

    class NodeLP_PACKET_State(Enum):
        """
        The various internam finite state machine states described in the paper
        For a NodeLP.

        They are per PACKET.
        """
        IDLE = auto()
        RETX_PENDING = auto()
        FOLLOWUP_PENDING = auto()
        DONE = auto() # Redundant to be honest. If done, just turn back to Idle immediately after done.

    class JitterSuppressionState:
        """
        This would be valid for every packet in the node's capacity.
        Therefore, it makes sense that this class regroups all relevant state variables per packet.
        TODO : different state variables per packet?? Or is this to be used for multiple sources?
        """

        JITTER_MIN_VALUE = 0.2
        JITTER_MAX_VALUE = 1.2 # 
        JITTER_INTERVALS = 10 # Number of intervals to divide the jitter to.
        # This corresponds to [0.2, 0.3], [0.3, 0.4], ... [1.1, 1.2]
        
        _JITTER_INTERVAL_DURATION = (JITTER_MAX_VALUE - JITTER_MIN_VALUE)/JITTER_INTERVALS # USEFUL TO USE.

        def __init__(self, packet_id = -1, source_id = -1, antecessor_id = -1):
            self.packet_id = packet_id # Packet ID.
            self.source_id = source_id # Source ID. 0 for "any gateway", > 0 for a specific source.
            # Jitter adaptation internal state

            self.min_jitter = 0 # MUST BE A NUMBER BETWEEN 0 and min(self.max_jitter,JITTER_INTERVALS)-1
            self.max_jitter = self.JITTER_INTERVALS # MUST BE A NUMBER max(self.min_jitter,0)+1 and JITTER_INTERVALS

            self.reset_jitter() # To keep the implementation self-coherent.

            self.id_node_antecessor_of_last_packet_forwarded = antecessor_id
            # Overhead suppression internal state
            self.number_of_heard_retransmissions_of_last_received = 0
            self.probability_of_forwarding = 1.0 # between 0.0 and 1.0
            self.internal_state_for_packet = NodeLP.NodeLP_PACKET_State.IDLE

            # For cancelling event of schedulered transmission or scheduled followup if necessary. It can be thought of as a time internal state variable.
            self.event_handle : Event = None

            # For time-based calculations :
            self.retransmission_time = None # None if not retransmitted yet, >0 otherwise.

        def soft_switch_to(self, packet_id, source_id = False, antecessor_id = False):
            """
            Keeps the jitter parameters, and merely changes the IDs treated by the jitter parameter
            """
            self.packet_id = packet_id
            if source_id != False:
                self.source_id = source_id
            if antecessor_id != False:
                self.antecessor_id = antecessor_id
            
            # Reset event handle
            self.event_handle = None

            # Reset retransmission time : new packet, we didn't retransmit it yet
            self.retransmission_time = None

        def get_max_jitter(self) -> float:
            return self.max_jitter/self.JITTER_INTERVALS * (self.JITTER_MAX_VALUE-self.JITTER_MIN_VALUE) + self.JITTER_MIN_VALUE

        def get_min_jitter(self) -> float:
            return self.min_jitter/self.JITTER_INTERVALS * (self.JITTER_MAX_VALUE-self.JITTER_MIN_VALUE) + self.JITTER_MIN_VALUE
            
        def get_jitter_random(self) -> float:
            """
            Return a random variable between jitter min and jitter max, as per the paper description.
            Though I'm slightly surprised it works this way, instead of updating a jitter value directly, it's kept randomized.
            """

            jitter = random.random() * (self.max_jitter - self.min_jitter) / self.JITTER_INTERVALS * self.JITTER_MAX_VALUE + self.min_jitter / self.JITTER_INTERVALS * self.JITTER_MAX_VALUE # Random jitter
            return jitter

        def get_jitter_average(self) -> float:
            """
            Returns the estimated average of the jitter used by this node
            """
            jitter = 0.5 * (self.max_jitter - self.min_jitter) / self.JITTER_INTERVALS * self.JITTER_MAX_VALUE + self.min_jitter / self.JITTER_INTERVALS * self.JITTER_MAX_VALUE # Random jitter
            return jitter

        def set_jitter_interval_around(self, jitter):
            """ Sets jitter to a narrow interval around the given value. """
            assert jitter >= self.JITTER_MIN_VALUE and jitter <= self.JITTER_MAX_VALUE, "Jitter set outside of allowed values"
            jitter_min_index = int(math.floor((jitter-self.JITTER_MIN_VALUE)/self._JITTER_INTERVAL_DURATION))
            jitter_max_index = int(math.ceil((jitter-self.JITTER_MIN_VALUE)/self._JITTER_INTERVAL_DURATION))
            self.min_jitter = jitter_min_index
            self.max_jitter = jitter_max_index

        def clip_jitter(self, jitter):
            """ Returns a cliped jitter in the appropriate interval """
            return max(self.JITTER_MIN_VALUE, min(self.JITTER_MAX_VALUE, jitter))

        def reduce_jitter(self):
            """
            Decreases jitter interval indexes of both min and max by 1
            """
            self.min_jitter = max(0, self.min_jitter - 1)
            self.max_jitter = max(self.min_jitter, self.max_jitter - 1)

        def increase_jitter(self):
            """
            Increases jitter interval indexes of both min and max by 1
            """
            self.min_jitter = max(0, self.min_jitter - 1)
            self.max_jitter = max(self.min_jitter, self.max_jitter - 1)
            

        def adapt_jitter(self):
            pass

        def minimize_jitter_interval(self):
            """ Makes it so that the jitter interval is set to the smallest possible interval around the average value. """
            self.set_jitter_interval_around(self.clip_jitter(self.get_jitter_average()))

        def reset_jitter(self):
            """
            Makes jitter random over the full range.
            This is different from having an assigned jitter interval.
            """
            self.min_jitter = 0 # MUST BE A NUMBER BETWEEN 0 and min(self.max_jitter,JITTER_INTERVALS)-1
            self.max_jitter = self.JITTER_INTERVALS # MUST BE A NUMBER max(self.min_jitter,0)+1 and JITTER_INTERVALS

    def estimate_jitter_of_next_forwarding_node_within_channel(self, simulator: 'Simulator', channel: 'Channel', window_id_index : int , packet: 'PacketLP'):
        """
        Attempts to estimate the jitter of the node from which the packet was received, assuming the node transmitted the packet and heard back its echo
        This unfortunately relies on a functional internal clock within each device. We'll assume it is the case, and cheat using Simulator's time.
        Here we also cheat by asking the channel how long it takes to get to said node.
        TODO: Fix this cheaty case?
        """
        assert self.last_packets_treated[window_id_index] != -1, "Unexpected error, problem in the code implementation"
        
        twottimestimeofarrivalplusjitter = simulator.get_current_time() - self.last_packets_treated[window_id_index].retransmission_time
        channelestimatedtimeofarrival = channel.get_distance(self.get_id(), packet.data.last_in_path)
        return twottimestimeofarrivalplusjitter - 2 * channelestimatedtimeofarrival

    def __init__(self, x: float, y: float, channel: 'Channel' = None):
        super().__init__(x, y, channel)
        # Stores list of last heard packet ids, with respect to the capacity
        # A packet_id is removed (set to -1) from the list when the node hears back its echo
        # This way, a packet never gets retransmitted twice by the same node (w/r to capacity)
        self.last_packets_treated = [-1 for i in range(NodeLP.PACKETS_STATE_CAPACITY)]

        # Internal state variables for each packet in capacity of being treated.
        self.last_packets_informations = [self.JitterSuppressionState() for i in range(NodeLP.PACKETS_STATE_CAPACITY)]

        # TODO : Assignment to whichever internal state is kind of random here. It should therefore depend on the source_id in priority.

        # Keeps track of how many more packets can be treated further.
        self.remaining_capacity = NodeLP.PACKETS_STATE_CAPACITY

    def get_packet_window_index(self, packet:'PacketLP'):
        """
        If the packet is part of the node's processing, it will return the appropriate index
        Otherwise, it will return -1
        """
        packet_id = packet.get_id()
        packet_id_index = -1

        try:
            packet_id_index = self.last_packets_treated.index(packet_id)
        except ValueError:
            packet_id_index = -1
        
        return packet_id_index

    def packet_window_register(self, packet:'PacketLP') -> Tuple(bool, int):
        """
        If the packet is part of one of the node's processing windows, it will return the appropriate index with (True, packet_id_index)
        Else, it will assign a window to it if the capacity allows it, returning the tuple (True, packet_id_index)
        Else, it will return (False, -1)
        :returns: (Whether the packet has a dedicated window or not, packet_id if assigned, otherwise -1)
        """
        packet_id = packet.get_id()
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
                self.last_packets_treated[packet_id_index] = packet_id_index

                # Here it is a soft switch : keep all the jitter and suppression configurations as they are.
                self.last_packets_informations[packet_id_index].soft_switch_to(packet_id=packet_id, source_id=packet.get_source_id(), antecessor_id=packet.get_antecessor_id())
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
            self.last_packets_treated[window_id_index] = 1

    def process_packet(self, simulator: 'Simulator', packet: 'PacketLP'):
        """
        First entry point when processing a packet fully received by the node.

        If possible, it'll treat it within the appropriate finite state that corresponds to it.
        """

        # First : is packet in list of being_treated_packets ?
        packet_id = packet.get_id()
        packet_id_index = self.get_packet_window_index(packet)
        register_result = self.packet_window_register(packet)
        packet_id_index = register_result[1]

        if register_result[0] == False:
            # What to do if packet couldn't get assigned a window ? Fow now, just drop and do nothing.
            return

        # Packet is assigned somewhere with packet_id_index in our list of packet ids that we can treat.
        internal_state = self.last_packets_informations[packet_id_index]
        
        if internal_state.internal_state_for_packet == self.NodeLP_PACKET_State.IDLE:
            # Schedule retransmission.
            if packet.data.ack:
                # TODO : Treat acks properly? For now paper says reduce jitter. To be explained I suppose.
                self.last_packets_informations[packet_id_index].reduce_jitter()
                pass
            else:
                # Schedule transmission. Save event handle should the event be cancelled (e.g ack received)
                event = simulator.schedule_event(internal_state.get_jitter(), self.transmit_packet_lp_schedulable, packet)
                self.last_packets_informations[packet_id_index].event_handle = event
                self.last_packets_informations[packet_id_index].internal_state_for_packet = self.NodeLP_PACKET_State.RETX_PENDING

            
        elif internal_state.internal_state_for_packet == self.NodeLP_PACKET_State.RETX_PENDING:
            # Increase neighbour count.
            self.last_packets_informations[packet_id_index].number_of_heard_retransmissions_of_last_received += 1
            # TODO : non disjoint case here. Packet that is Ack : do both n_neighour++ AND reduce_jitter?
            if packet.data.ack:
                self.last_packets_informations[packet_id_index].reduce_jitter() 
                self.last_packets_informations[packet_id_index].event_handle.cancel()   
            
        elif internal_state.internal_state_for_packet == self.NodeLP_PACKET_State.FOLLOWUP_PENDING:
            # If we hear a packet that is forwarding our message (last_in_path is this node) : move to Done.
            # TODO : increase neigbour count in both cases? Disjoint cases?
            self.last_packets_informations[packet_id_index].number_of_heard_retransmissions_of_last_received += 1
            # TODO : doesn't treat ACKs when doing this? For now I don't verify if it's an Ack or not : if we are last_in_path, validate in all cases.

            if packet.data.before_last_in_path == self.get_id():
                # Hear a forward retransmission? Treat it here
                # Acknowledgement based delay reduction  
                if packet.data.ack:
                    # TODO : Overwrite current state and focus on forwarding the ack?? Not clear, because it means the last_in_path was a gateway.
                    self.last_packets_informations[packet_id_index].reduce_jitter() # DIVIDE BY 2 ?
                else:
                    # Forward Delay Adaptation
                    self.last_packets_informations[packet_id_index].adapt_jitter() # TODO : properly treat this.
            else:
                # Hear a retransmission of said packet but by someone else? Treat it here.
                # For now, until we understand better how to treat packet retransmissions, just pass.
                pass
                

        elif internal_state.internal_state_for_packet == self.NodeLP_PACKET_State.DONE:
            raise AssertionError("Current implementation assumes DONE and IDLE are the same state for simplicity")
        

    def transmit_packet_lp_schedulable(self, simulator: 'Simulator', packet: 'PacketLP'):
        """
        Schedulable immediate transmission. It checks current state, but its aim is to initite immediate transmission
        TODO : If the transmission takes time, the node would no longer be able to receive packets, and collision can happen etc etc.
        """
        packet_id_index = self.get_packet_window_index(packet)

        if packet_id_index == -1:
            # This indicates the packet's window got dropped before the scheduled transmission. Not expected.
            raise AssertionError("Unexpected packet window removal. Please cancel transmission instead.")

        internal_state = self.last_packets_informations[packet_id_index]
        
        if internal_state.internal_state_for_packet == self.NodeLP_PACKET_State.IDLE:
            raise AssertionError("Idle state not expected in scheduled transmission. Event of retransmission should be _canceled_ in the case packet treatment halted")
            # Event handle is kept when scheduled, allowing the cancelling of the event. This shouldn't happen
            
        elif internal_state.internal_state_for_packet == self.NodeLP_PACKET_State.RETX_PENDING:
            # Expected state. Proceed as per the paper. This is the "jitter timeout" situation.
            # Two possibilities, depending on random probability outcome : allowed to send, or not allowed to send.

            random_decisive_variable = random()
            if random_decisive_variable < internal_state.probability_of_forwarding:
                # Forward packet, and go to followup state.
                transmit_packet_lp_effective(simulator, packet)
                self.last_packets_informations[packet_id_index].internal_state_for_packet = self.NodeLP_PACKET_State.FOLLOWUP_PENDING
                event = simulator.schedule_event(internal_state.get_jitter(), self.transmit_packet_lp_schedulable, packet)
                self.last_packets_informations[packet_id_index].event_handle = event
            else:
                # Drop packet and get to DONE state (Idle)
                self.last_packets_informations[packet_id_index].internal_state_for_packet = self.NodeLP_PACKET_State.IDLE
                self.last_packets_informations[packet_id_index].event_handle = None
                self.packet_window_free(packet_id_index)

        elif internal_state.internal_state_for_packet == self.NodeLP_PACKET_State.FOLLOWUP_PENDING:
            raise AssertionError("Followup state unexpected, as it is the transmission event that is supposed to set the state to followup_pending or done/idle")

        elif internal_state.internal_state_for_packet == self.NodeLP_PACKET_State.DONE:
            raise AssertionError("Current implementation assumes DONE and IDLE are the same state for simplicity")
        

    def end_of_followup_pending_schedulable(self, simulator: 'Simulator', packet: 'PacketLP'):
        """
        Schedules timeout of followup-pending.
        It automatically sets event callback to null.
        """

        packet_id_index = self.get_packet_window_index(packet)

        if packet_id_index == -1:
            # This indicates the packet's window got dropped before the follow-up timeout : unexpected, raise Alert
            raise AssertionError("Unexpected packet window removal. There is an error in the code, follow-up timeout cannot be realized.")

        self.last_packets_informations[packet_id_index].internal_state_for_packet = self.NodeLP_PACKET_State.IDLE
        self.last_packets_informations[packet_id_index].event_handle = None
        self.packet_window_free(packet_id_index)

    def transmit_packet_lp_effective(self, simulator: 'Simulator', packet: 'PacketLP'):
        """
        Effectively starts transmitting the packet. Any side effects are to be treated outside of this function (changing states etc ...)
        TODO : The node must become blocked and unable to do further calculations for a set amount of time to simulate packet sending
        NOTE : Real world situation is more complicated, where collisions can happen and the node can detect this more or less with CSMA.
        This introduces more time delays.
        ABOLUTE TODO : Estimate order of magnitude for EVERY impactful parameter.
        """
        packet.data.before_last_in_path = packet.data.last_in_path # Set the before-last-in-path.
        packet.data.last_in_path = self.get_id()  # Set last-in-path
        self.broadcast_packet(simulator, packet) # Broadcast the packet.


class GatewayLP(NodeLP):
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

class SourceLP(NodeLP):
    def start_sending(self, simulator: Simulator):
        self.send_packet(simulator)

        # UNCOMMENT FOR PERIODIC SENDING

        # simulator.schedule_event(self.interval, self.start_sending)
        # Don't add simulator as arg, added by default.

    def process_packet(self, simulator: Simulator, packet: PacketLP):
        # Drop packets.
        if packet.data.ack:
            SOURCE_LOGGER.log(f"Source {self.node_id} received ack for packet_id: {packet.data.ack[1]}, packet: {packet}")

        return

    def send_packet(self, simulator: Simulator):
        packet = PacketLP(self.get_id(), False)
        SOURCE_LOGGER.log(f"Source {self.node_id} sending packet: {packet}")
        self.broadcast_packet(simulator, packet)
