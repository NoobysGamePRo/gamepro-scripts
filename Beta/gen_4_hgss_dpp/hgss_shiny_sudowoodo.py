"""
HGSS - Shiny Sudowoodo
Game: Pokemon HeartGold / SoulSilver (DS via 3DS)

Soft-resets for the shiny Sudowoodo static encounter on Route 36.

Ported from HGSS_Shiny_Sudowoodo_2.0.cpp.

How it works:
  Uses avg_rgb comparison on the Sudowoodo battle sprite. Calibrate the
  region once, then the script cycles: SR → navigate → use SquirtBottle →
  battle loads → check colour → SR.

Setup:
  - Save on Route 36, standing directly in front of Sudowoodo, with the
    SquirtBottle registered (or accessible via the bag Y shortcut).
  - On first run, let the battle start, draw a region over Sudowoodo's sprite.
  - Delete calibration/hgss_shiny_sudowoodo.json to recalibrate.
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
    return os.path.join(cal_dir, 'hgss_shiny_sudowoodo.json')


class HGSSShinySudowoodo(BaseScript):
    NAME = "HGSS - Shiny Sudowoodo"
    DESCRIPTION = "Soft-resets for shiny Sudowoodo on Route 36 (HeartGold/SoulSilver)."

    # ── Timing (seconds) — from HGSS_Shiny_Sudowoodo_2.0.cpp ─────────────────
    SOFT_RESET_WAIT    = 12.0   # DS reload
    MENU_A_1_DELAY     = 4.0
    MENU_A_2_DELAY     = 5.0
    MENU_A_3_DELAY     = 5.0
    # Use SquirtBottle: Y (registered item) → A to confirm use on tree
    USE_ITEM_DELAY     = 2.0    # after Y to open registered item
    CONFIRM_DELAY      = 2.5    # after A to confirm use
    BATTLE_LOAD_WAIT   = 7.0    # wait for battle screen
    SHINY_RECHECK_WAIT = 3.0

    COLOUR_TOLERANCE   = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("HGSS - Shiny Sudowoodo started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Use the SquirtBottle, let the battle start, "
                "then draw a region over Sudowoodo's sprite.")
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

        log(f"Sudowoodo region: x={x} y={y} w={w} h={h} | tolerance ±{tolerance}")
        log("Starting soft reset loop. Press Stop at any time.")

        sr_count = 0

        controller.soft_reset()
        if not self.wait(self.SOFT_RESET_WAIT, stop_event):
            return

        while not stop_event.is_set():

            # ── Title / continue / load ───────────────────────────────────
            controller.press_a()
            if not self.wait(self.MENU_A_1_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.MENU_A_2_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.MENU_A_3_DELAY, stop_event): break

            # ── Use SquirtBottle on the odd tree ──────────────────────────
            # Y activates the registered item (SquirtBottle)
            controller.press_y()
            if not self.wait(self.USE_ITEM_DELAY, stop_event): break

            controller.press_a()   # confirm use on the tree
            if not self.wait(self.CONFIRM_DELAY, stop_event): break

            # Wait for battle to load
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
                                f"*** SHINY SUDOWOODO! "
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

        log("HGSS - Shiny Sudowoodo stopped.")

    # ── Calibration ───────────────────────────────────────────────────────────

    def _calibrate(self, controller, frame_grabber, stop_event,
                   log, request_calibration):
        log("With the Sudowoodo battle active, draw a region over its sprite.")

        region = request_calibration("Draw region over Sudowoodo's battle sprite")
        if stop_event.is_set():
            return None

        x, y, w, h = region
        time.sleep(0.1)
        frame = frame_grabber.get_latest_frame()
        if frame is None:
            log("No frame available — ensure webcam is connected.")
            return None

        r, g, b = self.avg_rgb(frame, x, y, w, h)
        log(f"Sudowoodo baseline — R:{r:.1f}  G:{g:.1f}  B:{b:.1f}")
        log("Calibration complete. Default tolerance ±15 applied.")
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
