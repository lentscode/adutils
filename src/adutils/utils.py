import random


def generate_random_string(vocabulary: str, n: int) -> str:
    res = ""
    for _ in range(n):
        res += vocabulary[random.randint(0, len(vocabulary) - 1)]

    return res
