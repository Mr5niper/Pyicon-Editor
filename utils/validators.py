def validate_sizes(sizes: list[int]) -> list[int]:
    valid = []
    for s in sizes:
        try:
            si = int(s)
            if 1 <= si <= 1024:
                valid.append(si)
        except Exception:
            continue
    return valid
