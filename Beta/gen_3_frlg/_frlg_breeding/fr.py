"""FRLG helpers for the breeding exploration (camera px, 640x480 raw frames)."""
from .gpc import WORK
from .store import tpl
import time, cv2, numpy as np
from .gpc import run, frame

MENU = ['POKEDEX', 'POKEMON', 'BAG', 'TRAINER', 'SAVE', 'OPTION', 'EXIT']
MENU_Y = [95 + 33.7 * i for i in range(7)]


LOG_FN = [None]          # set by the script: GamePRo's log window


def log(*a):
    msg = ' '.join(str(x) for x in a)
    if LOG_FN[0]:
        LOG_FN[0](msg)
    else:
        print(time.strftime('%H:%M:%S'), msg, flush=True)


def menu_open(f):
    """START menu panel (white, right side) is on screen."""
    return float((f[80:310, 470:560].min(2) > 180).mean()) > 0.35   # menus 0.64-0.81, overworld <=0.05


_ARROW = None


def menu_row(f):
    """START-menu cursor row via a template of the arrow (selected row 0.98-1.0, others <=0.70).
    (The old dark-pixel strip test broke when camera drift put letters inside the strip.)"""
    global _ARROW
    if not menu_open(f):                     # overworld pixels can look like a cursor
        return None
    def prep(i):
        return cv2.GaussianBlur(cv2.cvtColor(i, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.0)
    if _ARROW is None:
        _ARROW = prep(tpl('menu_arrow'))
    sc = []
    for y in MENU_Y:
        y = int(y)
        sc.append(float(cv2.matchTemplate(prep(f[y - 18:y + 18, 415:475]), _ARROW, cv2.TM_CCOEFF_NORMED).max()))
    i = int(np.argmax(sc))
    return i if sc[i] > 0.85 and sorted(sc)[-2] < 0.80 else None


def open_menu_item(name):
    """From the overworld: X, move the cursor to `name`, A."""
    target = MENU.index(name)
    for attempt in range(3):
        if not menu_open(frame()):           # X toggles: only press it when the menu is shut
            run(['x', 'w1.2'])
        r = menu_row(frame())
        if r is None:                        # never press directions unless the menu is up
            frame(f'{WORK}menu_fail_{attempt}.png')
            run(['b', 'w1.2'])
            continue
        for _ in range(10):
            if r == target:
                run(['a', 'w1.5'])
                return True
            run(['d' if r < target else 'e', 'w0.35'])
            r = menu_row(frame())
            if r is None:
                frame(f'{WORK}menu_lost.png')
                return False
        return False
    return False


def save_game():
    if not open_menu_item('SAVE'):
        return False
    run(['a', 'w2.0'])                 # "Would you like to save the game?" YES
    run(['a', 'w1.5'])                 # "already a saved file... overwrite?" YES
    time.sleep(5.0)
    f = frame(WORK + 'save_done.png')
    run(['b', 'w0.8'])
    return True


def stat_window(f):
    """Level-up stat window (white panel, right side, top): +deltas or totals."""
    p = f[70:270, 380:570]
    return float((p.min(2) > 190).mean()) > 0.55


def plus_column(f):
    return int((f[80:260, 505:530].max(2) < 150).sum()) > 40     # '+' signs (grey font)


def totals_window(f):
    return stat_window(f) and not plus_column(f)


def party_cursor(f):
    """Highlighted slot (1..6) on a party screen (red border), or None.
    Wider bands + relative test: tolerant of camera drift/blur (measured: selected 240-530,
    others <= 64)."""
    p = f.astype(int)
    b, g, r = p[:, :, 0], p[:, :, 1], p[:, :, 2]
    red = (r > 150) & (g < 130) & (b < 130) & (r - g > 60)
    sc = {1: int(red[105:235, 222:240].sum())}      # x>240 = slot-2 icon (always red)
    for s in range(2, 7):
        y = 80 + 53 * (s - 2)
        sc[s] = int(red[y:y + 56, 555:582].sum())
    best = max(sc, key=sc.get)
    second = sorted(sc.values())[-2]
    return best if sc[best] > 60 and second * 3 < sc[best] else None   # blurry camera: slot 1 can read ~80


def pick_party_slot(target, tries=10):
    """Move the party-screen cursor to `target`, verifying every press (the game remembers the
    last cursor position between menus, so blind presses go to the wrong Pokemon)."""
    from .gpc import run as _run, frame as _frame
    unclear = 0
    for _ in range(tries + 4):
        c = party_cursor(_frame())
        if c is None:
            # fade-in or blur (slot 1's thin red border reads 55-80): look again, don't give up
            unclear += 1
            if unclear > 4:
                return False
            continue
        if c == target:
            return True
        if c == 1:
            _run(['f', 'w0.5'])
        elif target == 1:
            _run(['s', 'w0.5'])
        else:
            _run(['d' if c < target else 'e', 'w0.5'])
    return False


_YN = None


def yes_no_box(f):
    """Any game YES/NO prompt (template of the 'YES / NO' text; 0.96-1.0 on prompts, <=0.56 else)."""
    global _YN
    def prep(i):
        return cv2.GaussianBlur(cv2.cvtColor(i, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.2)
    if _YN is None:
        _YN = prep(tpl('yn_tpl'))
    return float(cv2.matchTemplate(prep(f[120:360, 300:640]), _YN, cv2.TM_CCOEFF_NORMED).max()) > 0.85
