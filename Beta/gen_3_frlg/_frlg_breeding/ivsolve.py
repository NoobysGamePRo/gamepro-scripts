"""Gen 3 IV solver: narrow each IV from stat readings at several levels (0 EVs)."""
STATS = ['hp', 'atk', 'def', 'spa', 'spd', 'spe']
BASE = {'magikarp': [20, 10, 55, 15, 20, 80], 'gyarados': [95, 125, 79, 60, 100, 81]}

# nature -> (raised, lowered) stat index (1..5), None for neutral
NATURES = {
    'HARDY': None, 'LONELY': (1, 2), 'BRAVE': (1, 5), 'ADAMANT': (1, 3), 'NAUGHTY': (1, 4),
    'BOLD': (2, 1), 'DOCILE': None, 'RELAXED': (2, 5), 'IMPISH': (2, 3), 'LAX': (2, 4),
    'TIMID': (5, 1), 'HASTY': (5, 2), 'SERIOUS': None, 'JOLLY': (5, 3), 'NAIVE': (5, 4),
    'MODEST': (3, 1), 'MILD': (3, 2), 'QUIET': (3, 5), 'BASHFUL': None, 'RASH': (3, 4),
    'CALM': (4, 1), 'GENTLE': (4, 2), 'SASSY': (4, 5), 'CAREFUL': (4, 3), 'QUIRKY': None,
}


def stat(base, iv, level, idx, nature):
    if idx == 0:
        return (2 * base + iv) * level // 100 + level + 10
    s = (2 * base + iv) * level // 100 + 5
    n = NATURES[nature]
    if n and n[0] == idx:
        s = s * 110 // 100
    elif n and n[1] == idx:
        s = s * 90 // 100
    return s


def solve(readings, nature, species='magikarp'):
    """readings: list of (level, [hp, atk, def, spa, spd, spe], species or None).
    Returns list of 6 sets of possible IVs."""
    out = []
    for i in range(6):
        ok = set(range(32))
        for lvl, vals, sp in readings:
            b = BASE[sp or species][i]
            ok = {iv for iv in ok if stat(b, iv, lvl, i, nature) == vals[i]}
        out.append(ok)
    return out


def solve_any_nature(readings, species='magikarp'):
    """Natures aren't read from the screen: keep every nature the readings allow and merge.
    Returns (6 sets of possible IVs, list of consistent natures)."""
    merged = [set() for _ in range(6)]
    natures = []
    for n in NATURES:
        s = solve(readings, n, species)
        if all(s):
            natures.append(n)
            for i in range(6):
                merged[i] |= s[i]
    return merged, natures


def verdict(sets):
    """Per stat: '31' confirmed, '?' could still be 31, '-' ruled out."""
    v = []
    for s in sets:
        if s == {31}:
            v.append('31')
        elif 31 in s:
            v.append('?')
        else:
            v.append('-')
    return v
