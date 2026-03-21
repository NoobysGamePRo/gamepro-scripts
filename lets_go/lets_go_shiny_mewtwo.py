"""
Let's Go — Shiny Mewtwo Hunter
Game: Pokemon Let's Go Pikachu / Eevee (Nintendo Switch)

Soft-resets for shiny Mewtwo in Cerulean Cave.
Detection: avg_rgb comparison on Mewtwo's sprite region.

Same reset strategy as the Shiny Legendary script, tuned for Mewtwo.

How it works:
  1. Soft-resets via Home → X → A → A (reopen game).
  2. Waits for Switch load screens (dark/bright polling).
  3. Approaches Mewtwo with A → + → ANIMATION_DELAY.
  4. Checks avg_rgb at the calibrated region vs baseline.
  5. If outside ±COLOUR_TOLERANCE: shiny!

Setup:
  - Save directly in front of Mewtwo in Cerulean Cave.
  - Set ANIMATION_DELAY to match Mewtwo's encounter animation
    (approximately 13 seconds — adjust if needed).
  - On first run, draw a region over Mewtwo's sprite when prompted.
  - Calibration saved to calibration/lets_go_shiny_mewtwo.json.
  - Delete that file to recalibrate.
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
    return os.path.join(cal_dir, 'lets_go_shiny_mewtwo.json')


class LetsGoShinyMewtwo(BaseScript):
    NAME = "Let's Go – Shiny Mewtwo"
    DESCRIPTION = (
        "Soft-resets for shiny Mewtwo in Cerulean Cave "
        "(Let's Go Pikachu/Eevee)."
    )

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    HOME_DELAY          = 1.5
    CLOSE_X_DELAY       = 1.5
    CLOSE_A_DELAY       = 3.0
    SELECT_GAME_DELAY   = 1.5
    SELECT_USER_DELAY   = 2.0
    DARK_POLL_INTERVAL  = 0.1
    DARK_WAIT_TIMEOUT   = 20.0
    BRIGHT_WAIT_TIMEOUT = 20.0
    BRIGHT_EXTRA_DELAY  = 0.5
    CONTROLLER_DELAY    = 2.0
    CONFIRM_CTRL_DELAY  = 18.0
    ENTER_GAME_DELAY    = 1.5
    DARK2_EXTRA_DELAY   = 1.5
    CONTINUE_DELAY      = 6.0
    APPROACH_DELAY      = 4.0
    ANIMATION_DELAY     = 13.0   # Mewtwo encounter animation (~13 s)
    SHINY_RECHECK_WAIT  = 2.0

    # ── Detection ─────────────────────────────────────────────────────────────
    BRIGHTNESS_REGION   = (150, 150, 200, 100)
    BRIGHTNESS_DARK     = 100
    BRIGHTNESS_BRIGHT   = 100
    COLOUR_TOLERANCE    = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("Let's Go Shiny Mewtwo started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration — will prompt for sprite region on first encounter.")

        log("Performing initial soft reset...")
        if not self._soft_reset_and_boot(controller, frame_grabber, stop_event, log):
            return

        if cal is None:
            log("Approaching Mewtwo for calibration...")
            if not self._approach_mewtwo(controller, stop_event):
                return
            log("Draw a region over Mewtwo's sprite.")
            region = request_calibration("Draw region over Mewtwo's sprite")
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
            log("Calibration saved. Resetting...")
            controller.soft_reset()
            if not self.wait(1.0, stop_event): return
            if not self._soft_reset_and_boot(controller, frame_grabber, stop_event, log):
                return

        rx, ry, rw, rh = cal['region']
        br, bg, bb = cal['baseline']
        tol = cal.get('tolerance', self.COLOUR_TOLERANCE)
        sr_count = 0

        log(f"Shiny hunting Mewtwo. Tolerance ±{tol}")

        while not stop_event.is_set():
            if not self._approach_mewtwo(controller, stop_event):
                break

            frame = frame_grabber.get_latest_frame()
            if frame is not None:
                r, g, b = self.avg_rgb(frame, rx, ry, rw, rh)
                log(
                    f"SR #{sr_count + 1}: "
                    f"R:{r:.0f} G:{g:.0f} B:{b:.0f}  "
                    f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f})"
                )

                if (abs(r - br) > tol or abs(g - bg) > tol or abs(b - bb) > tol):
                    if not self.wait(self.SHINY_RECHECK_WAIT, stop_event): break
                    frame2 = frame_grabber.get_latest_frame()
                    if frame2 is not None:
                        r2, g2, b2 = self.avg_rgb(frame2, rx, ry, rw, rh)
                        if (abs(r2 - br) > tol or
                                abs(g2 - bg) > tol or
                                abs(b2 - bb) > tol):
                            log(
                                f"*** SHINY MEWTWO! "
                                f"R:{r2:.0f} G:{g2:.0f} B:{b2:.0f} ***"
                            )
                            log(f"Soft resets before shiny: {sr_count}")
                            controller.soft_reset()
                            log("Script stopped — catch your shiny! "
                                "Press ■ Stop when done.")
                            stop_event.wait()
                            return

            sr_count += 1
            log(f"Not shiny. Soft reset #{sr_count}...")
            if not self._soft_reset_and_boot(controller, frame_grabber, stop_event, log):
                break

        log("Let's Go Shiny Mewtwo stopped.")

    def _soft_reset_and_boot(self, controller, frame_grabber, stop_event, log) -> bool:
        controller.soft_reset()
        if not self.wait(self.HOME_DELAY, stop_event): return False
        controller.press_x()
        if not self.wait(self.CLOSE_X_DELAY, stop_event): return False
        controller.press_a()
        if not self.wait(self.CLOSE_A_DELAY, stop_event): return False
        controller.press_a()
        if not self.wait(self.SELECT_GAME_DELAY, stop_event): return False
        controller.press_a()
        if not self.wait(self.SELECT_USER_DELAY, stop_event): return False

        self._wait_for_brightness(frame_grabber, stop_event, dark=True,
                                  timeout=self.DARK_WAIT_TIMEOUT, log=log)
        if stop_event.is_set(): return False
        if not self.wait(5.0, stop_event): return False

        self._wait_for_brightness(frame_grabber, stop_event, dark=False,
                                  timeout=self.BRIGHT_WAIT_TIMEOUT, log=log)
        if stop_event.is_set(): return False
        if not self.wait(self.BRIGHT_EXTRA_DELAY, stop_event): return False

        controller.press_a()
        if not self.wait(self.CONTROLLER_DELAY, stop_event): return False
        controller.press_a()
        if not self.wait(self.CONFIRM_CTRL_DELAY, stop_event): return False

        controller.press_a()
        if not self.wait(self.ENTER_GAME_DELAY, stop_event): return False

        self._wait_for_brightness(frame_grabber, stop_event, dark=True,
                                  timeout=self.DARK_WAIT_TIMEOUT, log=None)
        if stop_event.is_set(): return False
        if not self.wait(self.DARK2_EXTRA_DELAY, stop_event): return False
        controller.press_a()
        if not self.wait(self.CONTINUE_DELAY, stop_event): return False
        return True

    def _approach_mewtwo(self, controller, stop_event) -> bool:
        controller.press_a()
        if not self.wait(self.APPROACH_DELAY, stop_event): return False
        controller.press_plus()
        if not self.wait(self.ANIMATION_DELAY, stop_event): return False
        return True

    def _wait_for_brightness(self, frame_grabber, stop_event, dark: bool,
                              timeout: float, log) -> bool:
        bx, by, bw, bh = self.BRIGHTNESS_REGION
        deadline = time.time() + timeout
        while time.time() < deadline:
            if stop_event.is_set():
                return False
            frame = frame_grabber.get_latest_frame() if frame_grabber else None
            if frame is not None:
                r, g, b = self.avg_rgb(frame, bx, by, bw, bh)
                avg = (r + g + b) / 3
                if dark and avg < self.BRIGHTNESS_DARK:
                    return True
                if not dark and avg > self.BRIGHTNESS_BRIGHT:
                    return True
            time.sleep(self.DARK_POLL_INTERVAL)
        if log:
            log("Screen brightness timeout — continuing.")
        return not stop_event.is_set()

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
