import io, sys, os, argparse, random, pickle, networkx as nx

from typing import List, Tuple, Optional
from dataclasses import dataclass
from copy import deepcopy

import nographs # For finding smallest path from source to gateway
import numpy as np; import numpy.ma as ma
from matplotlib import pyplot as plt; from matplotlib.figure import Figure; from matplotlib.axes import Axes
from math import ceil, inf

from .main import Simulator, Channel, Logger, NODE_LOGGER, GATEWAY_LOGGER, SOURCE_LOGGER, SIMULATOR_LOGGER, CHANNEL_LOGGER, EVENT_LOGGER, Simulator
from .lpwan_jitter import NodeLP, PacketLP, SourceLP, GatewayLP, NodeLP_Jitter_Configuration
from .graphical import plot_nodes_lpwan_better;
from .simulutils import Simulatable_MetadataAugmented_Dumpable_Network_Object ,SimulationParameters, GenerationParameters, VALID_MODES
from .logutils import LogDisector_Single_Source


"""
Graphutils contain classes, datastructures and functions that are helpful for analyzing log files and network dumps.
"""

# Some useful functions that I use nowhere else
def mean(l : ma.masked_array) -> ma.masked_array:
    return l.mean(axis=0)

def variance(l: ma.masked_array) -> ma.masked_array:
    return l.var(axis=0)

def standard_dev(l: ma.masked_array) -> ma.masked_array:
    return l.std(axis=0)

def two_sided_dev(l: ma.masked_array) -> Tuple[ma.masked_array, ma.masked_array]:
    """ returns Square root of Square Mean Absolute Deviation on "below mean" and "above mean" values."""
    m = l.mean(axis=0)
    dif = l - m
    dif_positive = dif.copy(); dif_positive[dif_positive<0] = 0; dif_positive **= 2;
    dif_negative = dif.copy(); dif_negative[dif_negative>0] = 0; dif_negative **= 2;
    return dif_negative.mean(axis=0)**0.5, dif_positive.mean(axis=0)**0.5


@dataclass
class Plot_Parameters:
    sim_duration: float # Duration of whole simulation to look at
    recurrent_duration: float # Duration of recurrence of sources
    departure_interval: float # Interval regrouping points when looking at for example delay time with respect to "departure time"
    max_departure_intervals:int # Max number of departure intervals = int(ceil(SIM_DURATION / departure_interval)) + 1
    success_failure_interval:float # Interval overwhich we analyze the sccess failure rate = RECURRENT_DURATION * 10
    max_intervals: int # Number of intervals when looking at success rates = int(ceil(SIM_DURATION / success_failure_interval)) + 1
    discard_event_after:float # Interval at the end where we don't consider packets emitted after it. = SIM_DURATION - RECURRENT_DURATION
    show_oracle:bool = False # Whether to show how the oracle would fare

def get_plotting_parameters(sim_params: SimulationParameters):
    """
    label is the mode (FLOODING, REGULAR, ...).
    Gets the plotting parameters used for the 4x4 figure.
    """
    SIM_DURATION = sim_params.simulation_total_duration
    RECURRENT_DURATION = sim_params.sources_recurrent_transmission_delays[0]

    discard_event_after = SIM_DURATION - RECURRENT_DURATION * 3
    departure_interval = RECURRENT_DURATION
    max_departure_intervals = int(ceil(discard_event_after / departure_interval)) + 1
    success_failure_interval = RECURRENT_DURATION * 10
    max_intervals = int(ceil(discard_event_after / success_failure_interval)) + 1

    return Plot_Parameters(sim_duration=SIM_DURATION, recurrent_duration=RECURRENT_DURATION, departure_interval=departure_interval,\
        max_departure_intervals=max_departure_intervals, success_failure_interval=success_failure_interval,\
        max_intervals=max_intervals, discard_event_after=discard_event_after)

def find_oracle_num_of_hops(all_data: Simulatable_MetadataAugmented_Dumpable_Network_Object):
    """ Returns the optimal minimum number of hops from source to gateway on the simulation """
    source_id = all_data.source_ids[0]
    gateway_ids = all_data.gateway_ids

    channel = all_data.channel
    source = all_data.nodes[source_id]
    gateways = [all_data.nodes[gateway_id] for gateway_id in gateway_ids]

    minimal_depth = inf

    print(gateway_ids)

    for gateway in gateways:
        traversal = nographs.TraversalBreadthFirst(lambda i,_: channel.get_neighbour_ids(i)).start_from(source.get_id())
        depths = {vertex: traversal.depth for vertex in traversal.go_for_depth_range(0, len(all_data.nodes))}
        if gateway.get_id() not in depths.keys():
            raise AssertionError("No possible path from source to one of the gateways.")
        else:
            minimal_depth = min(minimal_depth, depths[gateway.get_id()])

    return minimal_depth


def include_simulation_in_figure(ax1: Axes, ax2: Axes, ax3: Axes, ax4: Axes,\
        plot_params: Plot_Parameters, list_of_objects: List[LogDisector_Single_Source],
        mode:str, all_modes:List[str]):
    """
    Context : each figure is a 4x4 image subplot image.
    Each time we treat a set of simulations pertaining to the same topology and mode, we aggregate that information and we can add it to the figure.
    This function is a helper function allowing that
    """
    assert mode in all_modes, "Mode and set of modes evaluated not coherent"

    success_failure_interval_length = plot_params.success_failure_interval
    departure_interval_length = plot_params.departure_interval
    number_of_sucessratio_intervals = plot_params.max_intervals
    number_of_perdeparture_intervals = plot_params.max_departure_intervals
    discard_event_after_timestamp = plot_params.discard_event_after

    retx_amount_interval_length = plot_params.departure_interval * 3
    number_retx_amount_intervals = int(ceil(discard_event_after_timestamp / retx_amount_interval_length)) + 1

    success_timesignatures_all = []
    success_ratios_all = []
    success_percentages_all = []

    departure_timesignatures_for_delays_all = []
    delays_aggregator_all = []
    delays_count_division_all = []

    departure_timesignatures_for_hops_all = []
    hops_aggregator_all = []
    hops_counts_division_all = []

    retx_binedges_all = []
    retx_amounts_all = []

    for sample in list_of_objects:
        snapshot = sample.packet_lifetime_infos

        success_ratios = [ [0, 0] for i in range(number_of_sucessratio_intervals)]  # [amount of success, amount of non success]
        success_timesignatures = [ success_failure_interval_length * i for i in range(number_of_sucessratio_intervals) ]

        departure_timesignatures_for_delays = [departure_interval_length * i for i in range(number_of_perdeparture_intervals)]
        delays_aggregator = [ 0 for i in range(number_of_perdeparture_intervals)]
        delays_count_division = [0 for i in range(number_of_perdeparture_intervals)]

        departure_timesignatures_for_hops = [departure_interval_length * i for i in range(number_of_perdeparture_intervals)] # Use same division as delay for number of hops.
        hops_aggregator = [0 for i in range(number_of_perdeparture_intervals)]
        hops_counts_division = [0 for i in range(number_of_perdeparture_intervals)]

        # Aggregate amount of #retx
        transmission_times_combined = sample.node_stats['transmitted_packets_times']
        transmission_times_inhistogram_form, transmission_times_bin_edges = np.histogram(transmission_times_combined, bins=number_retx_amount_intervals)

        retx_amounts_all.append(deepcopy(transmission_times_inhistogram_form))
        retx_binedges_all.append(deepcopy(transmission_times_bin_edges))

        for packet_id, info in snapshot.items():
            # Ignore escaping last packets
            if info[0] > discard_event_after_timestamp:
                continue

            associated_successfailure_interval_number = int(info[0] // success_failure_interval_length)
            associated_departure_interval_number = int(info[0] // departure_interval_length)

            # If success
            if info[1] != False:
                delays_aggregator[associated_departure_interval_number] += info[1] - info[0]
                delays_count_division[associated_departure_interval_number] += 1
                success_ratios[associated_successfailure_interval_number][0] += 1
            else:
                success_ratios[associated_successfailure_interval_number][1] += 1

            # Number of hops keep counting
            if info[2] != False:
                hops_counts_division[associated_departure_interval_number] += 1
                hops_aggregator[associated_departure_interval_number] += info[2]

        success_percentages = [ float('nan') if ratio[0]+ratio[1] == 0 else ratio[0]/(ratio[0]+ratio[1]) \
            for ratio in success_ratios]
        delays_aggregator = [float('nan') if delays_count_division[i] == 0 else delays_aggregator[i] / delays_count_division[i] \
            for i in range(len(delays_aggregator))]
        hops_aggregator = [float('nan') if hops_counts_division[i] == 0 else hops_aggregator[i] / hops_counts_division[i] \
            for i in range(len(hops_aggregator))]

        """
        # Filter out the "Falses" from both x and y, so it does not get added anywhere.
        to_filter_delays = []; to_filter_hops = []; to_filter_successes = [];
        groups_to_treat = [[delays_aggregator, delays_count_division, departure_timesignatures_for_delays, to_filter_delays],\
            [hops_aggregator, hops_counts_division, departure_timesignatures_for_hops, to_filter_hops], \
            [success_percentages, success_ratios, success_timesignatures, to_filter_successes]] # [failure_percentages, to_filter_failures]]


        for group in groups_to_treat:
            for i in range(len(group[0])):
                if group[0][i] == False:
                    group[3].append(i)

        for group in groups_to_treat
            group[3].sort(); group[3].reverse()
            for i in group:
                group[0].pop(i)
                group[1].pop(i)
                group[2].pop(i)
        """

        # Add the lists to the aggregation
        success_ratios_all.append(deepcopy(success_ratios))
        success_percentages_all.append(deepcopy(success_percentages))
        success_timesignatures_all.append(deepcopy(success_timesignatures))

        delays_aggregator_all.append(deepcopy(delays_aggregator))
        delays_count_division_all.append(deepcopy(delays_count_division))
        departure_timesignatures_for_delays_all.append(deepcopy(departure_timesignatures_for_delays))

        hops_aggregator_all.append(deepcopy(hops_aggregator))
        hops_counts_division_all.append(deepcopy(hops_counts_division))
        departure_timesignatures_for_hops_all.append(deepcopy(departure_timesignatures_for_hops))

    success_ratios_all = np.ma.array(success_ratios_all, dtype=float, fill_value=99999)
    success_percentages_all = np.ma.array(success_percentages_all, dtype=float, fill_value=99999)
    success_timesignatures_all = np.ma.array(success_timesignatures_all, dtype=float, fill_value=99999)

    delays_aggregator_all = np.ma.array(delays_aggregator_all, dtype=float, fill_value=99999)
    delays_count_division_all = np.ma.array(delays_count_division_all, dtype=float, fill_value=99999)
    departure_timesignatures_for_delays_all = np.ma.array(departure_timesignatures_for_delays_all, dtype=float, fill_value=99999)

    hops_aggregator_all = np.ma.array(hops_aggregator_all, dtype=float, fill_value=99999)
    hops_counts_division_all = np.ma.array(hops_counts_division_all, dtype=float, fill_value=99999)
    departure_timesignatures_for_hops_all = np.ma.array(departure_timesignatures_for_hops_all, dtype=float, fill_value=99999)


    metrics = {
        'delay': {
            'all': np.ma.masked_where(np.isnan(delays_aggregator_all), delays_aggregator_all),
            'mean': None,
            'standard': None
            },
        'delay_count':{
            'all': np.ma.masked_where(np.isnan(delays_count_division_all), delays_count_division_all),
            'mean': None,
            'standard': None
            },
        'hops': {
            'all': np.ma.masked_where(np.isnan(hops_aggregator_all), hops_aggregator_all),
            'mean': None,
            'standard': None
            },
        'success': {
            'all': np.ma.masked_where(np.isnan(success_percentages_all), success_percentages_all),
            'mean': None,
            'standard': None
            },
        'retx': {
            'all': np.ma.masked_where(np.isnan(retx_amounts_all), retx_amounts_all),
            'mean': None,
            'standard': None
            }
    }

    for name, metric in metrics.items():

        data = metric['all']

        l_m = mean(data)
        # l_std = standard_dev(l)

        # MOD
        l_std_1, l_std_2 = two_sided_dev(data)

        metric['mean'] = l_m
        metric['standard'] = [l_std_1, l_std_2]

    # Done cleaning
    linestyle = {"markeredgewidth":1.5, "elinewidth":1.5, "capsize":2.5}
    final_sucess_deviation_up_and_down = [metrics['success']['standard'][0], metrics['success']['standard'][1]]
    ax1.errorbar(departure_timesignatures_for_delays_all[0], metrics['delay']['mean'], metrics['delay']['standard'], label=mode, errorevery=3*random.sample([2, 3, 5, 7, 11], 1)[0], **linestyle)
    #ax2.bar(success_timesignatures_all[0], success_percentages_mean, color='#23ff23', edgecolor='white', width=success_failure_interval)
    #ax2.bar(success_timesignatures_all[0], failure_percentages_mean, bottom=success_percentages_mean, color='#ff2323', edgecolor='white', width=success_failure_interval)
    ax2.errorbar(success_timesignatures_all[0], metrics['success']['mean'], final_sucess_deviation_up_and_down, label=mode, errorevery=1, **linestyle)

    # For ax3 : number of hops
    ax3.errorbar(departure_timesignatures_for_delays_all[0], metrics['hops']['mean'], metrics['hops']['standard'], label=mode, errorevery=3*random.sample([2, 3, 5], 1)[0], **linestyle)

    # For ax4 : amount of #retx
    if True:
        positions = deepcopy(retx_binedges_all[0][:-1])
        offset_index = all_modes.index(mode)
        num_of_modes = len(all_modes) + 1
        width = retx_amount_interval_length/num_of_modes

        positions = np.array(positions) + offset_index*width
        ax4.bar(positions, metrics['retx']['mean'], yerr=metrics['retx']['standard'], width=width, label=mode, error_kw = {'errorevery':2, 'capsize':1, 'elinewidth':0.75})

        """
        plt.hist(transmission_times_combined, edgecolor="indigo", bins=range(int(min(transmission_times_combined)), int(max(transmission_times_combined) + SOURCE_RECURRENT_TRANSMISSIONS_DELAY), int(SOURCE_RECURRENT_TRANSMISSIONS_DELAY)), label = label_names[counter_label_name])
        plt.xlabel('Time of packet retransmission')
        plt.ylabel('Number of packets retransmitted')
        plt.legend()
        plt.show()
        """
