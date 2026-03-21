"""
Sun / Moon - Shiny Wimpod
Game: Pokemon Sun / Moon (3DS)

Hunts for a shiny Wimpod on Route 8 (or Poni Wilds in USUM).
Wimpod is a static encounter that runs away; the script interacts
with it (A press), waits for the battle to load, and checks the
sprite for shininess via avg_rgb. If not shiny, the Wimpod fled so
the script soft-resets and repeats.

Ported from Shiny_Wimpod_Static_3.0.cpp.

How it works:
  The C++ program uses LDR timing with the same step-change
  detection pattern used for Crabrawler. The Python port uses
  avg_rgb comparison on a calibrated battle-sprite region.

  1. Soft-resets (S command) and waits 12 s.
  2. A 3.5 s → A 10 s (title / continue).
  3. A to approach and trigger the Wimpod encounter; waits for
     blackout.
  4. Waits BATTLE_WAIT s for the sprite to load.
  5. avg_rgb check vs. calibrated baseline ± tolerance.
  6. If not shiny: soft-reset and repeat.

Setup:
  - Save directly in front of Wimpod on Route 8 (or Poni Wilds).
  - On first run let the Wimpod battle load, then draw a region over
    its sprite.
  - Delete calibration/shiny_wimpod.json to recalibrate.
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
    return os.path.join(cal_dir, 'shiny_wimpod.json')


class ShinyWimpod(BaseScript):
    NAME = "Sun / Moon - Shiny Wimpod"
    DESCRIPTION = "Hunts for shiny Wimpod on Route 8 (Sun/Moon)."

    # ── Timing (seconds) — from Shiny_Wimpod_Static_3.0.cpp ─────────────────
    SOFT_RESET_WAIT    = 12.0   # 3DS reload
    MENU_A_1_DELAY     = 3.5    # title A
    MENU_A_2_DELAY     = 10.0   # continue A (world load + walk to Wimpod)
    BATTLE_A_DELAY     = 1.5    # between A presses to trigger encounter
    BATTLE_A_MAX       = 10     # safety limit
    BATTLE_WAIT        = 8.0    # wait after blackout for sprite
    SHINY_RECHECK_WAIT = 3.0

    # ── Blackout detection ────────────────────────────────────────────────────
    DARK_THRESHOLD = 40
    DARK_FRACTION  = 0.65

    COLOUR_TOLERANCE = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("Sun / Moon - Shiny Wimpod started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Let the Wimpod battle load, then draw a region over its sprite.")
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

        log(f"Wimpod region: x={x} y={y} w={w} h={h} | tolerance ±{tolerance}")
        log("Soft reset loop running. Press Stop at any time.")

        sr_count = 0

        controller.soft_reset()
        if not self.wait(self.SOFT_RESET_WAIT, stop_event):
            return

        while not stop_event.is_set():

            # ── Navigate menus ─────────────────────────────────────────────
            controller.press_a()
            if not self.wait(self.MENU_A_1_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.MENU_A_2_DELAY, stop_event): break

            # ── Press A until blackout ─────────────────────────────────────
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

            if not self.wait(self.BATTLE_WAIT, stop_event): break

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
                                f"*** SHINY WIMPOD! SR #{sr_count + 1} "
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

        log("Sun / Moon - Shiny Wimpod stopped.")

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
        log("Draw a region over the Wimpod's battle sprite.")
        region = request_calibration("Draw region over Wimpod's sprite")
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
