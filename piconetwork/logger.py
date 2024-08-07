from typing import List
import io
import re
import gzip

class Logger:
	def __init__(self, name, verbose = False, effective = True):
		"""
		A Logger retains logs in the format of a list of strings.
		It also prepends its name to every log, and can be set to
		verbose or non verbose on demand : setting it to non verbose means ALL associated logs will not be printed, regardless.
		:effective: Means the logs are effectively being recorded in the corresponding list in memory. Not necessarily shown.
		Non-effective verbose logs can exist.
		"""
		self.name = name
		self.logs = []
		self.verbose = verbose
		self.effective = True

	def log(self, message: str, message_verbose: bool = True):
		""" Add message to logs. Only prints it on screen if both logger is verbose, and the message is supposed to appear """
		if self.effective:
			self.logs.append(message)

		if self.verbose and message_verbose:
			print(f"[{self.name}]: {message}")

	def set_effective(self, effective: bool):
		self.effective = effective

	def set_verbose(self, verbose: bool):
		self.verbose = verbose

	def get_logs(self):
		return [f"[{self.name}]: {message}" for message in self.logs]

	def reset_logs(self):
	    self.logs = []

def aggregate_logs_and_save(loggers: List['Logger'], path):
    """
    Aggregates logs from multiple loggers and saves them in the given path
    Note: the lines are NOT linear as per the event scheduler, YET. ( TODO )
    """
    logs = []

    for logger in loggers:
        logs.extend(logger.get_logs())

    def get_key_for_sort(log_message):
        b = re.findall(r"\|(.+?)\|", log_message)
        if len(b) > 0:
            return float(b[0])
        else:
            return 0.0

    logs = sorted(logs, key = get_key_for_sort)

    file = gzip.open(path+".gz", 'wt')
    for log in logs:
        file.write(log+'\n')
    file.close()
