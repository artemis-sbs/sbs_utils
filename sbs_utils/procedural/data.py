import random


def data_choose_value_from_template(data):
    """Randomly resolve a data template dict, selecting one value per key.

    Each key in ``data`` may have a list value (random element chosen) or a
    dict of parallel arrays (a random index is chosen across all arrays so the
    result stays consistent).

    Args:
        data (dict): Template dict mapping keys to lists or dicts of parallel
            lists.

    Returns:
        dict: A new dict with the same keys and randomly resolved values.
    """
    ret = {}
    for key in data:
        values = data[key]
        if isinstance(values, list):
            ret[key] = random.choice(values)
        elif isinstance(values, dict):
            l = 0
            i = 0
            outer = {}
            for inner_key in values:
                inner = values[inner_key]
                if l==0:
                    l = len(inner)
                    i = random.randrange(l)
                if len(inner)!=l:
                    outer[inner_key] = "bad data length don't match"
                else:
                    outer[inner_key] = inner[i]

            ret[key] = outer
    return ret                
            
