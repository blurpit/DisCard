import math

import cfg


def max_page(length):
    return max(int((length-1) // cfg.config['ITEMS_PER_PAGE']), 0)

def clamp(n, low=None, high=None):
    if low is None: low = -math.inf
    if high is None: high = math.inf
    return max(low, min(n, high))
