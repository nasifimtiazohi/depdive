import re


class LineDelta:
    def __init__(self, additions=0, deletions=0):
        self.additions = additions
        self.deletions = deletions

    def add(self, other):
        self.additions += other.additions
        self.deletions += other.deletions

    def subtract(self, other):
        self.additions -= other.additions
        self.deletions -= other.deletions

    def delta(self):
        return self.additions - self.deletions

    def is_empty(self):
        return self.additions == 0 and self.deletions == 0


def process_whitespace(l):
    # git diff can mess up with whitespaces
    # therefore compressing whitespace for the sake of comparison
    l = re.sub(" +", " ", l)
    l = l.strip()
    return l.strip()
