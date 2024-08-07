from copy import deepcopy
from piconetwork.logutils import LogDisector_Single_Source
import matplotlib.pyplot as plt
from piconetwork.lpwan_jitter import *
from piconetwork.flooder import NodeLP_slowflood_mod, NodeLP_flood, NodeLP_flood_mod
from math import ceil
import numpy as np

NUM_OF_SAMPLES = 4

NODES_DENSITY = 1.9 # Inspired from percolation density limit before possible connectivity in grid case.
CHANNEL_DELAY_PER_UNIT = 5e-8 # used to be 0.001
NodeLP_Jitter_Configuration.JITTER_INTERVALS = 10
NodeLP_Jitter_Configuration.JITTER_MIN_VALUE = 0
NodeLP_Jitter_Configuration.JITTER_MAX_VALUE = (8*0.6)*(NodeLP_Jitter_Configuration.JITTER_INTERVALS)
NodeLP_Jitter_Configuration.ADAPTATION_FACTOR = 0.6
NodeLP.NODE_RECEPTION_OF_PACKET_DURATION = 0.6 # 0.6 milliseconds by calculating 255 octets / 50 kbps # used to be jitter interval / 6
NodeLP_slowflood_mod.NODE_RECEPTION_OF_PACKET_DURATION = NodeLP_slowflood_mod.NODE_RECEPTION_OF_PACKET_DURATION = NodeLP.NODE_RECEPTION_OF_PACKET_DURATION
NodeLP_slowflood_mod.NODE_TOTAL_JITTER_SPACE_VALUES = NodeLP_Jitter_Configuration.JITTER_MAX_VALUE
NodeLP_slowflood_mod.NUM_INTERVALS = NodeLP_Jitter_Configuration.JITTER_INTERVALS
SOURCE_RECURRENT_TRANSMISSIONS_DELAY = NodeLP_Jitter_Configuration.JITTER_MAX_VALUE * 20
SIMULATION_TOTAL_DURATION = SOURCE_RECURRENT_TRANSMISSIONS_DELAY * 90
HEARING_RADIUS = 30.0
DENSITY_RADIUS = 10.0

def mean(l : np.ndarray) -> np.ndarray:
    return l.mean(axis=0)

def variance(l: np.ndarray) -> np.ndarray:
    return l.var(axis=0)

def standard_dev(l: np.ndarray) -> np.ndarray:
    return l.std(axis=0)

prepend_files = "saved_logs/"
labels = ["FASTFLOODING", "REGULAR", "BOLD"]
files = [[f"tld7s_{label}_{i}" for i in range(NUM_OF_SAMPLES)] for label in labels] #, \
    #[f"tld6s_FASTFLOODING_{i}" for i in range(NUM_OF_SAMPLES)]]
objects = [[LogDisector_Single_Source(prepend_files+f) for f in files_subsect] for files_subsect in files]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 7))


label_counter = 0
for label in labels:

    departure_interval = SOURCE_RECURRENT_TRANSMISSIONS_DELAY
    max_departure_intervals = int(ceil(SIMULATION_TOTAL_DURATION / departure_interval)) + 1
    success_failure_interval = SOURCE_RECURRENT_TRANSMISSIONS_DELAY * 10
    max_intervals = int(ceil(SIMULATION_TOTAL_DURATION / success_failure_interval)) + 1

    success_timesignatures_all = []
    success_ratios_all = []
    departure_timesignatures_all = []
    delays_aggregator_all = []
    delays_count_division_all = []
    success_percentages_all = []
    failure_percentages_all = []

    for sample in objects[label_counter]:
        snapshot = sample.packet_lifetime_infos

        departure_times_successful, delays_successful, success_ratios = [], [], []
        success_ratios = [ [0, 0] for i in range(max_intervals)]  # [amount of success, amount of non success]
        success_timesignatures = [ success_failure_interval * i for i in range(max_intervals) ]

        departure_timesignatures = [departure_interval * i for i in range(max_departure_intervals)]
        delays_aggregator = [0 for i in range(max_departure_intervals)]
        delays_count_division = [0 for i in range(max_departure_intervals)]

        for packet_id, info in snapshot.items():
            # If success
            if info[0] > SIMULATION_TOTAL_DURATION - SOURCE_RECURRENT_TRANSMISSIONS_DELAY:
                # Ignore escaping last packet
                pass

            associated_interval = int(info[0] // success_failure_interval)
            associated_departure_interval = int(info[0] // departure_interval)

            if info[1] != False:
                delays_aggregator[associated_departure_interval] += info[1] - info[0]
                delays_count_division[associated_departure_interval] += 1

                delays_successful.append(info[1] - info[0])
                success_ratios[associated_interval][0] += 1
            else:
                success_ratios[associated_interval][1] += 1

        failure_percentages = [ 0 if ratio[0]+ratio[1] == 0 else ratio[1]/(ratio[0]+ratio[1]) for ratio in success_ratios]
        success_percentages = [ 0 if ratio[0]+ratio[1] == 0 else ratio[0]/(ratio[0]+ratio[1]) for ratio in success_ratios]

        delays_aggregator = [0 if delays_count_division[i] == 0 else delays_aggregator[i] / delays_count_division[i] for i in range(len(delays_aggregator))]

        # Add the lists to the aggregation
        success_ratios_all.append(deepcopy(success_ratios))
        delays_count_division_all.append(deepcopy(delays_count_division))
        departure_timesignatures_all.append(deepcopy(departure_timesignatures))
        delays_aggregator_all.append(deepcopy(delays_aggregator))
        success_timesignatures_all.append(deepcopy(success_timesignatures))
        success_percentages_all.append(deepcopy(success_percentages))
        failure_percentages_all.append(deepcopy(failure_percentages))

    success_timesignatures_mean, success_timesignatures_standard = [], []
    success_ratios_mean, success_ratios_standard = [], []
    departure_timesignatures_mean, departure_timesignatures_standard = [], []
    delays_aggregator_mean, delays_aggregator_standard = [], []
    delays_count_division_mean, delays_count_division_standard = [], []
    success_percentages_mean, success_percentages_standard = [], []
    failure_percentages_mean, failure_percentages_standard  = [], []

    lists_to_treat = [delays_aggregator_all, delays_count_division_all,\
        success_percentages_all, failure_percentages_all,]
    lists_in_result = [
        [delays_aggregator_mean, delays_aggregator_standard],
        [delays_count_division_mean, delays_count_division_standard],
        [success_percentages_mean, success_percentages_standard],
        [failure_percentages_mean, failure_percentages_standard],
    ]

    for l_i in range(len(lists_to_treat)):
        l = np.array(lists_to_treat[l_i]) # list to calculate mean and variance for
        #l_m, l_v = lists_in_result[l_i][0], lists_in_result[l_i][1]
        l_m = mean(l)
        l_v = standard_dev(l)

        lists_in_result[l_i][0].extend(list(l_m))
        lists_in_result[l_i][1].extend(list(l_v))

    # Clean up ax1
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
    # Clean up ax2
    indexes_to_remove = set()
    for i in range(len(success_percentages_mean)):
        if delays_count_division_mean[i] == 0:
            indexes_to_remove.add(i)
    indexes = list(indexes_to_remove); indexes.sort(); indexes.reverse()
    for index in indexes:
        success_timesignatures_all[0].pop(index)
        success_percentages_mean.pop(index)
        success_percentages_standard.pop(index)
    # Done cleaning

    ax1.errorbar(departure_timesignatures_all[0], delays_aggregator_mean, delays_aggregator_standard, ecolor="red", label=label)
    #ax2.bar(success_timesignatures_all[0], success_percentages_mean, color='#23ff23', edgecolor='white', width=success_failure_interval)
    #ax2.bar(success_timesignatures_all[0], failure_percentages_mean, bottom=success_percentages_mean, color='#ff2323', edgecolor='white', width=success_failure_interval)
    ax2.errorbar(success_timesignatures_all[0][:-2], success_percentages_mean[:-2], success_percentages_standard[:-2], label=label)
    label_counter += 1

ax1.set_xlabel('Time of departure of packet')
ax1.set_ylabel('Delay from source to gateway')

ax2.set_xlabel('Time windows of departure of packets')
ax2.set_ylabel('Success ratio')

ax1.legend()
ax2.legend()

plt.show()
