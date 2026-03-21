"""
ORAS - Shiny Legendary
Game: Pokemon Omega Ruby / Alpha Sapphire (3DS)

Soft-resets for shiny legendary encounters accessed via a dimensional
portal (e.g. Kyogre, Groudon, Rayquaza, Deoxys, and other event/story
legendaries that require walking through a portal or interacting with a
specific spot).

Ported from ORAS_Legendary_5.0.cpp.

How it works:
  After soft reset, navigates title/continue menus, optionally moves in
  one direction to reach the portal/legendary, then presses A repeatedly
  until the battle blackout is detected via avg_rgb. Checks for a shiny
  via avg_rgb comparison on the legendary's battle sprite.

Setup:
  - Save in front of the portal/legendary, OR save one directional move
    away. Set PORTAL_DIRECTION to the direction you need to walk ('up',
    'down', 'left', 'right'), or leave as '' if you are already in front.
  - On first run, let the battle load and draw a region over the
    legendary's sprite.
  - Delete calibration/oras_shiny_legendary.json to recalibrate.
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
    return os.path.join(cal_dir, 'oras_shiny_legendary.json')


class ORASShinyLegendary(BaseScript):
    NAME = "ORAS - Shiny Legendary"
    DESCRIPTION = "Soft-resets for shiny legendary encounters (ORAS)."

    # ── Direction to walk after menus ─────────────────────────────────────────
    # 'up', 'down', 'left', 'right', or '' if already in front of the portal
    PORTAL_DIRECTION = ''

    # ── Timing (seconds) — from ORAS_Legendary_5.0.cpp ──────────────────────
    SOFT_RESET_WAIT    = 12.0   # 3DS reload
    MENU_A_1_DELAY     = 5.0    # title
    MENU_A_2_DELAY     = 5.0    # continue
    MENU_A_3_DELAY     = 4.0    # world load
    MOVE_DELAY         = 2.0    # after directional move to portal
    # Loop: press A until battle blackout detected (up to BATTLE_A_MAX presses)
    BATTLE_A_DELAY     = 1.2    # delay between A presses during battle lead-up
    BATTLE_A_MAX       = 20     # safety limit (matches safetyCount=20 in C++)
    BATTLE_LOAD_WAIT   = 10.0   # wait after blackout for battle screen
    SHINY_RECHECK_WAIT = 3.0

    # ── Blackout detection ────────────────────────────────────────────────────
    DARK_THRESHOLD  = 40
    DARK_FRACTION   = 0.65

    COLOUR_TOLERANCE = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("ORAS - Shiny Legendary started.")
        if self.PORTAL_DIRECTION:
            log(f"Portal direction: {self.PORTAL_DIRECTION}")

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

            # ── Navigate title/continue menus ─────────────────────────────
            controller.press_a()
            if not self.wait(self.MENU_A_1_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.MENU_A_2_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.MENU_A_3_DELAY, stop_event): break

            # ── Optional directional move to portal ───────────────────────
            if self.PORTAL_DIRECTION:
                dir_map = {
                    'up':    controller.press_up,
                    'down':  controller.press_down,
                    'left':  controller.press_left,
                    'right': controller.press_right,
                }
                move_fn = dir_map.get(self.PORTAL_DIRECTION)
                if move_fn:
                    move_fn()
                    if not self.wait(self.MOVE_DELAY, stop_event): break

            # ── Press A until blackout detected ───────────────────────────
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
                log("Battle blackout not detected — retrying.")
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

        log("ORAS - Shiny Legendary stopped.")

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
