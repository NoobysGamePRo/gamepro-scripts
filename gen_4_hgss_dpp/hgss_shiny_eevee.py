"""
HGSS - Shiny Eevee
Game: Pokemon HeartGold / SoulSilver (DS via 3DS)

Soft-resets for the shiny Eevee gift from Bill in Goldenrod City.

Ported from HGSS_Shiny_Eevee_2.0.cpp.

How it works:
  - Navigates through the soft reset menu, talks to Bill, receives Eevee,
    then opens the party/summary screen to check Eevee's sprite colour
    via avg_rgb comparison against a calibrated baseline.
  - If colour differs from baseline by more than tolerance, shiny detected.

Setup:
  - Save outside Bill's house in Goldenrod City (or just inside facing Bill).
  - On first run, calibrate a region over Eevee's sprite on the summary screen.
  - Delete calibration/hgss_shiny_eevee.json to force recalibration.
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
    return os.path.join(cal_dir, 'hgss_shiny_eevee.json')


class HGSSShinyEevee(BaseScript):
    NAME = "HGSS - Shiny Eevee"
    DESCRIPTION = "Soft-resets for the shiny Eevee gift from Bill (HeartGold/SoulSilver)."

    # ── Timing (seconds) — from HGSS_Shiny_Eevee_2.0.cpp ─────────────────────
    SOFT_RESET_WAIT    = 12.0   # after L+R+Start+Select for DS to reload
    MENU_A_1_DELAY     = 4.0    # after first A (title screen)
    MENU_A_2_DELAY     = 5.0    # after second A (continue)
    MENU_A_3_DELAY     = 5.0    # after third A (loading world)
    BILL_A_DELAY       = 1.5    # between A presses through Bill's talk (x5)
    EXTRA_WAIT         = 1.0    # brief extra after Bill text block
    RECEIVE_A_DELAY    = 1.5    # A presses to receive Eevee (x3)
    PRE_NICKNAME_WAIT  = 5.0    # wait before nickname prompt
    DECLINE_DELAY      = 3.0    # after B to decline nickname
    POST_RECEIVE_DELAY = 1.5    # A presses after receiving (x2)
    # Check sequence (X → Down → A → Right → A × 2)
    CHECK_X_DELAY      = 1.3
    CHECK_DOWN_DELAY   = 1.3
    CHECK_A_DELAY      = 1.4
    CHECK_RIGHT_DELAY  = 1.4
    CHECK_A2_DELAY     = 1.4
    EXTRA_SETTLE_WAIT  = 1.5    # wait before sampling
    SHINY_RECHECK_WAIT = 3.0

    COLOUR_TOLERANCE   = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("HGSS - Shiny Eevee started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Receive Eevee from Bill, open its summary screen, "
                "then draw a region over its sprite.")
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

        controller.soft_reset()
        if not self.wait(self.SOFT_RESET_WAIT, stop_event):
            return

        while not stop_event.is_set():

            # ── Title / continue / load ───────────────────────────────────
            controller.press_a()
            if not self.wait(self.MENU_A_1_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.MENU_A_2_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.MENU_A_3_DELAY, stop_event): break

            # ── Talk to Bill ──────────────────────────────────────────────
            for _ in range(5):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.BILL_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            if not self.wait(self.EXTRA_WAIT, stop_event): break

            # ── Receive Eevee ─────────────────────────────────────────────
            for _ in range(3):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.RECEIVE_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            if not self.wait(self.PRE_NICKNAME_WAIT, stop_event): break

            controller.press_b()   # decline nickname
            if not self.wait(self.DECLINE_DELAY, stop_event): break

            for _ in range(2):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.POST_RECEIVE_DELAY, stop_event): break
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

            if not self.wait(self.EXTRA_SETTLE_WAIT, stop_event): break

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
            controller.soft_reset()
            if not self.wait(self.SOFT_RESET_WAIT, stop_event): break

        log("HGSS - Shiny Eevee stopped.")

    # ── Calibration ───────────────────────────────────────────────────────────

    def _calibrate(self, controller, frame_grabber, stop_event,
                   log, request_calibration):
        log("With Eevee's summary screen visible, draw a region over its sprite.")

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
        log("Edit calibration/hgss_shiny_eevee.json to change 'tolerance'.")
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
