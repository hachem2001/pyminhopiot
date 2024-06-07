from piconetwork.lpwan_jitter import *

"""
Linear cluster test
"""

random.seed(1)

# Set loggers
EVENT_LOGGER.set_verbose(False)
GATEWAY_LOGGER.set_verbose(True)
NODE_LOGGER.set_verbose(False)
SIMULATOR_LOGGER.set_verbose(False)
SOURCE_LOGGER.set_verbose(True)
CHANNEL_LOGGER.set_verbose(False)

def node_cluster_around(x, y, number, radius):
    theta = 0
    nodes = []
    for i in range(number):
        theta += math.pi * 2 / number
        this_x = x + radius * math.cos(theta)
        this_y = y + radius * math.sin(theta)
        nodes.append(NodeLP(this_x, this_y))
    return nodes

# Modify some innate values for better testing :
NodeLP.JitterSuppressionState.JITTER_MIN_VALUE = 0.2
NodeLP.JitterSuppressionState.JITTER_MAX_VALUE = 1.2
NodeLP.JitterSuppressionState.ADAPTATION_FACTOR = 0.5
NodeLP.JitterSuppressionState.JITTER_INTERVALS = 20

R_VALUE = 10.0

CHANNEL_HEARING_RADIUS = R_VALUE
inter_cluster_distance = R_VALUE * 5.0/6.0
intra_cluster_distance = R_VALUE
cluster_size = 5 # Number of nodes per cluster
number_of_clusters = 10 # MUST BE A PAIR NUMBER

start_x = 0.0
start_y = 0.0

nodes = []
source = SourceLP(start_x , start_y, 50)
nodes.append(source)

nodes_to_add_top_right = []
nodes_to_add_buttom_right = []

# TOP RIGHT
for i in range(number_of_clusters//2):
    # Set the logging verbosity of every node to False except a handful we cherry pick
    nodes_to_add_top_right_direction = node_cluster_around(start_x + inter_cluster_distance/math.sqrt(2)*(i+1), start_y + inter_cluster_distance/math.sqrt(2)*(i+1), cluster_size, intra_cluster_distance)
    
    for j in range(0, len(nodes_to_add_top_right_direction)):
        nodes_to_add_top_right_direction[j].set_logger_verbose_overwrite(False)
    
    nodes_to_add_top_right.extend(nodes_to_add_top_right_direction)

for i in range(number_of_clusters//2, number_of_clusters):

    this_i = i - (number_of_clusters//2 - 1)
    this_start_x = start_x + inter_cluster_distance/math.sqrt(2)*(number_of_clusters//2)
    this_start_y_top = start_y + inter_cluster_distance/math.sqrt(2)*(number_of_clusters//2)

    # Set the logging verbosity of every node to False except a handful we cherry pick
    nodes_to_add_top_right_direction = node_cluster_around(this_start_x + inter_cluster_distance/math.sqrt(2)*(this_i), this_start_y_top - inter_cluster_distance/math.sqrt(2)*(this_i) , cluster_size, intra_cluster_distance)
    
    for j in range(0, len(nodes_to_add_top_right_direction)):
        nodes_to_add_top_right_direction[j].set_logger_verbose_overwrite(False)
    
    nodes_to_add_top_right.extend(nodes_to_add_top_right_direction)

# BOTTOM RIGHT
for i in range(number_of_clusters//2):
    # Set the logging verbosity of every node to False except a handful we cherry pick
    nodes_to_add_bottom_right_direction = node_cluster_around(start_x + inter_cluster_distance/math.sqrt(2)*(i+1), start_y - inter_cluster_distance/math.sqrt(2)*(i+1), cluster_size, intra_cluster_distance)
    
    for j in range(0, len(nodes_to_add_top_right_direction)):
        nodes_to_add_bottom_right_direction[j].set_logger_verbose_overwrite(False)
    
    nodes_to_add_buttom_right.extend(nodes_to_add_bottom_right_direction)

for i in range(number_of_clusters//2, number_of_clusters):

    this_i = i - (number_of_clusters//2 - 1)
    this_start_x = start_x + inter_cluster_distance/math.sqrt(2)*(number_of_clusters//2)
    this_start_y_bottom = start_y - inter_cluster_distance/math.sqrt(2)*(number_of_clusters//2)

    # Set the logging verbosity of every node to False except a handful we cherry pick
    nodes_to_add_bottom_right_direction = node_cluster_around(this_start_x + inter_cluster_distance/math.sqrt(2)*(this_i), this_start_y_bottom + inter_cluster_distance/math.sqrt(2)*(this_i), cluster_size, intra_cluster_distance)
    
    for j in range(0, len(nodes_to_add_top_right_direction)):
        nodes_to_add_bottom_right_direction[j].set_logger_verbose_overwrite(False)
    
    nodes_to_add_buttom_right.extend(nodes_to_add_bottom_right_direction)

end_x = start_x + inter_cluster_distance/math.sqrt(2) * (number_of_clusters+1)
end_y = start_y

nodes.extend(nodes_to_add_top_right)
nodes.extend(nodes_to_add_buttom_right)

nodes.append(GatewayLP(end_x, end_y))

# Example usage:
sim = Simulator(20000, 0.01)

# Assign simulator for every logger we want to keep track of time for
for node in nodes:
    node.set_logger_simulator(sim)

# Create channel
channel = Channel(packet_delay_per_unit=0.001) # If delay per unit is too high, it will mess up all calculations. TODO : fix that.

# Register all nodes to channel
channel.create_metric_mesh(CHANNEL_HEARING_RADIUS, *nodes)

# Add nodes to simulator
sim.add_nodes(*nodes)

# List of nodes

# Connect nodes within a certain distance
# add_neighbors_within_distance(nodes, distance_threshold=6)

# Start sending packets from source
source.start_sending(sim)

# Run the simulator
sim.run()
