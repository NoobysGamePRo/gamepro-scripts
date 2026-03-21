"""
SV — Wild Encounter Shiny Hunter
Game: Pokemon Scarlet / Violet (Nintendo Switch)

Walks in a small area to trigger overworld wild encounters, then checks
the wild Pokemon's sprite for shiny via avg_rgb and flees if not shiny.

Detection: avg_rgb comparison on the wild Pokemon's sprite region.

How it works:
  1. Holds Up for WALK_STEP seconds, then Down for WALK_STEP seconds
     to rock back and forth over a patch where wild Pokemon appear.
  2. Between steps, polls for a battle encounter by checking for a
     significant brightness drop (screen darkens during the encounter
     transition / catch camera pan).
  3. When an encounter is detected, waits ENCOUNTER_SETTLE for the
     animation to finish, then checks avg_rgb at the calibrated region.
  4. Double-checks after SHINY_RECHECK_WAIT to confirm shiny.
  5. If not shiny: presses B to run, waits RETURN_TO_OVERWORLD_WAIT,
     then resumes walking.
  6. If shiny: pauses — user catches the Pokemon manually.

Setup:
  - Save standing in a grassy area with the wild Pokemon you want to
    hunt (e.g. a short patch of grass on Route 1 / South Province).
  - On first run, the script triggers one encounter and asks you to
    draw a region over the wild Pokemon's sprite.
  - Calibration saved to calibration/sv_wild_encounter.json.
  - Delete that file to recalibrate.

Notes:
  - Adjust WALK_STEP to cover more or less ground before checking.
  - Increase ENCOUNTER_SETTLE if the battle animation takes longer
    than expected before the sprite is visible.
  - If encounters are not being triggered, try a different area or
    reduce WALK_STEP.
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
    return os.path.join(cal_dir, 'sv_wild_encounter.json')


class SVRoute1WildEncounter(BaseScript):
    NAME = "SV – Wild Encounter"
    DESCRIPTION = (
        "Walks to trigger wild Pokemon encounters and hunts for shinies "
        "(Scarlet/Violet)."
    )

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    WALK_STEP             = 1.5   # each Up/Down hold duration
    ENCOUNTER_POLL_INTERVAL = 0.15  # how often to check for encounter
    ENCOUNTER_POLL_CYCLES = 10    # polls per walk step before moving on
    ENCOUNTER_SETTLE      = 4.0   # wait after encounter detected before checking sprite
    SHINY_RECHECK_WAIT    = 2.5   # recheck delay before confirming shiny
    RUN_B_DELAY           = 1.0   # between B presses when fleeing
    RETURN_TO_OVERWORLD   = 3.0   # wait after fleeing for overworld to reappear

    # ── Detection ─────────────────────────────────────────────────────────────
    BRIGHTNESS_REGION     = (200, 150, 200, 150)  # (x, y, w, h) centre of screen
    ENCOUNTER_DARK_THRESH = 60    # avg RGB below this = encounter transition dark
    COLOUR_TOLERANCE      = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("SV Wild Encounter Shiny Hunter started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration — triggering first encounter for calibration.")
            cal = self._calibrate(
                controller, frame_grabber, stop_event, log, request_calibration
            )
            if stop_event.is_set() or cal is None:
                return
            self._save_calibration(cal)
            log("Calibration saved.")
            # Flee from calibration encounter
            log("Fleeing calibration encounter...")
            if not self._flee(controller, stop_event):
                return
        else:
            log(f"Calibration loaded from {_cal_path()}")

        rx, ry, rw, rh = cal['region']
        br, bg, bb = cal['baseline']
        tol = cal.get('tolerance', self.COLOUR_TOLERANCE)
        sr_count = 0

        log(f"Shiny hunt loop running. Tolerance ±{tol}. Press ■ Stop at any time.")

        while not stop_event.is_set():

            # ── Walk Up then Down, polling for encounter each step ────────────
            encounter = False
            for direction in ('up', 'down'):
                if stop_event.is_set():
                    break
                if direction == 'up':
                    controller.hold_up()
                else:
                    controller.hold_down()

                # Poll for encounter during the walk
                for _ in range(self.ENCOUNTER_POLL_CYCLES):
                    if stop_event.is_set():
                        break
                    if not self.wait(self.ENCOUNTER_POLL_INTERVAL, stop_event):
                        break
                    frame = frame_grabber.get_latest_frame()
                    if frame is not None:
                        bx, by, bw, bh = self.BRIGHTNESS_REGION
                        r, g, b = self.avg_rgb(frame, bx, by, bw, bh)
                        avg = (r + g + b) / 3
                        if avg < self.ENCOUNTER_DARK_THRESH:
                            controller.release_all()
                            encounter = True
                            break

                if encounter:
                    break

                controller.release_all()
                if not self.wait(0.2, stop_event):
                    break

            if stop_event.is_set():
                break

            if not encounter:
                continue

            # ── Encounter detected ────────────────────────────────────────────
            log(f"Encounter #{sr_count + 1} detected. Waiting for sprite...")
            if not self.wait(self.ENCOUNTER_SETTLE, stop_event):
                break

            frame = frame_grabber.get_latest_frame()
            shiny_found = False

            if frame is not None:
                r, g, b = self.avg_rgb(frame, rx, ry, rw, rh)
                log(
                    f"SR #{sr_count + 1}: "
                    f"R:{r:.0f} G:{g:.0f} B:{b:.0f}  "
                    f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f})"
                )

                if (abs(r - br) > tol or abs(g - bg) > tol or abs(b - bb) > tol):
                    if not self.wait(self.SHINY_RECHECK_WAIT, stop_event):
                        break
                    frame2 = frame_grabber.get_latest_frame()
                    if frame2 is not None:
                        r2, g2, b2 = self.avg_rgb(frame2, rx, ry, rw, rh)
                        if (abs(r2 - br) > tol or
                                abs(g2 - bg) > tol or
                                abs(b2 - bb) > tol):
                            log(
                                f"*** SHINY FOUND! "
                                f"R:{r2:.0f} G:{g2:.0f} B:{b2:.0f}  "
                                f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f}) ***"
                            )
                            log(f"Encounters before shiny: {sr_count}")
                            shiny_found = True

            if stop_event.is_set():
                break

            if shiny_found:
                log("Script paused — catch your shiny! Press ■ Stop when done.")
                stop_event.wait()
                break

            # ── Flee ──────────────────────────────────────────────────────────
            sr_count += 1
            log(f"Not shiny. Fleeing (encounter #{sr_count})...")
            if not self._flee(controller, stop_event):
                break

        log("SV Wild Encounter Shiny Hunter stopped.")

    def _flee(self, controller, stop_event) -> bool:
        """Press B to run from the current battle."""
        for _ in range(3):
            if stop_event.is_set(): return False
            controller.press_b()
            if not self.wait(self.RUN_B_DELAY, stop_event): return False
        if not self.wait(self.RETURN_TO_OVERWORLD, stop_event): return False
        return True

    # ── Calibration ───────────────────────────────────────────────────────────

    def _calibrate(self, controller, frame_grabber, stop_event,
                   log, request_calibration):
        """Walk into one encounter and capture the baseline sprite region."""
        log("Walking to trigger a wild encounter...")

        # Walk up until an encounter is detected (up to ENCOUNTER_POLL_CYCLES × 10 polls)
        controller.hold_up()
        encountered = False
        for _ in range(self.ENCOUNTER_POLL_CYCLES * 10):
            if stop_event.is_set():
                controller.release_all()
                return None
            time.sleep(self.ENCOUNTER_POLL_INTERVAL)
            frame = frame_grabber.get_latest_frame()
            if frame is not None:
                bx, by, bw, bh = self.BRIGHTNESS_REGION
                r, g, b = self.avg_rgb(frame, bx, by, bw, bh)
                if (r + g + b) / 3 < self.ENCOUNTER_DARK_THRESH:
                    controller.release_all()
                    encountered = True
                    break
        controller.release_all()

        if not encountered:
            log("No encounter triggered — move to a grassy area and retry.")
            return None

        log(f"Encounter detected. Waiting {self.ENCOUNTER_SETTLE}s for sprite...")
        if not self.wait(self.ENCOUNTER_SETTLE, stop_event):
            return None

        log("Wild Pokemon on screen. Draw a region over its sprite.")
        region = request_calibration("Draw region over the wild Pokemon's sprite")
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
        return {
            'region': [rx, ry, rw, rh],
            'baseline': [r, g, b],
            'tolerance': self.COLOUR_TOLERANCE,
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
        with open(_cal_path(), 'w') as f:
            json.dump(cal, f, indent=2)
