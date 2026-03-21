"""
VC Crystal Shiny Starter
Game: Pokemon Crystal (3DS Virtual Console)

Soft-resets for a shiny Chikorita, Cyndaquil, or Totodile.
Detection: avg_rgb comparison — a shiny starter's sprite colours
differ noticeably from the normal baseline sample.

Ported from VC_Crystal_Shiny_Starter_2.0.cpp.

Setup:
  - Save inside Prof. Elm's lab, standing in front of the Poke Ball case.
  - On first run the script navigates to the starter selection and asks
    you to draw a region over each starter's sprite in turn.
  - Calibration is saved so subsequent runs skip the setup step.
  - Delete calibration/vc_crystal_shiny_starter.json to recalibrate.

Timing notes:
  - All delays are tunable via the constants at the top of the class.
  - If the script presses buttons at the wrong time, increase the
    relevant delay constant by ~0.5 s and try again.
"""

import json
import os
import sys
import time
from scripts.base_script import BaseScript

NUM_STARTERS = 3


def _cal_path() -> str:
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cal_dir = os.path.join(base, 'calibration')
    os.makedirs(cal_dir, exist_ok=True)
    return os.path.join(cal_dir, 'vc_crystal_shiny_starter.json')


class CrystalShinyStarter(BaseScript):
    NAME = "VC Crystal – Shiny Starter"
    DESCRIPTION = (
        "Soft-resets Pokemon Crystal (3DS VC) for a shiny starter. "
        "Calibrate each starter's sprite region on first run."
    )

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    SOFT_RESET_WAIT    = 5.0   # after Z reset for VC to reload
    MENU_A_DELAY       = 1.4   # between A presses through title/continue screen
    INTERACT_DELAY     = 2.5   # after A to interact with the Pokemon case
    MOVE_DELAY         = 1.6   # after A to move Pokemon image on screen
    ADD_PARTY_DELAY    = 1.3   # between A presses to add starter to party
    RECEIVE_DELAY      = 1.3   # between A presses through receiving-Pokemon text
    PRE_NICKNAME_WAIT  = 2.4   # wait before nickname prompts appear
    NICKNAME_DELAY     = 1.3   # between A presses through nickname prompts
    NO_NICKNAME_WAIT   = 3.0   # after B (decline nickname)
    MR_POKEMON_DELAY   = 1.3   # between A presses through Elm/Mr. Pokemon text
    HEAL_WAIT_1        = 0.5   # brief pause before heal
    HEAL_DELAY         = 1.3   # between A presses through heal text
    HEAL_WAIT_2        = 4.0   # wait for healing machine animation
    HEAL_EXTRA_DELAY   = 2.0   # A press delay after healing wait
    HEAL_TEXT_DELAY    = 1.3   # between A presses through post-heal text
    GOOD_LUCK_WAIT     = 2.8   # wait before final good-luck text
    GOOD_LUCK_DELAY    = 1.5   # after good-luck A press
    CHECK_DELAY        = 1.3   # between button presses in check sequence
    LEFT_MOVE_DELAY    = 1.5   # between starters when pressing Left
    SHINY_RECHECK_WAIT = 3.0   # wait before confirming a suspected shiny

    COLOUR_TOLERANCE   = 15    # ±tolerance per channel for shiny detection

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("VC Crystal Shiny Starter started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Navigate to the starter selection screen, then follow prompts.")
            cal = self._calibrate(
                controller, frame_grabber, stop_event, log, request_calibration
            )
            if stop_event.is_set() or cal is None:
                return
            self._save_calibration(cal)
            log("Calibration saved.")
        else:
            log(f"Calibration loaded from {_cal_path()}")

        regions   = cal['regions']
        baselines = cal['baselines']
        tolerance = cal.get('tolerance', self.COLOUR_TOLERANCE)

        log(f"Monitoring {NUM_STARTERS} starters with tolerance ±{tolerance}.")
        log("Soft reset loop running. Press ■ Stop at any time.")

        sr_count = 0

        # Initial soft reset
        controller.soft_reset_z()
        if not self.wait(self.SOFT_RESET_WAIT, stop_event):
            return

        while not stop_event.is_set():

            # ── Title / continue screen ───────────────────────────────────
            for _ in range(4):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.MENU_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Navigate to receive starter ───────────────────────────────
            controller.press_a()
            if not self.wait(self.INTERACT_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.MOVE_DELAY, stop_event): break

            for _ in range(2):   # add to party
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.ADD_PARTY_DELAY, stop_event): break
            if stop_event.is_set(): break

            for _ in range(2):   # receiving text
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.RECEIVE_DELAY, stop_event): break
            if stop_event.is_set(): break

            if not self.wait(self.PRE_NICKNAME_WAIT, stop_event): break

            for _ in range(2):   # nickname prompts
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.NICKNAME_DELAY, stop_event): break
            if stop_event.is_set(): break

            controller.press_b()   # decline nickname
            if not self.wait(self.NO_NICKNAME_WAIT, stop_event): break

            for _ in range(4):   # Elm / Mr. Pokemon dialogue
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.MR_POKEMON_DELAY, stop_event): break
            if stop_event.is_set(): break

            if not self.wait(self.HEAL_WAIT_1, stop_event): break

            for _ in range(2):   # heal text
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.HEAL_DELAY, stop_event): break
            if stop_event.is_set(): break

            if not self.wait(self.HEAL_WAIT_2, stop_event): break

            controller.press_a()
            if not self.wait(self.HEAL_EXTRA_DELAY, stop_event): break

            for _ in range(3):   # post-heal text
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.HEAL_TEXT_DELAY, stop_event): break
            if stop_event.is_set(): break

            if not self.wait(self.GOOD_LUCK_WAIT, stop_event): break

            controller.press_a()
            if not self.wait(self.GOOD_LUCK_DELAY, stop_event): break

            # ── Trigger check sequence ────────────────────────────────────
            controller.press_x()
            if not self.wait(self.CHECK_DELAY, stop_event): break

            for _ in range(3):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.CHECK_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Shiny check for each starter ──────────────────────────────
            shiny_found = False
            for i in range(NUM_STARTERS):
                if stop_event.is_set(): break

                x, y, w, h = regions[i]
                br, bg, bb = baselines[i]

                frame = frame_grabber.get_latest_frame()
                if frame is None:
                    continue

                r, g, b = self.avg_rgb(frame, x, y, w, h)

                if (abs(r - br) > tolerance or
                        abs(g - bg) > tolerance or
                        abs(b - bb) > tolerance):

                    if not self.wait(self.SHINY_RECHECK_WAIT, stop_event): break
                    frame = frame_grabber.get_latest_frame()
                    if frame is None:
                        continue
                    r2, g2, b2 = self.avg_rgb(frame, x, y, w, h)

                    if (abs(r2 - br) > tolerance or
                            abs(g2 - bg) > tolerance or
                            abs(b2 - bb) > tolerance):
                        names = ['Chikorita', 'Cyndaquil', 'Totodile']
                        log(
                            f"*** SHINY {names[i]}! "
                            f"R:{r2:.0f} G:{g2:.0f} B:{b2:.0f}  "
                            f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f}) ***"
                        )
                        log(f"Soft resets before shiny: {sr_count}")
                        shiny_found = True
                        break

                if i < NUM_STARTERS - 1:
                    controller.press_left()
                    if not self.wait(self.LEFT_MOVE_DELAY, stop_event): break

            if stop_event.is_set(): break

            if shiny_found:
                log("Script paused — catch your shiny! Press ■ Stop when done.")
                stop_event.wait()
                break

            sr_count += 1
            log(f"No shiny. Soft reset #{sr_count}...")
            controller.soft_reset_z()
            if not self.wait(self.SOFT_RESET_WAIT, stop_event): break

        log("VC Crystal Shiny Starter stopped.")

    # ── Calibration ───────────────────────────────────────────────────────────

    def _calibrate(self, controller, frame_grabber, stop_event,
                   log, request_calibration):
        STARTER_NAMES = ['Chikorita', 'Cyndaquil', 'Totodile']
        regions, baselines = [], []

        for i in range(NUM_STARTERS):
            if stop_event.is_set():
                return None

            name = STARTER_NAMES[i]
            log(f"Calibrating {i + 1}/{NUM_STARTERS}: {name}")
            log(f"Make sure {name} is visible on screen, then draw a "
                "region over its sprite.")

            region = request_calibration(
                f"Draw region over {name}'s sprite ({i + 1}/{NUM_STARTERS})"
            )
            if stop_event.is_set():
                return None

            x, y, w, h = region
            time.sleep(0.1)
            frame = frame_grabber.get_latest_frame()
            if frame is None:
                log("No frame available — ensure webcam is connected.")
                return None

            r, g, b = self.avg_rgb(frame, x, y, w, h)
            log(f"{name} baseline — R:{r:.1f}  G:{g:.1f}  B:{b:.1f}")

            regions.append([x, y, w, h])
            baselines.append([r, g, b])

            if i < NUM_STARTERS - 1:
                log("Moving to next starter — pressing Left...")
                controller.press_left()
                self.wait(self.LEFT_MOVE_DELAY, stop_event)

        log("Calibration complete. Default tolerance ±15 applied.")
        log("Edit calibration/vc_crystal_shiny_starter.json to change 'tolerance'.")
        return {'regions': regions, 'baselines': baselines, 'tolerance': 15}

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
