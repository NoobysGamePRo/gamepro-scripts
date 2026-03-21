"""
Platinum - Shiny Darkrai
Game: Pokemon Platinum (DS via 3DS)

Soft-resets for shiny Darkrai on Newmoon Island (requires the Member Card
event item).

How it works:
  Navigates from soft reset to Newmoon Island, walks to Darkrai, triggers
  the battle, then checks avg_rgb on Darkrai's sprite.

Setup:
  - Save on Newmoon Island near Darkrai's location (the centre of the island).
  - The player should already be at the entrance to the clearing where Darkrai
    appears at night.
  - On first run, let the battle start and draw a region over Darkrai's sprite.
  - Delete calibration/platinum_shiny_darkrai.json to recalibrate.

Timing notes:
  Darkrai's encounter uses the same LDR-timing structure as other DPPt
  legendaries. Adjust BATTLE_LOAD_WAIT if detection fires too early/late.
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
    return os.path.join(cal_dir, 'platinum_shiny_darkrai.json')


class PlatinumShinyDarkrai(BaseScript):
    NAME = "Platinum - Shiny Darkrai"
    DESCRIPTION = "Soft-resets for shiny Darkrai on Newmoon Island (Platinum)."

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    SOFT_RESET_WAIT    = 12.0
    MENU_A_1_DELAY     = 4.0
    MENU_A_2_DELAY     = 5.0
    MENU_A_3_DELAY     = 5.0
    APPROACH_A_DELAY   = 3.0    # after A to walk/interact with Darkrai
    BATTLE_LOAD_WAIT   = 10.0   # wait for battle screen
    SHINY_RECHECK_WAIT = 3.0

    COLOUR_TOLERANCE   = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("Platinum - Shiny Darkrai started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Trigger the Darkrai battle, wait for the battle screen to "
                "load, then draw a region over Darkrai's sprite.")
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

        log(f"Darkrai region: x={x} y={y} w={w} h={h} | tolerance ±{tolerance}")
        log("Soft reset loop running. Press Stop at any time.")

        sr_count = 0

        controller.soft_reset()
        if not self.wait(self.SOFT_RESET_WAIT, stop_event):
            return

        while not stop_event.is_set():

            controller.press_a()
            if not self.wait(self.MENU_A_1_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.MENU_A_2_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.MENU_A_3_DELAY, stop_event): break

            # Approach Darkrai
            controller.press_a()
            if not self.wait(self.APPROACH_A_DELAY, stop_event): break

            if not self.wait(self.BATTLE_LOAD_WAIT, stop_event): break

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
                                f"*** SHINY DARKRAI! "
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

        log("Platinum - Shiny Darkrai stopped.")

    def _calibrate(self, controller, frame_grabber, stop_event,
                   log, request_calibration):
        log("Draw a region over Darkrai's battle sprite.")
        region = request_calibration("Draw region over Darkrai's sprite")
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
