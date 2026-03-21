"""
Platinum - Shiny Starter
Game: Pokemon Platinum (DS via 3DS)

Soft-resets for a shiny Turtwig, Chimchar, or Piplup from Prof. Rowan's
briefcase on Route 201.

Ported from Platinum_Shiny_Starter_2.0.cpp.

How it works:
  The C++ version uses LDR timing — it starts a timer when the final A
  is pressed to trigger the battle with the starter, then waits for the
  screen brightness step-change (battle blackout). A shiny starter causes
  a longer delay.

  This Python port uses avg_rgb comparison on the starter's battle sprite.

Starter selection:
  Set STARTER = 'turtwig', 'chimchar', or 'piplup'.
  - Turtwig: no navigation needed (default/left position)
  - Chimchar: Right x1
  - Piplup:   Right x2

Setup:
  - Save on Route 201 just before the cutscene where the Starly attacks
    and Rowan's briefcase is available.
  - On first run, navigate to a starter, select it, let the battle start,
    then draw a region over the starter's sprite.
  - Delete calibration/platinum_shiny_starter.json to recalibrate.
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
    return os.path.join(cal_dir, 'platinum_shiny_starter.json')


class PlatinumShinyStarter(BaseScript):
    NAME = "Platinum - Shiny Starter"
    DESCRIPTION = "Soft-resets for a shiny starter in Pokemon Platinum."

    # ── Starter choice ────────────────────────────────────────────────────────
    # 'turtwig', 'chimchar', or 'piplup'
    STARTER = 'turtwig'

    # ── Timing (seconds) — from Platinum_Shiny_Starter_2.0.cpp ───────────────
    SOFT_RESET_WAIT    = 12.0   # DS reload
    MENU_A_1_DELAY     = 3.0    # A1 (title)
    MENU_A_2_DELAY     = 6.0    # A2 (continue / load map - menuDelay in C++)
    MENU_A_3_DELAY     = 5.0    # A3 (load world)
    MENU_A_4_DELAY     = 6.0    # A4 (load world / reach overworld)
    MENU_A_5_DELAY     = 1.5    # A5 (cutscene)
    NAV_DELAY          = 1.5    # after each Right press when selecting starter
    # Briefcase interaction sequence (from C++):
    CHOOSE_A_DELAY     = 2.0    # after A to choose starter
    CONFIRM_A_DELAY    = 4.0    # after A to confirm
    BATTLE_SEQ_DELAY   = 2.0    # between multiple A presses in battle trigger
    A_LOOP_DELAY       = 1.5    # between loop A presses (x6 then x5)
    FINAL_A_DELAY      = 7.0    # before LDR monitoring in C++ (battle triggers)
    BATTLE_LOAD_WAIT   = 8.0    # additional wait for battle screen
    SHINY_RECHECK_WAIT = 3.0

    COLOUR_TOLERANCE   = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("Platinum - Shiny Starter started.")
        log(f"Starter: {self.STARTER.title()}")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Navigate to a starter, let the Starly battle begin, then "
                "draw a region over the starter's sprite.")
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

            # ── Navigate menus ────────────────────────────────────────────
            controller.press_a()
            if not self.wait(self.MENU_A_1_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.MENU_A_2_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.MENU_A_3_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.MENU_A_4_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.MENU_A_5_DELAY, stop_event): break

            # ── Select starter ────────────────────────────────────────────
            if self.STARTER == 'chimchar':
                controller.press_right()
                if not self.wait(self.NAV_DELAY, stop_event): break
            elif self.STARTER == 'piplup':
                controller.press_right()
                if not self.wait(self.NAV_DELAY, stop_event): break
                controller.press_right()
                if not self.wait(self.NAV_DELAY, stop_event): break

            # ── Choose and confirm starter ────────────────────────────────
            controller.press_a()   # choose starter
            if not self.wait(self.CHOOSE_A_DELAY, stop_event): break
            controller.press_a()   # confirm
            if not self.wait(self.CONFIRM_A_DELAY, stop_event): break

            controller.press_a()   # continue cutscene/battle
            if not self.wait(self.BATTLE_SEQ_DELAY, stop_event): break

            # ── Button sequence from C++ before battle triggers ───────────
            for _ in range(6):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.A_LOOP_DELAY, stop_event): break
            if stop_event.is_set(): break

            controller.press_a()   # "final" A — battle begins
            if not self.wait(self.FINAL_A_DELAY, stop_event): break

            for _ in range(5):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.A_LOOP_DELAY, stop_event): break
            if stop_event.is_set(): break

            controller.press_a()
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
                                f"*** SHINY {self.STARTER.title()}! "
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

        log("Platinum - Shiny Starter stopped.")

    def _calibrate(self, controller, frame_grabber, stop_event,
                   log, request_calibration):
        log("Draw a region over the starter's battle sprite.")
        region = request_calibration(f"Draw region over {self.STARTER.title()}'s sprite")
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
