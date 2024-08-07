from piconetwork.lpwan_jitter import *
from piconetwork.flooder import NodeLP_slowflood_mod, NodeLP_fastflood_mod, NodeLP_flood, NodeLP_flood_mod
import sys
import nographs
from piconetwork.graphical import plot_nodes_lpwan, plot_lpwan_jitter_interval_distribution, plot_lpwan_jitter_metrics, plot_delays_of_packet_arrival; import matplotlib.pyplot as plt
import threading
from copy import deepcopy
from typing import Type, TypeVar
from math import ceil
import pandas as pd
from piconetwork.logger import aggregate_logs_and_save


TNodeLP = TypeVar("TNodeLP", bound=NodeLP)


"""
Distribution of nodes over a strip, test.
"""

# Interesting config : 5, 30.0, 19.0
random.seed(6)

# Set loggers
LOGGERS_CONSIDERED = [GATEWAY_LOGGER, NODE_LOGGER, SOURCE_LOGGER]
EVENT_LOGGER.set_verbose(False); EVENT_LOGGER.set_effective(False)
GATEWAY_LOGGER.set_verbose(True) ; GATEWAY_LOGGER.set_effective(True)
NODE_LOGGER.set_verbose(False) ; NODE_LOGGER.set_effective(True)
SIMULATOR_LOGGER.set_verbose(False) ; SIMULATOR_LOGGER.set_effective(False)
SOURCE_LOGGER.set_verbose(True) ; SOURCE_LOGGER.set_effective(True)
CHANNEL_LOGGER.set_verbose(False) ; CHANNEL_LOGGER.set_effective(False)


# Subclass GatewayLP to add our own average time delay followup of ToA of packets to gateways from source
packet_lifetime_infos = {} # An element would be of the form : packetid:[timesent, timearrived or False]

packet_lifetime_infos_snapshots = [] # every new scenario setup, just deepcopy packet lifetime information

class SourceLP_mod(SourceLP):
    def __init__(self, x: float, y: float, interval: float, channel: 'Channel' = None ):
        """
        :interval: Interval between each message retransmission
        """
        super().__init__(x, y, interval, channel)

    def broadcast_packet(self, simulator: Simulator, packet: Packet):
        assert(isinstance(packet, PacketLP))

        super().broadcast_packet(simulator, packet)
        packet_lifetime_infos[ packet.get_id() ] = [packet.first_emission_time, False]


class GatewayLP_mod(GatewayLP):
    def arrival_successful_callback(self, simulator: 'Simulator', packet: 'PacketLP'):
        packet_lifetime_infos[packet.get_id()][1] = simulator.get_current_time()

class NodeLP_mod(NodeLP):
    def __init__(self, x: float, y: float, channel: 'Channel' = None):
        super().__init__(x, y, channel)
        self.received_packets_times = []
        self.transmitted_packets_times = []

    def process_packet(self, simulator: 'Simulator', packet: 'PacketLP', do_not_schedule_reception : bool = False):
        self.received_packets_times.append(simulator.get_current_time())
        super().process_packet(simulator, packet, do_not_schedule_reception)

    def transmit_packet_lp_effective(self, simulator: 'Simulator', packet: 'PacketLP'):
        self.transmitted_packets_times.append(simulator.get_current_time())
        super().transmit_packet_lp_effective(simulator, packet)

def node_point_random_picky(node_class : Type[TNodeLP], x_start, y_start, x_end, y_end, nodes, prohibitive_distance:float):
    """ Similar to the other version of the test, except it keeps trying to find random position when node is too close to another one """
    x_point = random.random() * (x_end - x_start) + x_start
    y_point = random.random() * (y_end - y_start) + y_start

    number_of_retries = 0
    MAX_RETRIES = 1000
    while number_of_retries < MAX_RETRIES: # Sad way of doing this.
        number_of_retries += 1
        is_good = True
        for node in nodes:
            if math.sqrt((node.x - x_point) ** 2 + (node.y - y_point) ** 2) < prohibitive_distance:
                is_good = False
                x_point = random.random() * (x_end - x_start) + x_start
                y_point = random.random() * (y_end - y_start) + y_start
                break
        if is_good:
            break

    if number_of_retries >= MAX_RETRIES:
        print("Too many retries.")
        sys.exit(1)
    return node_class(x_point, y_point)

NODES_DENSITY = 1.9 ; assert(NODES_DENSITY > 0.58) # Inspired from percolation density limit before possible connectivity in grid case.
# With node density 7, it takes 1mn10s to just finish the breadthfirstsearch and channel configuration : beware! Very slow simulation.
# Although, it eventually gets slightly faster as the jitter decreases and some nodes drop instead of forwarding.
# Modify some innate values for better testing :

CHANNEL_DELAY_PER_UNIT = 5e-8 # used to be 0.001

NodeLP_Jitter_Configuration.JITTER_INTERVALS = 10
NodeLP_Jitter_Configuration.JITTER_MIN_VALUE = 0
NodeLP_Jitter_Configuration.JITTER_MAX_VALUE = (8*0.6)*(NodeLP_Jitter_Configuration.JITTER_INTERVALS)
NodeLP_Jitter_Configuration.ADAPTATION_FACTOR = 0.6

NodeLP.NODE_RECEPTION_OF_PACKET_DURATION = 0.6 # 0.6 milliseconds by calculating 255 octets / 50 kbps # used to be jitter interval / 6
NodeLP_slowflood_mod.NODE_RECEPTION_OF_PACKET_DURATION = NodeLP_slowflood_mod.NODE_RECEPTION_OF_PACKET_DURATION = NodeLP.NODE_RECEPTION_OF_PACKET_DURATION

NodeLP_slowflood_mod.NODE_TOTAL_JITTER_SPACE_VALUES = NodeLP_Jitter_Configuration.JITTER_MAX_VALUE
NodeLP_slowflood_mod.NUM_INTERVALS = NodeLP_Jitter_Configuration.JITTER_INTERVALS

NUM_OF_SAMPLES = 4
START_COUNT_SAVE = 0

SOURCE_RECURRENT_TRANSMISSIONS_DELAY = NodeLP_Jitter_Configuration.JITTER_MAX_VALUE * 20 * 20
SIMULATION_TOTAL_DURATION = SOURCE_RECURRENT_TRANSMISSIONS_DELAY * 90
HEARING_RADIUS = 30.0
DENSITY_RADIUS = 10.0

RANDOM_SEED = 9

x_box_min = 0.0
x_box_max = 600.0
y_box_min = -200.0
y_box_max = 200.0

x_width = x_box_max - x_box_min
y_height = y_box_max - y_box_max

box_surface_max = (y_box_max - y_box_min) * (x_box_max - x_box_min)
node_classes = [NodeLP_slowflood_mod, NodeLP_mod] # [NodeLP_flood_mod, NodeLP_fastflood_mod, NodeLP_mod]
node_classes_names = ["FASTFLOODING", "PROTOCOL"] # ["FASTFLOODING"] # ["FLOODING", "FASTFLOODING", "PROTOCOL"]
suppression_modes = [[None], [NodeLP_Suppression_Mode.REGULAR, NodeLP_Suppression_Mode.CONSERVATIVE, NodeLP_Suppression_Mode.AGGRESSIVE, NodeLP_Suppression_Mode.BOLD]] # [[None]] # [[None], [None], [NodeLP_Suppression_Mode.REGULAR, NodeLP_Suppression_Mode.CONSERVATIVE, NodeLP_Suppression_Mode.AGGRESSIVE, NodeLP_Suppression_Mode.BOLD]]
label_names = ["FASTFLOODING"] + ["REGULAR", "CONSERVATIVE", "AGGRESSIVE", "BOLD"] # ["FASTFLOODING"] # ["FLOODING", "FASTFLOODING"] + ["REGULAR", "CONSERVATIVE", "AGGRESSIVE", "BOLD"]

counter_label_name = 0

for node_class_index in range(len(node_classes)):

    node_class = node_classes[node_class_index]
    node_class_name = node_classes_names[node_class_index]

    for suppression_mode in suppression_modes[node_class_index]:
        for sample in range(NUM_OF_SAMPLES):
            random.seed(RANDOM_SEED) # Essential, otherwise the initial configuration differs every time ...
            if suppression_mode != None:
                NodeLP_Jitter_Configuration.SUPPRESSION_MODE_SWITCH = suppression_mode
            Node.next_id = 1

            nodes = []
            source = SourceLP_mod(x_box_min , (y_box_max+y_box_min)/2.0, SOURCE_RECURRENT_TRANSMISSIONS_DELAY)
            nodes.append(source)

            # Add nodes until full density with regards to "surface of possible hearing" matches with NODES_DENSITY.
            total_surface_no_clamp = 0.0

            while total_surface_no_clamp < box_surface_max * NODES_DENSITY:
                total_surface_no_clamp += ((DENSITY_RADIUS) ** 2) * math.pi
                nodes.append(node_point_random_picky(node_class, x_box_min, y_box_min, x_box_max, y_box_max, nodes, DENSITY_RADIUS))

            gateway = GatewayLP_mod(x_box_max, (y_box_max+y_box_min)/2.0)
            nodes.append(gateway)

            # Create channel
            channel = Channel(packet_delay_per_unit=0.001) # If delay per unit is too high, it will mess up all calculations. TODO : fix that.

            # Register all nodes to channel
            channel.create_metric_mesh(HEARING_RADIUS, *nodes)

            # Check path existence with NoGraphs library
            traversal = nographs.TraversalBreadthFirst(lambda i,_: channel.get_neighbour_ids(i)).start_from(source.get_id())
            depths = {vertex: traversal.depth for vertex in traversal.go_for_depth_range(0, len(nodes))}

            if gateway.get_id() not in depths.keys():
                print("No possible path from source to gateway. Abort!")
                sys.exit(0)
            else:
                print("Path from source to gateway exists, with BreadthFirstSearch depth :", depths[gateway.get_id()])

            # Useful DEBUG notes
            print("Number of source neighbours : ", len(channel.adjacencies_per_node[source.get_id()]))

            # Example usage:
            sim = Simulator(SIMULATION_TOTAL_DURATION, 0.)

            # Assign simulator for every logger we want to keep track of time for
            for node in nodes:
                node.set_logger_simulator(sim)

            # Add nodes to simulator
            sim.add_nodes(*nodes)

            random.seed() # Randomize initial distribution

            # Start sending packets from source
            source.start_sending(sim)

            #plot_nodes_lpwan(nodes, channel, x_box_min - x_width*0.05, y_box_min - y_height*0.05, x_box_max + x_width*0.05, y_box_max + y_height*0.05)
            #plot_lpwan_jitter_interval_distribution(nodes)

            # Run the simulator
            sim.run()

            #plot_nodes_lpwan(nodes, channel, x_box_min - x_width*0.05, y_box_min - y_height*0.05, x_box_max + x_width*0.05, y_box_max + y_height*0.05)
            #plot_lpwan_jitter_interval_distribution(nodes)

            packet_lifetime_infos_snapshots.append(deepcopy(packet_lifetime_infos))

            # Now : the total number of RETX in some bins!
            if False:
                transmission_times_combined = []
                for node in nodes:
                    if isinstance(node, NodeLP_mod) or isinstance(node, NodeLP_flood_mod) or isinstance(node, NodeLP_slowflood_mod):
                        transmission_times_combined.extend(node.transmitted_packets_times)
                plt.hist(transmission_times_combined, edgecolor="indigo", bins=range(int(min(transmission_times_combined)), int(max(transmission_times_combined) + SOURCE_RECURRENT_TRANSMISSIONS_DELAY), int(SOURCE_RECURRENT_TRANSMISSIONS_DELAY)), label = label_names[counter_label_name])
                plt.xlabel('Time of packet retransmission')
                plt.ylabel('Number of packets retransmitted')
                plt.legend()
                plt.show()

            # Save logs to appropriate files
            aggregate_logs_and_save(LOGGERS_CONSIDERED, "saved_logs/tld7slf_"+label_names[counter_label_name]+"_"+str(sample+START_COUNT_SAVE))
            for logger in LOGGERS_CONSIDERED: logger.reset_logs();
        counter_label_name += 1

"""
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(17, 12))

for i in range(len(packet_lifetime_infos_snapshots)):
    snapshot = packet_lifetime_infos_snapshots[i]
    # Plot this snapshot and assign it its appropriate label!
    departure_times_successful, delays_successful, success_ratios, success_failure_interval = [], [], [], SOURCE_RECURRENT_TRANSMISSIONS_DELAY * 10
    max_intervals = int(ceil(SIMULATION_TOTAL_DURATION / success_failure_interval)) + 1
    success_ratios = [ [0, 0] for i in range(max_intervals)]  # [amount of success, amount of non success]
    success_timesignatures = [ success_failure_interval * i for i in range(max_intervals) ]

    print(max_intervals)

    for packet_id, info in snapshot.items():
        # If success
        if info[0] > SIMULATION_TOTAL_DURATION:
            # Ignore escaping last packet
            pass

        associated_interval = int(info[0] // success_failure_interval)

        if info[1] != False:
            departure_times_successful.append(info[0])
            delays_successful.append(info[1] - info[0])
            success_ratios[associated_interval][0] += 1
        else:
            success_ratios[associated_interval][1] += 1

    failure_percentages = [ 0 if ratio[0]+ratio[1] == 0 else ratio[1]/(ratio[0]+ratio[1]) for ratio in success_ratios]
    success_percentages = [ 0 if ratio[0]+ratio[1] == 0 else ratio[0]/(ratio[0]+ratio[1]) for ratio in success_ratios]

    # For simplicity all plots are on dots basically.
    ax1.plot(departure_times_successful, delays_successful, label = label_names[i])
    ax2.bar(success_timesignatures, success_percentages, color='#23ff23', edgecolor='white', width=success_failure_interval)
    ax2.bar(success_timesignatures, failure_percentages, bottom=success_percentages, color='#ff2323', edgecolor='white', width=success_failure_interval)


ax1.set_xlabel('Time of departure of packet')
ax1.set_ylabel('Delay from source to gateway')

ax2.set_xlabel('Time windows of departure of packets')
ax2.set_ylabel('Success ratio')

plt.legend()
plt.show()
"""
