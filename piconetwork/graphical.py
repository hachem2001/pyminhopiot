from .lpwan_jitter import *
import matplotlib.pyplot as plt

def plot_nodes_agnostic(nodes_list: List['Node'], channel: 'Channel', min_x, min_y, max_x, max_y, ):
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

def plot_nodes_lpwan(nodes_list: List['NodeLP'], channel: 'Channel', min_x, min_y, max_x, max_y, ):
    # Create a figure and axis
    fig, ax = plt.subplots()

    # Define different markers and colors for different types of nodes
    markers = {'source': 'o', 'gateway': 's', 'node': 'x', 'suppressed': '.', 'unengaged': '1', 'disabled': '2', 'disabled_gw': 's', 'disabled_sr': 'o'}
    colors = {'source': 'blue', 'gateway': 'red', 'node': 'green', 'suppressed': 'orange', 'unengaged': 'black', 'disabled': 'gray', 'disabled_gw': 'gray', 'disabled_sr': 'gray'}

    for node in nodes_list:
        x = node.x
        y = node.y
        node_type = 'node'
        if isinstance(node, GatewayLP):
            if node.get_enabled() == False:
                node_type = 'disabled_gw'
            else:
                node_type = 'gateway'
        elif isinstance(node, SourceLP):
            # Check if suppressed or not
            if node.get_enabled() == False:
                node_type = 'disabled_sr'
            else:
                node_type = 'source'
        else:
            suppression_mode = node.last_packets_informations[0].suppression_mode
            if node.get_enabled() == False:
                node_type = 'disabled'
            elif suppression_mode == NodeLP_Suppression_Mode.REGULAR:
                node_type = 'node'
            elif suppression_mode == node.last_packets_informations[0].SUPPRESSION_MODE_SWITCH:
                node_type = 'suppressed'
            elif suppression_mode == NodeLP_Suppression_Mode.NEVER_ENGAGED:
                node_type = 'unengaged'
            else:
                raise AssertionError("Not possible?")

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

def plot_lpwan_jitter_interval_distribution(nodes: List[NodeLP]):
    count_per_jitter_interval = [0 for i in range(NodeLP_Jitter_Configuration.JITTER_INTERVALS)]
    for node in nodes:
        if isinstance(node, NodeLP) and node.get_enabled():
            count_per_jitter_interval[node.last_packets_informations[0].min_jitter] += 1
    plt.bar([i+1 for i in range(NodeLP_Jitter_Configuration.JITTER_INTERVALS)], count_per_jitter_interval, label='Number of Nodes (Exluding Disabled)')
    plt.legend()
    plt.xlabel('Jitter Interval')
    plt.show()

def plot_delays_of_packet_arrival(delays_of_arrival_source_to_gateway, times_of_arrival_source_to_gateway, times_of_departure_source_to_gateway, connect : bool = False):
    # TODO : make the plot per "group of packets emitted at a certain time" instead of the way it is done now

    plt.plot(times_of_departure_source_to_gateway, delays_of_arrival_source_to_gateway, connect and 'r' or 'ro')
    plt.xlabel('Time of departure of packet')
    plt.ylabel('Delay from source to gateway')
    plt.show()

def plot_helper_lpwan_jitter_recurrent_metric(simulator: 'Simulator', nodes : List['NodeLP'], jitter_distributions, jitter_distributions_timestamps, recurrent_interval : float = 100.0):
    """
    For making a graph on evolution of jitter over simulation time 
    :nodes: List of nodes to keep track of.
    :jitter_distributions: List!
    :jitter_distirbutions_timestamps : List as well
    """
    count_per_jitter_interval = [0 for i in range(NodeLP_Jitter_Configuration.JITTER_INTERVALS)]
    for node in nodes:
        if isinstance(node, NodeLP) and node.get_enabled():
            count_per_jitter_interval[node.last_packets_informations[0].min_jitter] += 1
    jitter_distributions.append(list(count_per_jitter_interval))
    jitter_distributions_timestamps.append(simulator.get_current_time())
    simulator.schedule_event(recurrent_interval, plot_helper_lpwan_jitter_recurrent_metric, nodes, jitter_distributions, jitter_distributions_timestamps, recurrent_interval = recurrent_interval)

def plot_lpwan_jitter_metrics(jitter_distributions_timestamps, jitter_distributions, recurrent_interval : float = 100.0):
    # Each jitter interval has its label and gets plotted as a bar graph
    fig, ax = plt.subplots()

    plot_bars_drawn = []
    bottom = [0 for i in range(len(jitter_distributions_timestamps))]
    for i in range(NodeLP_Jitter_Configuration.JITTER_INTERVALS):

        to_be_filled = []
        for j in range(len(jitter_distributions_timestamps)):
            to_be_filled.append(jitter_distributions[j][i])
        
        plot_bars_drawn.append(plt.bar(jitter_distributions_timestamps, to_be_filled, bottom=bottom, width=recurrent_interval*0.9))
        
        for j in range(len(jitter_distributions_timestamps)):
            bottom[j] += jitter_distributions[j][i]

    
    handles = [plot_bars_drawn[i][0] for i in range(NodeLP_Jitter_Configuration.JITTER_INTERVALS)]
    labels = [i for i in range(NodeLP_Jitter_Configuration.JITTER_INTERVALS)]
    ax.legend(handles, labels, loc='upper left', bbox_to_anchor=(1, 1))

    plt.xlabel('Time Stamp')
    plt.tight_layout()
    fig.subplots_adjust(right=0.8)  # Adjust right to make space for the legend

    plt.show()