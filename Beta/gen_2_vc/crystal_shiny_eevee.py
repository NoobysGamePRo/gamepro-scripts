"""
Crystal - Shiny Eevee
Game: Pokemon Crystal (3DS Virtual Console)

Soft-resets for the shiny Eevee gift from Bill in Goldenrod City.

Ported from VC_Crystal_Shiny_Eevee_2.0.cpp.

How it works:
  1. Calibrate a region over Eevee's sprite on the party/summary screen.
  2. The script presses A through Bill's dialogue and the receiving sequence,
     then opens the party/Pokemon menu to check Eevee's sprite colour.
  3. If the average RGB differs from the baseline by more than the tolerance,
     a shiny is detected.

Setup:
  - Save outside Bill's house in Goldenrod City (or just inside, facing Bill).
  - On first run, navigate to Bill's dialogue, receive the Eevee, and draw a
    region over its sprite in the party or summary screen when prompted.
  - Delete calibration/crystal_shiny_eevee.json to force recalibration.
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
    return os.path.join(cal_dir, 'crystal_shiny_eevee.json')


class CrystalShinyEevee(BaseScript):
    NAME = "Crystal - Shiny Eevee"
    DESCRIPTION = "Soft-resets for the shiny Eevee gift from Bill (Crystal VC)."

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    SOFT_RESET_WAIT    = 5.0    # after Z reset for VC to reload
    MENU_A_DELAY       = 1.4    # between A presses through title/continue
    BILL_DIALOGUE_1    = 4.0    # wait after first A to Bill (talk delay)
    BILL_DIALOGUE_2    = 5.0    # wait after second A (Bill asks about Eevee)
    BILL_A_DELAY       = 1.5    # between A presses through Bill's text (x5)
    RECEIVE_DELAY      = 1.5    # between A presses to receive Eevee (x3)
    PRE_NICKNAME_WAIT  = 5.0    # wait for nickname prompt to appear
    NICKNAME_DELAY     = 1.3    # between A presses through nickname prompts
    POST_RECEIVE_DELAY = 2.0    # after declining nickname
    EXIT_DELAY         = 1.5    # between A presses after receiving (x2)
    CHECK_X_DELAY      = 1.3    # after X to open menu
    CHECK_DOWN_DELAY   = 1.3    # after Down to reach Pokemon menu item
    CHECK_A_DELAY      = 1.4    # after A to open Pokemon list
    CHECK_RIGHT_DELAY  = 1.4    # after Right (Summary screen)
    CHECK_A2_DELAY     = 1.4    # A presses on summary screen (x2)
    SHINY_RECHECK_WAIT = 3.0    # wait before confirming suspected shiny

    COLOUR_TOLERANCE   = 15     # ±tolerance per channel

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("Crystal - Shiny Eevee started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Receive Eevee from Bill manually, then navigate to the party "
                "summary screen so Eevee's sprite is visible.")
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

        log(f"Eevee region: x={x} y={y} w={w} h={h} | tolerance ±{tolerance}")
        log("Starting soft reset loop. Press Stop at any time.")

        sr_count = 0

        # Initial reset to get into the loop
        controller.soft_reset_z()
        if not self.wait(self.SOFT_RESET_WAIT, stop_event):
            return

        while not stop_event.is_set():

            # ── Title / continue screen (4 A presses) ────────────────────
            for _ in range(4):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.MENU_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Talk to Bill ──────────────────────────────────────────────
            controller.press_a()
            if not self.wait(self.BILL_DIALOGUE_1, stop_event): break

            controller.press_a()
            if not self.wait(self.BILL_DIALOGUE_2, stop_event): break

            # Bill's dialogue (5 A presses through his speech)
            for _ in range(5):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.BILL_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Receive Eevee (3 A presses) ───────────────────────────────
            for _ in range(3):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.RECEIVE_DELAY, stop_event): break
            if stop_event.is_set(): break

            if not self.wait(self.PRE_NICKNAME_WAIT, stop_event): break

            # ── Nickname prompt ───────────────────────────────────────────
            # Press A once for "Give nickname?" then B to decline
            controller.press_a()
            if not self.wait(self.NICKNAME_DELAY, stop_event): break

            controller.press_b()   # decline nickname
            if not self.wait(self.POST_RECEIVE_DELAY, stop_event): break

            # ── Post-receive text (2 more A presses) ─────────────────────
            for _ in range(2):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.EXIT_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Open party/summary to check Eevee ────────────────────────
            controller.press_x()
            if not self.wait(self.CHECK_X_DELAY, stop_event): break

            controller.press_down()
            if not self.wait(self.CHECK_DOWN_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.CHECK_A_DELAY, stop_event): break

            controller.press_right()
            if not self.wait(self.CHECK_RIGHT_DELAY, stop_event): break

            for _ in range(2):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.CHECK_A2_DELAY, stop_event): break
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
                                f"*** SHINY EEVEE! "
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
            controller.soft_reset_z()
            if not self.wait(self.SOFT_RESET_WAIT, stop_event): break

        log("Crystal - Shiny Eevee stopped.")

    # ── Calibration ───────────────────────────────────────────────────────────

    def _calibrate(self, controller, frame_grabber, stop_event,
                   log, request_calibration):
        log("Navigate to Eevee's sprite in the party/summary screen, "
            "then draw a region over it.")

        region = request_calibration("Draw region over Eevee's sprite")
        if stop_event.is_set():
            return None

        x, y, w, h = region
        time.sleep(0.1)
        frame = frame_grabber.get_latest_frame()
        if frame is None:
            log("No frame available — ensure webcam is connected.")
            return None

        r, g, b = self.avg_rgb(frame, x, y, w, h)
        log(f"Eevee baseline — R:{r:.1f}  G:{g:.1f}  B:{b:.1f}")
        log("Calibration complete. Default tolerance ±15 applied.")
        log("Edit calibration/crystal_shiny_eevee.json to change 'tolerance'.")
        return {'region': [x, y, w, h], 'baseline': [r, g, b], 'tolerance': 15}

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
