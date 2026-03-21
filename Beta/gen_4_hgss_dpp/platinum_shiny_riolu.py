"""
Platinum - Shiny Riolu
Game: Pokemon Platinum (DS via 3DS)

Soft-resets for the shiny Riolu egg gift from Riley on Iron Island.

Ported from Shiny_Gift_Riolu_1.5.cpp.

How it works:
  Riley gives the player a Riolu egg on Iron Island. The script:
  1. Navigates through the title/continue screens after soft reset.
  2. Talks to Riley to receive the egg.
  3. Rides the bicycle to hatch the egg (holding left/right).
  4. After hatching, checks the Riolu's sprite via avg_rgb.

Setup:
  - Save inside Riley's room on Iron Island, standing in front of Riley.
  - On first run, hatch the egg and navigate to Riolu's summary screen,
    then draw a region over its sprite.
  - Delete calibration/platinum_shiny_riolu.json to recalibrate.

Note on timing: The C++ source (Shiny_Gift_Riolu_1.5.cpp) is complex —
it uses the LDR to detect the hatch animation and the egg hatching text
detection. This port uses a simpler walk loop with white-pixel detection
for the hatch notification, similar to the BDSP breeding implementation.
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
    return os.path.join(cal_dir, 'platinum_shiny_riolu.json')


class PlatinumShinyRiolu(BaseScript):
    NAME = "Platinum - Shiny Riolu"
    DESCRIPTION = "Soft-resets for the shiny Riolu egg from Riley on Iron Island (Platinum)."

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    SOFT_RESET_WAIT    = 12.0   # DS reload
    MENU_A_1_DELAY     = 2.0    # title
    MENU_A_2_DELAY     = 3.0    # continue
    MENU_A_3_DELAY     = 3.0    # load world
    MENU_A_4_DELAY     = 4.0    # load world complete / world interactive
    # Flee B sequence to exit conversation & get outdoors (after SR):
    MENU_B_DELAY       = 3.0    # after B presses (x4) to exit Riley room
    RILEY_A_COUNT      = 4      # A presses through Riley's text to accept egg
    RILEY_A_DELAY      = 1.5
    NICKNAME_B_WAIT    = 3.0    # wait then B to decline nickname
    POST_EGG_DELAY     = 1.5    # A presses after egg received (x2)
    # Bicycle / walk to hatch
    BIKE_Y_DELAY       = 1.2    # after Y to use bicycle
    WALK_DURATION      = 3.0    # duration per walk pass
    MAX_WALK_PASSES    = 80     # Riolu egg takes ~6630 steps (~5000 on bike)
    HATCH_TEXT_WAIT    = 15.0   # wait for hatch animation
    HATCH_A_COUNT      = 5      # A presses through hatch text
    HATCH_A_DELAY      = 1.5
    # Check via summary screen
    CHECK_DELAY        = 1.3
    SHINY_RECHECK_WAIT = 3.0

    COLOUR_TOLERANCE   = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("Platinum - Shiny Riolu started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Hatch the egg and open Riolu's summary screen, "
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

        log(f"Riolu region: x={x} y={y} w={w} h={h} | tolerance ±{tolerance}")
        log("Soft reset loop running. Press Stop at any time.")

        sr_count = 0

        controller.soft_reset()
        if not self.wait(self.SOFT_RESET_WAIT, stop_event):
            return

        while not stop_event.is_set():

            # ── Navigate to overworld ─────────────────────────────────────
            controller.press_a()
            if not self.wait(self.MENU_A_1_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.MENU_A_2_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.MENU_A_3_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.MENU_A_4_DELAY, stop_event): break

            # ── Talk to Riley ─────────────────────────────────────────────
            for _ in range(self.RILEY_A_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.RILEY_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            # B to decline nickname
            if not self.wait(self.NICKNAME_B_WAIT, stop_event): break
            controller.press_b()
            if not self.wait(1.5, stop_event): break

            for _ in range(2):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.POST_EGG_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Bike and walk to hatch ────────────────────────────────────
            controller.press_y()   # use bicycle
            if not self.wait(self.BIKE_Y_DELAY, stop_event): break

            log(f"SR #{sr_count + 1}: walking to hatch egg...")
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

                # Check for hatch notification (white text pixels)
                frame = frame_grabber.get_latest_frame()
                if frame is not None:
                    n_white = self.count_matching_pixels(
                        frame, 50, 50, 540, 50, 255, 255, 255, 40
                    )
                    if n_white > 200:
                        controller.release_all()
                        hatched = True
                        break

            controller.release_all()
            if stop_event.is_set(): break

            if not hatched:
                log(f"SR #{sr_count + 1}: egg did not hatch — retrying.")
                sr_count += 1
                controller.soft_reset()
                if not self.wait(self.SOFT_RESET_WAIT, stop_event): break
                continue

            # ── Hatch dialogue ────────────────────────────────────────────
            if not self.wait(self.HATCH_TEXT_WAIT, stop_event): break
            for _ in range(self.HATCH_A_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.HATCH_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Open summary to check Riolu ───────────────────────────────
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
                                f"*** SHINY RIOLU! "
                                f"R:{r2:.0f} G:{g2:.0f} B:{b2:.0f}  "
                                f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f}) ***"
                            )
                            log(f"Soft resets before shiny: {sr_count}")
                            shiny_found = True

            if stop_event.is_set(): break

            if shiny_found:
                log("Script paused — enjoy your shiny! Press Stop when done.")
                stop_event.wait()
                break

            sr_count += 1
            log(f"No shiny. Soft reset #{sr_count}...")
            controller.soft_reset()
            if not self.wait(self.SOFT_RESET_WAIT, stop_event): break

        log("Platinum - Shiny Riolu stopped.")

    def _calibrate(self, controller, frame_grabber, stop_event,
                   log, request_calibration):
        log("Draw a region over Riolu's sprite on the summary screen.")
        region = request_calibration("Draw region over Riolu's sprite")
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
