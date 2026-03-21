"""
HGSS Shiny Starter — HeartGold / SoulSilver starter shiny hunter.

Ported from HGSS_Shiny_Starter.cpp.

How it works:
  1. On first run, calibration: the user draws a region for each of the three
     starters on the live video feed. The average RGB of each region is stored
     as the "normal" baseline. A tolerance value is entered via the log.
  2. The automation loop:
       - Navigates to the starter selection screen (button presses with delays)
       - Reads the average RGB of each starter region
       - If any region differs from its baseline by more than the tolerance, a
         shiny has been detected — the script pauses and logs the discovery
       - Otherwise does a soft reset and tries again
  3. Calibration is saved to a JSON file next to the script so it persists
     between sessions. Delete the JSON file to force recalibration.

Save file note: save the game immediately before the starter selection screen,
inside the lab, before talking to the professor's aide.
"""

import json
import os
import sys
import time
import threading
from scripts.base_script import BaseScript

# Number of starters to calibrate (Chikorita, Cyndaquil, Totodile)
NUM_STARTERS = 3

# Where calibration data is stored
def _cal_path() -> str:
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cal_dir = os.path.join(base, 'calibration')
    os.makedirs(cal_dir, exist_ok=True)
    return os.path.join(cal_dir, 'hgss_shiny_starter.json')


class HGSSShinyStarter(BaseScript):
    NAME = "HGSS Shiny Starter"
    DESCRIPTION = (
        "Automatically soft-resets HeartGold/SoulSilver until a shiny starter "
        "is found. Requires calibration on first run."
    )

    # Button timing (milliseconds → converted to seconds for wait())
    MENU_DELAY_1 = 5.0    # after first A press
    MENU_DELAY_2 = 7.0    # after second A press
    MENU_DELAY_3 = 4.0    # after third A press
    MENU_DELAY_4 = 4.0    # after fourth A press
    ENCOUNTER_DELAY = 3.0 # after final A (before starters appear)
    LEFT_MOVE_DELAY = 1.5 # after pressing Left to scroll starters
    SHINY_RECHECK_DELAY = 3.0  # wait before re-checking a suspected shiny
    SOFT_RESET_DELAY = 12.0    # wait after soft reset for game to reload

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("HGSS Shiny Starter started.")

        # ── Load or create calibration ────────────────────────────────────────
        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting calibration for all 3 starters.")
            cal = self._calibrate(
                controller, frame_grabber, stop_event, log, request_calibration
            )
            if stop_event.is_set() or cal is None:
                return
            self._save_calibration(cal)
            log("Calibration saved.")
        else:
            log(f"Loaded saved calibration from {_cal_path()}")

        regions   = cal['regions']    # list of 3 × (x, y, w, h)
        baselines = cal['baselines']  # list of 3 × (R, G, B)
        tolerance = cal['tolerance']  # single int

        log(f"Tolerance: ±{tolerance}   Monitoring {NUM_STARTERS} starter regions.")
        log("Soft reset loop running. Press ■ Stop at any time.")

        sr_count = 0

        # ── Automation loop ───────────────────────────────────────────────────
        while not stop_event.is_set():

            # Navigate to starter selection
            controller.press_a()
            if not self.wait(self.MENU_DELAY_1, stop_event): break

            controller.press_a()
            if not self.wait(self.MENU_DELAY_2, stop_event): break

            controller.press_a()
            if not self.wait(self.MENU_DELAY_3, stop_event): break

            controller.press_a()
            if not self.wait(self.MENU_DELAY_4, stop_event): break

            controller.press_a()
            if not self.wait(self.ENCOUNTER_DELAY, stop_event): break

            # Check each starter region
            shiny_found = False
            for i in range(NUM_STARTERS):
                if stop_event.is_set():
                    break

                x, y, w, h = regions[i]
                br, bg, bb = baselines[i]

                frame = frame_grabber.get_latest_frame()
                if frame is None:
                    continue

                r, g, b = self.avg_rgb(frame, x, y, w, h)

                if (abs(r - br) > tolerance or
                        abs(g - bg) > tolerance or
                        abs(b - bb) > tolerance):

                    # Possible shiny — wait and recheck to rule out transition frames
                    if not self.wait(self.SHINY_RECHECK_DELAY, stop_event):
                        break

                    frame = frame_grabber.get_latest_frame()
                    if frame is None:
                        continue
                    r2, g2, b2 = self.avg_rgb(frame, x, y, w, h)

                    if (abs(r2 - br) > tolerance or
                            abs(g2 - bg) > tolerance or
                            abs(b2 - bb) > tolerance):
                        log(
                            f"*** SHINY DETECTED! Starter {i + 1} — "
                            f"R:{r2:.0f} G:{g2:.0f} B:{b2:.0f}  "
                            f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f}) ***"
                        )
                        log(f"Soft resets before shiny: {sr_count}")
                        shiny_found = True
                        break

                # Press Left to move to next starter (skip after last)
                if i < NUM_STARTERS - 1:
                    controller.press_left()
                    if not self.wait(self.LEFT_MOVE_DELAY, stop_event):
                        break

            if stop_event.is_set():
                break

            if shiny_found:
                log("Script paused — catch your shiny! Press ■ Stop when done.")
                stop_event.wait()   # wait until user presses Stop
                break

            # Soft reset
            sr_count += 1
            log(f"No shiny. Soft reset #{sr_count}...")
            controller.soft_reset()
            if not self.wait(self.SOFT_RESET_DELAY, stop_event):
                break

        log("HGSS Shiny Starter stopped.")

    # ── Calibration ───────────────────────────────────────────────────────────

    def _calibrate(self, controller, frame_grabber, stop_event,
                   log, request_calibration):
        """
        Walk the user through calibrating all 3 starter regions.
        Returns a calibration dict, or None if stopped.
        """
        STARTER_NAMES = ['Chikorita', 'Cyndaquil', 'Totodile']

        regions = []
        baselines = []

        for i in range(NUM_STARTERS):
            if stop_event.is_set():
                return None

            name = STARTER_NAMES[i]
            log(f"Calibrating starter {i + 1}/{NUM_STARTERS}: {name}")
            log("Navigate to the starter selection screen, then draw a region "
                f"over {name}'s sprite on the video feed.")

            region = request_calibration(
                f"Draw a region over {name}'s sprite ({i+1}/{NUM_STARTERS})"
            )
            if stop_event.is_set():
                return None

            x, y, w, h = region
            log(f"{name} region: x={x} y={y} w={w} h={h}")

            # Sample the baseline colour
            time.sleep(0.1)
            frame = frame_grabber.get_latest_frame()
            if frame is None:
                log("No frame available — please ensure the webcam is connected.")
                return None

            r, g, b = self.avg_rgb(frame, x, y, w, h)
            log(f"{name} baseline — R:{r:.1f}  G:{g:.1f}  B:{b:.1f}")

            regions.append([x, y, w, h])
            baselines.append([r, g, b])

            # Move to next starter (press Left) — skip after the last one
            if i < NUM_STARTERS - 1:
                controller.press_left()
                self.wait(self.LEFT_MOVE_DELAY, stop_event)

        # Get tolerance from user via log prompt (default 15 if not provided)
        log("Calibration regions set.")
        log("Using default colour tolerance of 15.")
        log("(To change this, edit the calibration JSON file and adjust 'tolerance'.)")
        tolerance = 15

        return {
            'regions': regions,
            'baselines': baselines,
            'tolerance': tolerance,
        }

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
        path = _cal_path()
        with open(path, 'w') as f:
            json.dump(cal, f, indent=2)
