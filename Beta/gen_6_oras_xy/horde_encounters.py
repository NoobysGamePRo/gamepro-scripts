"""
XY - Horde Encounter
Game: Pokemon X / Y (3DS) — also works in ORAS

Uses Sweet Scent to trigger horde encounters for shiny hunting. A Pokemon
in the party must know Sweet Scent.

Ported from Horde_Encounters_3.0.cpp.

How it works:
  1. Opens the Pokemon menu (X → A → Right → A → Down → A → A) to use
     Sweet Scent.
  2. Waits for the battle blackout (screen goes dark) to detect the
     encounter.
  3. Waits for the battle to load, then checks avg_rgb on the calibrated
     region to look for a shiny in the horde.
  4. If not shiny, presses Up + A to flee.
  5. Repeats.

Setup:
  - Save in a location with hordes of the Pokemon you want to hunt.
  - Ensure the Sweet Scent user is the second Pokemon in your party
    (slot 2 — the script navigates Right once in the party screen to
    reach it). Adjust SWEET_SCENT_SLOT if needed.
  - On first run, let a horde encounter load and draw a region over one
    of the wild Pokemon sprites (any one is fine — aim for a consistent
    position).
  - Delete calibration/horde_encounters.json to recalibrate.
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
    return os.path.join(cal_dir, 'horde_encounters.json')


class HordeEncounters(BaseScript):
    NAME = "XY - Horde Encounter"
    DESCRIPTION = "Uses Sweet Scent to trigger horde encounters for shiny hunting (X/Y)."

    # ── Timing (seconds) — from Horde_Encounters_3.0.cpp ────────────────────
    MENU_X_DELAY       = 0.6    # after X to open menu
    MENU_A_DELAY       = 2.0    # after A to open Pokemon list
    NAV_R_DELAY        = 0.6    # after right to reach Sweet Scent user
    SWEET_SCENT_DELAYS = (0.6, 0.6, 0.6, 4.0)  # A×4 to use Sweet Scent
    BATTLE_WAIT        = 8.0    # after encounter detected, wait for battle
    FLEE_UP_DELAY      = 1.3    # after Up in battle to reach Run
    FLEE_A_DELAY       = 2.0    # after A to confirm Run
    SHINY_RECHECK      = 3.0

    # ── Blackout detection ────────────────────────────────────────────────────
    DARK_THRESHOLD  = 40
    DARK_FRACTION   = 0.65
    BLACKOUT_WAIT   = 20.0  # max seconds to wait for encounter blackout

    COLOUR_TOLERANCE = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("XY - Horde Encounter started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Use Sweet Scent to trigger a horde, let it load, then draw "
                "a region over one of the wild Pokemon sprites.")
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

        log(f"Wild Pokemon region: x={x} y={y} w={w} h={h} | tolerance ±{tolerance}")
        log("Horde encounter loop running. Press Stop at any time.")

        encounter_count = 0

        while not stop_event.is_set():

            # ── Open menu and use Sweet Scent ─────────────────────────────
            controller.press_x()
            if not self.wait(self.MENU_X_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.MENU_A_DELAY, stop_event): break

            controller.press_right()
            if not self.wait(self.NAV_R_DELAY, stop_event): break

            # A → A (select Pokemon) → Down (Use move) → A (use) → A (Sweet Scent)
            for delay in self.SWEET_SCENT_DELAYS:
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(delay, stop_event): break
            if stop_event.is_set(): break

            # ── Wait for blackout ─────────────────────────────────────────
            blackout = self._wait_for_blackout(
                frame_grabber, stop_event, self.BLACKOUT_WAIT
            )
            if stop_event.is_set(): break

            if not blackout:
                log("Blackout not detected — retrying.")
                continue

            encounter_count += 1
            log(f"Horde #{encounter_count}: encounter detected")

            if not self.wait(self.BATTLE_WAIT, stop_event): break

            # ── Shiny check ───────────────────────────────────────────────
            frame = frame_grabber.get_latest_frame()
            shiny_found = False

            if frame is not None:
                r, g, b = self.avg_rgb(frame, x, y, w, h)
                if (abs(r - br) > tolerance or
                        abs(g - bg) > tolerance or
                        abs(b - bb) > tolerance):
                    if not self.wait(self.SHINY_RECHECK, stop_event): break
                    frame = frame_grabber.get_latest_frame()
                    if frame is not None:
                        r2, g2, b2 = self.avg_rgb(frame, x, y, w, h)
                        if (abs(r2 - br) > tolerance or
                                abs(g2 - bg) > tolerance or
                                abs(b2 - bb) > tolerance):
                            log(
                                f"*** SHINY HORDE POKEMON! Encounter #{encounter_count} "
                                f"R:{r2:.0f} G:{g2:.0f} B:{b2:.0f}  "
                                f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f}) ***"
                            )
                            shiny_found = True

            if stop_event.is_set(): break

            if shiny_found:
                log("Script paused — catch your shiny! Press Stop when done.")
                stop_event.wait()
                break

            # ── Flee ──────────────────────────────────────────────────────
            log(f"Horde #{encounter_count}: not shiny — fleeing")
            controller.press_up()
            if not self.wait(self.FLEE_UP_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.FLEE_A_DELAY, stop_event): break

        log("XY - Horde Encounter stopped.")

    def _wait_for_blackout(self, frame_grabber, stop_event, timeout: float) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if stop_event.is_set():
                return False
            frame = frame_grabber.get_latest_frame()
            if frame is not None:
                sample = frame[50:430, 50:590]
                dark = (
                    (sample[:, :, 0] < self.DARK_THRESHOLD) &
                    (sample[:, :, 1] < self.DARK_THRESHOLD) &
                    (sample[:, :, 2] < self.DARK_THRESHOLD)
                )
                if dark.mean() > self.DARK_FRACTION:
                    return True
            time.sleep(0.03)
        return False

    def _calibrate(self, controller, frame_grabber, stop_event,
                   log, request_calibration):
        log("Draw a region over one of the wild Pokemon sprites in the horde.")
        region = request_calibration("Draw region over a wild Pokemon sprite")
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
