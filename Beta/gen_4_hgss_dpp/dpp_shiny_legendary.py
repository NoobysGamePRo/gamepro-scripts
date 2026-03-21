"""
DPPt - Shiny Legendary
Game: Pokemon Diamond / Pearl / Platinum (DS via 3DS)

Generic soft-reset shiny hunter for miscellaneous static legendaries in
Diamond, Pearl, and Platinum. Works for: Giratina, Rotom, Cresselia,
Uxie, Mesprit, Azelf, Heatran, Regigigas, and others.

How it works:
  Navigates from soft reset through the title screen, loads the save,
  interacts with the legendary, then checks its battle sprite colour.

Setup:
  - Save directly in front of / approaching the legendary Pokemon.
  - On first run, start the battle and draw a region over the legendary's
    battle sprite.
  - Delete calibration/dpp_shiny_legendary.json to recalibrate.
  - Adjust APPROACH_A_COUNT and BATTLE_LOAD_WAIT for the specific legendary.
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
    return os.path.join(cal_dir, 'dpp_shiny_legendary.json')


class DPPShinyLegendary(BaseScript):
    NAME = "DPPt - Shiny Legendary"
    DESCRIPTION = (
        "Soft-resets for miscellaneous shiny legendaries in Diamond/Pearl/Platinum "
        "(Giratina, Cresselia, lake trio, etc.)."
    )

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    SOFT_RESET_WAIT    = 12.0   # DS reload
    MENU_A_1_DELAY     = 4.0
    MENU_A_2_DELAY     = 5.0
    MENU_A_3_DELAY     = 5.0
    APPROACH_A_COUNT   = 1      # number of A presses to trigger the battle
    APPROACH_A_DELAY   = 3.0    # delay between approach A presses
    BATTLE_LOAD_WAIT   = 10.0   # wait for battle screen to load
    SHINY_RECHECK_WAIT = 3.0

    COLOUR_TOLERANCE   = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("DPPt - Shiny Legendary started.")
        log(f"Approach A presses: {self.APPROACH_A_COUNT} | "
            f"Battle load wait: {self.BATTLE_LOAD_WAIT}s")
        log("Adjust APPROACH_A_COUNT and BATTLE_LOAD_WAIT in the script "
            "constants for your specific legendary.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Start the battle manually, wait for the legendary sprite to "
                "appear, then draw a region over it.")
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

        log(f"Legendary region: x={x} y={y} w={w} h={h} | tolerance ±{tolerance}")
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

            # Approach/interact with legendary
            for _ in range(self.APPROACH_A_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.APPROACH_A_DELAY, stop_event): break
            if stop_event.is_set(): break

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
                                f"*** SHINY LEGENDARY! "
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

        log("DPPt - Shiny Legendary stopped.")

    def _calibrate(self, controller, frame_grabber, stop_event,
                   log, request_calibration):
        log("Draw a region over the legendary's battle sprite.")
        region = request_calibration("Draw region over the legendary's sprite")
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
