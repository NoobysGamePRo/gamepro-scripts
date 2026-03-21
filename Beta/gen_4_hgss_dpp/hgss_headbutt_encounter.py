"""
HGSS Headbutt Shiny Encounter
Game: Pokemon HeartGold / SoulSilver (DS / 3DS)

Headbutts trees to trigger wild encounters and detects shiny Pokemon
using avg_rgb comparison.

Ported from HGSS_Headbutt_Shiny_Encounter_2.0.cpp.

How it works:
  1. Presses A twice to face the tree and confirm headbutt.
  2. Watches for a screen blackout (encounter flash) for up to
     ENCOUNTER_WAIT seconds.
  3. If an encounter occurs, the script waits for the battle to load and
     checks the calibrated sprite region for a shiny.
  4. If no encounter, it presses Left to move to the next tree and tries
     again.

Setup:
  - Save in a forest area with headbutt trees nearby, standing facing
    the first tree.
  - On first encounter, draw a region over the wild Pokemon sprite to
    calibrate baseline colours.
  - Calibration is saved so subsequent runs skip setup.
  - Delete calibration/hgss_headbutt_encounter.json to recalibrate.

Notes:
  - HEADBUTT_A1_DELAY / HEADBUTT_A2_DELAY cover the "Would you like to
    use Headbutt?" confirmation sequence.
  - Adjust ENCOUNTER_WAIT if some trees consistently miss detection.
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
    return os.path.join(cal_dir, 'hgss_headbutt_encounter.json')


class HGSSHeadbuttEncounter(BaseScript):
    NAME = "HGSS – Headbutt Encounter"
    DESCRIPTION = (
        "Headbutts trees to trigger shiny wild encounters "
        "(HeartGold/SoulSilver)."
    )

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    HEADBUTT_A1_DELAY  = 2.0   # after first A (face tree / open dialogue)
    HEADBUTT_A2_DELAY  = 1.5   # after second A (confirm headbutt)
    ENCOUNTER_WAIT     = 10.0  # max wait for blackout after headbutt
    BATTLE_LOAD_WAIT   = 8.0   # wait after blackout for battle to load
    LEAD_FLEE_DELAY    = 4.5   # delay after first A before flee menu appears
    FLEE_NAV_DELAY     = 0.5   # delay between menu navigation presses
    FLEE_CONFIRM_DELAY = 2.0   # after selecting Run
    POST_FLEE_DELAY    = 3.0   # wait after fleeing before next headbutt
    NO_ENCOUNTER_DELAY = 2.0   # wait after no-encounter before moving on
    SHINY_RECHECK_WAIT = 2.0   # recheck delay before confirming shiny

    # ── Detection ─────────────────────────────────────────────────────────────
    BLACKOUT_THRESHOLD = 0.60  # fraction of dark pixels = encounter blackout
    COLOUR_TOLERANCE   = 20    # ±tolerance per channel for shiny detection

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("HGSS Headbutt Encounter started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration — first encounter will prompt for sprite region.")
        else:
            log(f"Calibration loaded from {_cal_path()}")

        encounter_count = 0
        log("Headbutting trees. Watching for encounters...")

        while not stop_event.is_set():

            # ── Headbutt sequence ─────────────────────────────────────────────
            controller.press_a()
            if not self.wait(self.HEADBUTT_A1_DELAY, stop_event):
                return

            controller.press_a()
            if not self.wait(self.HEADBUTT_A2_DELAY, stop_event):
                return

            # ── Wait for encounter blackout ───────────────────────────────────
            encounter_detected = self._wait_for_blackout(
                frame_grabber, stop_event, self.ENCOUNTER_WAIT
            )
            if stop_event.is_set():
                return

            if not encounter_detected:
                log("No encounter — moving to next tree.")
                controller.press_left()
                if not self.wait(self.NO_ENCOUNTER_DELAY, stop_event):
                    return
                continue

            # ── Encounter detected ────────────────────────────────────────────
            log(f"Encounter #{encounter_count + 1} detected!")
            if not self.wait(self.BATTLE_LOAD_WAIT, stop_event):
                return

            # ── Calibrate on first encounter ──────────────────────────────────
            if cal is None:
                log("First encounter — calibrate the detection region.")
                log("Draw a rectangle over the wild Pokemon's sprite.")
                region = request_calibration(
                    "Draw region over the wild Pokemon's sprite"
                )
                if stop_event.is_set():
                    return
                rx, ry, rw, rh = region
                frame = frame_grabber.get_latest_frame()
                if frame is None:
                    log("No frame — ensure webcam is connected.")
                    return
                r, g, b = self.avg_rgb(frame, rx, ry, rw, rh)
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
                continue

            # ── Shiny check ───────────────────────────────────────────────────
            rx, ry, rw, rh = cal['region']
            br, bg, bb = cal['baseline']
            tol = cal.get('tolerance', self.COLOUR_TOLERANCE)

            frame = frame_grabber.get_latest_frame()
            if frame is not None:
                r, g, b = self.avg_rgb(frame, rx, ry, rw, rh)
                log(
                    f"Encounter #{encounter_count + 1}: "
                    f"R:{r:.0f} G:{g:.0f} B:{b:.0f}  "
                    f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f})"
                )

                if (abs(r - br) > tol or abs(g - bg) > tol or abs(b - bb) > tol):
                    if not self.wait(self.SHINY_RECHECK_WAIT, stop_event):
                        return
                    frame2 = frame_grabber.get_latest_frame()
                    if frame2 is not None:
                        r2, g2, b2 = self.avg_rgb(frame2, rx, ry, rw, rh)
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

        log("HGSS Headbutt Encounter stopped.")

    def _flee(self, controller, stop_event):
        """Navigate the battle menu to select Run."""
        controller.press_a()
        self.wait(self.LEAD_FLEE_DELAY, stop_event)
        # From Fight (top-left): Down then Right to reach Run (bottom-right)
        controller.press_down()
        self.wait(self.FLEE_NAV_DELAY, stop_event)
        controller.press_right()
        self.wait(self.FLEE_NAV_DELAY, stop_event)
        controller.press_a()
        self.wait(self.FLEE_CONFIRM_DELAY, stop_event)
        controller.press_b()
        self.wait(1.5, stop_event)

    def _wait_for_blackout(self, frame_grabber, stop_event, timeout: float) -> bool:
        """Poll for encounter blackout; return True if detected."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if stop_event.is_set():
                return False
            frame = frame_grabber.get_latest_frame() if frame_grabber else None
            if frame is not None:
                sample = frame[50:430, 50:590]
                dark = (
                    (sample[:, :, 0] < 40) &
                    (sample[:, :, 1] < 40) &
                    (sample[:, :, 2] < 40)
                )
                if dark.mean() > self.BLACKOUT_THRESHOLD:
                    return True
            time.sleep(0.05)
        return False

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
