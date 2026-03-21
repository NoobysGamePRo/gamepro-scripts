"""
BW - Shiny Starter
Game: Pokemon Black / White (DS via 3DS)

Soft-resets for a shiny Snivy, Tepig, or Oshawott from Prof. Juniper's lab
in Nuvema Town.

Ported from BW_Shiny_Starter_2.0.cpp.

How it works:
  The C++ version uses LDR timing — it starts timing when the final A is
  pressed to trigger the rival battle with the starter, waiting for the
  screen brightness step-change. Shiny starters take longer.

  This Python port uses avg_rgb comparison on the starter's battle sprite.

Starter selection:
  Set STARTER = 'snivy', 'tepig', or 'oshawott'.
  - Snivy:    Left x1 from default
  - Tepig:    Centre (default)
  - Oshawott: Right x1

Setup:
  - Save in Juniper's lab facing the three Poke Balls.
  - On first run, trigger the rival battle and draw a region over the
    starter's sprite when the battle screen loads.
  - Delete calibration/bw_shiny_starter.json to recalibrate.
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
    return os.path.join(cal_dir, 'bw_shiny_starter.json')


class BWShinyStarter(BaseScript):
    NAME = "BW - Shiny Starter"
    DESCRIPTION = "Soft-resets for a shiny starter in Pokemon Black / White."

    # ── Starter choice ────────────────────────────────────────────────────────
    # 'snivy' (grass/left), 'tepig' (fire/centre), 'oshawott' (water/right)
    STARTER = 'tepig'

    # ── Timing (seconds) — from BW_Shiny_Starter_2.0.cpp ─────────────────────
    SOFT_RESET_WAIT    = 14.0   # DS reload (BW takes ~14s)
    MENU_A_1_DELAY     = 2.5    # A1 (title)
    MENU_A_2_DELAY     = 3.5    # A2 (continue)
    MENU_A_3_DELAY     = 9.0    # A3 (long load in BW)
    MENU_A_4_DELAY     = 1.0    # A4
    MENU_A_5_DELAY     = 4.0    # A5
    MENU_A_6_DELAY     = 5.0    # A6
    MENU_A_7_DELAY     = 1.0    # A7 (before starter choice)
    NAV_DELAY          = 1.0    # after Left/Right to select starter
    # After selecting starter (A → A):
    CHOOSE_A_DELAY     = 1.0
    CONFIRM_DELAY      = 8.5    # long wait (battle animation)
    POST_CONFIRM_LOOP1 = 2.0    # A×2 with this delay
    POST_CONFIRM_LOOP2 = 1.0    # A×2 with this delay
    EXTRA_WAIT         = 2.5
    LOOP_A_DELAY       = 1.1    # A×7
    # Final A before LDR timing in C++ (battle trigger):
    FINAL_A_WAIT       = 10.0   # wait before LDR trigger in C++ → battle load
    BATTLE_LOAD_WAIT   = 8.0    # additional wait for battle screen
    SHINY_RECHECK_WAIT = 3.0

    COLOUR_TOLERANCE   = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("BW - Shiny Starter started.")
        log(f"Starter: {self.STARTER.title()}")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Trigger the rival battle, let the starter appear, "
                "then draw a region over it.")
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
            controller.press_a()
            if not self.wait(self.MENU_A_6_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.MENU_A_7_DELAY, stop_event): break

            # ── Navigate to starter ───────────────────────────────────────
            if self.STARTER == 'snivy':
                controller.press_left()
                if not self.wait(self.NAV_DELAY, stop_event): break
            elif self.STARTER == 'oshawott':
                controller.press_right()
                if not self.wait(self.NAV_DELAY, stop_event): break

            # ── Choose and confirm ────────────────────────────────────────
            controller.press_a()
            if not self.wait(self.CHOOSE_A_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.CONFIRM_DELAY, stop_event): break

            for _ in range(2):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.POST_CONFIRM_LOOP1, stop_event): break
            if stop_event.is_set(): break

            for _ in range(2):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.POST_CONFIRM_LOOP2, stop_event): break
            if stop_event.is_set(): break

            if not self.wait(self.EXTRA_WAIT, stop_event): break

            for _ in range(7):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.LOOP_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            # Final A triggers rival battle
            controller.press_a()
            if not self.wait(self.FINAL_A_WAIT, stop_event): break
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

        log("BW - Shiny Starter stopped.")

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
