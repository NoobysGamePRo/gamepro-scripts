"""Release the hatchling in party slot 2 at the Four Island day care PC - with a screen check before
EVERY step.  Any mismatch -> back out with B and return 'abort' (never guess near RELEASE).

Safety rules (Carl, 2026-10-31): never release Pokemon already in the PC boxes; keep shinies.
  * Only DEPOSIT (party column) is used - verified by the cyan party column, not the box grid.
  * RELEASE only when the selected Pokemon's panel matches 'MAGIKARP / MAGIKARP Lv5' (template).
  * The submenu must start with STORE (party) - WITHDRAW means a box view -> abort.
  * Summary page checked for the shiny star first.
"""
from .gpc import WORK
from .store import tpl
import time, cv2, numpy as np
from .gpc import run, frame
from .fr import log
from .evalbaby import star_px, gender_from_summary, same_nature

D = WORK
OUT = D + 'rel'
T_NAME = tpl('safe_name_magikarp_lv5')
T_STORE = tpl('safe_store_menu')
T_SUMHDR = tpl('safe_summary_hdr')
STORAGE_ROWS = [96, 132, 168, 204, 240]          # WITHDRAW / DEPOSIT / MOVE / MOVE ITEMS / SEE YA!
SUB_ROWS = [168, 204, 240, 276, 312]             # STORE / SUMMARY / MARK / RELEASE / CANCEL


def taps(seq):
    for k in seq:                       # one tap per step: turning taps don't move, so repeat
        run([k, 'w0.45'])


def walk_in_to_pc():
    """From anywhere in front of the day care: camera-guided to the door, inside, to the PC."""
    from .daycare_nav import enter_daycare, go_below, offset_to
    g = cv2.cvtColor(frame()[60:418, 36:576], cv2.COLOR_BGR2GRAY)
    inside = float((g < 25).mean()) > 0.15              # indoors the room is boxed in black (0.3-0.55; outside 0)
    if not inside:
        from .daycare_nav import go_to_man
        if offset_to(tpl('door_tpl'), 0.55) is None and not go_to_man():
            return False                                # door off-screen: the man is the anchor
        if not enter_daycare():
            return False
        taps(['e', 'e'])                                # off the mat so the PC is in view
    if not go_below(tpl('pc_tpl'), 40):
        return False
    run(['e', 'w0.5', 'a', 'w1.8'])                     # face up, "NOOBY booted up the PC."
    f = frame(f'{OUT}_boot.png')
    return f[330:400, 60:560, 2].mean() > 180


def _prep(img):
    return cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.5)


def match(f, tpl, region):
    # blurred greyscale: tolerant of small camera shifts, still separates different text
    y0, y1, x0, x1 = region
    return float(cv2.matchTemplate(_prep(f[y0:y1, x0:x1]), _prep(tpl), cv2.TM_CCOEFF_NORMED).max())


def cursor_row(f, rows, x0, x1):
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(int)
    d = [int(g[y - 8:y + 8, x0:x1].min()) for y in rows]
    i = int(np.argmin(d))
    return i if d[i] < 160 and sorted(d)[1] > 180 else None


T_STORAGE = None


def storage_menu(f):
    """WITHDRAW / DEPOSIT / MOVE / MOVE ITEMS / SEE YA! menu (not BILL'S PC / NOOBY's PC menu)."""
    global T_STORAGE
    if T_STORAGE is None:
        T_STORAGE = tpl('safe_storage_menu')
    return match(f, T_STORAGE, (60, 280, 40, 330)) > 0.85 and cursor_row(f, STORAGE_ROWS, 56, 70) is not None


def release_yes(f):
    """'Release this POKEMON?' box with the cursor on YES (YES/NO panel bottom-right)."""
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(int)
    yes, no = int(g[268:290, 470:484].min()), int(g[300:322, 470:484].min())
    return yes < 150 and no > 180 and float((f[250:340, 460:570].min(2) > 200).mean()) > 0.4


def party_column(f):
    p = f[150:330, 240:330].astype(int)
    return p[:, :, 0].mean() > 200 and p[:, :, 2].mean() < 130


def panel_widths(f):
    """Widths of the white text lines in the PKMN DATA panel: name, /species, gender+Lv."""
    p = f[240:370, 40:190].astype(int)
    g = p.mean(2); sat = p.max(2) - p.min(2)
    m = (g > np.median(g) + 12) & (sat < 45)
    out = []
    for y0, y1 in [(10, 42), (42, 74), (78, 112)]:
        cols = np.where(m[y0:y1].sum(0) >= 2)[0]
        out.append(int(cols.max() - cols.min()) if len(cols) else 0)
    return out


def level_blocks(f):
    """Text blocks on the gender/level line right of the gender symbol: 'Lv'+'5' = 2, 'Lv'+'4'+'5' = 3."""
    p = f[240:370, 40:190].astype(int)
    g = p.mean(2); sat = p.max(2) - p.min(2)
    m = (g > np.median(g) + 12) & (sat < 45)
    cols = list(m[78:112].sum(0)[55:] >= 2) + [False]
    runs, n = 0, 0
    for c in cols:
        if c:
            n += 1
        else:
            runs += n >= 5
            n = 0
    return runs


def hand_px(f, y0, y1, x0, x1):
    return int((f[y0:y1, x0:x1].min(2) > 215).sum())


def hand_region(slot):
    """Glove cursor area above party slot `slot` (2..6) in the DEPOSIT view (camera px)."""
    y = 50 + 52 * (slot - 2)
    return (y, y + 45, 335, 405)


GLOVE = tpl('glove_tpl')


TOPS = {2: 78, 3: 132, 4: 188, 5: 240, 6: 292}       # party box top edges, DEPOSIT view (camera px)


def glove_slot(f):
    """Slot (1..6) the white glove cursor points at in the DEPOSIT view, or None if unsure.
    The glove hovers just ABOVE the chosen box; count grey-white pixels in the band above each box.
    Measured (2026-11-01): pointed-at slot 187-514, other slots 0-145; slot 1 (Dodrio) 585-604.
    (Template matching failed: the glove bobs and partly overlaps the box / screen edge.)"""
    p = f.astype(int)
    g = (p.min(2) > 160) & (p.max(2) - p.min(2) < 40)
    if int(g[130:190, 245:300].sum()) > 300:
        return 1
    sc = {s_: int(g[t - 24:t - 2, 345:405].sum()) for s_, t in TOPS.items()}
    best = max(sc, key=sc.get)
    second = sorted(sc.values())[-2]
    return best if sc[best] >= 150 and sc[best] - second >= 60 else None


def is_slot_selected(f, slot):
    return party_column(f) and glove_slot(f) == slot


def lv5_summary(f):
    """Summary title says exactly 'Lv5' (fresh hatchling) - never a returned parent (Lv>5)."""
    # Three independent tests (2026-11-03: Lv5 alone scored 0.798 on a real hatchling but 0.894 on
    # an old Lv9 Kakuna frame): 'Lv5' template, no second level digit, name MAGIKARP.
    # Hatchlings: lv 0.80-0.97, name 0.83-0.99. Others: Kakuna Lv9 name 0.60, Marill Lv13 name 0.79
    # + 2nd digit, Mewtwo lv 0.59.
    t = _prep(tpl('safe_lv5'))
    s = float(cv2.matchTemplate(_prep(f[85:150, 30:110]), t, cv2.TM_CCOEFF_NORMED).max())
    dark = f[104:132, 88:116].astype(int).max(2) < 130      # below the panel's top border (y~100)
    after = int(dark[dark.sum(1) < 20].sum())       # ignore the panel border line (camera shift)
    n = float(cv2.matchTemplate(_prep(f[85:150, 100:280]), _prep(tpl('safe_magikarp')),
                                cv2.TM_CCOEFF_NORMED).max())
    return s > 0.75 and after <= 5 and n > 0.80


def bred_parent_summary(f):
    """A parent the script bred and swapped in, back from the day care at any level: name MAGIKARP,
    second level digit allowed, memo "Hatched: FOUR ISLAND" (hatched 0.86-1.00, Mewtwo's "Met in"
    0.45) - never a Pokemon you caught."""
    n = float(cv2.matchTemplate(_prep(f[85:150, 100:280]), _prep(tpl('safe_magikarp')),
                                cv2.TM_CCOEFF_NORMED).max())
    return n > 0.80 and match(f, tpl('safe_hatched'), (340, 392, 36, 345)) > 0.75


def is_target(f):
    """DEPOSIT party view with the hand cursor on party slot 2 (top of the right column).
    The DEPOSIT view only contains the party (Dodrio + the hatchling), so boxed Pokemon can never
    be selected.  Measured: hand over slot 2 = 137-228 px (slot-1 area 0); Dodrio selected = 531 px
    over slot 1 and 0 over slot 2.  (Text/template checks drifted with camera exposure.)"""
    return party_column(f) and hand_px(f, 50, 95, 335, 405) > 80 and hand_px(f, 135, 190, 240, 305) < 20


def submenu_is_party(f):
    return match(f, T_STORE, (130, 220, 370, 540)) > 0.85


def move_cursor(rows, x0, x1, target, tag):
    for _ in range(8):
        r = cursor_row(frame(), rows, x0, x1)
        if r is None:
            frame(f'{OUT}_{tag}_nocursor.png'); return False
        if r == target:
            return True
        run(['d' if r < target else 'e', 'w0.6'])
    return False


def abort(why):
    log('RELEASE ABORTED:', why)
    frame(f'{OUT}_abort.png')
    for _ in range(6):
        run(['b', 'w1.6'])
    return 'abort'


def _tprep(i):
    return cv2.GaussianBlur(cv2.cvtColor(i, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.2)


PC_T = {n: _tprep(tpl(n)) for n in
        ('pc_t_booted', 'pc_t_whichpc', 'pc_t_accessed', 'pc_t_opened', 'pc_t_descwd', 'pc_t_descdep')}


def screen_is(f, name):
    """Message/description text in the bottom box matches `name` (score 1.0 vs <=0.67 others)."""
    r = _tprep(f[300:420, 20:620])
    return float(cv2.matchTemplate(r, PC_T[name], cv2.TM_CCOEFF_NORMED).max()) > 0.85


def expect(name, tries=4):
    for _ in range(tries):
        if screen_is(frame(), name):
            return True
        time.sleep(0.5)
    frame(f'{OUT}_expect_{name}.png')
    return False


def bill_selected(f):
    """Which-PC menu: arrow on the first row (BILL'S PC)."""
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(int)
    # arrow columns only (x52-62): the letters start at x~66 and their edges reached a 54-68 window
    d = [int(g[y - 8:y + 8, 52:62].min()) for y in (90, 129, 165, 202, 239)]
    return d[0] < 150 and min(d[1:]) > d[0] + 60


def _column(f):
    return cv2.cvtColor(f[40:360, 335:425], cv2.COLOR_BGR2GRAY).astype(np.float32)


def _press_moved(key, tries=3):
    """Press `key` once; True when the glove column changed. If it didn't, look again a second
    later before pressing again (camera lag must not turn one move into two)."""
    for _ in range(tries):
        before = _column(frame())
        run([key, 'w0.8'])
        for _ in range(2):
            if float(np.abs(_column(frame()) - before).mean()) > 2.0:
                return True
            time.sleep(1.0)
    return False


def panel_empty(f):
    """PKMN DATA sprite area is blank (glove on CANCEL or an empty slot): std 14 vs 37-55."""
    return float(cv2.cvtColor(f[95:235, 65:200], cv2.COLOR_BGR2GRAY).astype(float).std()) < 25


def at_cancel(f):
    p = f.astype(int)
    g = (p.min(2) > 160) & (p.max(2) - p.min(2) < 40)
    return panel_empty(f) and int(g[330:362, 345:415].sum()) > 300


def glove_to(slot, tries=8):
    """Dead reckoning from CANCEL with every press verified. (Right from Dodrio returns to the
    last-used right-column slot, so slot 1 is NOT a usable anchor.) Down -> CANCEL; up from CANCEL
    = slot 6, 5, ...  Needs (7 - slot) verified up-presses."""
    if slot < 2:
        return False
    for _ in range(tries):
        f = frame()
        if at_cancel(f):
            break
        run(['f' if glove_slot(f) == 1 else 'd', 'w0.8'])
    else:
        return False
    for _ in range(7 - slot):
        if not _press_moved('e'):
            return False
    return not panel_empty(frame())


def enter_deposit():
    """From "NOOBY booted up the PC." to the DEPOSIT party view - every A screen-verified."""
    for step in ('pc_t_booted', 'pc_t_whichpc', 'pc_t_accessed', 'pc_t_opened'):
        if not expect(step):
            return not abort('expected screen ' + step + ' not seen')
        if step == 'pc_t_whichpc' and not bill_selected(frame()):
            return not abort("cursor is not on BILL'S PC")
        run(['a', 'w1.8'])
    if not expect('pc_t_descwd'):                       # storage menu, cursor on WITHDRAW
        return not abort('storage menu (WITHDRAW highlighted) not seen')
    run(['d', 'w0.8'])
    if not expect('pc_t_descdep'):                      # cursor on DEPOSIT
        return not abort('DEPOSIT not highlighted - not pressing A')
    run(['a', 'w2.8'])
    return party_column(frame()) or not abort('not the DEPOSIT party view')


NATURE_OK = 0.86                                 # same nature 0.90-1.00, different <= 0.82


def release_slot(slot=2, rec=None, kind='hatchling'):
    """Call with "NOOBY booted up the PC." on screen.  rec = {'g': gender, 'img': nature-line
    image} recorded when this hatchling was first checked: released only if both still match.
    kind 'parent' = a replaced parent the script bred (any level, must say Hatched: FOUR ISLAND)."""
    # Every A below is pressed only after the exact screen text was recognised. (2026-11-01 a
    # template miss made a "press A until the storage menu" loop open WITHDRAW -> box view ->
    # Carl's shiny Mewtwo's RELEASE menu. Nothing was lost, but never press A on a guess here.)
    if not enter_deposit():
        return 'abort'
    if not glove_to(slot):
        return abort(f'could not move the glove to slot {slot}')
    f = frame(f'{OUT}_sel.png')
    if not party_column(f):
        return abort('not the DEPOSIT party view')
    run(['a', 'w1.4'])
    f = frame()
    if not submenu_is_party(f):
        return abort('submenu does not start with STORE')
    if not move_cursor(SUB_ROWS, 398, 412, 1, 'sub'):
        return abort('could not select SUMMARY')
    run(['a', 'w2.4'])
    from .evalbaby import settled_summary
    f = settled_summary(f'{OUT}_summary.png')
    if match(f, T_SUMHDR, (40, 120, 20, 260)) < 0.8:
        return abort('summary page not recognised')
    if kind == 'parent':
        if not bred_parent_summary(f):
            run(['b', 'w2.2'])
            return abort('summary is not a MAGIKARP hatched at FOUR ISLAND')
    elif not lv5_summary(f):
        run(['b', 'w2.2'])
        return abort('summary is not a Lv5 hatchling')
    if star_px(f) > 10:
        log('SHINY STAR - keeping it')
        run(['b', 'w2.2'])
        return abort('shiny - kept') and 'shiny'
    if rec is None:
        run(['b', 'w2.2'])
        return abort('no record of this hatchling - not releasing')
    g, ns = gender_from_summary(f), same_nature(f, rec['img'])
    log('   identity: gender %s (recorded %s), nature line %.2f' % (g, rec['g'], ns))
    if g != rec['g'] or ns < NATURE_OK:
        run(['b', 'w2.2'])
        return abort('this is not the hatchling the script checked (gender / nature differ)')
    run(['b', 'w2.2'])
    f = frame()
    if not party_column(f):
        return abort('lost the party view after SUMMARY')
    run(['a', 'w1.4'])
    if not submenu_is_party(frame()):
        return abort('submenu (2nd) does not start with STORE')
    if not move_cursor(SUB_ROWS, 398, 412, 3, 'sub2'):
        return abort('could not select RELEASE')
    run(['a', 'w1.6'])                                  # "Release this POKEMON?" YES / >NO
    f = frame(f'{OUT}_confirm.png')
    run(['e', 'w0.6'])                                  # -> YES
    f = frame(f'{OUT}_yes.png')
    if not release_yes(f):
        return abort('"Release this POKEMON?" with YES selected not recognised')
    run(['a', 'w2.0'])                                  # released
    frame(f'{OUT}_released.png')
    run(['a', 'w1.8', 'a', 'w1.8'])                     # "was released." / "Bye-bye"
    if party_column(frame()) and match(frame(), T_NAME, (230, 370, 30, 230)) > 0.93:
        log('WARNING: a Lv5 Magikarp is still selected after release')
    for _ in range(4):
        run(['b', 'w1.8'])                              # out of the PC
    return 'released'


def release_slot2():
    return release_slot(2)


def _bprep(i):
    return cv2.GaussianBlur(cv2.cvtColor(i, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 0.8)


BOX5 = _bprep(tpl('box5_tpl'))
BOX_TPL = {5: (BOX5, 0.88),                                # old parents
           6: (_bprep(tpl('box6_tpl')), 0.92)}   # keepers (others <= 0.86)


BOXD = {b: _bprep(tpl('boxd_%d' % b)) for b in range(1, 15)}


def box_shown(f):
    """Box number in the 'Deposit in which BOX?' label (digit area, 1-14), or None if unsure.
    Same-frame self score 1.0, other boxes <= 0.91; an independent frame scored 0.90 vs <= 0.73."""
    big = _bprep(f[211:265, 353:403])
    sc = {b: float(cv2.matchTemplate(big, t, cv2.TM_CCOEFF_NORMED).max()) for b, t in BOXD.items()}
    s = sorted(sc.items(), key=lambda x: -x[1])
    return s[0][0] if s[0][1] > 0.80 and s[0][1] - s[1][1] > 0.06 else None


def at_box(f, box):
    """`box` is shown on two frames in a row (a misfiled Pokemon is not lost, but be sure)."""
    return box_shown(f) == box and box_shown(frame()) == box


def at_box5(f):
    """'Deposit in which BOX?' label shows BOX5 (digit template: 0.94-0.99 vs <=0.82 for other boxes;
    0.93 once missed it on the rig, 2026-11-02)."""
    return float(cv2.matchTemplate(_bprep(f[215:262, 355:395]), BOX5, cv2.TM_CCOEFF_NORMED).max()) > 0.88


def store_slot(slot, box=5):
    """Store party `slot` in BOX `box` (5 = Carl's box for old parents, 6 = keepers). Same verified DEPOSIT entry as
    release; never touches RELEASE. Call with "NOOBY booted up the PC." on screen."""
    if not enter_deposit():
        return 'abort'
    if not glove_to(slot):
        return abort(f'could not move the glove to slot {slot}')
    run(['a', 'w1.4'])
    if not submenu_is_party(frame()):
        return abort('submenu does not start with STORE')
    if not move_cursor(SUB_ROWS, 398, 412, 0, 'store'):
        return abort('could not select STORE')
    run(['a', 'w2.2'])                                   # "Deposit in which BOX?"
    for _ in range(32):                                  # right from BOX1 (wraps)
        f = frame()
        if at_box(f, box):
            break
        run(['f', 'w1.0'])
    else:
        return abort(f'could not find BOX{box}')
    frame(f'{OUT}_store_box.png')
    run(['a', 'w2.5'])                                   # stored
    if not party_column(frame()):
        return abort('not back in the party view after storing')
    for _ in range(4):
        run(['b', 'w1.8'])                               # out of the PC
    return 'stored'
