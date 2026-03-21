"""
USUM - Shiny Legendary
Game: Pokemon Ultra Sun / Ultra Moon (3DS)

Soft-resets for shiny static legendary encounters (e.g. Solgaleo,
Lunala, Necrozma, and other fixed encounters). After reloading the
save, presses A through the title and continue screens, then presses
A to trigger the legendary encounter and checks the battle sprite for
shininess via avg_rgb.

Ported from USUM_Shiny_Static_Legendary_7.0.cpp.

How it works:
  The original C++ version uses LDR timing to measure the battle-
  intro duration and flags a shiny when it takes longer than the
  baseline. The Python port replaces this with avg_rgb comparison on
  a calibrated region of the legendary's battle sprite.

  1. Soft-resets (S command) with configurable SRdelay.
  2. A menuDelay → A 5 s (title + continue).
  3. Waits for the blackout (battle intro) then waits for the battle
     screen to load.
  4. avg_rgb check on the calibrated region.

Setup:
  - Save in front of the legendary spot.
  - On first run let the battle load and draw a region over the
    legendary's sprite.
  - Delete calibration/usum_shiny_legendary.json to recalibrate.
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
    return os.path.join(cal_dir, 'usum_shiny_legendary.json')


class USUMShinyLegendary(BaseScript):
    NAME = "USUM - Shiny Legendary"
    DESCRIPTION = "Soft-resets for shiny legendary encounters (Ultra Sun/Ultra Moon)."

    # ── Timing (seconds) — from USUM_Shiny_Static_Legendary_7.0.cpp ─────────
    SOFT_RESET_WAIT    = 8.0    # SRdelay (configurable in C++)
    MENU_A_1_DELAY     = 5.0    # menuDelay (configurable in C++)
    MENU_A_2_DELAY     = 5.0    # after second A (world loads)
    BATTLE_A_DELAY     = 1.5    # between A presses to trigger battle
    BATTLE_A_MAX       = 15     # safety limit for A presses
    BATTLE_LOAD_WAIT   = 10.0   # wait after blackout for sprite to appear
    SHINY_RECHECK_WAIT = 3.0

    # ── Blackout detection ────────────────────────────────────────────────────
    DARK_THRESHOLD = 40
    DARK_FRACTION  = 0.65

    COLOUR_TOLERANCE = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("USUM - Shiny Legendary started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Let the battle load, then draw a region over the legendary's sprite.")
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

        log(f"Legendary region: x={x} y={y} w={w} h={h} | tolerance ±{tolerance}")
        log("Soft reset loop running. Press Stop at any time.")

        sr_count = 0

        controller.soft_reset()
        if not self.wait(self.SOFT_RESET_WAIT, stop_event):
            return

        while not stop_event.is_set():

            # ── Navigate title / continue ──────────────────────────────────
            controller.press_a()
            if not self.wait(self.MENU_A_1_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.MENU_A_2_DELAY, stop_event): break

            # ── Press A until battle blackout ─────────────────────────────
            blackout = False
            for _ in range(self.BATTLE_A_MAX):
                if stop_event.is_set(): break
                controller.press_a()
                blackout = self._wait_for_blackout(
                    frame_grabber, stop_event, self.BATTLE_A_DELAY
                )
                if blackout:
                    break
            if stop_event.is_set(): break

            if not blackout:
                log("Blackout not detected — retrying.")
                controller.soft_reset()
                if not self.wait(self.SOFT_RESET_WAIT, stop_event): break
                continue

            if not self.wait(self.BATTLE_LOAD_WAIT, stop_event): break

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
                                f"*** SHINY LEGENDARY! "
                                f"R:{r2:.0f} G:{g2:.0f} B:{b2:.0f}  "
                                f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f}) ***"
                            )
                            log(f"Soft resets before shiny: {sr_count}")
                            shiny_found = True

            if stop_event.is_set(): break

            if shiny_found:
                log("Script paused — catch your shiny! Press Stop when done.")
                stop_event.wait()
                break

            sr_count += 1
            log(f"No shiny. Soft reset #{sr_count}...")
            controller.soft_reset()
            if not self.wait(self.SOFT_RESET_WAIT, stop_event): break

        log("USUM - Shiny Legendary stopped.")

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
        log("Draw a region over the legendary's battle sprite.")
        region = request_calibration("Draw region over legendary's sprite")
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
