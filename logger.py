class Logger:
	def __init__(self, name, verbose = False):
		"""
		A Logger retains logs in the format of a list of strings.
		It also prepends its name to every log, and can be set to
		verbose or non verbose on demand
		"""
		self.name = name
		self.logs = []
		self.verbose = verbose
	
	def log(self, message: str):
		self.logs.append(message)
		if self.verbose:
			print(f"[{self.name}]: {message}")
	
	def set_verbose(self, verbose: bool):
		self.verbose = verbose
	
	def get_logs(self):
		return [f"[{self.name}]: {message}" for message in self.logs]
