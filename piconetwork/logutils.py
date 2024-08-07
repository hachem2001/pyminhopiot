"""
The original graphical module was meant to assist with live one-simulation => display-statistics
This module is to allow drawing statistics from log files.
"""

import io, re, gzip, os
from typing import Optional, Tuple
from .simulutils import VALID_MODES, Simulatable_MetadataAugmented_Dumpable_Network_Object,\
    SimulationParameters, GenerationParameters
import pickle

def get_mode(log):
    b = re.findall(r"^\[(.+?)\]", log)
    assert(len(b)>0)
    return b[0]

def get_timestamp(log):
    b = re.findall(r"\|(.+?)\|", log)
    #print(len(b), float(b[0]))
    return float(b[0]) if (len(b)>0) else None

def get_packet_info(log):
    b = re.findall(r"Packet\((.+?)\)", log)
    assert(len(b)>0)
    m = re.findall(r"\<(\d+),.+?\>",b[0])
    return int(m[0]) # id

def get_number_of_hops(log):
    """ returns (id, num_of_hops) """
    # Example : packet 2354 is ... ... through 4 intermediate hops
    #
    b = re.findall(r"packet (\d+) is.+through (\d+) intermediate hops", log)
    assert(len(b)>0)
    return int(b[0][0]), int(b[0][1]) # id, hops

class LogDisector_Single_Source:
    """ Adapted to the case where we have a single source, and we consider any gateway to be the same at the end bit. """

    def __init__(self, path_logs, path_metadata_dump):
        """
        :path_logs: Path to aggregated logs file
        :path_metadata_dump: Path to metadata aggregated dump
        """

        self.path = path_logs
        self.logs = []
        self.node_stats = {
            'received_packets_times': [], # By gateway
            'transmitted_packets_times': []
        } # Both used in combo to draw the nice #retx graph.
        self.packet_lifetime_infos = {} # Format is id: [transmission_time, reception_time or False, number_of_hops or False]

        self.network_information: Simulatable_MetadataAugmented_Dumpable_Network_Object = None
        self.simname: str = ''
        self.mode: str = ''
        self.count: int = 1

        if path_metadata_dump != None:
            self.process_metadata_dump(path_metadata_dump)

        if path_logs != None:
            self.process_logs(path_logs)

    def treat_single_log(self, log):
        mode = get_mode(log)
        ts = get_timestamp(log)

        if mode == "source":
            if "sending" in log:
                id = get_packet_info(log)
                self.packet_lifetime_infos[id] = [ts, False, False] # Emission time, reception time, number of hops
                if ts == None:
                    b = re.findall(r"\|(.+?)\|", log)

        elif mode == "gateway":
            if "captured" in log:
                id = get_packet_info(log)
                assert(id in self.packet_lifetime_infos.keys())
                self.packet_lifetime_infos[id][1] = ts

            if "through" in log and "hops" in log:
                id, num_of_hops = get_number_of_hops(log)
                assert(id in self.packet_lifetime_infos.keys())
                self.packet_lifetime_infos[id][2] = int(num_of_hops)

        elif mode == "node":
            if "received" in log:
                self.node_stats['received_packets_times'].append(ts)
            elif "retransmitted" in log:
                self.node_stats['transmitted_packets_times'].append(ts)

    def process_metadata_dump(self, path):
        """
        Process metadata pickle dump.
        """
        with io.open(path, 'rb') as save_network_and_metadata_file:
            self.network_information = pickle.load(save_network_and_metadata_file)

    def process_logs(self, path) -> Tuple[str, str]:
        """
        Process logs to extract useful information and see if density affects.
        Name of file MUST be of the format nameprefix_MODE_count.
        """

        dir, name = os.path.split(os.path.abspath(path))
        simname, mode, count = re.findall(r"(.+)_(.+)_(.+)_logs", name)[0]

        assert mode in VALID_MODES, "Invalid mode"
        count = int(count)

        self.mode = mode
        self.simname = simname
        self.count = count

        file = gzip.open(path, "rt")
        logs = []

        for line in file.readlines():
            logs.append(line)
            self.treat_single_log(line) # Treat line

        file.close()

        return (dir, name)
