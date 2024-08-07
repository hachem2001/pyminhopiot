from piconetwork.logutils import LogDisector_Single_Source
import matplotlib.pyplot as plt
from piconetwork.lpwan_jitter import *
from piconetwork.flooder import NodeLP_slowflood_mod, NodeLP_flood, NodeLP_flood_mod
from math import ceil

object = LogDisector_Single_Source("saved_logs/tld5gcf_REGULAR")

NODES_DENSITY = 1.5 # Inspired from percolation density limit before possible connectivity in grid case.
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
DENSITY_RADIUS = 15.0

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(17, 12))

snapshot = object.packet_lifetime_infos

# Plot this snapshot and assign it its appropriate label!
departure_times_successful, delays_successful, success_ratios, success_failure_interval = [], [], [], SOURCE_RECURRENT_TRANSMISSIONS_DELAY * 10

max_intervals = int(ceil(SIMULATION_TOTAL_DURATION / success_failure_interval)) + 1
success_ratios = [ [0, 0] for i in range(max_intervals)]  # [amount of success, amount of non success]
success_timesignatures = [ success_failure_interval * i for i in range(max_intervals) ]
print(max_intervals)

if False:
    for packet_id, info in snapshot.items():
        # If success
        if info[0] > SIMULATION_TOTAL_DURATION:
            # Ignore escaping last packet
            pass

        associated_interval = int(info[0] // success_failure_interval)

        if info[1] != False:
            departure_times_successful.append(info[0])
            delays_successful.append(info[1] - info[0])
            success_ratios[associated_interval][0] += 1
        else:
            success_ratios[associated_interval][1] += 1

    failure_percentages = [ 0 if ratio[0]+ratio[1] == 0 else ratio[1]/(ratio[0]+ratio[1]) for ratio in success_ratios]
    success_percentages = [ 0 if ratio[0]+ratio[1] == 0 else ratio[0]/(ratio[0]+ratio[1]) for ratio in success_ratios]

    # For simplicity all plots are on dots basically.
    ax1.plot(departure_times_successful, delays_successful)
    ax2.bar(success_timesignatures, success_percentages, color='#23ff23', edgecolor='white', width=success_failure_interval)
    ax2.bar(success_timesignatures, failure_percentages, bottom=success_percentages, color='#ff2323', edgecolor='white', width=success_failure_interval)


    ax1.set_xlabel('Time of departure of packet')
    ax1.set_ylabel('Delay from source to gateway')

    ax2.set_xlabel('Time windows of departure of packets')
    ax2.set_ylabel('Success ratio')

    plt.legend()
    plt.show()

if True:
    departure_interval = SOURCE_RECURRENT_TRANSMISSIONS_DELAY
    max_departure_intervals = int(ceil(SIMULATION_TOTAL_DURATION / departure_interval)) + 1
    departure_timesignatures = [departure_interval * i for i in range(max_departure_intervals)]
    delays_aggregator = [0 for i in range(max_departure_intervals)]
    delays_count_division = [0 for i in range(max_departure_intervals)]

    for packet_id, info in snapshot.items():
        # If success
        if info[0] > SIMULATION_TOTAL_DURATION:
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
    indexes_to_remove = set()

    for i in range(len(delays_aggregator)):
        if delays_count_division[i] == 0:
            indexes_to_remove.add(i)

    indexes = list(indexes_to_remove); indexes.sort(); indexes.reverse()

    for index in indexes:
        delays_count_division.pop(index)
        delays_aggregator.pop(index)
        departure_timesignatures.pop(index)

    # For simplicity all plots are on dots basically.
    ax1.plot(departure_timesignatures, delays_aggregator)
    ax2.bar(success_timesignatures, success_percentages, color='#23ff23', edgecolor='white', width=success_failure_interval)
    ax2.bar(success_timesignatures, failure_percentages, bottom=success_percentages, color='#ff2323', edgecolor='white', width=success_failure_interval)


    ax1.set_xlabel('Time of departure of packet')
    ax1.set_ylabel('Delay from source to gateway')

    ax2.set_xlabel('Time windows of departure of packets')
    ax2.set_ylabel('Success ratio')

    plt.legend()
    plt.show()
