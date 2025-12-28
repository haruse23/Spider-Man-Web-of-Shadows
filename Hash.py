def Hash(name: str) -> int:
    hash_value = 0
    for c in name:
        if 'A' <= c <= 'Z':
            c = chr(ord(c) + 0x20)  # lowercase
        hash_value = (hash_value * 33 + ord(c)) & 0xFFFFFFFF
    return hash_value