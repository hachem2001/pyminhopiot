from piconetwork.generic import *
import nographs

"""
Example of how to use nographs to check depth of nodes within a BreadFirstSearch from source.
This allows to verify in other simulations for example, to verify that a path from source to gateway exists.
"""

# Set loggers
EVENT_LOGGER.set_verbose(False)
GATEWAY_LOGGER.set_verbose(True)
NODE_LOGGER.set_verbose(True)
SIMULATOR_LOGGER.set_verbose(False)
SOURCE_LOGGER.set_verbose(False)
CHANNEL_LOGGER.set_verbose(False)

# Example usage:
sim = Simulator(20, 0.01)

# Create nodes with coordinates
source = SourceGeneric(0, 0, interval=5)
node1 = NodeGeneric(5, 0)
node2 = NodeGeneric(10, 0)
node3 = NodeGeneric(15, 0)
gateway = GatewayGeneric(20, 0)

# List of nodes
nodes = [source, node1, node2, node3, gateway]

# Create channel
channel = ChannelGeneric()

# Register all nodes to channel
channel.create_metric_mesh(6.0, source, node1, node2, node3, gateway)

# Check path existence with NoGraphs library
traversal = nographs.TraversalBreadthFirst(lambda i,_: channel.get_neighbour_ids(i)).start_from(source.get_id())
depths = {vertex: traversal.depth for vertex in traversal.go_for_depth_range(0, len(nodes))}