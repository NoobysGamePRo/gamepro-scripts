"""
XY - Shiny Starters
Game: Pokemon X / Y (3DS)

Soft-resets for a shiny Chespin, Fennekin, or Froakie from Professor
Sycamore in Lumiose City.

Ported from XY_Shiny_Starters_2.0.cpp.

How it works:
  Navigates from soft reset through title/continue menus, walks to
  Sycamore's lab, navigates to the starter suitcase, then checks avg_rgb
  on the Pokemon's summary screen.

Starter selection:
  Set STARTER = 'chespin', 'fennekin', or 'froakie'.
  - Chespin:  Left from centre
  - Fennekin: Centre (default)
  - Froakie:  Right from centre

Setup:
  - Save in Lumiose City just before entering Sycamore's lab, or wherever
    is most convenient before starter selection.
  - On first run, navigate to the starter's summary screen and draw a
    region over its sprite.
  - Delete calibration/xy_shiny_starters.json to recalibrate.
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
    return os.path.join(cal_dir, 'xy_shiny_starters.json')


class XYShinyStarters(BaseScript):
    NAME = "XY - Shiny Starters"
    DESCRIPTION = "Soft-resets for a shiny starter from Professor Sycamore (X/Y)."

    # ── Starter choice ────────────────────────────────────────────────────────
    # 'chespin' (grass/left), 'fennekin' (fire/centre), 'froakie' (water/right)
    STARTER = 'fennekin'

    # ── Timing (seconds) — derived from XY_Shiny_Starters_2.0.cpp ───────────
    SOFT_RESET_WAIT    = 10.0   # 3DS reload
    MENU_A_1_DELAY     = 4.0    # menuDelay (user-tunable in C++, default ~4 s)
    MENU_A_2_DELAY     = 5.0    # continue
    HOLD_LEFT_DELAY    = 0.8    # hold left to face bag
    RELEASE_WAIT       = 3.0    # settle
    CHOOSE_A_1_DELAY   = 1.0    # A × 2 to open bag
    CHOOSE_A_2_DELAY   = 1.0
    PRE_NAV_WAIT       = 2.5    # wait before starter navigation
    NAV_DELAY          = 1.5    # after L/R to navigate to starter
    CONFIRM_A_1_DELAY  = 2.5    # A confirm
    CONFIRM_A_2_DELAY  = 11.5   # long wait — receive animation
    NICKNAME_B_COUNT   = 4      # B × 4 to skip nickname
    NICKNAME_B_DELAY   = 1.0
    MISC_A1_COUNT      = 6      # misc dialogue A presses
    MISC_A1_DELAY      = 1.0
    POST_MISC1_WAIT    = 3.0
    MISC_A2_COUNT      = 8
    MISC_A2_DELAY      = 1.0
    POST_MISC2_WAIT    = 3.0
    MISC_A3_COUNT      = 3
    MISC_A3_DELAY      = 1.0
    POST_MISC3_WAIT    = 3.5
    MISC_A4_COUNT      = 5
    MISC_A4_DELAY      = 1.0
    POST_MISC4_WAIT    = 4.0
    MISC_A5_COUNT      = 2
    MISC_A5_DELAY      = 1.0
    POST_MISC5_WAIT    = 3.0
    MISC_A6_COUNT      = 2
    MISC_A6_DELAY      = 1.0
    PRE_SUMMARY_WAIT   = 6.0
    PRE_SUMMARY_A      = 1      # final A before summary
    PRE_SUMMARY_A_DELAY = 7.0   # last long wait before summary check
    SUMMARY_DELAY      = 1.0
    SHINY_RECHECK_WAIT = 3.0

    COLOUR_TOLERANCE   = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("XY - Shiny Starters started.")
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

            # ── Hold left to face/approach the bag ────────────────────────
            controller.hold_left()
            if not self.wait(self.HOLD_LEFT_DELAY, stop_event):
                controller.release_all()
                break
            controller.release_all()
            if not self.wait(self.RELEASE_WAIT, stop_event): break

            # ── Open bag ──────────────────────────────────────────────────
            controller.press_a()
            if not self.wait(self.CHOOSE_A_1_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.CHOOSE_A_2_DELAY, stop_event): break

            if not self.wait(self.PRE_NAV_WAIT, stop_event): break

            # ── Navigate to chosen starter ────────────────────────────────
            if self.STARTER == 'chespin':
                controller.press_left()
                if not self.wait(self.NAV_DELAY, stop_event): break
            elif self.STARTER == 'froakie':
                controller.press_right()
                if not self.wait(self.NAV_DELAY, stop_event): break

            # ── Confirm selection ─────────────────────────────────────────
            controller.press_a()
            if not self.wait(self.CONFIRM_A_1_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.CONFIRM_A_2_DELAY, stop_event): break

            # ── Skip nickname ─────────────────────────────────────────────
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
            if not self.wait(self.POST_MISC1_WAIT, stop_event): break

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
            if not self.wait(self.POST_MISC5_WAIT, stop_event): break

            for _ in range(self.MISC_A6_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.MISC_A6_DELAY, stop_event): break
            if stop_event.is_set(): break

            if not self.wait(self.PRE_SUMMARY_WAIT, stop_event): break
            controller.press_a()
            if not self.wait(self.PRE_SUMMARY_A_DELAY, stop_event): break

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

        log("XY - Shiny Starters stopped.")

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
