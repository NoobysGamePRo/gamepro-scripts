"""
Sun / Moon - Shiny Crabrawler
Game: Pokemon Sun / Moon (3DS)

Hunts for a shiny Crabrawler by interacting with the berry pile on
Route 10 / Poni Island. Crabrawler jumps out when a berry pile is
interacted with (A press). If not shiny, flees and repeats.

Ported from Shiny_Crabrawler_3.0.cpp.

How it works:
  The C++ program uses LDR step-change timing: it presses A to
  interact with the pile, waits for the LDR to detect a screen
  brightness change (battle start), and compares the blackout
  duration to a shiny baseline (shinies take longer due to the
  sparkle animation).

  The Python port replaces LDR timing with avg_rgb comparison on a
  calibrated region of the Crabrawler battle sprite.

  1. A 3.5 s → A 6 s → A 2.5 s → A 8 s (title/continue/walk to pile).
  2. Loop:
     a. A to interact with pile → wait for blackout → wait 8 s.
     b. avg_rgb check on calibrated region.
     c. If not shiny: Up + A to flee (1.3 s + 7 s), repeat.

Setup:
  - Save directly in front of a berry pile that contains Crabrawler.
  - On first run let a Crabrawler encounter load, then draw a region
    over its battle sprite.
  - Delete calibration/shiny_crabrawler.json to recalibrate.
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
    return os.path.join(cal_dir, 'shiny_crabrawler.json')


class ShinyCrabrawler(BaseScript):
    NAME = "Sun / Moon - Shiny Crabrawler"
    DESCRIPTION = "Hunts for shiny Crabrawler at the berry pile (Sun/Moon)."

    # ── Initial navigation delays (seconds) ──────────────────────────────────
    INIT_A_1_DELAY   = 3.5   # title A
    INIT_A_2_DELAY   = 6.0   # continue A
    INIT_A_3_DELAY   = 2.5   # world load A
    INIT_A_4_DELAY   = 8.0   # walk to pile A

    # ── Loop timing ───────────────────────────────────────────────────────────
    BLACKOUT_WAIT    = 20.0  # max seconds to wait for blackout
    BATTLE_WAIT      = 8.0   # wait after blackout for sprite to load
    FLEE_UP_DELAY    = 1.3   # after Up to reach Run
    FLEE_A_DELAY     = 7.0   # after A to confirm flee + return to overworld
    SHINY_RECHECK    = 3.0

    # ── Blackout detection ────────────────────────────────────────────────────
    DARK_THRESHOLD   = 40
    DARK_FRACTION    = 0.65

    COLOUR_TOLERANCE = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("Sun / Moon - Shiny Crabrawler started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Interact with the berry pile, let Crabrawler appear, "
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

        log(f"Crabrawler region: x={x} y={y} w={w} h={h} | tolerance ±{tolerance}")
        log("Encounter loop running. Press Stop at any time.")

        encounter_count = 0

        while not stop_event.is_set():

            # ── Interact with berry pile ───────────────────────────────────
            log(f"Encounter #{encounter_count + 1}: pressing A on berry pile...")
            controller.press_a()

            # ── Wait for blackout ─────────────────────────────────────────
            blackout = self._wait_for_blackout(
                frame_grabber, stop_event, self.BLACKOUT_WAIT
            )
            if stop_event.is_set(): break

            if not blackout:
                log("Blackout not detected — retrying.")
                continue

            encounter_count += 1
            log(f"Encounter #{encounter_count}: Crabrawler appeared")

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
                                f"*** SHINY CRABRAWLER! Encounter #{encounter_count} "
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
            log(f"Encounter #{encounter_count}: not shiny — fleeing")
            controller.press_up()
            if not self.wait(self.FLEE_UP_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.FLEE_A_DELAY, stop_event): break

        log("Sun / Moon - Shiny Crabrawler stopped.")

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
        log("Draw a region over the Crabrawler's battle sprite.")
        region = request_calibration("Draw region over Crabrawler's sprite")
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
