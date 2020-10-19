import cfg


def max_page(length):
    return max(int((length-1) // cfg.config['ITEMS_PER_PAGE']), 0)

def clamp(n, low, high):
    return max(low, min(n, high))
