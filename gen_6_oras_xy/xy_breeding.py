"""
XY - Egg Breeding
Game: Pokemon X / Y (3DS)

Automates egg collection from the Day Care couple on Route 7 and hatches
eggs while checking each hatchling for shininess via avg_rgb on the Pokemon
summary screen.

Ported from XY_Breeding_2.0.cpp.

How it works:
  1. Walks to the Day Care man and collects an egg (A × 4 through dialogue).
  2. Rides the Bike left/right to hatch the egg, detecting the hatch
     notification via white-pixel count in the lower screen area.
  3. After hatching, opens the summary screen and checks avg_rgb.
  4. If not shiny, continues the breeding loop.

Setup:
  - Save on Route 7 standing in front of the Day Care man.
  - Ensure the Bike is registered to Y button.
  - On first run, hatch an egg and open the hatchling's summary screen,
    then draw a region over its sprite.
  - Delete calibration/xy_breeding.json to recalibrate.
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
    return os.path.join(cal_dir, 'xy_breeding.json')


class XYBreeding(BaseScript):
    NAME = "XY - Egg Breeding"
    DESCRIPTION = "Automates egg collection and hatching with shiny check (X/Y)."

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    EGG_COLLECT_A_COUNT = 5     # A presses through Day Care man dialogue
    EGG_COLLECT_A_DELAY = 1.0
    BIKE_Y_DELAY        = 1.2   # after Y to mount bike
    WALK_DURATION       = 3.5   # seconds per walk pass (left or right)
    MAX_WALK_PASSES     = 120   # safety limit
    HATCH_TEXT_WAIT     = 18.0  # wait for hatch animation
    HATCH_A_COUNT       = 5     # A presses through hatch text
    HATCH_A_DELAY       = 1.5
    CHECK_DELAY         = 1.3   # delay between summary navigation presses
    SHINY_RECHECK_WAIT  = 3.0

    # ── Hatch detection ───────────────────────────────────────────────────────
    WHITE_PIXEL_COUNT   = 200   # minimum white pixels to flag hatch text

    COLOUR_TOLERANCE    = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("XY - Egg Breeding started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Hatch an egg and open the summary screen, then draw a "
                "region over the hatchling's sprite.")
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

        log(f"Hatchling region: x={x} y={y} w={w} h={h} | tolerance ±{tolerance}")
        log("Breeding loop running. Press Stop at any time.")

        hatch_count = 0

        while not stop_event.is_set():

            # ── Collect egg ───────────────────────────────────────────────
            log(f"Egg #{hatch_count + 1}: collecting egg from Day Care man...")
            for _ in range(self.EGG_COLLECT_A_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.EGG_COLLECT_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Mount bike ────────────────────────────────────────────────
            controller.press_y()
            if not self.wait(self.BIKE_Y_DELAY, stop_event): break

            # ── Bike left/right to hatch ──────────────────────────────────
            log(f"Egg #{hatch_count + 1}: biking to hatch egg...")
            hatched = False

            for _ in range(self.MAX_WALK_PASSES):
                if stop_event.is_set(): break

                controller.hold_left()
                if not self.wait(self.WALK_DURATION, stop_event):
                    controller.release_all()
                    break
                controller.hold_right()
                if not self.wait(self.WALK_DURATION, stop_event):
                    controller.release_all()
                    break

                frame = frame_grabber.get_latest_frame()
                if frame is not None:
                    n_white = self.count_matching_pixels(
                        frame, 50, 50, 540, 50,
                        255, 255, 255, 40
                    )
                    if n_white > self.WHITE_PIXEL_COUNT:
                        controller.release_all()
                        hatched = True
                        break

            controller.release_all()
            if stop_event.is_set(): break

            if not hatched:
                log(f"Egg #{hatch_count + 1}: egg did not hatch — retrying.")
                continue

            # ── Hatch dialogue ────────────────────────────────────────────
            if not self.wait(self.HATCH_TEXT_WAIT, stop_event): break
            for _ in range(self.HATCH_A_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.HATCH_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            hatch_count += 1

            # ── Open summary ──────────────────────────────────────────────
            controller.press_x()
            if not self.wait(self.CHECK_DELAY, stop_event): break
            controller.press_down()
            if not self.wait(self.CHECK_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.CHECK_DELAY, stop_event): break
            controller.press_right()
            if not self.wait(self.CHECK_DELAY, stop_event): break
            for _ in range(2):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.CHECK_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Shiny check ───────────────────────────────────────────────
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
                                f"*** SHINY HATCHLING! Egg #{hatch_count} "
                                f"R:{r2:.0f} G:{g2:.0f} B:{b2:.0f}  "
                                f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f}) ***"
                            )
                            shiny_found = True

            if stop_event.is_set(): break

            if shiny_found:
                log("Script paused — enjoy your shiny! Press Stop when done.")
                stop_event.wait()
                break

            log(f"Egg #{hatch_count}: not shiny — continuing.")
            for _ in range(3):
                if stop_event.is_set(): break
                controller.press_b()
                if not self.wait(0.8, stop_event): break

        log("XY - Egg Breeding stopped.")

    def _calibrate(self, controller, frame_grabber, stop_event,
                   log, request_calibration):
        log("Draw a region over the hatchling's sprite on the summary screen.")
        region = request_calibration("Draw region over hatchling sprite")
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
