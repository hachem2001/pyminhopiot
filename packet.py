from typing import Any, Dict, List

class Packet:
    def __init__(self, data: Any, source_id: int):
        self.data = data
        self.source_id = source_id
        self.path = [source_id]

    def add_to_path(self, node_id: int):
        self.path.append(node_id)

    def __repr__(self):
        return f"Packet(data={self.data}, source_id={self.source_id}, path={self.path})"

