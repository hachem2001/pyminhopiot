from piconetwork.lpwan_jitter import *
import sys
import nographs
import matplotlib.pyplot as plt
import threading

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

NODES_DENSITY = 1.5 ; assert(NODES_DENSITY > 0.58) # Inspired from percolation density limit before possible connectivity in grid case.
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
x_box_max = 300.0
y_box_min = -30.0
y_box_max = 30.0

x_width = x_box_max - x_box_min
y_height = y_box_max - y_box_max

box_surface_max = (y_box_max - y_box_min) * (x_box_max - x_box_min)
nodes = []

source = SourceLP(x_box_min , (y_box_max+y_box_min)/2.0, 50)
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

# Plot the graph
def plot_nodes(nodes_list, channel, min_x, min_y, max_x, max_y):
    # Example data

    # Create a figure and axis
    fig, ax = plt.subplots()

    # Define different markers and colors for different types of nodes
    markers = {'source': 'o', 'gateway': 's', 'node': 'x'}
    colors = {'source': 'blue', 'gateway': 'red', 'node': 'green'}

    for node in nodes_list:
        x = node.x
        y = node.y
        node_type = 'node'
        if isinstance(node, GatewayLP):
            node_type = 'gateway'
        if isinstance(node, SourceLP):
            node_type = 'source'

        marker = markers[node_type]
        color = colors[node_type]
        
        ax.scatter(x, y, label=node_type, marker=marker, color=color, s=100)  # s is the size of the marker
        if node_type == 'gateway' or node_type == 'source':
            ax.text(x, y, node.get_id(), fontsize=12, ha='right')  # Annotate the node with its ID

    # Plot the connections
    for node in nodes_list:
        x1 = node.x
        y1 = node.y
        for neighbor_id in channel.get_neighbour_ids(node.get_id()):
            neighbour = channel.get_assigned_node(neighbor_id)
            x2 = neighbour.x
            y2 = neighbour.y
            ax.plot([x1, x2], [y1, y2], 'k-', lw=1)  # k- is black color line, lw is line width

    # Add legend
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='upper left', bbox_to_anchor=(1, 1))

    # Set axis limits
    ax.set_xlim(min_x, max_x)
    ax.set_ylim(min_y, max_y)
    ax.set_aspect('equal', 'box') # For faithful representation

    # Set labels
    ax.set_xlabel('X Coordinate')
    ax.set_ylabel('Y Coordinate')
    ax.set_title('Node Network')

    # Show plot
    plt.tight_layout()
    fig.subplots_adjust(right=0.8)  # Adjust right to make space for the legend

    plt.show()

plotting_thread = threading.Thread(target=plot_nodes, args=(nodes, channel, x_box_min - x_width*0.05, y_box_min - y_height*0.05, x_box_max + x_width*0.05, y_box_max + y_height*0.05))
plotting_thread.start()

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
