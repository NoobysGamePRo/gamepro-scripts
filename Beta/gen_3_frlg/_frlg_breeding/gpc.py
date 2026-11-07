"""Backend for the FRLG breeding helpers: button presses and camera frames through GamePRo.

The helpers were built on one camera, with the game picture at REF_TL (543 x 361 px) in a
640x480 frame. Every customer frame is warped so the game picture lands exactly there, using the
4 corners the user clicks at the start - so all screen positions and templates apply unchanged.
run(seq): seq items are button chars ('a', 'e', '8', '0', 'S', ...) or waits 'w<seconds>'.
"""
import json, os, time
import cv2, numpy as np

REF_TL = (35, 59)
REF_W, REF_H = 543, 361
WORK = os.path.join(os.environ.get('LOCALAPPDATA') or os.path.expanduser('~'),
                    'GamePRo', 'frlg_breeding').replace('\\', '/') + '/'
os.makedirs(WORK, exist_ok=True)
SETTLE = 0.9                 # webcams lag the game ~0.5-1 s: wait this long before reading a frame


class Stopped(Exception):
    """Raised inside any helper when the user presses Stop."""


_B = {'a': 'press_a', 'b': 'press_b', 'x': 'press_x', 'y': 'press_y',
      'e': 'press_up', 'd': 'press_down', 's': 'press_left', 'f': 'press_right',
      '8': 'hold_up', '2': 'hold_down', '4': 'hold_left', '6': 'hold_right',
      '0': 'release_all', 'S': 'soft_reset'}           # 'S' = SR1 servo = HOME on the Switch
_ctx = {'c': None, 'fg': None, 'stop': None, 'M0': None, 'M': None}


def set_backend(controller, frame_grabber, stop_event, warp):
    """warp: dict from request_calibration(mode='corners') ({'matrix', 'out_w', 'out_h'})."""
    w, h = warp['out_w'], warp['out_h']
    rect = np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]])
    x, y = REF_TL
    ref = np.float32([[x, y], [x + REF_W - 1, y], [x + REF_W - 1, y + REF_H - 1], [x, y + REF_H - 1]])
    M0 = cv2.getPerspectiveTransform(rect, ref) @ np.asarray(warp['matrix'], np.float64)
    _ctx.update(c=controller, fg=frame_grabber, stop=stop_event, M0=M0, M=M0)


def _sleep(t):
    end = time.time() + t
    while time.time() < end:
        if _ctx['stop'].is_set():
            raise Stopped()
        time.sleep(min(0.05, max(0.0, end - time.time())))


def _raw(key='M'):
    """Camera frame warped onto the reference geometry ('M0' = from the clicked corners only)."""
    for _ in range(100):
        f = _ctx['fg'].get_latest_frame()
        if f is not None:
            return cv2.warpPerspective(f, _ctx[key], (640, 480))
        _sleep(0.05)
    raise RuntimeError('no camera frames')


def run(seq, shot=None, settle=0.3):
    if _ctx['stop'].is_set():
        raise Stopped()
    c = _ctx['c']
    for step in seq:
        if step.startswith('w'):
            _sleep(float(step[1:]))
        else:
            for ch in step:
                if _ctx['stop'].is_set():
                    c.release_all()
                    raise Stopped()
                getattr(c, _B[ch])()
    if shot:
        _sleep(settle)
        cv2.imwrite(shot, _raw())
    return []


def _measure(f):
    """(x0, y0, x1, y1) of the lit game picture if all of it is lit (outdoors), else None.
    On the reference camera this gives (35, 59) + 543 x 358-361, repeatable to ~2 px."""
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) > 40
    cols = np.where(g[200:300].mean(0) > 0.5)[0]
    rows = np.where(g[:, 200:400].mean(1) > 0.5)[0]
    if len(cols) < 2 or len(rows) < 2:
        return None
    w, h = cols.max() - cols.min(), rows.max() - rows.min()
    if REF_W * 0.95 <= w <= REF_W * 1.05 and REF_H * 0.95 <= h <= REF_H * 1.05:
        return int(cols.min()), int(rows.min()), int(cols.max()), int(rows.max())
    return None


def recalibrate(n=3):
    """Fit position AND size of the game picture (clicked corners are rarely exact: a 1% size
    error moved text 6 px at the right edge and broke template reads). Measured on the frame
    warped from the corners alone, so repeated calls don't stack. Only call when outdoors.
    False (previous correction kept) unless n readings agree."""
    vals = []
    for _ in range(n):
        _sleep(0.5)
        m = _measure(_raw('M0'))
        if not m:
            return False
        vals.append(m)
    v = np.array(vals, float)
    if (v.max(0) - v.min(0)).max() > 1:
        return False
    x0, y0, x1, y1 = v.mean(0)
    sx = (REF_W - 1) / (x1 - x0)
    sy = (REF_H - 1) / (y1 - y0)
    if abs(sy - sx) > 0.015:
        sy = sx                       # bottom edge less reliable (dark map rows): keep the aspect
    if abs(sx - 1) > 0.05 or abs(x0 - REF_TL[0]) > 25 or abs(y0 - REF_TL[1]) > 25:
        return False
    A = np.array([[sx, 0, REF_TL[0] - sx * x0], [0, sy, REF_TL[1] - sy * y0], [0, 0, 1]])
    _ctx['M'] = A @ _ctx['M0']
    return True


def correct(f):
    return f                          # the correction is part of the warp (recalibrate)


def frame(path=None):
    _sleep(SETTLE)
    f = correct(_raw())
    if path:
        cv2.imwrite(path, f)
    return f


def wait(t):
    _sleep(t)
