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
SOURCE_LOGGER.set_verbose(False)
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

CHANNEL_HEARING_RADIUS = 10.0
inter_cluster_distance = 8.0
intra_cluster_distance = 3.0
cluster_number = 20
number_of_clusters = 20

start_x = 0.0
start_y = 0.0

nodes = []
source = SourceLP(start_x - inter_cluster_distance, start_y, 50)
nodes.append(source)

for i in range(number_of_clusters):
    # Set the logging verbosity of every node to False except a handful we cherry pick
    nodes_to_add = node_cluster_around(start_x + inter_cluster_distance*i, start_y, cluster_number, intra_cluster_distance)
    
    for j in range(0, len(nodes_to_add)-1):
        nodes_to_add[j].set_logger_active(True)
    
    nodes.extend(nodes_to_add)
end_x = start_x + inter_cluster_distance * number_of_clusters
end_y = 0

nodes.append(GatewayLP(end_x, end_y))

# Example usage:
sim = Simulator(2000, 0.001)

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
