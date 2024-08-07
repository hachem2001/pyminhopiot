import io, sys, os
import argparse
from typing import List, Tuple, Optional

from piconetwork.simulutils import SimulationParameters, GenerationParameters, \
    Simulatable_MetadataAugmented_Dumpable_Network_Object, generate_topology, run_simulation

from piconetwork.main import Simulator, Channel, Logger, \
    NODE_LOGGER, GATEWAY_LOGGER, SOURCE_LOGGER, SIMULATOR_LOGGER, CHANNEL_LOGGER, EVENT_LOGGER

from zipfile import ZipFile, ZIP_LZMA, ZIP_BZIP2, ZIP_DEFLATED

"""
Steps :
    1) Get the name of the simulation set. Default : "sim"

    2) Get classes to simulate : FLOODING, SLOWFLOODING, FASTFLOODING, REGULAR, CONSERVATIVE, AGGRESSIVE, BOLD

    3) Do we save simulation logs? Default : no.
        When yes : save as name_of_sim_set + class_simulated + some hash
        and save : name_of_sim_set + class_simulated + some hash + ".metadata" containing :
            - used simulation parameters
            - topology

    4) Do we show logs? Default yes for gateway + source
        - Some way to say which ones to show
    5) Do we draw graphs?
        - Default : no
        - If yes :
            - Success rate over time ?
            - Jitter evolution ?
            - Packet delay over time ?
            - Number of total retransmissions over time ?
            - Collisions over time ?
            - Length of path of packets over time ?
    6) Write TODO list of all this
"""

VALID_MODES = ["FLOODING", "SLOWFLOODING", "FASTFLOODING", "REGULAR", "CONSERVATIVE", "AGGRESSIVE", "BOLD"]
VALID_TOPOLOGIES = ["random_gauss", "random_linear", "stretched_random_gauss"]
VALID_LOGS = ["node", "gateway", "source", "simulator", "channel", "event"]
LOGGERS_DICT = {'node': NODE_LOGGER, 'gateway': GATEWAY_LOGGER, 'source': SOURCE_LOGGER, 'channel': CHANNEL_LOGGER, 'event':EVENT_LOGGER, 'simulator': SIMULATOR_LOGGER}

def init_argparse() -> argparse.ArgumentParser:
    """ Credits : https://realpython.com/python-command-line-arguments/#the-python-standard-library as of 2024 """
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTION] [name_prefix]",
        description="Wrapper allowing easier simulation of piconetworks."
    )

    parser.add_argument(
        "-v", "--version", action="version",
        version = f"{parser.prog} version 1.0.0 - I guess ?"
    )

    parser.add_argument(
        "-c", "--count", default=1, type=int,
        help="Number of simulations to be done over the same topology. Default: 1"
    )

    parser.add_argument(
        "-m", "--modes", default=["REGULAR"], nargs='+',
        help="Modes to be evaluated amont FLOODING, SLOWFLOODING, FASTFLOODING, REGULAR, CONSERVATIVE, AGGRESSIVE, BOLD. Default: REGULAR.",
        required=False
    )

    parser.add_argument(
        "--density", default=[GenerationParameters.density], nargs=1, type=float,
        help=f"Density of the network generated. Default: {GenerationParameters.density}",
        required=False
    )

    parser.add_argument(
        "--nodes_generated", default=GenerationParameters.n_to_generate, type=int,
        help=f"Maximum number of networks that can be used to create the topology. The real number of nodes in the final connected mesh is LOWER. Default: {GenerationParameters.n_to_generate}",
        required=False
    )

    parser.add_argument(
        "--topology_type", default=[GenerationParameters.type_of_network], nargs=1, type=str,
        help=f"Type of topology. Two types : random_gauss, or random_horizontal_strip. Defaults to {GenerationParameters.type_of_network}",
        required=False
    )

    parser.add_argument(
        "--seed", default=GenerationParameters.seed, type=int,
        help="Seed for generating the topology. If not set : random run.",
        required=False
    )

    parser.add_argument(
        "--hearing_radius", default=[GenerationParameters.hearing_radius], type=float,
        help=f"Hearing radius of each node. Default: {GenerationParameters.hearing_radius}",
        required=False
    )

    parser.add_argument(
        "--recurrent_delay", default=[GenerationParameters.sources_recurrent_transmission_delays[0]], nargs='+', type=float,
        help=f"Delay of recurrent transmissions from sources. Default: {GenerationParameters.sources_recurrent_transmission_delays[0]}",
        required=False
    )

    parser.add_argument(
        "--jitter_max", default=[SimulationParameters.jitter_max_value], nargs=1, type=float,
        help=f"Maximum jitter value. Default: {SimulationParameters.jitter_max_value}",
        required=False
    )

    parser.add_argument(
        "--jitter_min", default=[SimulationParameters.jitter_min_value], nargs=1, type=float,
        help=f"Minimum jitter value. Default: {SimulationParameters.jitter_min_value}", # TODO : make non 0, proportional to max or smth
        required=False
    )

    parser.add_argument(
        "--jitter_intervals", default=[SimulationParameters.jitter_intervals], nargs=1, type=int,
        help=f"Number of intervals to divide the jitter space to. Default: {SimulationParameters.jitter_intervals}",
        required=False
    )

    parser.add_argument(
        "--channel_delay_per_unit", default=[SimulationParameters.channel_delay_per_unit], nargs=1, type=float,
        help="Packet 'slowness' per unit of distance. Default: 5e-8 (~ 1/c) (practically 0).",
        required=False
    )

    parser.add_argument(
        "--adaptation_factor", default=[SimulationParameters.adaptation_factor], nargs=1, type=float,
        help=f"Jitter adaptation factor. If below 0.3, can cause convergence problems. Default: {SimulationParameters.adaptation_factor}",
        required=False
    )

    parser.add_argument(
        "--simulation_length", default=[SimulationParameters.simulation_total_duration], nargs=1, type=float,
        help=f"Total duration of the simulation. Default: {SimulationParameters.simulation_total_duration}",
        required=False
    )

    parser.add_argument(
        "--simulation_slowness", default=[SimulationParameters.simulation_slowness], nargs=1, type=float,
        help=f"For simulating delay in live logs. 1.0 is 'real-time'. Default: {SimulationParameters.simulation_slowness}",
        required=False
    )

    parser.add_argument(
        "--node_reception_collision_window", default=[SimulationParameters.node_reception_of_packet_duration], nargs=1, type=float,
        help=f"Duration a packet takes to be received by a node. Affects collision rates. Default: {SimulationParameters.node_reception_of_packet_duration}",
        required=False
    )

    parser.add_argument(
        "-d", "--dir", default=['.'], nargs=1,
        help="Directory in which to save the logs. Default: current directory.",
    )

    parser.add_argument(
        "--savelogs", default=["node", "source", "gateway"], nargs='*',
        help="Which logs to save IF saving logs is enabled. Options are : node, source, gateway, channel, simulator. \
        Default : node, source and gateway.",
    )

    parser.add_argument(
        "-s", "--save", action='store_true',
        help="Whether or not to save logs.",
    )

    parser.add_argument(
        "--show_network", action='store_true',
        help="Whether or not to show the topology of the network before and after each simulation.",
    )

    parser.add_argument(
        "-l", "--logsshow", default=["source", "gateway"], nargs='*',
        help="Whether or not to show logs live. Options are : node, source, gateway, channel, simulator. \
        Default : source, gateway.",
    )

    # KEVIN : peut rendre optionnel pour avoir la date du jour par exemple
    parser.add_argument('name_prefix', nargs=1, help="Simulation prefix when saving logs.")

    return parser

def main() -> None:
    """ Parse command-line arguments """
    parser = init_argparse()
    args = parser.parse_args()

    # Extract everything in variables
    filenames_prefix : str = args.name_prefix[0]
    directory_prefix : str = args.dir[0]
    count : int = args.count # Number of times a single mode will be resimulated.
    modes : List[str] = args.modes # E.g ['REGULAR']
    density : float = args.density[0]
    nodes_generated : int = args.nodes_generated
    topology_type: str = args.topology_type[0]
    seed : Optional[int] = args.seed == 0 and None or args.seed
    hearing_radius : float = args.hearing_radius[0]
    source_recurrent_delays : Tuple[float, ...] = tuple(args.recurrent_delay)
    jitter_max : float = args.jitter_max[0]
    jitter_min : float = args.jitter_min[0]
    jitter_intervals : int = args.jitter_intervals[0]
    channel_delay_per_unit : float = args.channel_delay_per_unit[0]
    adaptation_factor : float = args.adaptation_factor[0]
    simulation_length : float = args.simulation_length[0]
    simulation_slowness : float = args.simulation_slowness[0]
    node_reception_collision_window : float = args.node_reception_collision_window[0]
    savelogs : List[str] = args.savelogs
    showlogs : List[str] = args.logsshow
    show_network : bool = args.show_network
    do_save_logs_or_not_option : bool = args.save

    # Assert that the values are appropriate
    # TODO : assert path where we want to save files is accessible/usable.
    assert density > 0.0, "Density must be a strictly positive float"
    assert count > 0, "Count must be at least 1"
    assert jitter_min < jitter_max, "Jitter interval is invalid."
    assert jitter_min >= 0.0, "Minimum jitter cannot be negative"
    assert jitter_intervals > 0, "jitter_intervals must be a strictly positive integer"
    assert channel_delay_per_unit > 0.0, "Delay over channel cannot be negative"
    assert adaptation_factor >= 0.0 and adaptation_factor <= 1.0, "Adaptation factor must be between 0.0 and 1.0 included"
    assert simulation_length >= 0.0, "Simulation length must be positive"
    assert simulation_slowness >= 0.0, "Simulation slowness (or replay speed) must be positive"
    assert node_reception_collision_window >= 0.0, "Node reception window (or transmission-level collision time window) must be positive"
    assert all([x in VALID_LOGS for x in savelogs]), "Invalid logger name in list of logs to save"
    assert all([x in VALID_LOGS for x in showlogs]), "Invalid logger name in list of logs to display/show"
    assert all([x>0 for x in source_recurrent_delays]), "all sources' delays but be positive floats"
    assert all([x in VALID_MODES for x in modes]), "One of the modes does not exist"
    assert nodes_generated > 0, "Number of nodes to attempt generating must be higher than 0"
    assert topology_type in VALID_TOPOLOGIES, "topology given unrecognized. Valid topologies are " + ",".join(VALID_TOPOLOGIES) + "."
    assert hearing_radius > 0.0, "Hearing radius must be a positive float"

    # Generate associated GenerationParameters and SimulationParameters
    # NOTE : the nodes' mode must be set manually every time to the appropriate mode during simulation.
    # Therefore, everytime a new simulation occurs, simulation_parameters must be updated
    generation_parameters = GenerationParameters(
        density = density, hearing_radius = hearing_radius, seed = seed,
        n_to_generate = nodes_generated, type_of_network = topology_type,
        nodes_mode = modes[0], sources_recurrent_transmission_delays = source_recurrent_delays
    )

    simulation_parameters = SimulationParameters(
        nodes_mode = modes[0], channel_delay_per_unit = channel_delay_per_unit,
        hearing_radius = hearing_radius, jitter_intervals = jitter_intervals,
        jitter_max_value = jitter_max, jitter_min_value = jitter_min,
        adaptation_factor = adaptation_factor, sources_recurrent_transmission_delays = source_recurrent_delays
    )
    print("Simulation arguments : ", args)

    # First : generate topology
    nodes_all, source_ids, node_ids, gateway_ids, channel = generate_topology(generation_parameters)

    # TODO : take "count" into account and redo this sequence many times
    # TODO : take into account every different mode
    for counter in range(count):
        for i in range(len(modes)):
            simulation_parameters.nodes_mode = modes[i]
            # Generate full meta_data object
            simulation_full_parameters_and_metadata = Simulatable_MetadataAugmented_Dumpable_Network_Object(
                nodes=nodes_all, loggers_effective=savelogs, loggers_verbose=showlogs,
                simulation_parameters=simulation_parameters,generation_parameters=generation_parameters,
                source_ids=source_ids, gateway_ids=gateway_ids, nodes_ids=node_ids,channel=channel
            )

            # Name of associated files :
            zip_prefix = directory_prefix + '/' + filenames_prefix + "_" + modes[i] + "_" + str(counter)
            file_logs_name = zip_prefix + "_logs"
            file_topology_info_name = zip_prefix + "_topology_info"

            # Run simulation!
            run_simulation(simulation_full_parameters_and_metadata, file_logs_name, file_topology_info_name,
                save_results = do_save_logs_or_not_option, show_network = show_network)

            if do_save_logs_or_not_option:
                with ZipFile(zip_prefix + ".zip", "w", compression=ZIP_DEFLATED, compresslevel=7) as zipped_archive:
                    zipped_archive.write(file_logs_name+".gz")
                    zipped_archive.write(file_topology_info_name)

                os.remove(file_logs_name+".gz")
                os.remove(file_topology_info_name)

if __name__ == "__main__":
    main()
