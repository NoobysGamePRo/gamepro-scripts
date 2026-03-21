"""
Sun / Moon - Shiny Starter
Game: Pokemon Sun / Moon (3DS)

Soft-resets for a shiny Rowlet, Litten, or Popplio. The Sun/Moon
intro sequence is similar to USUM but with a shorter load time and
slightly different dialogue pacing.

How it works:
  1. Soft-resets (S command).
  2. Navigates title + continue menus (A × menuDelay → A 8 s).
  3. Waits through the Kukui intro (A 10 s → A 12.5 s → A × 4 at 2.8 s).
  4. Advances the Rotom cutscene and trainer-card dialogue.
  5. Selects the chosen starter via Down navigation.
  6. Waits for the battle to load, then checks avg_rgb on the
     calibrated region vs. baseline ± tolerance.

Setup:
  - Save just before the intro sequence begins (new game / continue).
  - On first run let the starter battle load and draw a region over
    the starter's battle sprite.
  - STARTER: 'rowlet' (no nav), 'litten' (Down × 1),
    'popplio' (Down × 2).
  - Delete calibration/sun_moon_shiny_starter.json to recalibrate.
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
    return os.path.join(cal_dir, 'sun_moon_shiny_starter.json')


class SunMoonShinyStarter(BaseScript):
    NAME = "Sun / Moon - Shiny Starter"
    DESCRIPTION = "Soft-resets for a shiny starter (Sun/Moon)."

    # ── Starter choice ─────────────────────────────────────────────────────────
    # 'rowlet' = no navigation, 'litten' = Down × 1, 'popplio' = Down × 2
    STARTER = 'rowlet'

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    SOFT_RESET_WAIT  = 8.0    # 3DS reload
    MENU_A_DELAY     = 5.0    # title / continue screens
    INTRO_A_1_DELAY  = 8.0    # after second title A (walk into overworld)
    INTRO_A_2_DELAY  = 10.0   # Yungoos encounter lead-up
    INTRO_A_3_DELAY  = 12.5   # rescued by starters
    RESCUE_A_COUNT   = 4
    RESCUE_A_DELAY   = 2.8    # A × 4 through rescue cutscene
    RESCUE_WAIT      = 16.0   # cutscene loads
    DIAL_A_DELAY     = 1.2    # short dialogue A presses
    DIAL_A_LONG_1    = 3.5    # longer dialogue gaps
    DIAL_A_LONG_2    = 3.0
    DIAL_SHORT_COUNT = 4      # A × 4 short sequence
    DIAL_LONG_COUNT  = 7      # A × 7 long sequence
    DIAL_WAIT_1      = 4.0
    DIAL_CYCLE_A     = 3.0    # alternating 3 s / 2 s × 3
    DIAL_CYCLE_B     = 2.0
    DIAL_CYCLE_COUNT = 3
    DIAL_A_END_COUNT = 2      # A × 2 before wait
    DIAL_WAIT_2      = 3.0
    DIAL_A_END2_COUNT = 2     # A × 2 after second wait
    DIAL_WAIT_3      = 6.0
    PRE_SELECT_DELAY = 1.2    # A before starter selection
    SELECT_A_DELAY   = 1.8
    CONFIRM_A_COUNT  = 2
    CONFIRM_A_DELAY  = 1.2
    POST_CONFIRM_A   = 2.5
    BATTLE_WAIT      = 27.0   # wait for battle sprite
    CHECK_A_DELAY    = 5.0
    SHINY_RECHECK    = 3.0

    COLOUR_TOLERANCE = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("Sun / Moon - Shiny Starter started.")
        log(f"Starter: {self.STARTER.title()}")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Let the starter battle load, then draw a region over its sprite.")
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

        log(f"Starter region: x={x} y={y} w={w} h={h} | tolerance ±{tolerance}")
        log("Soft reset loop running. Press Stop at any time.")

        sr_count = 0

        controller.soft_reset()
        if not self.wait(self.SOFT_RESET_WAIT, stop_event):
            return

        while not stop_event.is_set():

            # ── Title / intro ─────────────────────────────────────────────
            controller.press_a()
            if not self.wait(self.MENU_A_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.INTRO_A_1_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.INTRO_A_2_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.INTRO_A_3_DELAY, stop_event): break

            # ── Rescue cutscene ───────────────────────────────────────────
            for _ in range(self.RESCUE_A_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.RESCUE_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            if not self.wait(self.RESCUE_WAIT, stop_event): break

            # ── Dialogue ──────────────────────────────────────────────────
            controller.press_a()
            if not self.wait(self.DIAL_A_LONG_1, stop_event): break

            controller.press_a()
            if not self.wait(self.DIAL_A_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.DIAL_A_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.DIAL_A_LONG_2, stop_event): break

            for _ in range(self.DIAL_SHORT_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.DIAL_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            controller.press_a()
            if not self.wait(1.5, stop_event): break

            for _ in range(self.DIAL_LONG_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.DIAL_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            if not self.wait(self.DIAL_WAIT_1, stop_event): break

            for _ in range(self.DIAL_CYCLE_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.DIAL_CYCLE_A, stop_event): break
                controller.press_a()
                if not self.wait(self.DIAL_CYCLE_B, stop_event): break
            if stop_event.is_set(): break

            for _ in range(self.DIAL_A_END_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.DIAL_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            if not self.wait(self.DIAL_WAIT_2, stop_event): break

            for _ in range(self.DIAL_A_END2_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.DIAL_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            if not self.wait(self.DIAL_WAIT_3, stop_event): break

            # ── Starter selection ─────────────────────────────────────────
            controller.press_a()
            if not self.wait(self.PRE_SELECT_DELAY, stop_event): break

            if self.STARTER == 'litten':
                controller.press_down()
                if not self.wait(self.DIAL_A_DELAY, stop_event): break
            elif self.STARTER == 'popplio':
                controller.press_down()
                if not self.wait(self.DIAL_A_DELAY, stop_event): break
                controller.press_down()
                if not self.wait(self.DIAL_A_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.SELECT_A_DELAY, stop_event): break

            for _ in range(self.CONFIRM_A_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.CONFIRM_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            controller.press_a()
            if not self.wait(self.POST_CONFIRM_A, stop_event): break

            if not self.wait(self.BATTLE_WAIT, stop_event): break

            controller.press_a()
            if not self.wait(self.CHECK_A_DELAY, stop_event): break

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
                                f"*** SHINY {self.STARTER.title()}! SR #{sr_count + 1} "
                                f"R:{r2:.0f} G:{g2:.0f} B:{b2:.0f}  "
                                f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f}) ***"
                            )
                            shiny_found = True

            if stop_event.is_set(): break

            if shiny_found:
                log("Script paused — catch your shiny! Press Stop when done.")
                stop_event.wait()
                break

            sr_count += 1
            log(f"Not shiny. Soft reset #{sr_count}...")
            controller.soft_reset()
            if not self.wait(self.SOFT_RESET_WAIT, stop_event): break

        log("Sun / Moon - Shiny Starter stopped.")

    def _calibrate(self, controller, frame_grabber, stop_event,
                   log, request_calibration):
        log("Draw a region over the starter's battle sprite.")
        region = request_calibration("Draw region over starter sprite")
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
