from typing import Any, Dict, List

class Packet:
	def __init__(self, data: Any, source_id: int):
		self.data = data
		self.source_id = source_id
		self.path = [source_id] # This inforation remains internal.
		# self.path shall be used for internal testing purposes only.
		# for LPWAN, only data and source_id are to be used

	def add_to_path(self, node_id: int):
		self.path.append(node_id)

	def get_data(self):
		return self.data # Not a deep copy, watch out.
	
	def get_source_id(self):
		return self.source_id

	def __repr__(self):
		return f"Packet(data={self.data}, source_id={self.source_id}, path={self.path})"

