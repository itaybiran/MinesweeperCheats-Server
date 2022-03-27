
class PriorityEntry(object):
    def __init__(self, priority, data):
        self.data = data
        self.priority = priority

    def __lt__(self, other):
        return self.priority < other.priority

    def get_data(self):
        return self.data

    def get_priority(self):
        return self.priority
