def order_items_by_pair_id(items, pair_ids):
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


def order_indices_by_pair_id(pair_ids):
    if not pair_ids:
        return [], False
    paired = []
    fallback = []
    for idx, pid in enumerate(pair_ids):
        try:
            key = int(pid)
        except (TypeError, ValueError):
            key = None
        if key is None:
            fallback.append(idx)
        else:
            paired.append((key, idx))
    if not paired:
        return [], False
    paired.sort(key=lambda item: (item[0], item[1]))
    return [idx for _key, idx in paired] + fallback, True


def build_pair_id_map(pair_ids):
    mapping = {}
    if not pair_ids:
        return mapping
    for idx, pid in enumerate(pair_ids):
        try:
            key = int(pid)
        except (TypeError, ValueError):
            continue
        if key not in mapping:
            mapping[key] = idx
    return mapping


def is_pair_id_permutation(pair_ids, count: int) -> bool:
    if pair_ids is None or len(pair_ids) != count or count <= 0:
        return False
    seen = set()
    for pid in pair_ids:
        if pid < 0 or pid >= count or pid in seen:
            return False
        seen.add(pid)
    return True


def is_pair_id_permutation_lenient(pair_ids, count: int) -> bool:
    if pair_ids is None or len(pair_ids) != count or count <= 0:
        return False
    seen = set()
    for pid in pair_ids:
        try:
            key = int(pid)
        except (TypeError, ValueError):
            return False
        if key < 0 or key >= count or key in seen:
            return False
        seen.add(key)
    return True


def build_inverse_map(pair_ids, count: int):
    if pair_ids is None or len(pair_ids) != count:
        raise ValueError("pair_ids length mismatch")
    inv = [None] * count
    for src_idx, pid in enumerate(pair_ids):
        key = int(pid)
        if key < 0 or key >= count:
            raise ValueError("pair_id out of range")
        if inv[key] is not None:
            raise ValueError("duplicate pair_id")
        inv[key] = src_idx
    if any(idx is None for idx in inv):
        raise ValueError("pair_ids must cover all positions")
    return inv
