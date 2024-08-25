import io, sys, os, re
import argparse
from copy import deepcopy
from math import ceil
from typing import List, Tuple, Optional, Dict

from piconetwork.simulutils import SimulationParameters, GenerationParameters, \
    Simulatable_MetadataAugmented_Dumpable_Network_Object, generate_topology, run_simulation, \
    set_simulation_parameters

from piconetwork.graphutils import Plot_Parameters, get_plotting_parameters, \
    include_simulation_in_figure, find_oracle_num_of_hops, include_simulation_sensitivity_in_figure

from piconetwork.logutils import LogDisector_Single_Source

from piconetwork.main import Simulator, Channel, Logger, \
    NODE_LOGGER, GATEWAY_LOGGER, SOURCE_LOGGER, SIMULATOR_LOGGER, CHANNEL_LOGGER, EVENT_LOGGER

from zipfile import ZipFile, ZIP_LZMA, ZIP_BZIP2, ZIP_DEFLATED

import numpy as np
import matplotlib.pyplot as plt; from matplotlib.figure import Figure; from matplotlib.axes import Axes

import scienceplots # For plotlib styling

"""
File used to generate analysis graphs of logs.

"""

VALID_MODES = ["FLOODING", "SLOWFLOODING", "FASTFLOODING", "REGULAR", "CONSERVATIVE", "AGGRESSIVE", "BOLD"]
VALID_TOPOLOGIES = ["random_gauss", "random_linear"]
VALID_LOGS = ["node", "gateway", "source", "simulator", "channel", "event"]
LOGGERS_DICT = {'node': NODE_LOGGER, 'gateway': GATEWAY_LOGGER, 'source': SOURCE_LOGGER, 'channel': CHANNEL_LOGGER, 'event':EVENT_LOGGER, 'simulator': SIMULATOR_LOGGER}

plt.style.use(['science', 'ieee'])
plt.rcParams.update({'figure.dpi': '100'})

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
        "-s", "--save", action='store_true',
        help="Whether or not to save logs.",
    )

    parser.add_argument(
        "--show_network", action='store_true',
        help="Whether or not to show the topology of the network before and after each simulation.",
    )

    parser.add_argument(
        "--sensitivity", action='store_true',
        help="Only do sensitivity analysis over simulations.",
    )

    # KEVIN : peut rendre optionnel pour avoir la date du jour par exemple
    parser.add_argument('files', nargs='*', help="Simulation prefix when saving logs.")

    return parser

def main() -> None:
    """ Parse command-line arguments """
    parser = init_argparse()
    args = parser.parse_args()

    # Extract everything in variables
    files = args.files
    show_network: bool = args.show_network
    do_save_logs_or_not_option: bool = args.save
    sensitivity: bool = args.sensitivity

    # Map files to categories by "simulation" (extract name), and map each files in each category by appropriate MODES.
    objects_logdisectors: List[LogDisector_Single_Source] = []
    simulation_names: Dict[str, Dict[str, List[LogDisector_Single_Source]]]= {
        # each 'name': simulation_category = {
        #   each 'mode': [list of associated simulations]
        # }
    }

    for file in files:
        with ZipFile(file, 'r') as zip:
            files_names = zip.namelist()
            # Extract in working directory, but delete as soon as properly read

            zip.extractall()

            (log_file_name, metadata_file_name) = (files_names[0], files_names[1])
            (common_prefix, lfilename) = re.findall(r"(.*)/?(.+)", log_file_name)[0]
            (_, mfilename) = re.findall(r"(.*)/?(.+)", metadata_file_name)[0]

            if "log" in mfilename:
                (log_file_name, metadata_file_name) = (metadata_file_name, log_file_name)

            # Read the file objects
            obj = LogDisector_Single_Source(log_file_name, metadata_file_name)
            objects_logdisectors.append(obj)

            if not obj.simname in simulation_names.keys():
                simulation_names[obj.simname] = {}

            if not obj.mode in simulation_names[obj.simname].keys():
                simulation_names[obj.simname][obj.mode] = []

            simulation_names[obj.simname][obj.mode].append(obj)

            for name in files_names:
                os.remove(os.getcwd()+"/"+name)

    print(simulation_names)

    for name, category in simulation_names.items():
        # Treat this simulation on its own
        # Extract ONE simulation's information from one of the cases. Sufficient for all of the others.
        reference_mode = list(category.keys())[0]; reference_object = category[reference_mode][0]
        common_network_info = reference_object.network_information
        sim_params = common_network_info.simulation_parameters
        gen_params = common_network_info.generation_parameters
        # Set only once, use the first object. This is to have the same subdivisions and parameters, for the graphs
        # Create a fake simulator to bind with this function
        simulator = Simulator(sim_params.simulation_total_duration, sim_params.simulation_slowness)
        set_simulation_parameters(sim_params, common_network_info.channel, simulator, \
            common_network_info.nodes, common_network_info.source_ids, common_network_info.nodes_ids, common_network_info.gateway_ids)
        # Define figure to show all of the category's info at once
        ax1:Axes; ax2:Axes; ax3: Axes; ax4:Axes; fig1: Figure; fig2: Figure; fig3: Figure; fig4: Figure
        fig1, ax1 = plt.subplots()
        fig2, ax2 = plt.subplots()
        fig3, ax3 = plt.subplots()
        fig4, ax4 = plt.subplots()
        min_number_of_hops_by_oracle_lambda = find_oracle_num_of_hops(common_network_info)
        # ax1 : delay
        # ax2 : success rate
        # ax3 : number of hops
        # ax4 : number of retransmissions
        # Common parameters for ALL simulations of the same category
        plot_params = get_plotting_parameters(sim_params)
        # Mode and list of objects
        all_modes = list(category.keys())
        if sensitivity:
            for mode, list_of_objects in category.items():
                # BIIIG DUMP HERE - WORKS FOR 1 SOURCE CASE only
                include_simulation_sensitivity_in_figure(ax1, ax2, ax3, ax4, plot_params, list_of_objects,
                    mode, all_modes)

            # Plot oracle
            if min_number_of_hops_by_oracle_lambda != None:
                sensitivity_counts = len(category[list(category.keys())[0]])
                l = [i/sensitivity_counts for i in range(sensitivity_counts)]
                ax3.plot(l, [min_number_of_hops_by_oracle_lambda(plot_params.sim_duration * 15.0/16.0) for li in l], label='ORACLE')

            ax1.set_xlabel('Reliability of links')
            ax1.set_ylabel('Delay from source to gateway')

            ax2.set_xlabel('Reliability of links')
            ax2.set_ylabel('Success ratio')

            ax3.set_xlabel('Reliability of links')
            ax3.set_ylabel('Number of hops')

            ax4.set_xlabel('Reliability of links')
            ax4.set_ylabel('Number of retransmissions over paacket window')

            ax1.legend()
            ax2.legend()
            ax3.legend()
            ax4.legend()

            fig1.suptitle(f"Simulation name : {name}")
            fig2.suptitle(f"Simulation name : {name}")
            fig3.suptitle(f"Simulation name : {name}")
            fig4.suptitle(f"Simulation name : {name}")
            plt.show()

        else:
            for mode, list_of_objects in category.items():
                # BIIIG DUMP HERE - WORKS FOR 1 SOURCE CASE only
                include_simulation_in_figure(ax1, ax2, ax3, ax4, plot_params, list_of_objects,
                    mode, all_modes)

            # Plot oracle
            if min_number_of_hops_by_oracle_lambda != None:
                l = [plot_params.departure_interval * i for i in range(plot_params.max_departure_intervals)]
                ax3.plot(l, [min_number_of_hops_by_oracle_lambda(li) for li in l], label='ORACLE')

            ax1.set_xlabel('Time of departure of packet')
            ax1.set_ylabel('Delay from source to gateway')

            ax2.set_xlabel('Time windows of departure of packets')
            ax2.set_ylabel('Success ratio')

            ax3.set_xlabel('Time of departure of packet')
            ax3.set_ylabel('Number of hops')

            ax4.set_xlabel('Time windows of departure of packets')
            ax4.set_ylabel('Number of retransmissions over paacket window')

            ax1.legend()
            ax2.legend()
            ax3.legend()
            ax4.legend()

            fig1.suptitle(f"Simulation name : {name}")
            fig2.suptitle(f"Simulation name : {name}")
            fig3.suptitle(f"Simulation name : {name}")
            fig4.suptitle(f"Simulation name : {name}")
            plt.show()

if __name__ == "__main__":
    main()
