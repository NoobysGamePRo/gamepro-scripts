"""
USUM - Static Type: Null
Game: Pokemon Ultra Sun / Ultra Moon (3DS)

Soft-resets for the shiny Type: Null gift from Wicke in Aether
Paradise. After each soft reset, navigates the title and continue
screens, advances through the Wicke dialogue, and checks the summary
screen (or battle sprite region) for shininess via avg_rgb.

Ported from Static_Shiny_Type_Null_2.0.cpp.

How it works:
  1. Soft-resets (S command) and waits 7 s for the 3DS to reload.
  2. A 3.8 s → A 6.5 s → A 2.2 s (title / continue / world load).
  3. A × 16 (1.1 s each) — Wicke dialogue to gift Type: Null.
  4. 4.4 s wait for the summary / naming screen.
  5. A 7 s — final confirmation, summary loads.
  6. avg_rgb check on the calibrated sprite region.

Setup:
  - Save in front of Wicke in Aether Paradise just before the gift
    dialogue begins.
  - On first run let the Type: Null summary screen appear, then draw
    a region over its sprite.
  - Delete calibration/static_type_null.json to recalibrate.
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
    return os.path.join(cal_dir, 'static_type_null.json')


class StaticTypeNull(BaseScript):
    NAME = "USUM - Static Type: Null"
    DESCRIPTION = "Soft-resets for the shiny Type: Null gift (Ultra Sun/Ultra Moon)."

    # ── Timing (seconds) — from Static_Shiny_Type_Null_2.0.cpp ──────────────
    SOFT_RESET_WAIT  = 7.0    # 3DS reload
    MENU_A_1_DELAY   = 3.8    # title A
    MENU_A_2_DELAY   = 6.5    # continue A
    MENU_A_3_DELAY   = 2.2    # world load A
    WICKE_A_COUNT    = 16     # A presses through Wicke gift dialogue
    WICKE_A_DELAY    = 1.1    # delay between each dialogue A
    POST_GIFT_WAIT   = 4.4    # wait after gift for summary/naming screen
    SUMMARY_A_DELAY  = 7.0    # A to open summary / confirm
    SHINY_RECHECK    = 3.0

    COLOUR_TOLERANCE = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("USUM - Static Type: Null started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Let the Type: Null summary screen appear, then draw a region "
                "over its sprite.")
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

        log(f"Type: Null region: x={x} y={y} w={w} h={h} | tolerance ±{tolerance}")
        log("Soft reset loop running. Press Stop at any time.")

        sr_count = 0

        controller.soft_reset()
        if not self.wait(self.SOFT_RESET_WAIT, stop_event):
            return

        while not stop_event.is_set():

            # ── Navigate menus ────────────────────────────────────────────
            controller.press_a()
            if not self.wait(self.MENU_A_1_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.MENU_A_2_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.MENU_A_3_DELAY, stop_event): break

            # ── Wicke dialogue × 16 ───────────────────────────────────────
            for _ in range(self.WICKE_A_COUNT):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.WICKE_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Wait for summary / naming screen ──────────────────────────
            if not self.wait(self.POST_GIFT_WAIT, stop_event): break

            controller.press_a()
            if not self.wait(self.SUMMARY_A_DELAY, stop_event): break

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
                                f"*** SHINY TYPE: NULL! SR #{sr_count + 1} "
                                f"R:{r2:.0f} G:{g2:.0f} B:{b2:.0f}  "
                                f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f}) ***"
                            )
                            shiny_found = True

            if stop_event.is_set(): break

            if shiny_found:
                log("Script paused — enjoy your shiny! Press Stop when done.")
                stop_event.wait()
                break

            sr_count += 1
            log(f"Not shiny. Soft reset #{sr_count}...")
            controller.soft_reset()
            if not self.wait(self.SOFT_RESET_WAIT, stop_event): break

        log("USUM - Static Type: Null stopped.")

    def _calibrate(self, controller, frame_grabber, stop_event,
                   log, request_calibration):
        log("Draw a region over the Type: Null sprite on the summary screen.")
        region = request_calibration("Draw region over Type: Null sprite")
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
