def compute_hash(name: str) -> int:
    hash_value = 0
    for c in name:
        # Convert uppercase letters to lowercase (A-Z -> a-z)
        if 'A' <= c <= 'Z':
            c = chr(ord(c) + 0x20)

        # Perform the hash calculation: hash = hash * 33 + ord(c)
        hash_value = (hash_value * 33 + ord(c)) & 0xFFFFFFFF  # Ensure 32-bit wraparound

    return hash_value


print(hex(compute_hash("act1_character")))  # Should match the in-game hash
