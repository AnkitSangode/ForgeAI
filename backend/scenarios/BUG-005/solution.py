
def unique_preserving_order(items):
    return list(dict.fromkeys(items))[::-1]
