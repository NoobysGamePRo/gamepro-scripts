"""
HGSS Random Encounter Shiny Hunter
Game: Pokemon HeartGold / SoulSilver (DS / 3DS)

Walks the player back and forth in grass to trigger wild encounters.
Uses avg_rgb comparison to detect shiny Pokemon.

The approach:
  1. First encounter calibrates the baseline Pokemon sprite colours.
  2. On every subsequent encounter, the sprite area is compared to the
     baseline. A shiny Pokemon has significantly different colours.
  3. Non-shiny encounters: navigate the battle menu to Run, then
     continue walking.

Ported from HGSS_Random_Encounter_Shiny_2.0.cpp.

Setup:
  - Save in a grass patch with a healthy lead Pokemon.
  - Script starts walking immediately — stand at the edge of long grass.
  - First encounter: script pauses to let you calibrate the detection
    region over the wild Pokemon sprite, then samples baseline colours.
  - Adjust STEPS (tiles per direction) to your grass patch size.

Notes:
  - The light sensor can also be used to detect encounters. This script
    uses the webcam (screen blackout) for broader compatibility.
  - Increase LEAD_FLEE_DELAY if the flee menu doesn't appear in time.
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
    return os.path.join(cal_dir, 'hgss_random_encounter.json')


class HGSSRandomEncounter(BaseScript):
    NAME = "HGSS – Random Encounter"
    DESCRIPTION = (
        "Walks in grass and detects shiny wild Pokemon using avg_rgb "
        "comparison (HeartGold/SoulSilver)."
    )

    # ── Walk settings ─────────────────────────────────────────────────────────
    STEPS        = 5     # tiles to walk per direction (adjust for grass size)
    MOVE_DIR     = 'lr'  # 'lr' = left/right, 'ud' = up/down

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    STEP_DURATION      = 0.28   # seconds per tile step
    ENCOUNTER_WAIT     = 4.5    # wait after blackout for battle screen to load
    LEAD_FLEE_DELAY    = 4.5    # A press delay (advance battle text to menu)
    FLEE_NAV_DELAY     = 0.5    # delay between menu navigation presses
    FLEE_CONFIRM_DELAY = 2.0    # after selecting Run
    POST_FLEE_DELAY    = 3.0    # wait after fleeing before resuming walk
    SHINY_RECHECK_WAIT = 2.0    # recheck delay before confirming shiny

    # ── Detection ─────────────────────────────────────────────────────────────
    BLACKOUT_THRESHOLD = 0.60   # fraction of dark pixels = encounter blackout
    COLOUR_TOLERANCE   = 20     # ±tolerance per channel for shiny detection

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("HGSS Random Encounter started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration — first encounter will prompt for sprite region.")
        else:
            log(f"Calibration loaded from {_cal_path()}")

        encounter_count = 0

        # Direction pair for movement
        if self.MOVE_DIR == 'ud':
            moves = (controller.hold_up, controller.hold_down)
        else:
            moves = (controller.hold_left, controller.hold_right)

        log(f"Walking {'left/right' if self.MOVE_DIR == 'lr' else 'up/down'} "
            f"{self.STEPS} tiles per direction. Watching for encounters...")

        while not stop_event.is_set():
            for move_fn in moves:
                if stop_event.is_set():
                    break

                # Walk N tiles in this direction
                for step in range(self.STEPS):
                    if stop_event.is_set():
                        break

                    move_fn()
                    if not self.wait(self.STEP_DURATION, stop_event):
                        controller.release_all()
                        return
                    controller.release_all()
                    if not self.wait(0.05, stop_event):
                        return

                    # Check for encounter (screen blackout)
                    frame = frame_grabber.get_latest_frame() if frame_grabber else None
                    if frame is not None and self._is_blackout(frame):
                        controller.release_all()

                        log(f"Encounter #{encounter_count + 1} detected!")
                        if not self.wait(self.ENCOUNTER_WAIT, stop_event):
                            return

                        # Calibrate on first encounter
                        if cal is None:
                            log("First encounter — calibrate the detection region.")
                            log("Draw a rectangle over the wild Pokemon's sprite.")
                            region = request_calibration(
                                "Draw region over the wild Pokemon's sprite"
                            )
                            if stop_event.is_set():
                                return
                            rx, ry, rw, rh = region
                            frame2 = frame_grabber.get_latest_frame()
                            if frame2 is None:
                                log("No frame — ensure webcam is connected.")
                                return
                            r, g, b = self.avg_rgb(frame2, rx, ry, rw, rh)
                            log(f"Baseline — R:{r:.1f} G:{g:.1f} B:{b:.1f}")
                            cal = {
                                'region': [rx, ry, rw, rh],
                                'baseline': [r, g, b],
                                'tolerance': self.COLOUR_TOLERANCE,
                            }
                            self._save_calibration(cal)
                            log("Calibration saved. Fleeing first encounter...")
                            self._flee(controller, stop_event)
                            if not self.wait(self.POST_FLEE_DELAY, stop_event):
                                return
                            encounter_count += 1
                            break  # restart walk loop

                        # Check for shiny
                        rx, ry, rw, rh = cal['region']
                        br, bg, bb = cal['baseline']
                        tol = cal.get('tolerance', self.COLOUR_TOLERANCE)

                        frame3 = frame_grabber.get_latest_frame()
                        if frame3 is not None:
                            r, g, b = self.avg_rgb(frame3, rx, ry, rw, rh)
                            log(f"Encounter #{encounter_count + 1}: "
                                f"R:{r:.0f} G:{g:.0f} B:{b:.0f}  "
                                f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f})")

                            if (abs(r - br) > tol or
                                    abs(g - bg) > tol or
                                    abs(b - bb) > tol):

                                # Recheck to rule out transition
                                if not self.wait(self.SHINY_RECHECK_WAIT, stop_event):
                                    return
                                frame4 = frame_grabber.get_latest_frame()
                                if frame4 is not None:
                                    r2, g2, b2 = self.avg_rgb(
                                        frame4, rx, ry, rw, rh)
                                    if (abs(r2 - br) > tol or
                                            abs(g2 - bg) > tol or
                                            abs(b2 - bb) > tol):
                                        log(
                                            f"*** SHINY DETECTED! "
                                            f"R:{r2:.0f} G:{g2:.0f} B:{b2:.0f} ***"
                                        )
                                        log(f"Encounters so far: {encounter_count + 1}")
                                        log("Script paused — catch your shiny! "
                                            "Press ■ Stop when done.")
                                        stop_event.wait()
                                        return

                        encounter_count += 1
                        self._flee(controller, stop_event)
                        if not self.wait(self.POST_FLEE_DELAY, stop_event):
                            return
                        break  # restart walk after encounter

        log("HGSS Random Encounter stopped.")

    def _flee(self, controller, stop_event):
        """Navigate the battle menu to select Run."""
        controller.press_a()
        self.wait(self.LEAD_FLEE_DELAY, stop_event)
        # Navigate to Run: from Fight (top-left), Down then Right
        controller.press_down()
        self.wait(self.FLEE_NAV_DELAY, stop_event)
        controller.press_right()
        self.wait(self.FLEE_NAV_DELAY, stop_event)
        controller.press_a()
        self.wait(self.FLEE_CONFIRM_DELAY, stop_event)
        controller.press_b()
        self.wait(1.5, stop_event)

    def _is_blackout(self, frame) -> bool:
        """True if the screen has gone mostly dark (encounter flash)."""
        sample = frame[50:430, 50:590]
        dark = (
            (sample[:, :, 0] < 40) &
            (sample[:, :, 1] < 40) &
            (sample[:, :, 2] < 40)
        )
        return dark.mean() > self.BLACKOUT_THRESHOLD

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
