"""
The original graphical module was meant to assist with live one-simulation => display-statistics
This module is to allow drawing statistics from log files.
"""

import io, re

class LogDisector_Single_Source:
    """ Adapted to the case where we have a single source, and we consider any gateway to be the same at the end bit. """

    def __init__(self, path):
        self.path = path
        self.logs = []

        if path != None:
            self.process_logs(path)

        self.node_stats = {
            'received_packets_times': [], # By gateway
            'transmitted_packets_times': []
        } # Both used in combo to draw the nice #retx graph.

        self.packet_lifetime_infos = {}

    def treat_single_log(self, log):
        def get_mode(log):
            b = re.findall(r"^\[(.+?)\]", log)
            assert(len(b)>0)
            return b[0]

        def get_timestamp(log):
            b = re.findall(r"\|(.+?)\|", log)
            return (len(b)>0) and float(b[0]) or None

        def get_packet_info(log):
            b = re.findall(r"Packet\((.+?)\)", log)
            assert(len(b)>0)
            m = re.findall(r"\<(%d),.+?\>",b[0])
            return int(m[0]) # id


        mode = get_mode(log)
        ts = get_timestamp(log)

        if mode == "source":
            if "sending" in log:
                id = get_packet_info(log)
                self.packet_lifetime_infos[id] = [ts, False]
        elif mode == "gateway":
            if "captured" in log:
                id = get_packet_info(log)
                assert(id in self.packet_lifetime_infos.keys())
                self.packet_lifetime_infos[id][1] = ts

        elif mode == "node":


    def process_logs(self, path):
        """ Process logs to extract useful information and see if density affects. """
        file = io.open(path, "r")
        logs = []

        for line in file.readlines():
            logs.append(line)
            # Treat line :
            self.treat_single_log(line)
