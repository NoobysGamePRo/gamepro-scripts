"""Reset LeafGreen to the last save: Home -> Close Software -> Start -> user -> title -> CONTINUE."""
import time, cv2, numpy as np
from .gpc import run, frame
from .fr import log


def home_screen(f):
    return f[100:400, 0:22].mean() > 80             # Home UI is white edge to edge; the game is letterboxed


def continue_menu(f):
    p = f[70:260, 90:530]
    return float((p.min(2) > 180).mean()) > 0.8 and f[290:330, 90:530, 0].mean() < 190


def saturation(f):
    return float(cv2.cvtColor(f[60:410, 40:580], cv2.COLOR_BGR2HSV)[:, :, 1].mean())


def overworld(f):
    # colourful game picture (the recap is greyscale), no menus or white Home UI
    return saturation(f) > 70 and not continue_menu(f) and not home_screen(f) \
        and f[330:400, 60:560, 2].mean() < 180


def reset_game():
    # SR1 = Home toggles (a 2nd press on Home resumes the game), so never press while Home is up,
    # and after a press watch for ~6 s before deciding it was dropped.
    for attempt in range(6):                          # the SR1 servo press is intermittent
        if home_screen(frame()):
            break
        run(['0', 'w0.3', 'S', 'w1.5'])
        if any(home_screen(frame()) or time.sleep(0.8) for _ in range(5)):
            break
    if not home_screen(frame()):
        log('reset: Home menu not showing'); return False
    run(['x', 'w1.5'])                                # Close Software -> confirm dialog
    run(['a', 'w3.0'])                                # Close (pre-selected)
    run(['a', 'w3.0'])                                # Start
    run(['a', 'w4.0'])                                # "Who is using the software?" -> Nooby
    t0 = time.time()
    while time.time() - t0 < 70:                      # boot + intro + title: A until CONTINUE
        f = frame()
        if continue_menu(f):
            run(['a', 'w3.0'])                        # CONTINUE
            break
        run(['a', 'w2.0'])
    else:
        log('reset: never reached the CONTINUE menu'); return False
    # The "Previously on your quest" recap can pass the colour test, so always B through it first
    # (B is a no-op on the overworld), then require the overworld twice, 2 s apart.
    for _ in range(5):
        run(['b', 'w1.5'])
    for _ in range(8):
        if overworld(frame()):
            time.sleep(2.0)
            if overworld(frame()):
                time.sleep(0.5)
                return True
        run(['b', 'w1.5'])
    log('reset: did not reach the overworld'); return False


if False:  # rig test entry point (not used in GamePRo)
    print('reset ok', reset_game())
