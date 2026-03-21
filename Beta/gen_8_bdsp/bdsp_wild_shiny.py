"""
BDSP - Wild Shiny
Game: Pokemon Brilliant Diamond / Shining Pearl (Nintendo Switch)

Hunts for shiny wild Pokemon in the Grand Underground or overworld
grass by walking back and forth to trigger encounters, then checking
each encounter for shininess via avg_rgb on a calibrated region of
the wild Pokemon's battle sprite.

Ported from BDSP_Wild_Shiny_2.0.cpp.

How it works:
  The C++ version detects the wild Pokemon text appearing in the
  dialogue box (white-pixel count in a fixed strip) and then times
  how long the "Your Pokemon" text takes to appear. Shinies have a
  longer animation (~3.5 s delay threshold). The Python port uses
  avg_rgb comparison on a calibrated battle-sprite region instead.

  Loop:
    1. Walk left/right to trigger a random encounter.
    2. Detect battle blackout (dark frame).
    3. Wait BATTLE_WAIT s for the sprite to load.
    4. avg_rgb check vs. calibrated baseline ± tolerance.
    5. If not shiny: Up + A to flee, then continue walking.

Setup:
  - Save in a location with wild Pokemon encounters.
  - On first run let an encounter load, then draw a region over the
    wild Pokemon's battle sprite.
  - Delete calibration/bdsp_wild_shiny.json to recalibrate.
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
    return os.path.join(cal_dir, 'bdsp_wild_shiny.json')


class BDSPWildShiny(BaseScript):
    NAME = "BDSP - Wild Shiny"
    DESCRIPTION = "Hunts for shiny wild Pokemon in the Grand Underground or grass (Brilliant Diamond/Pearl)."

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    WALK_DURATION     = 3.0    # seconds per walk pass (left or right)
    MAX_WALK_PASSES   = 200    # safety limit
    BLACKOUT_WAIT     = 15.0   # max seconds to wait for battle blackout
    BATTLE_WAIT       = 8.0    # wait after blackout for sprite to load
    FLEE_UP_DELAY     = 0.6    # after Up to reach Run
    FLEE_A_DELAY      = 7.0    # after A to confirm flee + return
    SHINY_RECHECK     = 3.0

    # ── Blackout detection ────────────────────────────────────────────────────
    DARK_THRESHOLD    = 40
    DARK_FRACTION     = 0.65

    COLOUR_TOLERANCE  = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("BDSP - Wild Shiny started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Trigger an encounter, let it load, then draw a region over "
                "the wild Pokemon's sprite.")
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
        log("Encounter loop running. Press Stop at any time.")

        encounter_count = 0

        while not stop_event.is_set():

            # ── Walk left/right to trigger an encounter ────────────────────
            encounter_found = False
            for _ in range(self.MAX_WALK_PASSES):
                if stop_event.is_set(): break

                controller.hold_left()
                blackout = self._wait_for_blackout_while_walking(
                    frame_grabber, stop_event, self.WALK_DURATION
                )
                controller.release_all()
                if blackout:
                    encounter_found = True
                    break
                if stop_event.is_set(): break

                controller.hold_right()
                blackout = self._wait_for_blackout_while_walking(
                    frame_grabber, stop_event, self.WALK_DURATION
                )
                controller.release_all()
                if blackout:
                    encounter_found = True
                    break

            controller.release_all()
            if stop_event.is_set(): break

            if not encounter_found:
                log("No encounter found after max walk passes — retrying.")
                continue

            encounter_count += 1
            log(f"Encounter #{encounter_count}: battle detected")

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
                                f"*** SHINY WILD POKEMON! Encounter #{encounter_count} "
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

        log("BDSP - Wild Shiny stopped.")

    def _wait_for_blackout_while_walking(self, frame_grabber, stop_event,
                                          duration: float) -> bool:
        """Walk for `duration` seconds, return True if blackout detected."""
        deadline = time.time() + duration
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
        log("Draw a region over the wild Pokemon's battle sprite.")
        region = request_calibration("Draw region over wild Pokemon sprite")
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
