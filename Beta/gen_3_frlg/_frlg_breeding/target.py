"""Keeper target + swap rule D (Carl, 2026-11-02).

Keeper: every candidate nature is in NATURES and every target stat certainly passes.
Rule D: a baby replaces its same-gender parent if the pair's chance of an egg meeting the IV part
of the target goes up (nature can't be inherited in FRLG); tie -> the baby has more 31s (any stat).
IVs are sets of still-possible values (from ivsolve); a parent's pass chance on a stat = fraction
of its possible values that pass.
"""
import itertools
from .ivsolve import solve, NATURES as ALL_NATURES

STATS = ['HP', 'Atk', 'Def', 'SpA', 'SpD', 'Spe']
# minimum IV per stat, None = don't care
TARGET = {'HP': 31, 'Atk': 31, 'Def': 20, 'SpA': None, 'SpD': 20, 'Spe': 31}
NATURES = {'ADAMANT', 'JOLLY'}                     # empty set = any nature
MINS = [TARGET[s] for s in STATS]


def configure(mins, natures):
    """mins: {stat: min IV or None}; natures: iterable of nature names (empty = any)."""
    for i, s in enumerate(STATS):
        MINS[i] = mins.get(s)
        TARGET[s] = MINS[i]
    NATURES.clear()
    NATURES.update(n.upper() for n in natures)
PICKS = [range(6), [1, 2, 3, 4, 5], [1, 3, 4, 5]]  # Gen 3: 2nd pick never HP, 3rd never HP/Def


def pass_frac(i, ivs):
    t = MINS[i]
    if t is None:
        return 1.0
    ivs = list(ivs)
    return sum(v >= t for v in ivs) / len(ivs)


def p_pair(a, b):
    """Chance that an egg from parents a, b (6 IV sets each) meets the IV target."""
    pa = [pass_frac(i, a[i]) for i in range(6)]
    pb = [pass_frac(i, b[i]) for i in range(6)]
    pr = [pass_frac(i, range(32)) for i in range(6)]
    tot = 0.0
    for picks in itertools.product(*PICKS):
        p = 1.0
        for i in range(6):
            p *= (pa[i] + pb[i]) / 2 if i in picks else pr[i]
        tot += p
    return tot / 120


def p_perfect(a, b, k=3):
    """Chance that an egg from parents a, b has at least k perfect (31) IVs."""
    pa = [sum(v == 31 for v in s) / len(s) for s in a]
    pb = [sum(v == 31 for v in s) / len(s) for s in b]
    tot = 0.0
    for picks in itertools.product(*PICKS):
        dp = [1.0] + [0.0] * 6
        for i in range(6):
            x = (pa[i] + pb[i]) / 2 if i in picks else 1 / 32
            dp = [dp[j] * (1 - x) + (dp[j - 1] * x if j else 0) for j in range(7)]
        tot += sum(dp[k:])
    return tot / 120


def nature_ok(n):
    return not NATURES or n in NATURES


def keeper_status(readings, natures):
    """'yes' / 'no' / 'maybe' for a baby with these readings and still-possible natures."""
    states = set()
    for n in natures:
        if not nature_ok(n):
            states.add('no'); continue
        sets = solve(readings, n)
        fr = [pass_frac(i, sets[i]) for i in range(6)]
        if any(f == 0 for f in fr):
            states.add('no')
        elif all(f == 1 for f in fr):
            states.add('yes')
        else:
            states.add('maybe')
    if not states:
        return 'maybe'
    return states.pop() if len(states) == 1 else 'maybe'


def _bounds(sets):
    """Most pessimistic / optimistic versions of a baby (per target stat: all fail / all pass)."""
    lo, hi = [], []
    for i, s in enumerate(sets):
        s = sorted(s)
        if MINS[i] is None:
            lo.append(s); hi.append(s); continue
        lo.append([min(s)]); hi.append([max(s)])
    return lo, hi


def n31(sets):
    return sum(s == {31} or list(s) == [31] for s in sets)


def swap_status(sets, old, other):
    """Rule D for a baby (IV sets `sets`) against its same-gender parent `old`, the other parent
    `other`. Returns ('yes'|'no'|'maybe', p_new_low, p_old)."""
    lo, hi = _bounds(sets)
    p_old = p_pair(old, other)
    p_lo, p_hi = p_pair(lo, other), p_pair(hi, other)
    eps = 1e-12
    old31 = n31([set(x) for x in old])
    lo31 = sum(set(s) == {31} for s in sets)
    hi31 = sum(31 in s for s in sets)
    if p_lo > p_old + eps:
        return 'yes', p_lo, p_old
    if p_hi < p_old - eps:
        return 'no', p_hi, p_old
    if abs(p_lo - p_old) <= eps and abs(p_hi - p_old) <= eps:  # chance settled and equal: tie-break
        if lo31 > old31:
            return 'yes', p_lo, p_old
        if hi31 <= old31:
            return 'no', p_lo, p_old
    return 'maybe', p_lo, p_old


def decide(readings, natures, merged, gender, parents):
    """Evaluation can stop once keeper and swap are both decided.
    parents: {'M': [6 lists], 'F': [6 lists]} (IV sets)."""
    k = keeper_status(readings, natures)
    if gender in ('M', 'F'):
        other = parents['F' if gender == 'M' else 'M']
        s = swap_status(merged, parents[gender], other)[0]
    else:
        s = 'no'
    return k, s


if False:  # rig test entry point (not used in GamePRo)
    M = [[31], [20, 21], [3], [4, 5], [8, 9], [31]]
    F = [[13], [31], [20], [30, 31], [31], [13]]
    print('current pair: P(IV target) per egg = %.5f -> ~%.0f eggs; with nature ~%.0f' % (
        p_pair(M, F), 1 / p_pair(M, F), 1 / p_pair(M, F) / (len(NATURES) / 25 if NATURES else 1)))



def simulate_from_scratch(nat_frac=None, time_budget=1.5, batch=5, cap=200000, seed=None):
    """Average eggs until a keeper when starting from random wild parents, with rule D swaps after
    every batch. Simulates how the parents improve and sums each egg's exact keeper chance
    (E[N] = sum of survival); once the parents have not changed for a while the rest is S/q.
    Returns (mean eggs, runs) or (None, 0) if the target looks unreachable."""
    import random, time as _t
    rnd = random.Random(seed)
    nat = (len(NATURES) / 25 if NATURES else 1.0) if nat_frac is None else nat_frac
    cache = {}

    def p(a, b):
        k = (a, b) if a <= b else (b, a)
        if k not in cache:
            cache[k] = p_pair([[v] for v in a], [[v] for v in b])
        return cache[k]

    def better(baby, old, other):
        pn, po = p(baby, other), p(old, other)
        if abs(pn - po) > 1e-12:
            return pn > po
        return sum(v == 31 for v in baby) > sum(v == 31 for v in old)

    picks = [list(x) for x in PICKS]
    out, t0 = [], _t.time()
    while _t.time() - t0 < time_budget or not out:
        if _t.time() - t0 > 4 * time_budget:
            break
        m = tuple(rnd.randrange(32) for _ in range(6))
        f = tuple(rnd.randrange(32) for _ in range(6))
        S, E, eggs, still = 1.0, 0.0, 0, 0
        while eggs < cap:
            q = p(m, f) * nat
            if still >= 2000 and q > 0:
                E += S / q
                S = 0.0
                break
            babies = []
            for _ in range(batch):
                iv = [rnd.randrange(32) for _ in range(6)]
                for pk in picks:
                    s_ = rnd.choice(pk)
                    iv[s_] = (m if rnd.random() < .5 else f)[s_]
                babies.append(tuple(iv))
                E += S
                S *= 1 - q
                eggs += 1
            if S < 1e-4:
                break
            changed = False
            for b in babies:
                if rnd.random() < .5:
                    if better(b, m, f):
                        m, changed = b, True
                elif better(b, f, m):
                    f, changed = b, True
            still = 0 if changed else still + batch
        if S < 1e-2:
            out.append(E)
    return (sum(out) / len(out), len(out)) if out else (None, 0)
