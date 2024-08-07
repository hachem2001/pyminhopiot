import io, sys, os, argparse, random, pickle, networkx as nx

from typing import List, Tuple, Optional
from dataclasses import dataclass
from copy import deepcopy

import numpy as np
from matplotlib import pyplot as plt; from matplotlib.figure import Figure; from matplotlib.axes import Axes
from math import ceil

from .main import Simulator, Channel, Logger, NODE_LOGGER, GATEWAY_LOGGER, SOURCE_LOGGER, SIMULATOR_LOGGER, CHANNEL_LOGGER, EVENT_LOGGER, Simulator
from .lpwan_jitter import NodeLP, PacketLP, SourceLP, GatewayLP, NodeLP_Jitter_Configuration
from .graphical import plot_nodes_lpwan_better;
from .simulutils import SimulationParameters, GenerationParameters
from .logutils import LogDisector_Single_Source


"""
Graphutils contain classes, datastructures and functions that are helpful for analyzing log files and network dumps.
"""

# Some useful functions that I use nowhere else
def mean(l : np.ndarray) -> np.ndarray:
    return l.mean(axis=0)

def variance(l: np.ndarray) -> np.ndarray:
    return l.var(axis=0)

def standard_dev(l: np.ndarray) -> np.ndarray:
    return l.std(axis=0)

def two_sided_dev(l: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """ returns Mean Absolute Deviation on "below mean" and "above mean" values."""
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
    label is the mode (FLOODING, REGULAR, ...)
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

def include_simulation_in_figure(fig: Figure, ax1: Axes, ax2: Axes, ax3: Axes, ax4: Axes,\
        plot_params: Plot_Parameters, list_of_objects: List[LogDisector_Single_Source], mode:str):
    """
    Context : each figure is a 4x4 image subplot image.
    Each time we treat a set of simulations pertaining to the same topology and mode, we aggregate that information and we can add it to the figure.
    This function is a helper function allowing that
    """

    max_intervals = plot_params.max_intervals
    success_failure_interval = plot_params.success_failure_interval
    departure_interval = plot_params.departure_interval
    max_departure_intervals = plot_params.max_departure_intervals
    success_failure_interval = plot_params.success_failure_interval
    max_intervals = plot_params.max_intervals
    discard_event_after = plot_params.discard_event_after


    success_timesignatures_all = []
    success_ratios_all = []
    departure_timesignatures_all = []
    delays_aggregator_all = []
    delays_count_division_all = []
    number_of_hops_aggregator_all = []
    success_percentages_all = []
    failure_percentages_all = []


    for sample in list_of_objects:
        snapshot = sample.packet_lifetime_infos

        departure_times_successful, delays_successful, success_ratios = [], [], []
        success_ratios = [ [0, 0] for i in range(max_intervals)]  # [amount of success, amount of non success]
        success_timesignatures = [ success_failure_interval * i for i in range(max_intervals) ]

        departure_timesignatures = [departure_interval * i for i in range(max_departure_intervals)]
        delays_aggregator = [0 for i in range(max_departure_intervals)]
        delays_count_division = [0 for i in range(max_departure_intervals)]
        number_of_hops = [0 for i in range(max_departure_intervals)] # Use same division as delay for number of hops.


        for packet_id, info in snapshot.items():
            # Ignore escaping last packets
            if info[0] > discard_event_after:
                continue

            associated_interval = int(info[0] // success_failure_interval)
            associated_departure_interval = int(info[0] // departure_interval)
            # If success
            if info[1] != False:
                delays_aggregator[associated_departure_interval] += info[1] - info[0]
                delays_count_division[associated_departure_interval] += 1

                delays_successful.append(info[1] - info[0])
                success_ratios[associated_interval][0] += 1
            else:
                success_ratios[associated_interval][1] += 1

            # Number of hops keep counting
            if info[2] != False:
                number_of_hops[associated_departure_interval] += info[2]

        failure_percentages = [ 0 if ratio[0]+ratio[1] == 0 else ratio[1]/(ratio[0]+ratio[1]) for ratio in success_ratios]
        success_percentages = [ 0 if ratio[0]+ratio[1] == 0 else ratio[0]/(ratio[0]+ratio[1]) for ratio in success_ratios]

        delays_aggregator = [0 if delays_count_division[i] == 0 else delays_aggregator[i] / delays_count_division[i] \
            for i in range(len(delays_aggregator))]
        number_of_hops_aggregator = [0 if number_of_hops[i] == 0 else number_of_hops[i] / delays_count_division[i] \
            for i in range(len(number_of_hops))]

        # Add the lists to the aggregation
        success_ratios_all.append(deepcopy(success_ratios))
        delays_count_division_all.append(deepcopy(delays_count_division))
        departure_timesignatures_all.append(deepcopy(departure_timesignatures))
        delays_aggregator_all.append(deepcopy(delays_aggregator))
        number_of_hops_aggregator_all.append(deepcopy(number_of_hops_aggregator))
        success_timesignatures_all.append(deepcopy(success_timesignatures))
        success_percentages_all.append(deepcopy(success_percentages))
        failure_percentages_all.append(deepcopy(failure_percentages))

    success_timesignatures_mean, success_timesignatures_standard = [], []
    success_ratios_mean, success_ratios_standard = [], []
    departure_timesignatures_mean, departure_timesignatures_standard = [], []
    delays_aggregator_mean, delays_aggregator_standard = [], []
    delays_count_division_mean, delays_count_division_standard = [], []
    number_of_hops_aggregator_mean, number_of_hops_aggregator_standard = [], []
    success_percentages_mean, success_percentages_standard = [], []
    failure_percentages_mean, failure_percentages_standard  = [], []

    lists_to_treat = [delays_aggregator_all, delays_count_division_all,\
        number_of_hops_aggregator_all, success_percentages_all, failure_percentages_all,]

    lists_in_result = [
        [delays_aggregator_mean, delays_aggregator_standard],
        [delays_count_division_mean, delays_count_division_standard],
        [number_of_hops_aggregator_mean, number_of_hops_aggregator_standard],
        [success_percentages_mean, success_percentages_standard],
        [failure_percentages_mean, failure_percentages_standard],
    ]

    assert len(lists_to_treat) == len(lists_in_result), "Big mistake here."

    for l_i in range(len(lists_to_treat)):
        l = np.array(lists_to_treat[l_i]) # list to calculate mean and variance for
        #l_m, l_v = lists_in_result[l_i][0], lists_in_result[l_i][1]
        l_m = mean(l)
        l_std = standard_dev(l)

        # MOD
        l_std_1, l_std_2 = two_sided_dev(l)
        lists_in_result[l_i][0].extend(list(l_m))
        lists_in_result[l_i][1].extend([list(l_std_1), list(l_std_2)]) # used to be list(l_std)

    # Clean up ax1
    """
    indexes_to_remove = set()
    for i in range(len(delays_aggregator_mean)):
        if delays_count_division_mean[i] == 0:
            indexes_to_remove.add(i)
    indexes = list(indexes_to_remove); indexes.sort(); indexes.reverse()
    for index in indexes:
        delays_count_division_mean.pop(index)
        delays_aggregator_mean.pop(index)
        departure_timesignatures_all[0].pop(index)
        delays_count_division_standard.pop(index)
        delays_aggregator_standard.pop(index)
    """

    # Clean up ax2
    """
    indexes_to_remove = set()
    for i in range(len(success_percentages_mean)):
        if success_percentages_mean[i] == 0:
            indexes_to_remove.add(i)

    indexes = list(indexes_to_remove); indexes.sort(); indexes.reverse()
    for index in indexes:
        success_timesignatures_all[0].pop(index)
        success_percentages_mean.pop(index)
        success_percentages_standard.pop(index)
    """

    # Done cleaning
    linestyle = {"markeredgewidth":1.5, "elinewidth":1.5, "capsize":2.5}
    final_sucess_deviation_up_and_down = [success_percentages_standard[0][:-2], success_percentages_standard[1][:-2]]
    ax1.errorbar(departure_timesignatures_all[0], delays_aggregator_mean, delays_aggregator_standard, label=mode, errorevery=3*random.sample([2, 3, 5, 7, 11], 1)[0], **linestyle)
    #ax2.bar(success_timesignatures_all[0], success_percentages_mean, color='#23ff23', edgecolor='white', width=success_failure_interval)
    #ax2.bar(success_timesignatures_all[0], failure_percentages_mean, bottom=success_percentages_mean, color='#ff2323', edgecolor='white', width=success_failure_interval)
    ax2.errorbar(success_timesignatures_all[0][:-2], success_percentages_mean[:-2], final_sucess_deviation_up_and_down, label=mode, errorevery=1, **linestyle)

    print(departure_timesignatures_all[0], number_of_hops_aggregator_mean)
    ax3.errorbar(departure_timesignatures_all[0], number_of_hops_aggregator_mean, number_of_hops_aggregator_standard, label=mode, errorevery=3*random.sample([2, 3, 5], 1)[0], **linestyle)
