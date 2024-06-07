from piconetwork.lpwan_jitter import *
import sys
import nographs

"""
Distribution of nodes over a strip, test.
"""

#random.seed(1)

# Set loggers
EVENT_LOGGER.set_verbose(False); EVENT_LOGGER.set_effective(False)
GATEWAY_LOGGER.set_verbose(True) ; GATEWAY_LOGGER.set_effective(False)
NODE_LOGGER.set_verbose(False) ; NODE_LOGGER.set_effective(False)
SIMULATOR_LOGGER.set_verbose(False) ; SIMULATOR_LOGGER.set_effective(False)
SOURCE_LOGGER.set_verbose(True) ; SOURCE_LOGGER.set_effective(False)
CHANNEL_LOGGER.set_verbose(False) ; CHANNEL_LOGGER.set_effective(False)

def node_point_random(x_start, y_start, x_end, y_end):
    x_point = random.random() * (x_end - x_start) + x_start
    y_point = random.random() * (y_end - y_start) + y_start
    return NodeLP(x_point, y_point)

NODES_DENSITY = 7 ; assert(NODES_DENSITY > 0.58) # Inspired from percolation density limit before possible connectivity in grid case.
# With node density 7, it takes 1mn10s to just finish the breadthfirstsearch and channel configuration : beware! Very slow simulation.
# Although, it eventually gets slightly faster as the jitter decreases and some nodes drop instead of forwarding.
# Modify some innate values for better testing :
NodeLP.JitterSuppressionState.JITTER_MIN_VALUE = 0.2
NodeLP.JitterSuppressionState.JITTER_MAX_VALUE = 1.2
NodeLP.JitterSuppressionState.ADAPTATION_FACTOR = 0.5
NodeLP.JitterSuppressionState.JITTER_INTERVALS = 20

HEARING_RADIUS = 10.0
DENSITY_RADIUS = 5.0

x_box_min = 0.0
x_box_max = 1000.0
y_box_min = -30.0
y_box_max = 30.0

box_surface_max = (y_box_max - y_box_min) * (x_box_max - x_box_min)
nodes = []

source = SourceLP(x_box_min , (y_box_max+y_box_min)/2.0, 50)
nodes.append(source)

# Add nodes until full density with regards to "surface of possible hearing" matches with NODES_DENSITY.
total_surface_no_clamp = 0.0

while total_surface_no_clamp < box_surface_max * NODES_DENSITY:
    total_surface_no_clamp += ((DENSITY_RADIUS) ** 2) * math.pi
    nodes.append(node_point_random(x_box_min, y_box_min, x_box_max, y_box_max))

gateway = GatewayLP(x_box_max, (y_box_max+y_box_min)/2.0)
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
sim = Simulator(20000, 0.001)

# Assign simulator for every logger we want to keep track of time for
for node in nodes:
    node.set_logger_simulator(sim)

# Add nodes to simulator
sim.add_nodes(*nodes)

# Start sending packets from source
source.start_sending(sim)

# Run the simulator
sim.run()
