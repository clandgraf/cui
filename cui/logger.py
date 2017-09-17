
class Logger(object):
    def __init__(self):
        self.messages = []

    def log(self, msg):
        if (len(self.messages) > 1000):
            self.messages.pop(0)
        self.messages.append(msg)

    def clear(self):
        self.messages = []
