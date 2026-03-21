"""
ORAS - Shiny Starter
Game: Pokemon Omega Ruby / Alpha Sapphire (3DS)

Soft-resets for a shiny Treecko, Torchic, or Mudkip from the bag Professor
Birch leaves behind when he is attacked on Route 101.

Ported from ORAS_Shiny_Starter_2.0.cpp.

How it works:
  Navigates from soft reset through the title/continue menus, walks into
  the Birch encounter, chooses the starter, then checks avg_rgb on the
  Pokemon's summary screen.

Starter selection:
  Set STARTER = 'treecko', 'torchic', or 'mudkip'.
  - Treecko:  Left from centre
  - Torchic:  Centre (default)
  - Mudkip:   Right from centre

Setup:
  - Save on Route 101 just before the Birch cutscene begins, or at the
    first available save point prior to starter selection.
  - On first run, navigate to the starter's summary screen and draw a
    region over its sprite.
  - Delete calibration/oras_shiny_starter.json to recalibrate.
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
    return os.path.join(cal_dir, 'oras_shiny_starter.json')


class ORASShinyStarter(BaseScript):
    NAME = "ORAS - Shiny Starter"
    DESCRIPTION = "Soft-resets for a shiny starter (ORAS)."

    # ── Starter choice ────────────────────────────────────────────────────────
    # 'treecko' (grass/left), 'torchic' (fire/centre), 'mudkip' (water/right)
    STARTER = 'torchic'

    # ── Timing (seconds) — from ORAS_Shiny_Starter_2.0.cpp ──────────────────
    SOFT_RESET_WAIT    = 13.0   # DS reload
    MENU_A_1_DELAY     = 4.0    # title
    MENU_A_2_DELAY     = 5.5    # continue
    MENU_A_3_DELAY     = 6.0    # long load
    MENU_A_4_DELAY     = 4.5    # walk/interact
    MENU_A_5_DELAY     = 1.5    # confirm
    PRE_CHOICE_WAIT    = 2.5    # wait before navigation
    NAV_DELAY          = 1.2    # after L/R to select starter
    CHOOSE_A_1_DELAY   = 1.2    # first A on bag
    CHOOSE_A_2_DELAY   = 1.2    # confirm A
    CHOOSE_A_3_DELAY   = 1.2    # third A
    POST_CHOOSE_WAIT   = 11.5   # long wait — receive animation
    NICKNAME_B_COUNT   = 4      # B presses to skip nickname prompt
    NICKNAME_B_DELAY   = 1.0
    MISC_A1_COUNT      = 6      # A × 6 misc dialogue
    MISC_A1_DELAY      = 1.0
    POST_MISC_WAIT     = 3.0
    MISC_A2_COUNT      = 8      # A × 8 more dialogue
    MISC_A2_DELAY      = 1.0
    POST_MISC2_WAIT    = 3.0
    MISC_A3_COUNT      = 3      # A × 3
    MISC_A3_DELAY      = 1.0
    POST_MISC3_WAIT    = 3.5
    MISC_A4_COUNT      = 5      # A × 5
    MISC_A4_DELAY      = 1.0
    POST_MISC4_WAIT    = 4.0
    MISC_A5_COUNT      = 2      # A × 2
    MISC_A5_DELAY      = 1.0
    WALK_HOLD_R_DELAY  = 1.2    # hold right × 2 + hold down × 2 to walk
    WALK_HOLD_D_DELAY  = 2.4
    POST_WALK_WAIT     = 2.0
    PRE_SUMMARY_A_COUNT = 2     # A × 2 before summary
    PRE_SUMMARY_A_DELAY = 2.5
    SUMMARY_DELAY      = 1.0    # CHECK_DELAY equivalent
    SHINY_RECHECK_WAIT = 3.0

    COLOUR_TOLERANCE   = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("ORAS - Shiny Starter started.")
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

            # ── Navigate title/continue menus ─────────────────────────────
            controller.press_a()
            if not self.wait(self.MENU_A_1_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.MENU_A_2_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.MENU_A_3_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.MENU_A_4_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.MENU_A_5_DELAY, stop_event): break

            if not self.wait(self.PRE_CHOICE_WAIT, stop_event): break

            # ── Navigate to chosen starter ────────────────────────────────
            if self.STARTER == 'treecko':
                controller.press_left()
                if not self.wait(self.NAV_DELAY, stop_event): break
            elif self.STARTER == 'mudkip':
                controller.press_right()
                if not self.wait(self.NAV_DELAY, stop_event): break

            # ── Select and confirm ────────────────────────────────────────
            controller.press_a()
            if not self.wait(self.CHOOSE_A_1_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.CHOOSE_A_2_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.CHOOSE_A_3_DELAY, stop_event): break

            if not self.wait(self.POST_CHOOSE_WAIT, stop_event): break

            # ── Skip nickname prompt ──────────────────────────────────────
            for _ in range(self.NICKNAME_B_COUNT):
                if stop_event.is_set(): break
                controller.press_b()
                if not self.wait(self.NICKNAME_B_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Misc dialogue ─────────────────────────────────────────────
            for _ in range(self.MISC_A1_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.MISC_A1_DELAY, stop_event): break
            if stop_event.is_set(): break

            if not self.wait(self.POST_MISC_WAIT, stop_event): break

            for _ in range(self.MISC_A2_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.MISC_A2_DELAY, stop_event): break
            if stop_event.is_set(): break

            if not self.wait(self.POST_MISC2_WAIT, stop_event): break

            for _ in range(self.MISC_A3_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.MISC_A3_DELAY, stop_event): break
            if stop_event.is_set(): break

            if not self.wait(self.POST_MISC3_WAIT, stop_event): break

            for _ in range(self.MISC_A4_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.MISC_A4_DELAY, stop_event): break
            if stop_event.is_set(): break

            if not self.wait(self.POST_MISC4_WAIT, stop_event): break

            for _ in range(self.MISC_A5_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.MISC_A5_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Walk to trigger rival battle ──────────────────────────────
            for _ in range(2):
                if stop_event.is_set(): break
                controller.hold_right()
                if not self.wait(self.WALK_HOLD_R_DELAY, stop_event):
                    controller.release_all()
                    break
                controller.hold_down()
                if not self.wait(self.WALK_HOLD_D_DELAY, stop_event):
                    controller.release_all()
                    break
            controller.release_all()
            if stop_event.is_set(): break

            if not self.wait(self.POST_WALK_WAIT, stop_event): break

            # ── A × 2 before summary ──────────────────────────────────────
            for _ in range(self.PRE_SUMMARY_A_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.PRE_SUMMARY_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Open summary ──────────────────────────────────────────────
            controller.press_x()
            if not self.wait(self.SUMMARY_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.SUMMARY_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.SUMMARY_DELAY, stop_event): break
            controller.press_right()
            if not self.wait(self.SUMMARY_DELAY, stop_event): break
            for _ in range(2):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.SUMMARY_DELAY, stop_event): break
            if stop_event.is_set(): break

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

        log("ORAS - Shiny Starter stopped.")

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
