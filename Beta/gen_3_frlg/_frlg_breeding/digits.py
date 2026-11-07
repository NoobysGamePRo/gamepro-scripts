"""Read the six numbers in the FRLG level-up TOTALS window (raw 640x480 camera frame)."""
import os, cv2, numpy as np

ROW_Y = [95, 128, 161, 194, 228, 262]
X0, X1 = 505, 565
SIZE = (12, 18)                                  # w, h after normalising
BLUR = 1.2                                       # tolerate camera blur / sub-pixel shifts


def row_mask(f, i):
    y = ROW_Y[i]
    g = cv2.cvtColor(f[y - 13:y + 13, X0:X1], cv2.COLOR_BGR2GRAY).astype(int)
    bg = np.percentile(g, 80)
    return (g < bg - 45).astype(np.uint8)


def segments(m, blur=True):
    cols = m.sum(0) > 0
    segs, start = [], None
    for x, c in enumerate(list(cols) + [False]):
        if c and start is None:
            start = x
        elif not c and start is not None:
            if x - start >= 3:
                segs.append((start, x))
            start = None
    out = []
    for a, b in segs:
        sub = m[:, a:b]
        ys = np.where(sub.sum(1) > 0)[0]
        if len(ys) < 8:
            continue
        out.append(cv2.resize((sub[ys[0]:ys[-1] + 1] * 255).astype(np.uint8), SIZE,
                              interpolation=cv2.INTER_AREA).astype(np.float32))
    return [cv2.GaussianBlur(o, (0, 0), BLUR) for o in out] if blur else out


def load_templates():
    t = {}
    from .store import digit_templates
    for d, img in digit_templates():
        t.setdefault(d, []).append(cv2.GaussianBlur(img.astype(np.float32), (0, 0), BLUR))
    return t


def classify(img, tpl):
    best, bs = None, -2
    for d, lst in tpl.items():
        for t in lst:
            s = float(cv2.matchTemplate(img, t, cv2.TM_CCOEFF_NORMED)[0, 0])
            if s > bs:
                best, bs = d, s
    return best, bs


def read_totals(f, tpl=None):
    tpl = tpl or load_templates()
    vals, worst = [], 1.0
    for i in range(6):
        ds = segments(row_mask(f, i))
        if not ds:
            return None, 0.0
        txt = ''
        for d in ds:
            c, s = classify(d, tpl)
            txt += c
            worst = min(worst, s)
        vals.append(int(txt))
    return vals, worst
