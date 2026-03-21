"""
SwSh - Shiny Regi
Game: Pokemon Sword / Shield (Nintendo Switch)

Soft-resets for a shiny Regirock, Regice, Registeel, Regieleki, or
Regidrago in their respective dens. Each Regi requires the player to
press A on the dots at the den entrance to unlock the door, then
interact with the central statue to trigger the encounter.

Ported from SwordShield_ShinyRegi_2.0.cpp.

How it works:
  1. Full SwSh soft reset: Home → close game → confirm → select game
     → select user → wait for world to load.
  2. Press A × 3 (2 s each) to solve the door puzzle.
  3. Press A in a loop waiting up to ENCOUNTER_A_WAIT s per press
     for the encounter flash (>WHITE_COUNT_MIN white pixels).
  4. Wait BATTLE_LOAD_WAIT s for the sprite to appear.
  5. avg_rgb check on the calibrated region vs. baseline ± tolerance.
  6. Soft-reset and repeat if not shiny.

Setup:
  - Save directly in front of the Regi statue (door already open,
    or with the correct items used to open it).
  - On first run let the battle load and draw a region over the
    Regi's battle sprite.
  - Delete calibration/sword_shield_shiny_regi.json to recalibrate.
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
    return os.path.join(cal_dir, 'sword_shield_shiny_regi.json')


class SwordShieldShinyRegi(BaseScript):
    NAME = "SwSh - Shiny Regi"
    DESCRIPTION = "Soft-resets for shiny Regirock, Regice, or Registeel (Sword/Shield)."

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    # Full SwSh soft reset sequence (matches SwordShield_ShinyRegi_2.0.cpp)
    SR_HOME_WAIT      = 1.5    # after Home button
    SR_X_WAIT         = 1.5    # after X (close game menu)
    SR_A1_WAIT        = 3.0    # after A (confirm close)
    SR_A2_WAIT        = 2.0    # after A (open game)
    SR_A3_WAIT        = 16.0   # after A (select user) — game loads
    SR_A4_WAIT        = 4.0    # after A (load game)
    SR_A5_WAIT        = 8.0    # after A (world loads)

    DOOR_A_COUNT      = 3      # A presses to solve Regi door puzzle
    DOOR_A_DELAY      = 2.0    # wait between door A presses

    ENCOUNTER_A_WAIT  = 2.0    # wait per A press for encounter flash
    ENCOUNTER_A_MAX   = 6      # safety limit on A presses
    BATTLE_LOAD_WAIT  = 8.0    # wait after encounter flash for sprite
    SHINY_RECHECK_WAIT = 3.0

    # ── White pixel detection (encounter flash) ───────────────────────────────
    WHITE_THRESHOLD   = 200    # R, G, B all > this to count as white
    WHITE_COUNT_MIN   = 1000   # minimum white pixels to detect encounter flash

    COLOUR_TOLERANCE  = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("SwSh - Shiny Regi started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Let the Regi battle load, then draw a region over its sprite.")
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

        log(f"Regi region: x={x} y={y} w={w} h={h} | tolerance ±{tolerance}")
        log("Soft reset loop running. Press Stop at any time.")

        sr_count = 0

        # Perform the initial soft reset before entering the loop
        self._soft_reset(controller, stop_event)
        if stop_event.is_set():
            return

        while not stop_event.is_set():

            # ── Press A × 3 to activate Regi door puzzle ──────────────────
            for _ in range(self.DOOR_A_COUNT):
                if stop_event.is_set():
                    break
                controller.press_a()
                if not self.wait(self.DOOR_A_DELAY, stop_event):
                    break
            if stop_event.is_set():
                break

            # ── Press A to trigger encounter, watch for flash ──────────────
            encounter_detected = False
            for safety in range(self.ENCOUNTER_A_MAX):
                if stop_event.is_set():
                    break
                controller.press_a()
                encounter_detected = self._wait_for_encounter_flash(
                    frame_grabber, stop_event, self.ENCOUNTER_A_WAIT
                )
                if encounter_detected:
                    break

            if stop_event.is_set():
                break

            if not encounter_detected:
                log("Encounter flash not detected — soft resetting.")
                self._soft_reset(controller, stop_event)
                if stop_event.is_set():
                    break
                sr_count += 1
                log(f"Soft reset #{sr_count}")
                continue

            # ── Wait for battle sprite to load ─────────────────────────────
            if not self.wait(self.BATTLE_LOAD_WAIT, stop_event):
                break

            # ── Shiny check ────────────────────────────────────────────────
            frame = frame_grabber.get_latest_frame()
            shiny_found = False

            if frame is not None:
                r, g, b = self.avg_rgb(frame, x, y, w, h)
                if (abs(r - br) > tolerance or
                        abs(g - bg) > tolerance or
                        abs(b - bb) > tolerance):
                    if not self.wait(self.SHINY_RECHECK_WAIT, stop_event):
                        break
                    frame = frame_grabber.get_latest_frame()
                    if frame is not None:
                        r2, g2, b2 = self.avg_rgb(frame, x, y, w, h)
                        if (abs(r2 - br) > tolerance or
                                abs(g2 - bg) > tolerance or
                                abs(b2 - bb) > tolerance):
                            log(
                                f"*** SHINY REGI! "
                                f"R:{r2:.0f} G:{g2:.0f} B:{b2:.0f}  "
                                f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f}) ***"
                            )
                            log(f"Soft resets before shiny: {sr_count}")
                            shiny_found = True

            if stop_event.is_set():
                break

            if shiny_found:
                log("Script paused — catch your shiny! Press Stop when done.")
                stop_event.wait()
                break

            sr_count += 1
            log(f"No shiny. Soft reset #{sr_count}...")
            self._soft_reset(controller, stop_event)
            if stop_event.is_set():
                break

        log("SwSh - Shiny Regi stopped.")

    # ── Full SwSh soft reset sequence ─────────────────────────────────────────

    def _soft_reset(self, controller, stop_event):
        """
        Full Nintendo Switch soft reset:
        Home(1.5s) → X close(1.5s) → A confirm(3s) → A open(2s)
        → A user select(16s) → A load(4s) → A world(12s)
        """
        controller.soft_reset()             # sends 'S' = Home
        if not self.wait(self.SR_HOME_WAIT, stop_event): return
        controller.press_x()
        if not self.wait(self.SR_X_WAIT, stop_event): return
        controller.press_a()
        if not self.wait(self.SR_A1_WAIT, stop_event): return
        controller.press_a()
        if not self.wait(self.SR_A2_WAIT, stop_event): return
        controller.press_a()
        if not self.wait(self.SR_A3_WAIT, stop_event): return
        controller.press_a()
        if not self.wait(self.SR_A4_WAIT, stop_event): return
        controller.press_a()
        if not self.wait(self.SR_A5_WAIT, stop_event): return

    # ── Encounter flash detection ──────────────────────────────────────────────

    def _wait_for_encounter_flash(self, frame_grabber, stop_event,
                                   timeout: float) -> bool:
        """
        Wait up to `timeout` seconds for the white encounter flash
        (>WHITE_COUNT_MIN pixels above WHITE_THRESHOLD brightness).
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            if stop_event.is_set():
                return False
            frame = frame_grabber.get_latest_frame()
            if frame is not None:
                # Check the right-centre region where the white flash appears
                sample = frame[200:280, 370:470]
                white = (
                    (sample[:, :, 0] > self.WHITE_THRESHOLD) &
                    (sample[:, :, 1] > self.WHITE_THRESHOLD) &
                    (sample[:, :, 2] > self.WHITE_THRESHOLD)
                )
                if int(white.sum()) > self.WHITE_COUNT_MIN:
                    return True
            time.sleep(0.03)
        return False

    # ── Calibration helpers ───────────────────────────────────────────────────

    def _calibrate(self, controller, frame_grabber, stop_event,
                   log, request_calibration):
        log("Draw a region over the Regi's battle sprite.")
        region = request_calibration("Draw region over Regi sprite")
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
