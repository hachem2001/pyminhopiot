from piconetwork.lpwan_jitter import *
import sys
import nographs
from piconetwork.graphical import plot_nodes_lpwan, plot_lpwan_jitter_interval_distribution; import matplotlib.pyplot as plt
import threading

"""
Distribution of nodes over a strip, test.
"""

# Interesting config : 5, 30.0, 19.0

random.seed(5)

# Set loggers
EVENT_LOGGER.set_verbose(False); EVENT_LOGGER.set_effective(False)
GATEWAY_LOGGER.set_verbose(True) ; GATEWAY_LOGGER.set_effective(False)
NODE_LOGGER.set_verbose(False) ; NODE_LOGGER.set_effective(False)
SIMULATOR_LOGGER.set_verbose(False) ; SIMULATOR_LOGGER.set_effective(False)
SOURCE_LOGGER.set_verbose(True) ; SOURCE_LOGGER.set_effective(False)
CHANNEL_LOGGER.set_verbose(False) ; CHANNEL_LOGGER.set_effective(False)

def node_point_random_picky(x_start, y_start, x_end, y_end, nodes, prohibitive_distance:float):
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
    return NodeLP(x_point, y_point)

NODES_DENSITY = 2 ; assert(NODES_DENSITY > 0.58) # Inspired from percolation density limit before possible connectivity in grid case.
# With node density 7, it takes 1mn10s to just finish the breadthfirstsearch and channel configuration : beware! Very slow simulation.
# Although, it eventually gets slightly faster as the jitter decreases and some nodes drop instead of forwarding.
# Modify some innate values for better testing :
NodeLP_Jitter_Configuration.JITTER_MIN_VALUE = 0.2
NodeLP_Jitter_Configuration.JITTER_MAX_VALUE = 1.2
NodeLP_Jitter_Configuration.ADAPTATION_FACTOR = 0.6
NodeLP_Jitter_Configuration.JITTER_INTERVALS = 10
NodeLP_Jitter_Configuration.SUPPRESSION_MODE_SWITCH = NodeLP_Suppression_Mode.BOLD

HEARING_RADIUS = 30.0
DENSITY_RADIUS = 19.0

x_box_min = 0.0
x_box_max = 300.0
y_box_min = -150.0
y_box_max = 150.0

x_width = x_box_max - x_box_min
y_height = y_box_max - y_box_max

box_surface_max = (y_box_max - y_box_min) * (x_box_max - x_box_min)
nodes = []

source = SourceLP(x_box_min , (y_box_max+y_box_min)/2.0, 25)
nodes.append(source)

# Add nodes until full density with regards to "surface of possible hearing" matches with NODES_DENSITY.
total_surface_no_clamp = 0.0

while total_surface_no_clamp < box_surface_max * NODES_DENSITY:
    total_surface_no_clamp += ((DENSITY_RADIUS) ** 2) * math.pi
    nodes.append(node_point_random_picky(x_box_min, y_box_min, x_box_max, y_box_max, nodes, DENSITY_RADIUS))

gateway = GatewayLP(x_box_max, (y_box_max+y_box_min)/2.0)
nodes.append(gateway)

# Create channel
channel = Channel(packet_delay_per_unit=0.001) # If delay per unit is too high, it will mess up all calculations. TODO : fix that.

# Register all nodes to channel
channel.create_metric_mesh(HEARING_RADIUS, *nodes)

def recurrent_plot_nodes_lpwan(nodes: 'NodeLP', channel : 'Channel', x_min, y_min, x_max, y_max, interval, repetitions):

    for _ in range(repetitions):
        time.sleep(interval)

        plt.close('all')
        plt.ion()
        plot_nodes_lpwan(nodes, channel, x_min, y_min, x_max, y_max)
        plt.pause(interval)  # Pause to update the plot

# Plot the graph
update_interval_in_seconds = 1.5
repetitions_of_updates = 20
#plotting_thread = threading.Thread(target=recurrent_plot_nodes_lpwan, args=(nodes, channel, x_box_min - x_width*0.05, y_box_min - y_height*0.05, x_box_max + x_width*0.05, y_box_max + y_height*0.05, update_interval_in_seconds, repetitions_of_updates))
#plotting_thread.start()

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
sim = Simulator(800, 0.00001)

# Assign simulator for every logger we want to keep track of time for
for node in nodes:
    node.set_logger_simulator(sim)

# Add nodes to simulator
sim.add_nodes(*nodes)

# Start sending packets from source
source.start_sending(sim)

plot_nodes_lpwan(nodes, channel, x_box_min - x_width*0.05, y_box_min - y_height*0.05, x_box_max + x_width*0.05, y_box_max + y_height*0.05)
plot_lpwan_jitter_interval_distribution(nodes)

# Run the simulator
sim.run()

plot_nodes_lpwan(nodes, channel, x_box_min - x_width*0.05, y_box_min - y_height*0.05, x_box_max + x_width*0.05, y_box_max + y_height*0.05)
plot_lpwan_jitter_interval_distribution(nodes)
