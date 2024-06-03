from lpwan_jitter import *

random.seed(1)

# Set loggers
EVENT_LOGGER.set_verbose(True)
GATEWAY_LOGGER.set_verbose(True)
NODE_LOGGER.set_verbose(True)
SIMULATOR_LOGGER.set_verbose(False)
SOURCE_LOGGER.set_verbose(True)
CHANNEL_LOGGER.set_verbose(False)

# Example usage:
sim = Simulator(100, 0.01)

# Create nodes with coordinates
gateway = GatewayLP(0, 0)
node2 = NodeLP(5, 0)
node3 = NodeLP(10, 0)
node4 = NodeLP(15, 0)
source = SourceLP(20, 0, 10)

gateway.set_logger_active(True)
node2.set_logger_active(True)
node3.set_logger_active(True)
node4.set_logger_active(True)
source.set_logger_active(True)

# Create channel
channel = Channel()

# Register all nodes to channel
channel.create_metric_mesh(6.0, source, node2, node3, node4, gateway)

# Add nodes to simulator
sim.add_nodes(source, node2, node3, node4, gateway)

# List of nodes
nodes = [gateway, source, node2, node3, node4]

# Connect nodes within a certain distance
# add_neighbors_within_distance(nodes, distance_threshold=6)

# Start sending packets from source
source.start_sending(sim)

# Run the simulator
sim.run()
