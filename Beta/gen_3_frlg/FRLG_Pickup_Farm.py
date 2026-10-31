"""
FRLG Pickup Farm — Switch / Switch 2 (NSO GBA)

Farms items (Rare Candy, Nugget, PP Up, berries...) with Pickup Meowths on
Route 1, south of Viridian City.

Party:  slot 1 = lead that one-shots Route 1 wilds.  Moves 1-3: single-turn
                 attacking moves.  Move 4: FLY (only used to get back to the
                 Pokémon Centre - never used in battle).
        slots 2-6 = Pickup Meowths (not holding items)
        NOTE: when the lead levels up and wants to learn a new move, the script
        always says NO, so its moves never change.  Teach it new moves yourself
        if you want them (keep FLY as move 4).

Bag:    BICYCLE registered to Y.  Keep free space in the ITEMS pocket (Rare
        Candy / PP Up / Nugget each need a slot unless you already have some).
        For SHINY_ACTION = 'catch': POKé / GREAT / ULTRA BALLs in the bag
        (the MASTER BALL is never used).

Start:  on the bicycle, in the Route 1 tall grass patch directly below the
        first ledge south of Viridian City (tree line on your left).

Loop:   pace in grass -> battle -> shiny check -> KO with move 1/2/3
        every CHECK_EVERY battles: open party, TAKE any picked-up items
        when moves 1-3 are out of PP: FLY to Viridian, heal, walk back.

Shiny check: a shiny's sparkle animation delays the "Wild X appeared!" text.
The script times every battle intro and treats one that is SHINY_EXTRA seconds
slower than usual as a shiny, then does SHINY_ACTION.

Pickup only triggers after a battle you WIN (fleeing does not count in FRLG).
"""

import os
import time

import cv2
import numpy as np

from scripts.base_script import BaseScript


class FrlgPickupFarm(BaseScript):
    NAME = 'FRLG Pickup Farm'
    DESCRIPTION = ('Farms Rare Candies & other items with Pickup Meowths on Route 1. '
                   'Lead has FLY as move 4; start on the bike in the grass below Viridian.')

    # ── Options ─────────────────────────────────────────────────────────
    SHINY_ACTION = 'stop'     # 'stop'  = stop at the battle menu so you can catch it yourself
                              # 'catch' = throw balls until caught, then keep farming
                              # 'ko'    = knock it out like any other Pokémon
    BALLS = ['ULTRA BALL', 'GREAT BALL', 'POKé BALL']   # catch order; MASTER BALL is never used
    USE_BIKE     = True       # ride the bicycle (registered to Y) in the grass
    PICKUP_SLOTS = 5          # Meowths in party slots 2..6
    CHECK_EVERY  = 3          # battles between party item checks
    HEAL_FIRST   = False      # fly + heal before the first battle

    # ── Lead Pokémon moves: cursor presses from top-left of the move menu ──
    # Move menu layout:  1 2 / 3 4.  Slot 4 (FLY) is never used in battle.
    # Each move is used until its PP shows red (0); when all are red we RUN
    # and go to heal.
    MOVES = ['', 'f', 'd']    # moves 1, 2, 3

    # ── Timing constants (seconds) ──────────────────────────────────────
    PRESS_GAP       = 0.30    # gap between menu presses (back-to-back presses get dropped)
    PACE_LEFT       = 0.70    # on foot: slightly longer than right so we drift into the tree line
    PACE_RIGHT      = 0.60
    BIKE_LEFT       = 0.35    # on the bike (~5 tiles per 0.3 s)
    BIKE_RIGHT      = 0.30
    MAX_PACES       = 200     # no encounter after this many paces -> lost, stop
    INTRO_DEFAULT   = 2.6     # normal time from battle fade-in to "Wild X appeared!" text
    SHINY_EXTRA     = 0.35    # intro this much slower than usual = shiny sparkle
                              # (normal intros vary by < 0.1 s)
    STUCK_TIMEOUT   = 15.0    # unknown screen for this long inside a battle -> stop
    NURSE_PRESSES   = 8       # A presses after the greeting to "We hope to see you again!"
    NURSE_GAP       = 1.5
    FLY_LAND_WAIT   = 8.0     # fly animation + landing outside the Pokémon Centre

    # Walk from Viridian Pokémon Centre door to the grass: (hold char, seconds)
    WALK_TO_GRASS = [('2', 1.5), ('4', 0.45), ('2', 2.0), ('2', 1.3)]

    # ── Screen regions in native GBA pixels (240×160) ────────────────────
    R_RBOX     = (133, 124, 94, 24)    # battle text box right half / battle menu
    R_LBOX     = (12, 124, 98, 24)     # battle text box left half / move list
    R_BORDER   = (224, 124, 16, 26)    # right end of bottom box: green border = menu, gold = text
    R_PARTYBG  = (4, 95, 80, 20)       # teal party-screen background
    R_CHOOSE   = (8, 132, 160, 20)     # "Choose a POKéMON." box
    MENU_ARROW_X = 175                 # start menu cursor column
    MENU_ROW_Y   = [15 + 14.6 * i for i in range(7)]   # POKéDEX..EXIT
    ICON_X       = 106                 # held-item icon on party slots 2..6
    ICON_Y       = [26, 50, 74, 98, 121]
    TEXT_LINE1   = (6, 122, 148, 14)   # first line of the white message box
    R_PP_NUM     = (170, 121, 64, 15)  # "PP 20/20" in the move menu (red when 0)
    R_DIALOG     = (20, 128, 200, 24)  # white overworld dialogue box
    R_INTRO_TEXT = (10, 122, 200, 14)  # first line of the battle text ("Wild X appeared!")
    R_BALL_ICON  = (10, 124, 16, 16)   # selected item's icon in the battle bag
    R_POCKET_L   = (0, 62, 10, 16)     # red pocket arrows either side of the bag picture:
    R_POCKET_R   = (66, 62, 14, 16)    #   POKé BALLS pocket (the last one) has only the left
    R_YESNO_EDGE = (182, 78, 10, 28)   # green left border of the battle YES/NO box
    R_LINE1_MID  = (90, 122, 40, 12)   # middle of battle text line 1

    _BTN = {'a': 'press_a', 'b': 'press_b', 'x': 'press_x', 'y': 'press_y',
            'e': 'press_up', 'd': 'press_down', 's': 'press_left', 'f': 'press_right',
            '8': 'hold_up', '2': 'hold_down', '4': 'hold_left', '6': 'hold_right',
            '0': 'release_all'}

    # ════════════════════════════════════════════════════════════════════
    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        self.c, self.fg, self.stop, self.log = controller, frame_grabber, stop_event, log
        log('FRLG Pickup Farm started.')
        log('Click the 4 corners of the GAME picture (inside the black border).')
        self.warp = request_calibration('Click the 4 corners of the GBA game picture', mode='corners')
        if stop_event.is_set() or self.warp is None:
            log('Script stopped.')
            return

        self.tpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pickup_items')
        os.makedirs(self.tpl_dir, exist_ok=True)
        self.templates = self._load_templates()
        self.items = {}
        self.battles = 0
        self.shinies = 0
        self.intros = []                  # recent normal intro times (s)
        self.t0 = time.time()

        self.out_of_pp = False
        failed_heals = 0
        try:
            if self._state() != 'other' and not self._fight():   # started mid-battle
                return
            if self.HEAL_FIRST and not self._heal_cycle():
                return
            if self.USE_BIKE:
                self._check_bike()
            while not stop_event.is_set():
                if self.out_of_pp:
                    failed_heals += 1
                    if failed_heals > 2:
                        self._fail('Still out of PP after healing twice.')
                        break
                    if not self._collect_items():
                        break
                    self._summary()
                    if not self._heal_cycle():
                        break
                    continue
                if not self._find_battle():
                    break
                t = self._intro_time()
                if t is None and self._state() == 'other':
                    self.log('  (screen flicker, not a battle - carrying on)')
                    continue
                if self._is_shiny(t):
                    if not self._handle_shiny():
                        break
                elif not self._fight():
                    break
                if self.out_of_pp:
                    continue                  # ran away - no Pickup, go heal
                failed_heals = 0
                self.battles += 1
                if self.battles % 10 == 0:
                    self._summary()
                if self.battles % self.CHECK_EVERY == 0:
                    if not self._collect_items():
                        break
        finally:
            self.c.release_all()
            self._summary()
            log('Script stopped.')

    # ── Low-level helpers ───────────────────────────────────────────────
    def _press(self, seq, gap=None):
        """Press each char in seq with a gap after each (menu-safe)."""
        for ch in seq:
            if self.stop.is_set():
                return False
            getattr(self.c, self._BTN[ch])()
            if not self.wait(self.PRESS_GAP if gap is None else gap, self.stop):
                return False
        return True

    def _hold(self, ch, secs):
        getattr(self.c, self._BTN[ch])()
        ok = self.wait(secs, self.stop)
        self.c.release_all()
        return ok

    def _frame(self, w=240, h=160):
        for _ in range(40):
            f = self.fg.get_latest_frame()
            if f is not None:
                return cv2.resize(self.warp_frame(f, self.warp), (w, h),
                                  interpolation=cv2.INTER_AREA)
            time.sleep(0.05)
        raise RuntimeError('No camera frames')

    @staticmethod
    def _rgb(f, r):
        x, y, w, h = r
        b, g, rr = f[y:y + h, x:x + w].reshape(-1, 3).mean(0)
        return rr, g, b

    def _state(self, f=None):
        f = self._frame() if f is None else f
        R, L = self._rgb(f, self.R_RBOX), self._rgb(f, self.R_LBOX)
        if f.mean() < 20:              # whole frame (Pokémon Centre floor leaves black margins)
            return 'black'
        navy_l = L[0] < 110 and L[2] > L[0] + 30 and L[2] < 185
        navy_r = R[0] < 90 and R[2] > R[0] + 40 and R[2] < 185
        bright_r, bright_l = min(R) > 140, min(L) > 150
        x, y, w, h = self.R_BORDER     # count green pixels (tolerates a few px of calibration error)
        p = f[y:y + h, x:x + w].astype(int)
        green = int(((p[:, :, 1] > p[:, :, 2] + 40) & (p[:, :, 1] > p[:, :, 0] + 10)).sum()) >= 30
        if navy_l and navy_r:
            return 'btext'
        if navy_l and bright_r and green:
            return 'bmenu'
        if bright_l and bright_r and green:
            return 'mmenu'
        return 'other'

    def _is_party(self, f):
        p, c = self._rgb(f, self.R_PARTYBG), self._rgb(f, self.R_CHOOSE)
        return p[0] < 90 and p[1] > 140 and p[2] > 150 and min(c) > 190

    def _menu_row(self, f):
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        x = self.MENU_ARROW_X
        darks = [int(g[int(y) - 3:int(y) + 3, x:x + 6].min()) for y in self.MENU_ROW_Y]
        i = int(np.argmin(darks))
        return i if darks[i] < 180 else None

    def _pp_empty(self, f):
        """True if the highlighted move's PP text is red (0 PP)."""
        x, y, w, h = self.R_PP_NUM
        r = f[y:y + h, x:x + w].astype(int)
        red = (r[:, :, 2] > 150) & (r[:, :, 1] < 110) & (r[:, :, 0] < 120)
        return int(red.sum()) > 10

    def _yes_no(self, f):
        """YES/NO box above the right of the battle text (green left border)."""
        x, y, w, h = self.R_YESNO_EDGE
        p = f[y:y + h, x:x + w].astype(int)
        return int(((p[:, :, 1] > p[:, :, 2] + 40) & (p[:, :, 1] > p[:, :, 0] + 20)).sum()) > 70

    def _long_line1(self, f):
        """Text in the middle of line 1: "Delete a move to make" has it, "Stop learning" doesn't."""
        x, y, w, h = self.R_LINE1_MID
        return int((f[y:y + h, x:x + w].min(2) > 170).sum()) > 50

    def _is_dialog(self, f):
        r, g, b = self._rgb(f, self.R_DIALOG)
        return min(r, g, b) > 190 and b > 230

    # ── Overworld: pace in grass until a battle starts ──────────────────
    def _find_battle(self):
        left, right = ((self.BIKE_LEFT, self.BIKE_RIGHT) if self.USE_BIKE
                       else (self.PACE_LEFT, self.PACE_RIGHT))
        for _ in range(50):              # let any menu fade finish first
            if self._state() == 'other':
                break
            self.wait(0.1, self.stop)
        for i in range(self.MAX_PACES):
            d, t = ('4', left) if i % 2 == 0 else ('6', right)
            # watch the screen while moving so the battle fade is caught from its start
            getattr(self.c, self._BTN[d])()
            end, hit = time.time() + t, False
            while time.time() < end and not self.stop.is_set():
                if self._state() in ('black', 'btext'):
                    hit = True
                    break
            self.c.release_all()
            if hit:
                return True
            if not self.wait(0.05, self.stop):
                return False
        self._fail('No wild encounter after %d paces - not in the grass?' % self.MAX_PACES)
        return False

    def _check_bike(self):
        """Get on the bike if we aren't already (on the bike a short pace scrolls ~5 tiles)."""
        for d, back in (('6', '4'), ('4', '6')):        # try right; if blocked, left
            g0 = cv2.cvtColor(self._frame(), cv2.COLOR_BGR2GRAY).astype(np.float32)
            self._hold(d, 0.3)
            self.wait(0.4, self.stop)
            f = self._frame()
            if self._state(f) != 'other':
                return                                    # walked into a battle - check later
            g1 = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32)
            dx = abs(cv2.phaseCorrelate(g0[:60], g1[:60])[0][0])
            self._hold(back, 0.3)
            self.wait(0.3, self.stop)
            if dx >= 8:                                   # moved (not against a tree)
                if dx < 50:
                    self.log('Getting on the bike.')
                    self._press('y', 0.8)
                return

    # ── Shiny check: time the battle intro ──────────────────────────────
    def _ink(self, f):
        x, y, w, h = self.R_INTRO_TEXT
        return int((f[y:y + h, x:x + w].min(2) > 170).sum())

    def _intro_time(self):
        """Seconds from the battle fading in to the first text appearing, or None."""
        end, t0, black = time.time() + 12, None, False
        while time.time() < end and not self.stop.is_set():
            f = self._frame()
            now = time.time()
            if f.mean() < 20:
                black, t0 = True, None
            elif black and t0 is None:
                t0 = now
            elif t0 is not None and self._ink(f) > 40 and self._state(f) == 'btext':
                return now - t0
        return None

    def _is_shiny(self, t):
        if t is None:
            self.log('  (could not time this battle intro - shiny check skipped)')
            return False
        base = float(np.median(self.intros)) if len(self.intros) >= 3 else self.INTRO_DEFAULT
        if t > base + self.SHINY_EXTRA:
            self.log(f'*** SHINY! intro took {t:.2f} s (normal {base:.2f} s) ***')
            return True
        self.intros = (self.intros + [t])[-30:]
        return False

    def _handle_shiny(self):
        self.shinies += 1
        self._save_shot('shiny')
        action = self.SHINY_ACTION
        if action == 'ko':
            self.log('SHINY_ACTION is "ko" - knocking it out.')
            return self._fight()
        if action == 'catch':
            res = self._catch()
            if res == 'caught':
                self.log('Shiny caught! It has been sent to the PC. Carrying on.')
                return True
            if res != 'no balls':
                return False
        # 'stop', or no balls left: leave it at the battle menu for the player
        while not self.stop.is_set() and self._state() == 'btext':
            self._press('a', 0.6)
        self.log('STOPPED: shiny at the battle menu - catch it yourself!')
        return False

    # ── Catching (shiny) ────────────────────────────────────────────────
    def _ball_kind(self, f):
        """Ball type from the selected item's icon colours (None = not a ball / CANCEL)."""
        x, y, w, h = self.R_BALL_ICON
        hsv = cv2.cvtColor(f[y:y + h, x:x + w], cv2.COLOR_BGR2HSV).reshape(-1, 3).astype(int)
        hue = hsv[(hsv[:, 1] > 90) & (hsv[:, 2] > 80), 0]
        red = int(((hue < 25) | (hue >= 165)).sum())
        yellow = int(((hue >= 25) & (hue < 35)).sum())
        blue = int(((hue >= 95) & (hue < 125)).sum())
        purple = int(((hue >= 125) & (hue < 165)).sum())
        if purple >= 40:
            return 'MASTER BALL'
        if yellow >= 8:
            return 'ULTRA BALL'
        if blue >= 90 and red >= 8:
            return 'GREAT BALL'
        if red >= 40:
            return 'POKé BALL'
        return None

    def _in_ball_pocket(self, f):
        def red(r):
            x, y, w, h = r
            p = f[y:y + h, x:x + w].astype(int)
            return int((p[:, :, 2] > p[:, :, 1] + 50).sum()) > 20
        return red(self.R_POCKET_L) and not red(self.R_POCKET_R)

    def _throw_ball(self):
        """From the battle menu: open BAG, pick the best allowed ball, throw it.
        Returns the ball name, or None if there are none left."""
        self._press('efa', 0.4)                  # BAG (top-right)
        self.wait(1.2, self.stop)
        self._press('fff', 0.5)                  # last pocket = POKé BALLS
        if not self._in_ball_pocket(self._frame()):
            self._press('b', 1.2)
            return None
        self._press('e' * 13, 0.25)              # top of the list
        kinds = []
        for _ in range(14):                      # read each entry down to CANCEL
            self.wait(0.3, self.stop)
            k = self._ball_kind(self._frame())
            kinds.append(k)
            if k is None:
                break
            self._press('d')
        want = next((b for b in self.BALLS if b in kinds and b != 'MASTER BALL'), None)
        if want is None:
            self._press('b', 1.2)
            return None
        self._press('e' * (len(kinds) - 1 - kinds.index(want)))
        self.wait(0.3, self.stop)
        if self._ball_kind(self._frame()) != want:    # never risk the wrong ball
            self._press('b', 1.2)
            return None
        self._press('a', 0.8)                    # USE / CANCEL
        self._press('a', 1.0)                    # USE
        return want

    def _catch(self):
        """Throw balls until the wild Pokémon is caught. Returns 'caught', 'no balls' or 'stuck'."""
        throws, last_ok = 0, time.time()
        while not self.stop.is_set():
            st = self._state()
            if st != 'other':
                last_ok = time.time()
            if st == 'btext':
                self._press('b', 0.35)           # B also answers NO to "Give a nickname?"
            elif st == 'mmenu':
                self._press('b', 0.6)
            elif st == 'bmenu':
                ball = self._throw_ball()
                if ball is None:
                    self.log('No POKé / GREAT / ULTRA BALLs left.')
                    return 'no balls'
                throws += 1
                self.log(f'Threw {ball} #{throws}')
                last_ok = time.time()
            elif st == 'black' and throws:
                while self._state() == 'black' and not self.stop.is_set():
                    self.wait(0.2, self.stop)
                self._press('bbbb', 1.0)         # clear any POKéDEX page / nickname prompt
                return 'caught'
            elif st == 'other' and throws and time.time() - last_ok > 1.5:
                self._press('b', 0.8)            # nickname prompt / POKéDEX page
                if time.time() - last_ok > 30:
                    self._fail('Stuck while catching.')
                    return 'stuck'
            self.wait(0.3, self.stop)
        return 'stuck'

    # ── Battle: KO the wild Pokémon, wait for the fade back out ─────────
    def _fight(self):
        fought, last_ok = False, time.time()
        while not self.stop.is_set():
            st = self._state()
            if st != 'other':
                last_ok = time.time()
            if st == 'btext':
                f = self._frame()
                if self._yes_no(f):                      # lead levelled up and wants a 5th move
                    if self._long_line1(f):              # "Delete a move to make room for X?"
                        self.log('Lead wants to learn a new move - not learning it.')
                        self._press('b', 1.0)            # NO
                    else:                                # "Stop learning X?"
                        self._press('a', 1.0)            # YES
                else:
                    self._press('a', 0.35)
            elif st == 'bmenu':
                if self.out_of_pp:
                    self._press('dfa')                   # RUN (bottom-right)
                    fought = True
                else:
                    self._press('esa')                   # FIGHT (top-left)
                    self.wait(0.5, self.stop)
            elif st == 'mmenu':
                for nav in self.MOVES:
                    self._press('es' + nav)
                    if not self._pp_empty(self._frame()):
                        self._press('a')
                        fought = True
                        break
                else:
                    self.log('Lead is out of PP - running away to heal.')
                    self.out_of_pp = True
                    self._press('b', 0.6)                # back to FIGHT/BAG/RUN
            elif st == 'black' and fought:
                while self._state() == 'black' and not self.stop.is_set():
                    self.wait(0.2, self.stop)
                return self.wait(0.6, self.stop)
            elif st == 'other' and time.time() - last_ok > self.STUCK_TIMEOUT:
                self._fail('Unexpected screen in battle (level up / new move?).')
                return False
            self.wait(0.3, self.stop)
        return False

    # ── Party menu ──────────────────────────────────────────────────────
    def _open_party(self):
        for _ in range(3):
            self._press('x', 0.9)
            row = self._menu_row(self._frame())
            if row is None:
                continue
            for _ in range(8):
                if row == 1:
                    break
                self._press('d' if row < 1 else 'e')
                row = self._menu_row(self._frame())
                if row is None:
                    break
            if row != 1:
                self._press('b', 0.8)
                continue
            self._press('a', 1.2)
            for _ in range(15):
                if self._is_party(self._frame()):
                    return True
                self.wait(0.2, self.stop)
        self._fail('Could not open the party screen.')
        return False

    def _close_party(self):
        self._press('b', 1.2)
        self._press('b', 1.0)

    def _held(self, f):
        out = []
        # count warm (cream/red) pixels where the item icon sits: the slot panel is blue,
        # so empty slots score < 16 and holders > 23 in dim, bright and daylight rooms
        for y in self.ICON_Y[:self.PICKUP_SLOTS]:
            p = f[y - 2:y + 6, self.ICON_X:self.ICON_X + 9].astype(int)
            b, r = p[:, :, 0], p[:, :, 2]
            out.append(int(((r > b + 15) & (r > 120)).sum()) >= 18)
        return out

    def _collect_items(self):
        if not self._open_party():
            return False
        held = self._held(self._frame())
        for k, has in enumerate(held):
            if not has or self.stop.is_set():
                continue
            # slot k+2: left -> lead, down k+1 times, A, ITEM, TAKE
            self._press('s' + 'd' * (k + 1))
            self._press('a', 0.8)
            self._press('dd')
            self._press('a', 0.8)
            self._press('d')
            before = self._text_crop()
            self._press('a', 1.0)
            name = self._read_item(before)
            if self.stop.is_set():               # Stop pressed mid-TAKE - nothing to report
                return False
            self._press('a', 1.0)
            # no "Received the" and still holding it -> "The BAG is full"
            # (the icon check alone misreads the selected slot when the room lighting changes)
            if not self.took and self._held(self._frame())[k]:
                self._fail(f'Could not take the item from Meowth {k + 1} - the bag looks full. '
                           'Make room in the ITEMS pocket and restart.')
                return False
            self.items[name] = self.items.get(name, 0) + 1
            self.log(f'Battle {self.battles}: Meowth {k + 1} picked up {name}')
        self._close_party()
        return True

    # ── Item name recognition (template match on the message line) ──────
    def _text_crop(self, both=False):
        f = self._frame(720, 480)
        x, y, w, h = [v * 3 for v in self.TEXT_LINE1]
        g = cv2.cvtColor(f[y:y + h, x:x + w], cv2.COLOR_BGR2GRAY)
        crop = (g < g.mean() - 35).astype(np.uint8) * 255
        if not both:
            return crop
        # when the camera over-exposes the white message box the text goes faint grey
        # and the fixed cut-off above loses it - Otsu adapts to the crop's own levels
        _, otsu = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        return [crop, otsu]

    NAME_X       = 215     # item name starts after "Received the " (in the 3x crop)
    MATCH_MIN    = 0.85    # same item scores 0.86-0.99 (camera dependent), wrong items <= 0.84...
    MATCH_MARGIN = 0.06    # ...and must beat the best *other* item by this much

    @classmethod
    def _name_part(cls, crop):
        """Item-name portion only (the shared 'Received the' text swamps the score)."""
        return cv2.GaussianBlur(crop[:, cls.NAME_X:].astype(np.float32), (0, 0), 2.0)

    def _load_templates(self):
        """Templates are 'ITEM NAME.png'; extra samples as 'ITEM NAME_2.png' etc."""
        out = []
        for fn in os.listdir(self.tpl_dir):
            if fn.lower().endswith('.png') and not fn.startswith(('unknown', 'stuck')):
                t = cv2.imread(os.path.join(self.tpl_dir, fn), cv2.IMREAD_GRAYSCALE)
                if t is not None:
                    out.append((fn[:-4].split('_')[0], self._name_part(t)[4:-4, 6:-6]))
                    self.prefix = self._prefix_part(t)[4:-4, 6:-6]   # "Received the"
        return out

    @classmethod
    def _prefix_part(cls, crop):
        return cv2.GaussianBlur(crop[:, :cls.NAME_X].astype(np.float32), (0, 0), 2.0)

    def _read_item(self, before=None):
        # wait for the message to finish printing (two matching crops in a row,
        # and no longer the text that was showing before TAKE was pressed)
        crop = self._text_crop()
        for _ in range(10):
            self.wait(0.4, self.stop)
            nxt = self._text_crop()
            same = np.mean(nxt != crop) < 0.01
            crop = nxt
            if same and (before is None or np.mean(crop != before) >= 0.01):
                break
        # the message stays up until A is pressed, so re-read a few times before
        # calling it unknown (a camera frame can catch the text half-drawn or washed out)
        for attempt in range(3):
            if attempt:
                self.wait(0.4, self.stop)
            crops = self._text_crop(both=True)
            # "Received the ..." = taken; "The BAG is full." scores well below 0.6
            pre = [float(cv2.matchTemplate(self._prefix_part(c), self.prefix,
                                           cv2.TM_CCOEFF_NORMED).max()) for c in crops]
            self.took = max(pre) >= 0.6
            crop = crops[int(np.argmax(pre))]    # the clearer one, saved if it's unknown
            for c, washed in zip(crops, (False, True)):
                name = self._match_name(c, washed)
                if name:
                    return name
        if self.stop.is_set():
            return 'unknown item'
        fn = 'unknown_%s.png' % time.strftime('%Y%m%d_%H%M%S')
        cv2.imwrite(os.path.join(self.tpl_dir, fn), crop)
        self.log(f'  (new item - saved {fn}; rename it to the item name to teach me)')
        return 'unknown item'

    def _match_name(self, crop, washed=False):
        # washed-out (Otsu) text has thicker strokes than the templates, so the right item
        # tops out around 0.85 - accept a little lower there, but only with a clear lead
        lo, gap = (0.82, 0.10) if washed else (self.MATCH_MIN, self.MATCH_MARGIN)
        name_img = self._name_part(crop)
        scores = {}                              # best score per item name
        for name, t in self.templates:
            if t.shape[0] > name_img.shape[0] or t.shape[1] > name_img.shape[1]:
                continue
            s = float(cv2.matchTemplate(name_img, t, cv2.TM_CCOEFF_NORMED).max())
            scores[name] = max(s, scores.get(name, 0.0))
        ranked = sorted(scores.items(), key=lambda kv: -kv[1]) + [(None, 0.0), (None, 0.0)]
        (best, score), (_, second) = ranked[0], ranked[1]
        if best and score >= lo and score - second >= gap:
            return best
        return None

    # ── Fly to Viridian, heal, walk back to the grass ───────────────────
    def _heal_cycle(self):
        self.log('Flying to Viridian City to heal...')
        if not self._open_party():
            return False
        self._press('s')                 # lead
        self._press('a', 0.9)            # SUMMARY / field moves... / SWITCH / ITEM / CANCEL
        self._press('eeee')              # wraps to CANCEL, then up past ITEM, SWITCH ->
                                         # the last field move = FLY (move 4)
        self._press('a', 2.5)            # fly map, cursor on Route 1
        self._press('e', 0.6)            # Viridian City
        self._press('a', self.FLY_LAND_WAIT)   # fly + land outside the Pokémon Centre
        self._hold('8', 0.4)             # enter
        self._wait_fade()
        for _ in range(3):               # walk to the counter and talk
            self._hold('8', 1.6)
            self._press('a', 1.2)
            if self._is_dialog(self._frame()):
                break
        else:
            self._fail('Could not talk to the nurse.')
            return False
        self._press('a' * self.NURSE_PRESSES, self.NURSE_GAP)
        self._press('bb', 0.8)
        self._hold('2', 1.7)             # back out of the door
        self._wait_fade()
        for ch, t in self.WALK_TO_GRASS:
            if not self._hold(ch, t) or not self.wait(0.3, self.stop):
                return False
        if self._state() != 'other':
            self._fight()                # walked into a battle on the way (no shiny check)
        elif self.USE_BIKE:
            self._press('y', 0.8)        # always on foot after the Pokémon Centre
        self.out_of_pp = False
        self.log('Healed - back in the grass.')
        return not self.stop.is_set()

    def _wait_fade(self, timeout=6.0):
        """Wait for a door fade: screen goes black, then comes back."""
        end, seen_black = time.time() + timeout, False
        while time.time() < end and not self.stop.is_set():
            black = self._state() == 'black'
            seen_black = seen_black or black
            if seen_black and not black:
                break
            self.wait(0.1, self.stop)
        self.wait(0.6, self.stop)

    # ── Reporting ───────────────────────────────────────────────────────
    def _save_shot(self, tag):
        fn = os.path.join(self.tpl_dir, '%s_%s.png' % (tag, time.strftime('%Y%m%d_%H%M%S')))
        f = self.fg.get_latest_frame()
        if f is not None:
            cv2.imwrite(fn, f)
        return fn

    def _fail(self, msg):
        self.log(f'STOPPED: {msg} (screenshot: {self._save_shot("stuck")})')

    def _summary(self):
        mins = (time.time() - self.t0) / 60
        items = ', '.join(f'{n} x{c}' for n, c in sorted(self.items.items())) or 'none yet'
        intro = (f' | intro {min(self.intros):.2f}-{max(self.intros):.2f} s'
                 if self.intros else '')
        self.log(f'== {self.battles} battles in {mins:.0f} min | '
                 f'Rare Candy: {self.items.get("RARE CANDY", 0)} | shinies: {self.shinies}'
                 f'{intro} | {items}')
