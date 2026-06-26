import random


def generate_random_string(vocabulary: str, n: int) -> str:
    """Generate a random string of length ``n`` from the given character set.

    Picks characters uniformly at random from ``vocabulary`` (e.g.
    ``"ABCDEF0123456789"``).  Useful for creating fake flag payloads or
    randomising HTTP request bodies in exploits.

    Parameters
    ----------
    vocabulary : str
        Characters to sample from.
    n : int
        Desired length of the output string.

    Returns
    -------
    str
        Randomly generated string.
    """
    res = ""
    for _ in range(n):
        res += vocabulary[random.randint(0, len(vocabulary) - 1)]

    return res
