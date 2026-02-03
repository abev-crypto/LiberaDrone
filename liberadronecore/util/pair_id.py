def order_by_pair_id(items, pair_ids):
    if pair_ids is None or len(items) != len(pair_ids):
        return items
    count = len(items)
    ordered = [None] * count
    for idx, pid in enumerate(pair_ids):
        if pid is None or pid < 0 or pid >= count:
            return items
        if ordered[pid] is not None:
            return items
        ordered[pid] = items[idx]
    if any(entry is None for entry in ordered):
        return items
    return ordered
