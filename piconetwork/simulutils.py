import io, sys, os, argparse, random, pickle, networkx as nx
from time import sleep

from typing import List, Tuple, Optional
from dataclasses import dataclass

from matplotlib import pyplot as plt; from matplotlib.figure import Figure; from matplotlib.axes import Axes

from .main import Simulator, Channel, Logger, NODE_LOGGER, GATEWAY_LOGGER, SOURCE_LOGGER, SIMULATOR_LOGGER, CHANNEL_LOGGER, EVENT_LOGGER, Simulator
from .lpwan_jitter import NodeLP, PacketLP, SourceLP, GatewayLP, NodeLP_Jitter_Configuration
from .logger import aggregate_logs_and_save

from .graphical import plot_nodes_lpwan_better;

"""
Simulation utils contain classes, datastructures and functions that are helpful for simulating scenarios, and analyzing logs for graphs
"""

# VALID_TOPOLOGIES = ["random_gauss", "random_linear", "stretched_random_gauss", "two_gateways_switch_middle_random_linear"]
VALID_MODES = ["FLOODING", "SLOWFLOODING", "FASTFLOODING", "REGULAR", "CONSERVATIVE", "AGGRESSIVE", "BOLD"]
VALID_LOGS = ["node", "gateway", "source", "simulator", "channel", "event"]
LOGGERS_DICT = {'node': NODE_LOGGER, 'gateway': GATEWAY_LOGGER, 'source': SOURCE_LOGGER, 'channel': CHANNEL_LOGGER, 'event':EVENT_LOGGER, 'simulator': SIMULATOR_LOGGER}

_default_jitter_max_factor = 8*0.6*10

@dataclass
class SimulationParameters:
    nodes_mode: str = 'REGULAR' # Mode to be chosen from list of recognized modes of course.
    channel_delay_per_unit:float = 5e-8 # used to be 0.001
    hearing_radius: float = 30.0 # Between nodes
    jitter_intervals:int = 10
    jitter_min_value:float = 0.0
    jitter_max_value:float = _default_jitter_max_factor
    adaptation_factor:float = 0.6
    node_reception_of_packet_duration = 0.6
    sources_recurrent_transmission_delays: Tuple[float, ...] = (_default_jitter_max_factor * 20,)
    simulation_total_duration: float = _default_jitter_max_factor * 20 * 90
    simulation_slowness: float = 0.0 # 1.0 would be "real-time".

@dataclass
class GenerationParameters:
    density: float = 2.3
    hearing_radius: float = 10
    seed: Optional[int] = 0;
    n_to_generate:int = 200; # Does not correspond to the number of nodes in play.
    type_of_network: str = 'random_gauss' # there's also random_strip
    hearing_radius: float = 30.0
    nodes_mode: str = 'REGULAR' # Mode to be chosen from list of recognized modes of course.
    sources_recurrent_transmission_delays: Tuple[float, ...] = (8*0.6*10 * 20,) # Same parameter as above.

@dataclass
class Simulatable_MetadataAugmented_Dumpable_Network_Object:
    """
    I reckon the name of the class is pretty self-explanatory. This would allow pickle-dumping :
        - The whole network
        - The simulation parameters
        - The generation parameters
    It however DOES NOT contain :
        - the logs necessary to analyze the simulation.
    """
    nodes: List[NodeLP|SourceLP|GatewayLP]
    loggers_effective : List[str]
    loggers_verbose: List[str]
    simulation_parameters:SimulationParameters
    generation_parameters:GenerationParameters
    source_ids: List[int]
    nodes_ids: List[int]
    gateway_ids: List[int]
    channel: Channel
    pseudorandomization_seed: Optional[int] = None

def generate_topology(topology_parameters: GenerationParameters) -> Tuple[List[NodeLP|SourceLP|GatewayLP], List[int], List[int], List[int], Channel]:
    """
    Given the topology parameters given, returns [nodes], [sources_indexes], [relay_nodes_indexes], [gateway_indexes], and channel.
    """
    random.seed(topology_parameters.seed) # Randomize simulation seed.
    for logger in VALID_LOGS: LOGGERS_DICT[logger].set_effective(False); LOGGERS_DICT[logger].set_verbose(False)

    all_nodes = []
    source_ids = []
    nodes_ids = []
    gateway_ids = []
    channel = Channel()

    # For simplicity extract the relevent variables
    density = topology_parameters.density
    hearing_distance = topology_parameters.hearing_radius
    n = topology_parameters.n_to_generate

    # Result depends on topology type
    G, largest_cc, pos = None, None, None
    if topology_parameters.type_of_network == 'random_gauss':
        width = n**0.5 * hearing_distance
        height = n**0.5 * hearing_distance
        pos = {i: (random.gauss(0, width/density), random.gauss(0, height/density)) for i in range(n)} # Position of nodes
        G = nx.random_geometric_graph(n, dim=2, radius=hearing_distance, pos=pos)
        largest_cc = G.subgraph(max(nx.connected_components(G), key=len)).copy() # Keep the biggest connected subgraph.
    elif topology_parameters.type_of_network == 'random_linear':
        width = n**(0.5) * hearing_distance * 1.41 / density
        height = n**(0.5) * hearing_distance / 1.41 / density
        pos = {i: (random.random() * width - width/2, random.random() * height - height/2) for i in range(n)} # Position of nodes
        G = nx.random_geometric_graph(n, dim=2, radius=hearing_distance, pos=pos)
        largest_cc = G.subgraph(max(nx.connected_components(G), key=len)).copy() # Keep the biggest connected subgraph.
    elif topology_parameters.type_of_network == 'stretched_random_gauss':
        width = n**0.5 * hearing_distance * 4
        height = n**0.5 * hearing_distance * 1/4
        pos = {i: (random.gauss(0, width/density), random.gauss(0, height/density)) for i in range(n)} # Position of nodes
        G = nx.random_geometric_graph(n, dim=2, radius=hearing_distance, pos=pos)
        largest_cc = G.subgraph(max(nx.connected_components(G), key=len)).copy() # Keep the biggest connected subgraph.
    elif topology_parameters.type_of_network == 'two_gateways_switch_middle_random_linear':
        width = n**(0.5) * hearing_distance * 1.41 / density
        height = n**(0.5) * hearing_distance / 1.41 / density
        pos = {i: (random.random() * width - width/2, random.random() * height - height/2) for i in range(n)} # Position of nodes
        G = nx.random_geometric_graph(n, dim=2, radius=hearing_distance, pos=pos)
        largest_cc = G.subgraph(max(nx.connected_components(G), key=len)).copy() # Keep the biggest connected subgraph.
    else:
        raise ValueError(f"Unexpected network topology {topology_parameters.type_of_network}.")

    # Add the nodes in the generated topology, and subscribe them to the same channel with set hearing distance.
    assert len(largest_cc) > 0, "Empty topology - should not be possible"
    # Find source and gateway(s) : the second gateway depends on topology_type
    pairs_shortest = dict(nx.all_pairs_shortest_path_length(largest_cc))

    longest_pair = (-1, -1, -1)
    for node, dsnts in pairs_shortest.items():
        for node_2, distance in dsnts.items():
            if distance > longest_pair[2]:
                longest_pair = (node, node_2, distance)

    first_good_triplet = (longest_pair[0], longest_pair[1], -1, -1)
    for node, distance in pairs_shortest[longest_pair[0]].items():
        if node != longest_pair[0] and node != longest_pair[1]:
            distance_1 = longest_pair[2]
            distance_2 = pairs_shortest[first_good_triplet[0]][node]
            distance_3 = pairs_shortest[first_good_triplet[1]][node]
            value = distance_1 + distance_2 + distance_3
            if value > first_good_triplet[3]:
                first_good_triplet = (longest_pair[0], longest_pair[1], node, value)

    second_good_triplet = (longest_pair[1], longest_pair[0], -1, -1)
    for node, distance in pairs_shortest[longest_pair[0]].items():
        if node != longest_pair[0] and node != longest_pair[1]:
            distance_1 = longest_pair[2]
            distance_2 = pairs_shortest[second_good_triplet[0]][node]
            distance_3 = pairs_shortest[second_good_triplet[1]][node]
            value = distance_1 + distance_2 + distance_3
            if value > second_good_triplet[3]:
                second_good_triplet = (longest_pair[0], longest_pair[1], node, value)

    # (source, furthest_gateway, second_best_gateway)
    good_triplet = first_good_triplet[3] > second_good_triplet[3] and first_good_triplet or second_good_triplet

    if not topology_parameters.type_of_network in ['two_gateways_switch_middle_random_linear']:
        other_nodes = list(largest_cc.nodes); other_nodes.remove(good_triplet[0]); other_nodes.remove(good_triplet[1])

        # Now generate!
        source = SourceLP(pos[good_triplet[0]][0], pos[good_triplet[0]][1], interval=topology_parameters.sources_recurrent_transmission_delays[0])
        all_nodes.append(source)
        source_ids.append(len(all_nodes)-1)

        for node_id in other_nodes:
            node = NodeLP(pos[node_id][0], pos[node_id][1], mode=topology_parameters.nodes_mode)
            all_nodes.append(node)
            nodes_ids.append(len(all_nodes)-1)

        gateway = GatewayLP(pos[good_triplet[1]][0], pos[good_triplet[1]][1])
        all_nodes.append(gateway)
        gateway_ids.append(len(all_nodes)-1)
    else:
        other_nodes = list(largest_cc.nodes); other_nodes.remove(good_triplet[0]); other_nodes.remove(good_triplet[1]); other_nodes.remove(good_triplet[2])

        # Now generate!
        # 2nd is source
        source = SourceLP(pos[good_triplet[1]][0], pos[good_triplet[1]][1], interval=topology_parameters.sources_recurrent_transmission_delays[0])
        all_nodes.append(source)
        source_ids.append(len(all_nodes)-1)

        for node_id in other_nodes:
            node = NodeLP(pos[node_id][0], pos[node_id][1], mode=topology_parameters.nodes_mode)
            all_nodes.append(node)
            nodes_ids.append(len(all_nodes)-1)

        # 1st and 3nd as gateways. This allows better "distribution" basically
        gateway_1 = GatewayLP(pos[good_triplet[0]][0], pos[good_triplet[0]][1])
        gateway_2 = GatewayLP(pos[good_triplet[2]][0], pos[good_triplet[2]][1])
        all_nodes.append(gateway_1)
        all_nodes.append(gateway_2)
        gateway_ids.append(len(all_nodes)-2)
        gateway_ids.append(len(all_nodes)-1)


    # Now subscribe all the nodes to the channel
    channel.create_metric_mesh(topology_parameters.hearing_radius, *all_nodes)

    # Return the objects, and associated indexes in the list, as well as channel.
    return all_nodes, source_ids, nodes_ids, gateway_ids, channel


def set_simulation_parameters(simulation_parameters: SimulationParameters, channel: Channel, simulator: Simulator, all_nodes:List[NodeLP|SourceLP|GatewayLP], source_ids: List[int], nodes_ids: List[int], gateway_ids: List[int]) -> None:
    """
    Sets all the nodes and channel parameters according to the appropriate simulation parameters.
    This is typically called before every simulation.
    """
    channel.set_delay_per_distance_unit(simulation_parameters.channel_delay_per_unit)
    NodeLP_Jitter_Configuration.JITTER_INTERVALS = simulation_parameters.jitter_intervals
    NodeLP_Jitter_Configuration.JITTER_MIN_VALUE = simulation_parameters.jitter_min_value
    NodeLP_Jitter_Configuration.JITTER_MAX_VALUE = simulation_parameters.jitter_max_value
    NodeLP_Jitter_Configuration.ADAPTATION_FACTOR = simulation_parameters.adaptation_factor
    NodeLP.NODE_RECEPTION_OF_PACKET_DURATION = simulation_parameters.node_reception_of_packet_duration # 0.6 milliseconds by calculating 255 octets / 50 kbps # used to be jitter interval / 6

    for node in all_nodes: node.reset_mode_to(simulation_parameters.nodes_mode);node.set_logger_simulator(simulator)         # Assign simulator for every logger we want to keep track of time for


def run_simulation(network_and_metadata:Simulatable_MetadataAugmented_Dumpable_Network_Object,
    save_logs_file_name: str, save_network_and_metadata_file_name: str,
    save_results: bool = False, show_network = False) -> None:
    """
    Runs a simulation.
    First : Set effective loggers and verbose loggers as given in the lists
    Second : resets all the relay nodes. (TODO : reset sources and gateways?)
    Third : create simulator, run simulations with it.
    Fourth : clean up objects (from unnecessary reduncant logs) THEN save logs in appropriate file, save network topology,nodes,parameters together in appropriate file
    Notes :
        - Enabling nodes and disabling them is not set here.
        - This is generic. For more complex scenarios, must be edited accordingly.
    """
    # Zeroeth : Extract necessary information
    all_nodes = network_and_metadata.nodes
    loggers_effective = network_and_metadata.loggers_effective
    loggers_verbose = network_and_metadata.loggers_verbose
    simulation_parameters: SimulationParameters = network_and_metadata.simulation_parameters
    source_ids: List[int] = network_and_metadata.source_ids
    nodes_ids: List[int] = network_and_metadata.nodes_ids
    gateway_ids: List[int] = network_and_metadata.gateway_ids
    channel: Channel = network_and_metadata.channel
    seed = network_and_metadata.pseudorandomization_seed

    # First - Set up the loggers
    for logger in VALID_LOGS: LOGGERS_DICT[logger].set_effective(False); LOGGERS_DICT[logger].set_verbose(False)
    for logger in loggers_effective: LOGGERS_DICT[logger].set_effective(True)
    for logger in loggers_verbose: LOGGERS_DICT[logger].set_verbose(True)

    # Second - Setup everything
    simulator = Simulator(simulation_parameters.simulation_total_duration, simulation_parameters.simulation_slowness)
    set_simulation_parameters(simulation_parameters, channel, simulator, all_nodes, source_ids, nodes_ids, gateway_ids)

    # Third - Simulate!
    if show_network:
        plot_nodes_lpwan_better(all_nodes, channel)

    for source in source_ids: source_node = all_nodes[source];assert isinstance(source_node, SourceLP);source_node.start_sending(simulator)
    random.seed() # Randomize simulation seed.
    simulator.run()

    if show_network:
        plot_nodes_lpwan_better(all_nodes, channel, title=f"Node topology with {simulation_parameters.nodes_mode} mode")

    # Fourth - Save Everything!
    if save_results:
        all_loggers : List[Logger] = list(LOGGERS_DICT.values())

        os.makedirs(os.path.dirname(save_logs_file_name), exist_ok=True) # Create folder

        # First we save the logs
        aggregate_logs_and_save(all_loggers, save_logs_file_name)

        # Then to avoid saving logs twice in the pickle dump, we remove them after having saved them.
        # NOTE : THIS REMOVES THE SIMULATOR FROM LOGGABLE, THUS NODES MUST BE PROPERLY RESET FOR FUTURE LOGS
        for node in all_nodes: node._reset_loggable_part()

        # Save the pickle dump ^_^
        with io.open(save_network_and_metadata_file_name, 'wb') as save_network_and_metadata_file:
            pickle.dump(obj = network_and_metadata, file=save_network_and_metadata_file)

    return
