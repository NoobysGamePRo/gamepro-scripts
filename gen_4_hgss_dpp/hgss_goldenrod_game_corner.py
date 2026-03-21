"""
HGSS Goldenrod Game Corner — Shiny Prize Pokemon
Game: Pokemon HeartGold / SoulSilver (DS / 3DS)

Soft-resets for a shiny prize Pokemon (Abra, Ekans/Sandshrew, or Dratini)
from the Goldenrod Game Corner prize man.

Ported from HGSS_Goldenrod_Gamecorner_Shiny_1.0.cpp.

How it works:
  1. Talks to the prize man and receives the chosen Pokemon (repeated up
     to PRIZE_COUNT times per reset).
  2. Opens the party to view each prize Pokemon.
  3. Checks the sprite region via avg_rgb for shiny colours.
  4. If no shiny: soft resets and repeats.

Setup:
  - Save with coins already in the Coin Case, standing next to the prize
    man and facing him.
  - On first run the script performs the prize sequence once, then asks
    you to draw a region over the prize Pokemon sprite in the party.
  - Configure POKEMON_SLOT (1 = Abra, 2 = Ekans/Sandshrew, 3 = Dratini)
    and PRIZE_COUNT (how many to receive per reset, 1-5).
  - Calibration is saved so subsequent runs skip setup.
  - Delete calibration/hgss_goldenrod_game_corner.json to recalibrate.

Notes:
  - HeartGold prize is Ekans; SoulSilver prize is Sandshrew.
  - Increase timing constants if the game lags behind the script.
"""

import json
import os
import sys
import time
from scripts.base_script import BaseScript


def _cal_path() -> str:
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cal_dir = os.path.join(base, 'calibration')
    os.makedirs(cal_dir, exist_ok=True)
    return os.path.join(cal_dir, 'hgss_goldenrod_game_corner.json')


POKEMON_NAMES = {1: 'Abra', 2: 'Ekans / Sandshrew', 3: 'Dratini'}


class HGSSGoldenrodGameCorner(BaseScript):
    NAME = "HGSS – Goldenrod Game Corner"
    DESCRIPTION = (
        "Soft-resets for a shiny prize Pokemon at the Goldenrod Game Corner "
        "(HeartGold/SoulSilver)."
    )

    # ── Settings ──────────────────────────────────────────────────────────────
    POKEMON_SLOT = 3   # 1 = Abra, 2 = Ekans/Sandshrew, 3 = Dratini
    PRIZE_COUNT  = 1   # how many prize Pokemon to receive per reset (1-5)

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    SOFT_RESET_WAIT   = 10.0   # after S reset for title to reload
    MENU_A_DELAY      = 3.5    # between A presses through title/continue
    TALK_DELAY        = 1.5    # between A presses talking to prize man
    PRIZE_WAIT        = 1.0    # after dialogue opens before navigating
    NAV_DOWN_DELAY    = 0.8    # between Down presses when scrolling prize list
    RECEIVE_A_DELAY   = 1.5    # between A presses to receive prize Pokemon
    CLOSE_B_DELAY     = 1.5    # between B presses to close dialogue
    MENU_X_DELAY      = 1.5    # after X to open menu
    MENU_DOWN_DELAY   = 1.0    # after Down to reach Pokemon in menu
    PARTY_OPEN_DELAY  = 2.5    # after A to open party
    PARTY_NAV_DELAY   = 1.2    # after A to navigate inside party
    PARTY_MON_DELAY   = 2.0    # after Down to land on a party member
    SHINY_RECHECK     = 3.0    # recheck wait before confirming shiny

    COLOUR_TOLERANCE  = 15     # ±tolerance per channel

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("HGSS Goldenrod Game Corner started.")
        log(
            f"Receiving {self.PRIZE_COUNT}× "
            f"{POKEMON_NAMES.get(self.POKEMON_SLOT, str(self.POKEMON_SLOT))} "
            f"per reset."
        )

        cal = self._load_calibration()
        if cal is None:
            log("No calibration — performing first prize sequence, then calibrating.")
            cal = self._first_run_calibrate(
                controller, frame_grabber, stop_event, log, request_calibration
            )
            if stop_event.is_set() or cal is None:
                return
            self._save_calibration(cal)
            log("Calibration saved.")
        else:
            log(f"Calibration loaded from {_cal_path()}")

        rx, ry, rw, rh = cal['region']
        br, bg, bb = cal['baseline']
        tol = cal.get('tolerance', self.COLOUR_TOLERANCE)
        sr_count = 0

        # Initial soft reset to begin the loop cleanly
        controller.soft_reset()
        if not self.wait(self.SOFT_RESET_WAIT, stop_event):
            return

        while not stop_event.is_set():

            # ── Title / continue screen ───────────────────────────────────────
            for _ in range(3):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.MENU_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Receive prize Pokemon ─────────────────────────────────────────
            if not self._receive_prizes(controller, stop_event):
                break

            if stop_event.is_set(): break

            # ── Check party for shiny ─────────────────────────────────────────
            shiny_found = self._check_party(
                controller, frame_grabber, stop_event, log,
                rx, ry, rw, rh, br, bg, bb, tol, sr_count
            )
            if stop_event.is_set(): break

            if shiny_found:
                log("Script paused — catch your shiny! Press ■ Stop when done.")
                stop_event.wait()
                break

            sr_count += 1
            log(f"No shiny. Soft reset #{sr_count}...")
            controller.soft_reset()
            if not self.wait(self.SOFT_RESET_WAIT, stop_event): break

        log("HGSS Goldenrod Game Corner stopped.")

    # ── Receive prizes ────────────────────────────────────────────────────────

    def _receive_prizes(self, controller, stop_event) -> bool:
        """Talk to prize man and receive PRIZE_COUNT copies of POKEMON_SLOT."""
        # Talk to prize man (2 A presses)
        for _ in range(2):
            if stop_event.is_set(): return False
            controller.press_a()
            if not self.wait(self.TALK_DELAY, stop_event): return False

        if not self.wait(self.PRIZE_WAIT, stop_event): return False

        for _ in range(self.PRIZE_COUNT):
            if stop_event.is_set(): return False
            # Navigate down to the chosen Pokemon (slot 1 = no presses needed)
            for _ in range(self.POKEMON_SLOT - 1):
                if stop_event.is_set(): return False
                controller.press_down()
                if not self.wait(self.NAV_DOWN_DELAY, stop_event): return False
            # Receive (3 A presses)
            for _ in range(3):
                if stop_event.is_set(): return False
                controller.press_a()
                if not self.wait(self.RECEIVE_A_DELAY, stop_event): return False

        # Close dialogue (2 B presses)
        for _ in range(2):
            if stop_event.is_set(): return False
            controller.press_b()
            if not self.wait(self.CLOSE_B_DELAY, stop_event): return False

        return True

    # ── Check party ───────────────────────────────────────────────────────────

    def _check_party(self, controller, frame_grabber, stop_event, log,
                     rx, ry, rw, rh, br, bg, bb, tol, sr_count) -> bool:
        """Open party menu and check each prize Pokemon for shiny."""
        # X → Down → A×3 to open party and navigate
        controller.press_x()
        if not self.wait(self.MENU_X_DELAY, stop_event): return False
        controller.press_down()
        if not self.wait(self.MENU_DOWN_DELAY, stop_event): return False
        for _ in range(2):
            if stop_event.is_set(): return False
            controller.press_a()
            if not self.wait(self.PARTY_NAV_DELAY, stop_event): return False
        controller.press_a()
        if not self.wait(self.PARTY_OPEN_DELAY, stop_event): return False

        shiny_found = False
        for i in range(self.PRIZE_COUNT):
            if stop_event.is_set(): break

            controller.press_down()
            if not self.wait(self.PARTY_MON_DELAY, stop_event): break

            frame = frame_grabber.get_latest_frame()
            if frame is None:
                continue

            r, g, b = self.avg_rgb(frame, rx, ry, rw, rh)
            poke_name = POKEMON_NAMES.get(self.POKEMON_SLOT, 'Prize')
            log(
                f"SR #{sr_count + 1} prize {i + 1}: "
                f"R:{r:.0f} G:{g:.0f} B:{b:.0f}  "
                f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f})"
            )

            if (abs(r - br) > tol or abs(g - bg) > tol or abs(b - bb) > tol):
                if not self.wait(self.SHINY_RECHECK, stop_event): break
                frame = frame_grabber.get_latest_frame()
                if frame is None: continue
                r2, g2, b2 = self.avg_rgb(frame, rx, ry, rw, rh)
                if (abs(r2 - br) > tol or
                        abs(g2 - bg) > tol or
                        abs(b2 - bb) > tol):
                    log(
                        f"*** SHINY {poke_name}! "
                        f"R:{r2:.0f} G:{g2:.0f} B:{b2:.0f}  "
                        f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f}) ***"
                    )
                    log(f"Soft resets before shiny: {sr_count}")
                    shiny_found = True
                    break

        # Close party (B)
        controller.press_b()
        self.wait(1.0, stop_event)
        return shiny_found

    # ── First-run calibration ─────────────────────────────────────────────────

    def _first_run_calibrate(self, controller, frame_grabber, stop_event,
                              log, request_calibration):
        """Perform one full prize sequence then ask user to calibrate."""
        log("Navigating to prize Pokemon in party for calibration...")

        if not self._receive_prizes(controller, stop_event):
            return None

        # Open party to view the received Pokemon
        controller.press_x()
        if not self.wait(self.MENU_X_DELAY, stop_event): return None
        controller.press_down()
        if not self.wait(self.MENU_DOWN_DELAY, stop_event): return None
        for _ in range(2):
            if stop_event.is_set(): return None
            controller.press_a()
            if not self.wait(self.PARTY_NAV_DELAY, stop_event): return None
        controller.press_a()
        if not self.wait(self.PARTY_OPEN_DELAY, stop_event): return None

        # Navigate to last party slot (prize Pokemon)
        controller.press_down()
        if not self.wait(self.PARTY_MON_DELAY, stop_event): return None

        log("Prize Pokemon is on screen. Draw a region over its sprite.")
        region = request_calibration("Draw region over the prize Pokemon's sprite")
        if stop_event.is_set():
            return None

        time.sleep(0.1)
        frame = frame_grabber.get_latest_frame()
        if frame is None:
            log("No frame — ensure webcam is connected.")
            return None

        rx, ry, rw, rh = region
        r, g, b = self.avg_rgb(frame, rx, ry, rw, rh)
        log(f"Baseline — R:{r:.1f}  G:{g:.1f}  B:{b:.1f}")
        log("Calibration complete. Default tolerance ±15 applied.")
        log(f"Edit {_cal_path()} to change 'tolerance'.")

        controller.press_b()
        self.wait(1.0, stop_event)
        return {'region': [rx, ry, rw, rh], 'baseline': [r, g, b], 'tolerance': 15}

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_calibration(self):
        path = _cal_path()
        if not os.path.isfile(path):
            return None
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception:
            return None

    def _save_calibration(self, cal: dict):
        with open(_cal_path(), 'w') as f:
            json.dump(cal, f, indent=2)
