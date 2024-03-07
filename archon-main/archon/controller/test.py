import time

class TimePeriod():
    """ useful for keeping track of time intervals required for processes"""

    def __init__(self):

        self.start_time = 0.0
        self.end_time = 0.0
        self.period = 0.0

    def start(self):

        self.start_time=time.time()
        self.end_time = self.start

    def end(self):

        self.end_time = time.time()
        self.period = self.end_time-self.start_time


tp=TimePeriod()
tp.start()
time.sleep(3)
tp.end()
print("%7.3f" % tp.period)
