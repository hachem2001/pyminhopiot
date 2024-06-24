from piconetwork.lpwan_jitter import *
from piconetwork.graphical import plot_nodes_lpwan, plot_lpwan_jitter_interval_distribution; import matplotlib.pyplot as plt

"""
Linear cluster test

THIS TEST DEMONSTRATES THE SLOW CONVERGENCE OF AGGRESSIVE SUPPRESSION. (Very slow!)
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
        theta = i * math.pi * 2 / number
        this_x = x + radius * math.cos(theta)
        this_y = y + radius * math.sin(theta)
        nodes.append(NodeLP(this_x, this_y))

    return nodes

# SIMULATION DURATION
SIMULATION_DURATION = 4000
SIMULATION_DISABLE_BRANCH_TIMESTAMP = 2000

# Modify some innate values for better testing :
NodeLP_Jitter_Configuration.JITTER_MIN_VALUE = 0.2
NodeLP_Jitter_Configuration.JITTER_MAX_VALUE = 1.2
NodeLP_Jitter_Configuration.ADAPTATION_FACTOR = 0.5
NodeLP_Jitter_Configuration.JITTER_INTERVALS = 10
NodeLP_Jitter_Configuration.SUPPRESSION_MODE_SWITCH = NodeLP_Suppression_Mode.BOLD

R_VALUE = 10.0

CHANNEL_HEARING_RADIUS = R_VALUE 
intra_cluster_diameter = R_VALUE * 5.0/6.0
inter_cluster_distance = R_VALUE * 10.0/6.0
cluster_size = 5 ; assert(cluster_size > 1) # Number of nodes per cluster
number_of_clusters = 6 # MUST BE A PAIR NUMBER

start_x = 0.0
start_y = 0.0

nodes = []

nodes_before_bifurcating_branch = []
nodes_to_add_top_right = []
nodes_to_add_buttom_right = []
nodes_after_rejoining_branch = []

# SOURCE 
source = SourceLP(start_x - 2*inter_cluster_distance/3 , start_y, 20)
nodes.append(source)


# BEFORE BIFURCATION BRANCH
nodes_after_rejoining_branch.extend(node_cluster_around(start_x, start_y, cluster_size, intra_cluster_diameter/2))


# TOP RIGHT
for i in range(number_of_clusters//2):
    # Set the logging verbosity of every node to False except a handful we cherry pick
    nodes_to_add_top_right_direction = node_cluster_around(start_x + inter_cluster_distance/math.sqrt(2)*(i+1), start_y + inter_cluster_distance/math.sqrt(2)*(i+1), cluster_size, intra_cluster_diameter/2)
    
    for j in range(0, len(nodes_to_add_top_right_direction)):
        nodes_to_add_top_right_direction[j].set_logger_verbose_overwrite(False)
    
    nodes_to_add_top_right.extend(nodes_to_add_top_right_direction)

for i in range(number_of_clusters//2, number_of_clusters-1):
    this_i = i - (number_of_clusters//2 - 1)
    this_start_x = start_x + inter_cluster_distance/math.sqrt(2)*(number_of_clusters//2)
    this_start_y_top = start_y + inter_cluster_distance/math.sqrt(2)*(number_of_clusters//2)

    # Set the logging verbosity of every node to False except a handful we cherry pick
    nodes_to_add_top_right_direction = node_cluster_around(this_start_x + inter_cluster_distance/math.sqrt(2)*(this_i), this_start_y_top - inter_cluster_distance/math.sqrt(2)*(this_i) , cluster_size, intra_cluster_diameter/2)
    
    for j in range(0, len(nodes_to_add_top_right_direction)):
        nodes_to_add_top_right_direction[j].set_logger_verbose_overwrite(False)
    
    nodes_to_add_top_right.extend(nodes_to_add_top_right_direction)

# BOTTOM RIGHT
for i in range(number_of_clusters//2):
    # Set the logging verbosity of every node to False except a handful we cherry pick
    nodes_to_add_bottom_right_direction = node_cluster_around(start_x + inter_cluster_distance/math.sqrt(2)*(i+1), start_y - inter_cluster_distance/math.sqrt(2)*(i+1), cluster_size, intra_cluster_diameter/2)
    
    for j in range(0, len(nodes_to_add_top_right_direction)):
        nodes_to_add_bottom_right_direction[j].set_logger_verbose_overwrite(False)
    
    nodes_to_add_buttom_right.extend(nodes_to_add_bottom_right_direction)

for i in range(number_of_clusters//2, number_of_clusters-1):
    this_i = i - (number_of_clusters//2 - 1)
    this_start_x = start_x + inter_cluster_distance/math.sqrt(2)*(number_of_clusters//2)
    this_start_y_bottom = start_y - inter_cluster_distance/math.sqrt(2)*(number_of_clusters//2)

    # Set the logging verbosity of every node to False except a handful we cherry pick
    nodes_to_add_bottom_right_direction = node_cluster_around(this_start_x + inter_cluster_distance/math.sqrt(2)*(this_i), this_start_y_bottom + inter_cluster_distance/math.sqrt(2)*(this_i), cluster_size, intra_cluster_diameter/2)
    
    for j in range(0, len(nodes_to_add_top_right_direction)):
        nodes_to_add_bottom_right_direction[j].set_logger_verbose_overwrite(False)
    
    nodes_to_add_buttom_right.extend(nodes_to_add_bottom_right_direction)

# AFTER REJOINING BRANCH
nodes_after_rejoining_branch.extend(node_cluster_around(start_x + inter_cluster_distance/math.sqrt(2)*(number_of_clusters), start_y, cluster_size, intra_cluster_diameter/2))

# GATEWAY AND OTHERS
end_x = start_x + inter_cluster_distance/math.sqrt(2) * (number_of_clusters + 1)
end_y = start_y

nodes.extend(nodes_before_bifurcating_branch)
nodes.extend(nodes_to_add_top_right)
nodes.extend(nodes_to_add_buttom_right)
nodes.extend(nodes_after_rejoining_branch)

nodes.append(GatewayLP(end_x, end_y))
#nodes.append(GatewayLP(end_x, end_y + inter_cluster_distance))

# Example usage:
sim = Simulator(SIMULATION_DURATION, 0.00001)

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


x_box_min, x_box_max, y_box_min, y_box_max = min([node.x for node in nodes]), max([node.x for node in nodes]), min([node.y for node in nodes]), max([node.y for node in nodes])
x_width = x_box_max - x_box_min
y_height = y_box_max - y_box_min

def disable_upped_end(simulator: 'Simulator'):
    for node in nodes_to_add_top_right:
        node.set_enabled(False)

def draw_graphs(simulator: 'Simulator'):
    plot_nodes_lpwan(nodes, channel, x_box_min - x_width*0.05, y_box_min - y_height*0.05, x_box_max + x_width*0.05, y_box_max + y_height*0.05)
    plot_lpwan_jitter_interval_distribution(nodes)

jitter_distributions = [] # An element is a list of JITTER_INTERVALS elements, and corresponds to corresponding time stamp
jitter_distributions_timestamps = []
def recurrent_metric(simulator: 'Simulator', recurrent_interval : float = 100.0):
    """ For making a graph on evolution of jitter over simulation time """
    count_per_jitter_interval = [0 for i in range(NodeLP_Jitter_Configuration.JITTER_INTERVALS)]
    for node in nodes:
        if isinstance(node, NodeLP) and node.get_enabled():
            count_per_jitter_interval[node.last_packets_informations[0].min_jitter] += 1
    jitter_distributions.append(list(count_per_jitter_interval))
    jitter_distributions_timestamps.append(simulator.get_current_time())
    simulator.schedule_event(recurrent_interval, recurrent_metric, recurrent_interval = recurrent_interval)

def draw_metrics():
    # Each jitter interval has its label and gets plotted as a bar graph
    fig, ax = plt.subplots()

    plot_bars_drawn = []
    bottom = [0 for i in range(len(jitter_distributions_timestamps))]
    for i in range(NodeLP_Jitter_Configuration.JITTER_INTERVALS):

        to_be_filled = []
        for j in range(len(jitter_distributions_timestamps)):
            to_be_filled.append(jitter_distributions[j][i])
        
        plot_bars_drawn.append(plt.bar(jitter_distributions_timestamps, to_be_filled, bottom=bottom, width=100))
        
        for j in range(len(jitter_distributions_timestamps)):
            bottom[j] += jitter_distributions[j][i]

    
    handles = [plot_bars_drawn[i][0] for i in range(NodeLP_Jitter_Configuration.JITTER_INTERVALS)]
    labels = [i for i in range(NodeLP_Jitter_Configuration.JITTER_INTERVALS)]
    ax.legend(handles, labels, loc='upper left', bbox_to_anchor=(1, 1))

    plt.xlabel('Time Stamp')
    plt.tight_layout()
    fig.subplots_adjust(right=0.8)  # Adjust right to make space for the legend

    plt.show()

# Start sending packets from source
source.start_sending(sim)
# Enable recurrent metrics
recurrent_metric(sim)
draw_graphs(sim)

sim.schedule_event(SIMULATION_DISABLE_BRANCH_TIMESTAMP-1, draw_graphs)
sim.schedule_event(SIMULATION_DISABLE_BRANCH_TIMESTAMP, disable_upped_end)
sim.schedule_event(SIMULATION_DISABLE_BRANCH_TIMESTAMP+1, draw_graphs)

# Run the simulator
sim.run()

# End of simulation : draw graphs
draw_graphs(sim)

# Draw jitter bar plot distribution from recurrent metrics
draw_metrics()
