"""
Crystal - Shiny Sudowoodo
Game: Pokemon Crystal (3DS Virtual Console)

Soft-resets for the shiny Sudowoodo static encounter on Route 36.

Ported from VC_Crystal_Shiny_Sudowoodo_2.0.cpp.

How it works:
  The C++ original uses LDR timing — it measures the delay from using the
  SquirtBottle to the battle intro text appearing. Shiny encounters are longer.

  This Python version uses avg_rgb comparison on the battle sprite region.

Setup:
  - Save on Route 36, standing directly in front of the odd tree (Sudowoodo),
    with the SquirtBottle in your bag.
  - On first run, use the SquirtBottle and let the battle start, then draw a
    region over Sudowoodo's sprite.
  - Delete calibration/crystal_shiny_sudowoodo.json to recalibrate.
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
    return os.path.join(cal_dir, 'crystal_shiny_sudowoodo.json')


class CrystalShinySudowoodo(BaseScript):
    NAME = "Crystal - Shiny Sudowoodo"
    DESCRIPTION = "Soft-resets for shiny Sudowoodo on Route 36 (Crystal VC)."

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    SOFT_RESET_WAIT    = 5.0    # after Z reset for VC to reload
    MENU_A_DELAY       = 1.4    # between A presses through title/continue
    # Navigate menus to use SquirtBottle:
    OPEN_MENU_DELAY    = 1.3    # after X to open menu
    DOWN_TO_BAG_DELAY  = 1.3    # after Down to reach BAG
    OPEN_BAG_DELAY     = 2.0    # after A to open bag
    SELECT_ITEM_DELAY  = 2.0    # after A to select SquirtBottle
    USE_ITEM_DELAY     = 2.5    # after A to use item
    # A+2 to confirm use, then A: after A → 2.5s
    CONFIRM_DELAY      = 2.5    # after A to confirm
    INTERACT_DELAY     = 1.3    # A to interact with tree
    BATTLE_LOAD_WAIT   = 7.0    # wait for battle to load after interaction
    SHINY_RECHECK_WAIT = 3.0    # wait before confirming suspected shiny

    COLOUR_TOLERANCE   = 15     # ±tolerance per channel

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("Crystal - Shiny Sudowoodo started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Use the SquirtBottle on Sudowoodo manually, let the battle "
                "start, then draw a region over its sprite.")
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

            # ── Open menu and use SquirtBottle ────────────────────────────
            # X → Down → A (bag) → A (SquirtBottle) → A (use) → A (confirm)
            controller.press_x()
            if not self.wait(self.OPEN_MENU_DELAY, stop_event): break

            controller.press_down()
            if not self.wait(self.DOWN_TO_BAG_DELAY, stop_event): break

            controller.press_a()   # open bag
            if not self.wait(self.OPEN_BAG_DELAY, stop_event): break

            controller.press_a()   # select SquirtBottle
            if not self.wait(self.SELECT_ITEM_DELAY, stop_event): break

            controller.press_a()   # use
            if not self.wait(self.USE_ITEM_DELAY, stop_event): break

            controller.press_a()   # confirm target (odd tree)
            if not self.wait(self.CONFIRM_DELAY, stop_event): break

            # ── Battle loads ──────────────────────────────────────────────
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
            controller.soft_reset_z()
            if not self.wait(self.SOFT_RESET_WAIT, stop_event): break

        log("Crystal - Shiny Sudowoodo stopped.")

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
        log("Edit calibration/crystal_shiny_sudowoodo.json to change 'tolerance'.")
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
