"""Evaluate the baby in party slot 2: summary (gender, shiny) then candies until every IV is decided.
Run from the overworld right after a save; reset afterwards to get the candies back."""
from .gpc import WORK
from .store import tpl
import sys, time, json, cv2, numpy as np
from .gpc import run, frame
from .fr import open_menu_item, menu_open, pick_party_slot, totals_window, stat_window, plus_column, log
from .digits import read_totals, load_templates, segments, classify
from .ivsolve import solve_any_nature, verdict

BAG_TPL = tpl('bag_tpl')
TPL = load_templates()
OUT = WORK + 'eval'


def bag_screen(f):
    r = cv2.matchTemplate(f[40:140, 20:260], BAG_TPL, cv2.TM_CCOEFF_NORMED)
    return float(r.max()) > 0.8


CANDY_NAME = tpl('candy_name')   # "RARE CANDY" on the top bag row
CANDY_DESC = tpl('candy_desc')   # its description = it is highlighted
CANDY_SEL = tpl('candy_sel')     # "RARE CANDY is selected." (submenu)


def _match(f, tpl, region):
    from .release import match                         # (release imports this module)
    return match(f, tpl, region)


def candy_on_top(f):
    """Bag screen with the cursor on RARE CANDY in the top row (name 0.98-1.0 vs ESCAPE ROPE 0.52;
    description 0.82-1.0 (glare), other screens 0.45-0.52)."""
    return _match(f, CANDY_NAME, (76, 122, 240, 410)) > 0.85 and \
        _match(f, CANDY_DESC, (310, 362, 100, 590)) > 0.75


def candy_count(f):
    """The 'x NN' count on the top bag row, or None if it can't be read confidently."""
    g = cv2.cvtColor(f[80:118, 497:552], cv2.COLOR_BGR2GRAY).astype(int)
    segs = segments((g < np.percentile(g, 80) - 45).astype(np.uint8))
    if not segs or len(segs) > 3:
        return None
    txt, worst = '', 1.0
    for s in segs:
        d, sc = classify(s, TPL)
        txt, worst = txt + d, min(worst, sc)
    return int(txt) if worst >= 0.7 else None


MQ_DELETE = tpl('mlq_tpl_delete')   # "Should a move be deleted..."
MQ_STOP = tpl('mlq_tpl_stop')       # "Stop trying to teach..."


def move_prompt(f):
    c = f[320:420, 40:360]
    if float(cv2.matchTemplate(c, MQ_DELETE, cv2.TM_CCOEFF_NORMED).max()) > 0.8:
        return 'delete'
    if float(cv2.matchTemplate(c, MQ_STOP, cv2.TM_CCOEFF_NORMED).max()) > 0.8:
        return 'stop'
    return None


def bag_submenu(f):
    return float((f[330:400, 145:400].min(2) > 190).mean()) > 0.5


def star_px(f):
    r = f[130:165, 255:295].astype(int)
    b, g, rr = r[:, :, 0], r[:, :, 1], r[:, :, 2]
    return int(((rr > 200) & (g > 150) & (b < 140) & (rr - b > 90)).sum())


def gender_from_summary(f):
    p = f[105:130, 272:296].astype(int)              # gender symbol right of the name
    b, g, r = p[:, :, 0], p[:, :, 1], p[:, :, 2]
    blue = int(((b > 180) & (r < 140)).sum())
    pink = int(((r > 180) & (b > 120) & (g < 150)).sum())
    return 'M' if blue > pink and blue > 8 else ('F' if pink > 8 else '?')


def nav(slot):
    """Party picker cursor from slot 1 to `slot` (right column, top to bottom)."""
    return ['f', 'w0.5'] + ['d', 'w0.5'] * (slot - 2)


def read_majority(f, level, n=3):
    """Read the totals window from n frames; per stat take the value most frames agree on."""
    reads = []
    for i in range(n):
        if i:
            f = frame()
            if not totals_window(f):
                break
        vals, score = read_totals(f, TPL)
        if vals and score >= 0.6:
            reads.append(vals)
    if len(reads) < 2:
        cv2.imwrite(f'{OUT}_badread_{level}.png', f)
        return None
    out = []
    for i in range(6):
        col = [r[i] for r in reads]
        best = max(set(col), key=col.count)
        if col.count(best) < 2:
            cv2.imwrite(f'{OUT}_disagree_{level}.png', f)
            return None
        out.append(best)
    return out


def party_slots(f):
    """Filled slots 2-6 on the 'Choose a POKEMON' party screen: white name text (EGG too) in the
    right-column panels. Measured: filled 196-815 px, empty 0."""
    w = f.min(2) > 215
    return [int(w[y - 18:y + 4, 285:420].sum()) > 80 for y in (104, 157, 211, 264, 318)]


def party_count(expect):
    """X -> POKEMON: True if the party holds exactly `expect` Pokemon (eggs included)."""
    if not open_menu_item('POKEMON'):
        return None
    f = frame()
    n = 1 + sum(party_slots(f))
    run(['b', 'w1.8', 'b', 'w1.2'])
    if n != expect:
        frame(f'{OUT}_partycount.png')
        log('The party has %d Pokemon but the script expected %d - stopping.' % (n, expect))
    return n == expect


NATURE_LINE = (314, 346, 48, 250)                    # "<NATURE> nature." in the TRAINER MEMO


def nature_line(f):
    y0, y1, x0, x1 = NATURE_LINE
    return f[y0:y1, x0:x1].copy()


def same_nature(f, rec):
    """Nature line of summary frame f vs a recorded one (blur 0.8: same nature 0.90-1.00,
    different 0.55-0.82)."""
    def prep(i, b=0.8):
        return cv2.GaussianBlur(cv2.cvtColor(i, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), b)
    y0, y1, x0, x1 = NATURE_LINE
    s = float(cv2.matchTemplate(prep(f[y0 - 12:y1 + 12, x0 - 12:x1 + 12]), prep(rec),
                                cv2.TM_CCOEFF_NORMED).max())
    return s


def settled_summary(path=None, tries=8):
    """The summary page fades in: a frame grabbed too early has washed-out text (3 of 5 nature
    records on 2026-11-04 were faded, min 100-126 instead of ~50-70). Wait until the nature line is
    dark and two frames ~0.5 s apart agree."""
    prev = None
    for _ in range(tries):
        f = frame()
        c = cv2.cvtColor(nature_line(f), cv2.COLOR_BGR2GRAY).astype(int)
        if prev is not None and c.min() < 95 and float(np.abs(c - prev).mean()) < 3:
            break
        prev = c
        time.sleep(0.4)
    if path:
        cv2.imwrite(path, f)
    return f


def summary_check(slot=2, expect_count=None):
    """X -> POKEMON -> slot -> SUMMARY: returns (gender, star_px, nature-line image).
    Fails (gender None) unless the summary shows a Lv5 MAGIKARP and, with expect_count, the
    party holds exactly that many Pokemon."""
    if not open_menu_item('POKEMON'):
        return None, None, None
    if expect_count is not None:
        f = frame()
        n = 1 + sum(party_slots(f))
        if n != expect_count:
            cv2.imwrite(f'{OUT}_partycount.png', f)
            log('The party has %d Pokemon but the script expected %d - stopping.' % (n, expect_count))
            run(['b', 'w1.8', 'b', 'w1.2'])
            return None, None, None
    if not pick_party_slot(slot):
        frame(f'{OUT}_pickfail.png'); log('could not select slot', slot); return None, None, None
    run(['a', 'w1.0', 'a', 'w2.0'])                   # slot -> SUMMARY (first item)
    f = settled_summary(f'{OUT}_summary.png')
    g, s, nat = gender_from_summary(f), star_px(f), nature_line(f)
    from .release import lv5_summary                   # (release imports this module)
    if not lv5_summary(f):
        # already levelled = the game was not reset since candies were used: never go on
        log('slot', slot, 'is not a Lv5 hatchling - the game was not reset after the last check')
        g = None
    run(['b', 'w1.8', 'b', 'w1.5'])                   # summary -> party -> START menu
    for _ in range(4):                                # B until the menu is really shut
        f = frame()
        if menu_open(f) or f[330:400, 60:560, 2].mean() > 180:
            run(['b', 'w1.2'])
        else:
            break
    return g, s, nat


def evaluate(slot=2, start_level=5, max_candies=999, stop_fn=None, expect_count=None):
    """stop_fn(readings, natures, merged_sets, gender) -> True once nothing more needs knowing
    (default: every stat '31' or '-').  Only ever uses an item after the bag shows RARE CANDY
    highlighted on the top row and the submenu says "RARE CANDY is selected."
    Result 'left' = candies left in the bag (None if unread), 'out' = stopped for lack of candy,
    'nature_img' = the summary's nature line (identity check before a release)."""
    g, s, nat = summary_check(slot, expect_count)
    log('gender', g, 'star px', s)
    if g is None:
        return None
    if not open_menu_item('BAG'):
        log('no bag'); return None
    readings, level, candies = [], start_level, 0
    left, out = None, False
    for c in range(max_candies):
        f = frame()
        if not (bag_screen(f) and not bag_submenu(f)):
            frame(f'{OUT}_notbag_{c}.png'); log('not at the bag'); return None
        if not candy_on_top(f):
            cv2.imwrite(f'{OUT}_nocandy.png', f)
            log('   RARE CANDY is not highlighted at the top of the bag (none left?)')
            out = True
            break
        n = candy_count(f)
        if left is not None and n != left:
            log('   candy count read %s, expected %d - using %d' % (n, left, left))
            n = left
        if n is not None and n < 1:
            out = True
            break
        run(['a', 'w1.2'])                            # RARE CANDY -> submenu
        if _match(frame(), CANDY_SEL, (320, 410, 120, 420)) < 0.85:
            frame(f'{OUT}_nosel.png'); log('   "RARE CANDY is selected." not shown - stopping')
            run(['b', 'w1.2']); return None
        run(['a', 'w1.6'])                            # USE -> party picker
        left = n - 1 if n is not None else None
        if not pick_party_slot(slot):
            frame(f'{OUT}_pickfail.png'); log('could not select slot', slot); return None
        run(['a', 'w2.5'])
        candies += 1
        level += 1
        got = False
        for _ in range(30):
            f = frame()
            if bag_screen(f) and not bag_submenu(f):
                break
            if totals_window(f):
                vals = read_majority(f, level)
                sp = 'magikarp' if level <= 20 else 'gyarados'
                log('Lv', level, sp, vals)
                prev = readings[-1][1] if readings else None
                if vals and prev and any(v < p for v, p in zip(vals, prev)):
                    log('   stats went DOWN - misread, dropping'); vals = None
                if vals:
                    readings.append((level, vals, sp))
                    if not solve_any_nature(readings)[1]:
                        log('   no nature fits - misread, dropping')
                        cv2.imwrite(f'{OUT}_misread_{level}.png', f)
                        readings.pop()
                    else:
                        got = True
                run(['a', 'w1.4'])
            elif stat_window(f) and plus_column(f):
                run(['a', 'w1.2'])
            elif move_prompt(f) == 'delete':
                log('   declining new move'); run(['b', 'w1.5'])     # NO
            elif move_prompt(f) == 'stop':
                run(['a', 'w1.5'])                                  # YES, stop learning
            elif float((f[200:330, 420:600].min(2) > 200).mean()) > 0.45 and not stat_window(f):
                cv2.imwrite(f'{OUT}_yesno_{level}.png', f)
                log('unknown YES/NO prompt at Lv', level, '- stopping for a look'); return None
            else:
                run(['a', 'w1.2'])                # level-up text, evolution, "learned BITE!"
        else:
            frame(f'{OUT}_stuck_{level}.png'); log('stuck after candy'); return None
        if got:
            sets, natures = solve_any_nature(readings)
            v = verdict(sets)
            log('   ', v, 'natures', len(natures))
            if (stop_fn(readings, natures, sets, g) if stop_fn else '?' not in v):
                break
    run(['b', 'w1.5', 'b', 'w1.0'])                  # close bag and menu
    sets, natures = solve_any_nature(readings)
    res = {'slot': slot, 'candies': candies, 'gender': g, 'star_px': s, 'level': level, 'verdict': verdict(sets),
           'ivs': [sorted(x) for x in sets], 'natures': natures,
           'readings': readings, 'left': left, 'out': out}
    json.dump(res, open(f'{OUT}_result.json', 'w'))
    res['nature_img'] = nat
    return res


if False:  # rig test entry point (not used in GamePRo)
    print(evaluate())
