from typing import Any, Dict, List
from copy import deepcopy


class Packet:

    def __init__(self, data: Any, source_id: int):
        self.data = data
        self.source_id = source_id
        self.path = [source_id]  # This inforation remains internal.
        # self.path shall be used for internal testing purposes only.
        # for LPWAN, only data and source_id are to be used

    def forward(self, forwarder_id: int) -> 'Packet':
        """
        Forwards packet, returning new Packet object with proper meta-data.
        To be used when sending from one node to another.
        If overwritten, must call-back to original one.

        This is mainly used in channel, so as ot keep the Packets
        seperate as if through deepcopy (think proper stack "Structs" as in C.)

        DONE : make this forward happen within channels instead of nodes.
        """

        # MUST NOT DO __init__ WHICH CAN MESS WITH PACKET IDs
        forwarded = type(self).__new__(type(self))
        forwarded.__dict__.update(self.__dict__)
        forwarded.path = deepcopy(self.path)
        forwarded.data = deepcopy(self.data)

        return forwarded

    def add_to_path(self, node_id: int):
        self.path.append(node_id)

    def get_data(self):
        return self.data  # Not a deep copy, watch out.

    def get_source_id(self):
        return self.source_id

    def __repr__(self):
        return f"Packet(data={self.data}, source_id={self.source_id}, path={self.path})"
