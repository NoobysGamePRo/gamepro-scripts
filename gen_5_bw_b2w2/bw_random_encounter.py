"""
BW - Random Encounter
Game: Pokemon Black / White (DS via 3DS)

Walks in tall grass to trigger random encounters, checks for shiny via
avg_rgb comparison on the wild Pokemon's battle sprite.

Ported from BW_Random_Encounter_Shiny_2.0.cpp.

How it works:
  Holds left/right (or up/down) to walk in grass. When the screen goes
  dark (battle blackout), the script waits for the battle to load and
  checks the wild Pokemon's sprite colour.

Setup:
  - Save in a grass patch that you want to hunt in.
  - Set MOVE_DIRECTION = 'horizontal' or 'vertical'.
  - Calibrate the wild Pokemon sprite region on first run.
  - Delete calibration/bw_random_encounter.json to recalibrate.
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
    return os.path.join(cal_dir, 'bw_random_encounter.json')


class BWRandomEncounter(BaseScript):
    NAME = "BW - Random Encounter"
    DESCRIPTION = "Walks in grass for random shiny encounters (Black/White)."

    MOVE_DIRECTION  = 'horizontal'
    WALK_TIME       = 1.5
    BATTLE_WAIT     = 8.0
    FLEE_DELAY      = 1.3
    SHINY_RECHECK   = 3.0
    DARK_THRESHOLD  = 40
    DARK_FRACTION   = 0.65
    COLOUR_TOLERANCE = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("BW - Random Encounter started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — trigger an encounter, let the wild "
                "Pokemon appear, then draw a region over it.")
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

            if self.MOVE_DIRECTION == 'horizontal':
                first_dir  = controller.hold_left
                second_dir = controller.hold_right
            else:
                first_dir  = controller.hold_up
                second_dir = controller.hold_down

            first_dir()
            blackout = self._wait_for_blackout(frame_grabber, stop_event, self.WALK_TIME)
            controller.release_all()
            if stop_event.is_set(): break

            if not blackout:
                second_dir()
                blackout = self._wait_for_blackout(frame_grabber, stop_event, self.WALK_TIME)
                controller.release_all()
                if stop_event.is_set(): break

            if not blackout:
                continue

            encounter_count += 1
            log(f"Encounter #{encounter_count}: blackout detected")

            if not self.wait(self.BATTLE_WAIT, stop_event): break

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
                                f"R:{r2:.0f} G:{g2:.0f} B:{b2:.0f} ***"
                            )
                            shiny_found = True

            if stop_event.is_set(): break

            if shiny_found:
                log("Script paused — catch your shiny! Press Stop when done.")
                stop_event.wait()
                break

            log(f"Encounter #{encounter_count}: not shiny — fleeing")
            controller.press_up()
            if not self.wait(self.FLEE_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(2.0, stop_event): break

        log("BW - Random Encounter stopped.")

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
