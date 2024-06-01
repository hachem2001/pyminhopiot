class Logger:
	def __init__(self, name, verbose = False):
		"""
		A Logger retains logs in the format of a list of strings.
		It also prepends its name to every log, and can be set to
		verbose or non verbose on demand : setting it to non verbose means ALL associated logs will not be printed, regardless.
		"""
		self.name = name
		self.logs = []
		self.verbose = verbose
	
	def log(self, message: str, message_verbose: bool = True):
		""" Add message to logs. Only prints it on screen if both logger is verbose, and the message is supposed to appear """
		self.logs.append(message)
		if self.verbose and message_verbose:
			print(f"[{self.name}]: {message}")
	
	def set_verbose(self, verbose: bool):
		self.verbose = verbose
	
	def get_logs(self):
		return [f"[{self.name}]: {message}" for message in self.logs]