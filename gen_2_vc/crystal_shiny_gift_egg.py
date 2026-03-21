"""
Crystal - Shiny Gift Egg
Game: Pokemon Crystal (3DS Virtual Console)

Soft-resets for the shiny Odd Egg received from the Day Care Couple in
Goldenrod City. The Odd Egg hatches into one of: Pichu, Cleffa, Igglybuff,
Smoochum, Magby, Elekid, or Tyrogue.

How it works:
  1. Receive the Odd Egg from the Day Care Couple.
  2. Hatch the egg by walking around (this script presses A through the hatch).
  3. After hatching, check the Pokemon's sprite via avg_rgb.
  4. If colour differs from baseline, a shiny has been hatched.

Note: In Crystal VC the Odd Egg has a 50% chance of shiny, so the expected
wait is short. The script cycles: receive egg → walk to hatch → check → SR.

Setup:
  - Save inside the Day Care building in Goldenrod, standing in front of the
    Day Care woman ready to receive the egg.
  - On first run, hatch the egg manually and draw a region over the Pokemon's
    sprite on the party/summary screen.
  - Delete calibration/crystal_shiny_gift_egg.json to recalibrate.
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
    return os.path.join(cal_dir, 'crystal_shiny_gift_egg.json')


class CrystalShinyGiftEgg(BaseScript):
    NAME = "Crystal - Shiny Gift Egg"
    DESCRIPTION = "Soft-resets for the shiny Odd Egg from the Day Care (Crystal VC)."

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    SOFT_RESET_WAIT    = 5.0    # after Z reset
    MENU_A_DELAY       = 1.4    # between title/continue A presses
    RECEIVE_DIALOGUE   = 2.0    # wait after each A through Day Care dialogue
    RECEIVE_A_COUNT    = 5      # A presses to receive the egg
    PRE_NICKNAME_WAIT  = 3.5    # wait before nickname prompt
    NICKNAME_DELAY     = 1.3
    WALK_DURATION      = 3.0    # duration of each left/right walk pass
    WALK_PASSES        = 50     # max walk passes before expecting hatch
    HATCH_DETECT_WAIT  = 1.5    # polling interval while walking
    HATCH_TEXT_DELAY   = 15.0   # wait for hatch animation + text (long)
    HATCH_A_COUNT      = 5      # A presses through hatch dialogue
    HATCH_A_DELAY      = 1.5
    CHECK_DELAY        = 1.3    # between menu presses to check sprite
    SHINY_RECHECK_WAIT = 3.0

    COLOUR_TOLERANCE   = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("Crystal - Shiny Gift Egg started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Hatch the egg manually, then navigate to the hatched "
                "Pokemon's sprite in the party/summary screen and draw a region.")
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
        log("Starting soft reset loop. Press Stop at any time.")

        sr_count = 0

        controller.soft_reset_z()
        if not self.wait(self.SOFT_RESET_WAIT, stop_event):
            return

        while not stop_event.is_set():

            # ── Title / continue (4 A presses) ───────────────────────────
            for _ in range(4):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.MENU_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Receive the Odd Egg from the Day Care woman ───────────────
            for _ in range(self.RECEIVE_A_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.RECEIVE_DIALOGUE, stop_event): break
            if stop_event.is_set(): break

            if not self.wait(self.PRE_NICKNAME_WAIT, stop_event): break

            # Decline nickname
            controller.press_a()
            if not self.wait(self.NICKNAME_DELAY, stop_event): break
            controller.press_b()
            if not self.wait(1.5, stop_event): break

            # Final A to close dialogue
            controller.press_a()
            if not self.wait(1.5, stop_event): break

            # ── Walk to hatch the egg ─────────────────────────────────────
            log(f"SR #{sr_count + 1}: Walking to hatch egg...")
            hatched = False
            for pass_num in range(self.WALK_PASSES):
                if stop_event.is_set(): break

                controller.hold_left()
                if not self.wait(self.WALK_DURATION, stop_event):
                    controller.release_all()
                    break
                controller.hold_right()
                if not self.wait(self.WALK_DURATION, stop_event):
                    controller.release_all()
                    break

                # Check for hatch text (white pixels in top portion)
                frame = frame_grabber.get_latest_frame()
                if frame is not None:
                    # Look for bright pixels in the top-screen text area
                    # (hatch notification text appears)
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
                log(f"SR #{sr_count + 1}: Egg did not hatch in time — retrying.")
                sr_count += 1
                controller.soft_reset_z()
                if not self.wait(self.SOFT_RESET_WAIT, stop_event): break
                continue

            # ── Hatch dialogue ────────────────────────────────────────────
            if not self.wait(self.HATCH_TEXT_DELAY, stop_event): break

            for _ in range(self.HATCH_A_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.HATCH_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Open party to check hatchling ─────────────────────────────
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
                                f"*** SHINY HATCHLING! "
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
            controller.soft_reset_z()
            if not self.wait(self.SOFT_RESET_WAIT, stop_event): break

        log("Crystal - Shiny Gift Egg stopped.")

    # ── Calibration ───────────────────────────────────────────────────────────

    def _calibrate(self, controller, frame_grabber, stop_event,
                   log, request_calibration):
        log("With the hatched Pokemon visible on screen, draw a region "
            "over its sprite.")

        region = request_calibration("Draw region over the hatched Pokemon's sprite")
        if stop_event.is_set():
            return None

        x, y, w, h = region
        time.sleep(0.1)
        frame = frame_grabber.get_latest_frame()
        if frame is None:
            log("No frame available — ensure webcam is connected.")
            return None

        r, g, b = self.avg_rgb(frame, x, y, w, h)
        log(f"Hatchling baseline — R:{r:.1f}  G:{g:.1f}  B:{b:.1f}")
        log("Calibration complete. Default tolerance ±15 applied.")
        log("Edit calibration/crystal_shiny_gift_egg.json to change 'tolerance'.")
        return {'region': [x, y, w, h], 'baseline': [r, g, b], 'tolerance': 15}

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
