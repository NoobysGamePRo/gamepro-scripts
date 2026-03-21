"""
B2W2 - Shiny Starter
Game: Pokemon Black 2 / White 2 (DS via 3DS)

Soft-resets for a shiny Snivy, Tepig, or Oshawott from Bianca in Aspertia
City.

Ported from B2W2_Shiny_Starter_1.2.cpp.

How it works:
  Navigates from soft reset through the title/continue menus to Bianca's
  starter selection event, then checks avg_rgb on the Pokemon's summary
  screen.

Starter selection:
  Set STARTER = 'snivy', 'tepig', or 'oshawott'.
  - Snivy:    Left x1 from default (centre)
  - Tepig:    Centre (default)
  - Oshawott: Right x1 from default

Setup:
  - Save in Aspertia City facing Bianca (or wherever starter selection starts).
  - On first run, navigate to the Pokemon summary screen and draw a region
    over the starter's sprite.
  - Delete calibration/b2w2_shiny_starter.json to recalibrate.
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
    return os.path.join(cal_dir, 'b2w2_shiny_starter.json')


class B2W2ShinyStarter(BaseScript):
    NAME = "B2W2 - Shiny Starter"
    DESCRIPTION = "Soft-resets for a shiny starter (Black 2/White 2)."

    # ── Starter choice ────────────────────────────────────────────────────────
    # 'snivy' (grass/left), 'tepig' (fire/centre), 'oshawott' (water/right)
    STARTER = 'tepig'

    # ── Timing (seconds) — derived from B2W2_Shiny_Starter_1.2.cpp ──────────
    SOFT_RESET_WAIT    = 12.0   # DS reload
    MENU_A_1_DELAY     = 1.6    # A1 (title screen × 3)
    MENU_A_2_DELAY     = 1.6
    MENU_A_3_DELAY     = 1.6
    MENU_A_4_WAIT      = 1.8    # extra wait before long load
    MENU_A_4_DELAY     = 9.0    # A4 — long load in B2W2
    BIANCA_A_COUNT     = 4      # A presses through Bianca's text
    BIANCA_A_DELAY     = 1.2
    PRE_CHOICE_WAIT    = 5.5    # wait for Bianca to display starters
    NAV_DELAY          = 1.0    # after L/R to select starter
    CHOOSE_A_DELAY     = 1.5    # A × 2 to select and confirm
    POST_CHOOSE_WAIT   = 7.0    # wait for receive animation
    POST_CHOOSE_A1     = 1.2    # A × 2 after receive
    POST_CHOOSE_A2     = 1.2
    NICKNAME_B_DELAY   = 1.2    # B to decline nickname
    POKEDEX_A_DELAY    = 3.5    # A to receive Pokédex
    MISC_A_COUNT       = 6      # A × 6 misc dialogue
    MISC_A_DELAY       = 1.2
    SUMMARY_X_DELAY    = 1.5    # X to open menu
    SUMMARY_A_DELAY    = 2.5    # A to open Pokemon list
    SUMMARY_A2_DELAY   = 1.2    # A to open summary
    SUMMARY_A3_DELAY   = 3.0    # A to flip to sprite page
    SHINY_RECHECK_WAIT = 3.0

    COLOUR_TOLERANCE   = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("B2W2 - Shiny Starter started.")
        log(f"Starter: {self.STARTER.title()}")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Navigate to the starter's summary screen, then draw a "
                "region over its sprite.")
            cal = self._calibrate(
                controller, frame_grabber, stop_event, log, request_calibration
            )
            if stop_event.is_set() or cal is None:
                return
            self._save_calibration(cal)
            log("Calibration saved.")
        else:
            log(f"Calibration loaded from {_cal_path()}")

        x, y, w, h = cal['region']
        br, bg, bb = cal['baseline']
        tolerance  = cal.get('tolerance', self.COLOUR_TOLERANCE)

        log(f"Starter region: x={x} y={y} w={w} h={h} | tolerance ±{tolerance}")
        log("Soft reset loop running. Press Stop at any time.")

        sr_count = 0

        controller.soft_reset()
        if not self.wait(self.SOFT_RESET_WAIT, stop_event):
            return

        while not stop_event.is_set():

            # ── Navigate title / continue menus ───────────────────────────
            controller.press_a()
            if not self.wait(self.MENU_A_1_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.MENU_A_2_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.MENU_A_3_DELAY, stop_event): break
            if not self.wait(self.MENU_A_4_WAIT, stop_event): break
            controller.press_a()
            if not self.wait(self.MENU_A_4_DELAY, stop_event): break

            # ── Talk to Bianca ────────────────────────────────────────────
            for _ in range(self.BIANCA_A_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.BIANCA_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            if not self.wait(self.PRE_CHOICE_WAIT, stop_event): break

            # ── Navigate to chosen starter ────────────────────────────────
            controller.press_a()
            if not self.wait(1.5, stop_event): break

            if self.STARTER == 'snivy':
                controller.press_left()
                if not self.wait(self.NAV_DELAY, stop_event): break
            elif self.STARTER == 'oshawott':
                controller.press_right()
                if not self.wait(self.NAV_DELAY, stop_event): break

            # ── Select and confirm ────────────────────────────────────────
            controller.press_a()
            if not self.wait(self.CHOOSE_A_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.POST_CHOOSE_WAIT, stop_event): break

            # ── Post-receive dialogue ─────────────────────────────────────
            controller.press_a()
            if not self.wait(self.POST_CHOOSE_A1, stop_event): break
            controller.press_a()
            if not self.wait(self.POST_CHOOSE_A2, stop_event): break

            # B to decline nickname
            controller.press_b()
            if not self.wait(self.NICKNAME_B_DELAY, stop_event): break

            # A to accept Pokédex
            controller.press_a()
            if not self.wait(self.POKEDEX_A_DELAY, stop_event): break

            for _ in range(self.MISC_A_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.MISC_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Open summary to check starter ─────────────────────────────
            controller.press_x()
            if not self.wait(self.SUMMARY_X_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.SUMMARY_A_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.SUMMARY_A2_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.SUMMARY_A3_DELAY, stop_event): break

            # ── Shiny check ───────────────────────────────────────────────
            frame = frame_grabber.get_latest_frame()
            shiny_found = False

            if frame is not None:
                r, g, b = self.avg_rgb(frame, x, y, w, h)
                if (abs(r - br) > tolerance or
                        abs(g - bg) > tolerance or
                        abs(b - bb) > tolerance):
                    if not self.wait(self.SHINY_RECHECK_WAIT, stop_event): break
                    frame = frame_grabber.get_latest_frame()
                    if frame is not None:
                        r2, g2, b2 = self.avg_rgb(frame, x, y, w, h)
                        if (abs(r2 - br) > tolerance or
                                abs(g2 - bg) > tolerance or
                                abs(b2 - bb) > tolerance):
                            log(
                                f"*** SHINY {self.STARTER.title()}! "
                                f"R:{r2:.0f} G:{g2:.0f} B:{b2:.0f}  "
                                f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f}) ***"
                            )
                            log(f"Soft resets before shiny: {sr_count}")
                            shiny_found = True

            if stop_event.is_set(): break

            if shiny_found:
                log("Script paused — catch your shiny! Press Stop when done.")
                stop_event.wait()
                break

            sr_count += 1
            log(f"No shiny. Soft reset #{sr_count}...")
            controller.soft_reset()
            if not self.wait(self.SOFT_RESET_WAIT, stop_event): break

        log("B2W2 - Shiny Starter stopped.")

    def _calibrate(self, controller, frame_grabber, stop_event,
                   log, request_calibration):
        log("Draw a region over the starter's sprite on the summary screen.")
        region = request_calibration(f"Draw region over {self.STARTER.title()}'s sprite")
        if stop_event.is_set():
            return None
        x, y, w, h = region
        time.sleep(0.1)
        frame = frame_grabber.get_latest_frame()
        if frame is None:
            log("No frame — ensure webcam is connected.")
            return None
        r, g, b = self.avg_rgb(frame, x, y, w, h)
        log(f"Baseline — R:{r:.1f}  G:{g:.1f}  B:{b:.1f}")
        return {'region': [x, y, w, h], 'baseline': [r, g, b], 'tolerance': 15}

    def _load_calibration(self):
        path = _cal_path()
        if not os.path.isfile(path):
            return None
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception:
            return None

    def _save_calibration(self, cal):
        with open(_cal_path(), 'w') as f:
            json.dump(cal, f, indent=2)
