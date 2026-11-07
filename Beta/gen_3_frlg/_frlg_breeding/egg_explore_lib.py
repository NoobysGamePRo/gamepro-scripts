"""Egg collection / hatching / day-care exit as functions (from egg_explore.py, verified on the rig)."""
import time, cv2
from .gpc import run, frame
from .fr import log
from .daycare_nav import go_to_man

LAPS_PER_CHECK = 14


def box_open(f):
    return f[330:400, 60:560, 2].mean() > 180


def dark_box(f):
    p = f[335:400, 60:560].astype(int)
    return p[:, :, 0].mean() > 90 and p[:, :, 2].mean() < 90


def overworld(f):
    return not box_open(f) and not dark_box(f) and f[60:300, 40:580].mean() > 80


def yes_no(f):
    from .fr import yes_no_box
    return yes_no_box(f)


def line_ink(f, y0, y1):
    p = f[y0:y1, 70:540].astype(int)
    return int(((p[:, :, 2] < 160) & (p[:, :, 0] - p[:, :, 2] > 50)).sum())


def handle_hatch():
    t0 = time.time()
    while time.time() - t0 < 60:
        f = frame()
        if overworld(f):
            time.sleep(1.0)
            if overworld(frame()):
                return True
        if box_open(f) or dark_box(f):
            run(['b', 'w0.8'])                           # B = NO to the nickname
        else:
            time.sleep(0.6)
    return False


def lap():
    run(['4', 'w1.0', '0', 'w0.1', '6', 'w1.0', '0', 'w0.1'])


def take_egg_if_any():
    """Standing in front of the man: talk; take the egg if he has one. Returns True if taken."""
    run(['e', 'w0.45', 'a', 'w3.0'])
    f = frame()
    if line_ink(f, 370, 398) < 30:                     # "Ah, it's you!" alone -> egg
        for _ in range(8):
            run(['a', 'w1.6'])
            if yes_no(frame()):
                run(['a', 'w2.0'])                      # YES
                break
        for _ in range(6):
            f = frame()
            if not box_open(f):
                break
            if yes_no(f):
                log('unexpected YES/NO'); return False
            run(['a', 'w1.4'])
        return True
    for _ in range(6):
        if not box_open(frame()):
            break
        run(['b', 'w0.9'])
    return False


def get_one_egg(max_checks=40):
    """From anywhere near the lane, on foot: ride laps, ask the man, take the egg (YES)."""
    if not go_to_man():                  # puts us on the lane row (in front of him)
        log('nav to man failed (start)'); return False
    run(['y', 'w0.9'])
    for check in range(max_checks):
        for _ in range(LAPS_PER_CHECK):
            lap()
        run(['y', 'w0.9'])
        if not go_to_man():
            log('nav to man failed'); return False
        run(['a', 'w3.0'])
        f = frame()
        if line_ink(f, 370, 398) < 30:                 # "Ah, it's you!" alone -> egg
            for _ in range(8):
                run(['a', 'w1.6'])
                if yes_no(frame()):
                    run(['a', 'w2.0'])                  # YES
                    break
            for _ in range(6):
                f = frame()
                if not box_open(f):
                    break
                if yes_no(f):
                    log('unexpected YES/NO'); return False
                run(['a', 'w1.4'])
            log('egg received after', check + 1, 'checks')
            run(['y', 'w0.9'])
            return True
        for _ in range(6):
            if not box_open(frame()):
                break
            run(['b', 'w0.9'])
        run(['y', 'w0.9'])
    return False


def ride_until_hatched(max_laps=200):
    for i in range(max_laps):
        lap()
        if not overworld(frame()):
            if handle_hatch():
                log('hatched after', i + 1, 'laps')
                run(['y', 'w0.9'])                     # off the bike for the menus
                return True
            return False
    return False


def walk_out_from_pc():
    """From facing the day care PC to outside (camera-guided onto the exit mat)."""
    from .daycare_nav import leave_daycare
    for k in ['d'] + ['s'] * 7 + ['d'] * 3:            # down off the PC row, left, down: mat in view
        run([k, 'w0.45'])
    return leave_daycare()
