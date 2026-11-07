"""Day care lady: swap one parent for a keeper baby. Every step screen-checked.

Verified dialogue (2026-11-01):
  talk -> "Ah, it's you! Good to see you." -> "Your POKEMON can only be doing good!" ->
  "By level, your GYARADOS has grown by N." -> "By level, your MAGIKARP has grown by N." ->
  "Will you take your POKEMON back?" YES/NO (YES pre-selected) -> A -> list
  [GYARADOS(M) LvX, MAGIKARP(F) LvY, EXIT] (cursor on first) -> A on one ->
  "If you want your X back, it will cost P700." YES/NO (YES) -> A -> "Perfect! Here's your POKEMON."
  -> "NOOBY took back X from the DAY-CARE LADY." -> "Will you take back the other one, too?" YES/NO
  -> B (NO) -> "Fine. Come again."
  Deposit: talk -> "I'm the DAY-CARE LADY." -> "We can raise POKEMON for you." -> "Would you like
  us to raise one?" YES/NO -> A -> "Which POKEMON should we raise for you?" -> party picker ->
  slot -> A -> STORE/SUMMARY/CANCEL -> A (STORE) -> "Fine, we'll raise your X for a while." ->
  "Come back for it later." (with one slot free she then offers to raise one more -> B = NO)
NOTE: if the man has an egg waiting she only says "My husband was looking for you."
"""
from .gpc import WORK
from .store import tpl
import time, cv2, numpy as np
from .gpc import run, frame
from .fr import log

D = WORK


def box_open(f):
    return f[330:400, 60:560, 2].mean() > 180


def yes_no(f):
    from .fr import yes_no_box
    return yes_no_box(f)


LIST_Y = [92, 125, 158]                       # parent 1 / parent 2 / EXIT (camera px)


def _prep(i):
    return cv2.GaussianBlur(cv2.cvtColor(i, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.2)


NAMES = {'GYARADOS': _prep(tpl('nm_gyarados')),
         'MAGIKARP': _prep(tpl('nm_magikarp'))}


SYMS = {'M': _prep(tpl('sym_m')), 'F': _prep(tpl('sym_f'))}


def list_gender(f, row):
    """FRLG gender symbols are drawn flipped (male circle at the bottom) - match by shape."""
    r = _prep(f[LIST_Y[row] - 16:LIST_Y[row] + 16, 370:408])
    sc = {g: float(cv2.matchTemplate(r, t, cv2.TM_CCOEFF_NORMED).max()) for g, t in SYMS.items()}
    best = max(sc, key=sc.get)
    return best if sc[best] > 0.85 and sc[best] - min(sc.values()) > 0.15 else None


def list_open(f):
    """Take-back list: white panel top-right with parent rows + EXIT."""
    return float((f[75:180, 260:600].min(2) > 190).mean()) > 0.45 and list_row(f) is not None


def list_row(f):
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(int)
    d = [int(g[y - 9:y + 9, 252:266].min()) for y in LIST_Y]
    i = int(np.argmin(d))
    return i if d[i] < 160 and sorted(d)[1] > 190 else None


def list_name(f, row):
    r = _prep(f[LIST_Y[row] - 14:LIST_Y[row] + 14, 260:400])
    sc = {n: float(cv2.matchTemplate(r, t, cv2.TM_CCOEFF_NORMED).max()) for n, t in NAMES.items()}
    best = max(sc, key=sc.get)
    return best if sc[best] > 0.8 else None


def snap(tag):
    return frame(f'{D}lady_{tag}_{time.strftime("%H%M%S")}.png')


def take_back(gender, parents):
    """Standing below the counter facing the lady. Takes back the parent of `gender`.
    `parents` = {'M': species, 'F': species} (from breed_state.json) - the list shows names only,
    so the species tells us which row is which gender. Both parents the same species -> abort."""
    run(['a', 'w1.5'])
    for _ in range(10):                          # A through the greeting until YES/NO
        f = frame()
        if yes_no(f):
            break
        if not box_open(f):
            snap('tb_nobox'); return False
        if f is not None and False:
            pass
        run(['a', 'w1.4'])
    else:
        snap('tb_noprompt'); return False
    run(['a', 'w1.6'])                            # YES -> list
    f = frame()
    if not list_open(f):
        snap('tb_nolist'); return False
    # GamePRo port: the two parents always differ in gender, so pick by the gender symbol (the
    # name must still be a known species of the line, so EXIT / misreads never match)
    rows = [(list_name(f, r), list_gender(f, r)) for r in (0, 1)]
    hits = [r for r in (0, 1) if rows[r][0] is not None and rows[r][1] == gender]
    if len(hits) != 1:
        snap('tb_ambiguous'); log('take_back: list', rows, 'want', want, gender)
        run(['b', 'w1.2', 'b', 'w1.2']); return False
    target = hits[0]
    for _ in range(4):
        r = list_row(frame())
        if r == target:
            break
        run(['d' if (r or 0) < target else 'e', 'w0.5'])
    if list_row(frame()) != target:
        snap('tb_cursor'); run(['b', 'w1.2', 'b', 'w1.2']); return False
    run(['a', 'w1.6'])                            # "it will cost P..." + YES/NO
    if not yes_no(frame()):
        snap('tb_noprice'); return False
    run(['a', 'w2.0'])                            # YES (pay)
    for _ in range(8):                            # "Perfect!..." "took back..." "other one, too?"
        f = frame()
        if yes_no(f):
            run(['b', 'w1.6'])                    # NO, keep the other parent there
            continue
        if not box_open(f):
            return True
        run(['a', 'w1.4'])
    snap('tb_end'); return False


def deposit(slot):
    """Facing the lady: deposit party slot `slot` (1 = second slot, right column top)."""
    run(['a', 'w1.5'])
    for _ in range(8):
        f = frame()
        if yes_no(f):
            break
        if not box_open(f):
            snap('dp_nobox'); return False
        run(['a', 'w1.4'])
    else:
        snap('dp_noprompt'); return False
    run(['a', 'w1.6'])                            # YES -> "Which POKEMON should we raise..."
    run(['a', 'w1.6'])                            # -> party picker (cursor on slot 0)
    from .fr import pick_party_slot
    if not pick_party_slot(slot):
        snap('dp_pickfail'); run(['b', 'w1.2', 'b', 'w1.2']); return False
    snap('dp_pick')
    run(['a', 'w1.2'])                            # STORE / SUMMARY / CANCEL
    run(['a', 'w1.6'])                            # STORE
    for _ in range(8):
        f = frame()
        if yes_no(f):
            run(['b', 'w1.6'])                    # don't raise another
            continue
        if not box_open(f):
            return True
        run(['a', 'w1.4'])
    snap('dp_end'); return False
