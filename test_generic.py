from main import *

# Set loggers
EVENT_LOGGER.set_verbose(False)
GATEWAY_LOGGER.set_verbose(True)
NODE_LOGGER.set_verbose(False)
SIMULATOR_LOGGER.set_verbose(False)
SOURCE_LOGGER.set_verbose(False)
CHANNEL_LOGGER.set_verbose(False)

# Example usage:
sim = Simulator(20)

# Create nodes with coordinates
source = Source(20, 0, interval=5)
node1 = Node(5, 0)
node2 = Node(10, 0)
node3 = Node(15, 0)
gateway = Gateway(0, 0)

# Create channel
channel = Channel()

# Register all nodes to channel
channel.create_metric_mesh(6.0, source, node1, node2, node3, gateway)

# Add nodes to simulator
sim.add_nodes(source, node1, node2, node3, gateway)

# List of nodes
nodes = [gateway, source, node1, node2, node3]

# Connect nodes within a certain distance
# add_neighbors_within_distance(nodes, distance_threshold=6)

# Start sending packets from source
source.start_sending(sim)

# Run the simulator
sim.run()

