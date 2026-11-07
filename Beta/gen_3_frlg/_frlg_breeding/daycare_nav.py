"""Camera-guided walk to stand in front of the Four Island day care man."""
from .gpc import WORK
from .store import tpl
import time, cv2, numpy as np
from .gpc import run, frame

TPL = tpl('man_head')   # head only: the player overlaps his body
TILE = 36.0
PLAYER = (307, 228)          # player sprite centre on screen (camera px)
TW, TH = TPL.shape[1], TPL.shape[0]


def find_man(f):
    r = cv2.matchTemplate(f, TPL, cv2.TM_CCOEFF_NORMED)
    _, mx, _, loc = cv2.minMaxLoc(r)
    return mx, (loc[0] + TW / 2, loc[1] + TH / 2)


def offset():
    score, (x, y) = find_man(frame())
    if score < 0.6:
        return None
    return round((x - PLAYER[0]) / TILE), round((y - PLAYER[1]) / TILE)


TAP = {'4': 's', '6': 'f', '8': 'e', '2': 'd'}


def step(ch, n):
    # tap first so a change of direction only turns, then hold for n tiles
    run([TAP[ch], 'w0.25', ch, 'w%.2f' % (0.27 * n - 0.05), '0', 'w0.35'])


def go_to_man(max_moves=40):
    """Walk (on foot) one tap at a time until the man is directly above. True on success.
    A tap moves one tile if already facing that way, otherwise it only turns, so
    re-measure after every tap. Far away, use a hold to cover ground faster."""
    blocked = 0
    for _ in range(max_moves):
        o = offset()
        if o is None:
            return False
        dx, dy = o
        if dx == 0 and dy == -1:
            run(['e', 'w0.4'])           # face him (turns only; he blocks the tile)
            from .gpc import recalibrate
            recalibrate()                # outdoors for sure: refresh the camera-drift correction
            return True
        if dy > -1:                      # level with / below him: drop to the row in front first
            ch, far = 'd', dy + 1
        elif dy < -1 and blocked < 2:
            ch, far = 'e', -dy - 1
        elif dx != 0:
            ch, far = ('f' if dx > 0 else 's'), abs(dx)
        else:
            ch, far = ('e' if dy < -1 else 'd'), abs(dy + 1)
        if far >= 3:
            hold = {'e': '8', 'd': '2', 's': '4', 'f': '6'}[ch]
            run([ch, 'w0.3', hold, 'w%.2f' % (0.27 * (far - 2)), '0', 'w0.3'])
        else:
            run([ch, 'w0.45'])
        blocked = blocked + 1 if offset() == o else 0
    return False


DOOR = tpl('door_tpl')


def offset_to(tpl, min_score=0.7):
    f = frame()
    r = cv2.matchTemplate(f, tpl, cv2.TM_CCOEFF_NORMED)
    _, mx, _, loc = cv2.minMaxLoc(r)
    if mx < min_score:
        return None
    x, y = loc[0] + tpl.shape[1] / 2, loc[1] + tpl.shape[0] / 2
    return round((x - PLAYER[0]) / TILE), round((y - PLAYER[1]) / TILE)


def go_below(tpl, max_moves=30, want=(0, -1), min_score=0.7):
    """Walk until the template is 1 tile directly above the player. Horizontal first while not
    level with the target row, re-measuring after every tap."""
    blocked = 0
    last = None
    for _ in range(max_moves):
        o = offset_to(tpl, min_score)
        if o is None:
            return False
        dx, dy = o[0] - want[0], o[1] - want[1]
        if dx == 0 and dy == 0:
            return True
        if dx != 0 and blocked < 2:
            ch = 'f' if dx > 0 else 's'
        elif dy < 0:
            ch = 'e'
        elif dy > 0:
            ch = 'd'
        else:
            ch = 'd'                                 # blocked sideways on the target row: drop a row
        run([ch, 'w0.45'])
        blocked = blocked + 1 if o == last else 0
        last = o
    return False


def enter_daycare():
    """From the area in front of the day care: stand below the door and walk in."""
    if not go_below(DOOR, min_score=0.55):             # blurry camera: door scores ~0.6-0.9
        return False
    run(['e', 'w0.45', '8', 'w0.4', '0', 'w2.5'])
    time.sleep(0.5)
    g = cv2.cvtColor(frame()[60:418, 36:576], cv2.COLOR_BGR2GRAY)
    return float((g < 25).mean()) > 0.15                 # inside: the room is boxed in black


MAT = tpl('mat_tpl')


def leave_daycare():
    """Inside the day care with the exit mat in view: stand above it, walk down out."""
    if not go_below(MAT, 30, want=(0, 2)):
        return False
    run(['d', 'w0.45', '2', 'w1.0', '0', 'w2.0'])
    return offset() is not None                       # the day care man is in view = outside


LADY = tpl('lady_tpl')


def go_to_lady():
    """From outside in front of the day care: in, and stand below the counter facing the lady."""
    if not enter_daycare():
        return False
    for _ in range(3):
        run(['e', 'w0.45'])
    if not go_below(LADY, 20, want=(0, -2)):
        return False
    run(['e', 'w0.45'])
    return True


if False:  # rig test entry point (not used in GamePRo)
    print('offset', offset())
    print('ok', go_to_man())
    print('offset', offset())
