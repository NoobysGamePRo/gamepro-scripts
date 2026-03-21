"""
Sun / Moon - Honey Encounter
Game: Pokemon Sun / Moon (3DS)

Uses the X-menu Bag to apply a Honey/Lure (or Honey-item equivalent)
then encounters the triggered wild Pokemon and checks for shininess.
After 50 encounters it soft-resets to refresh the spawn and reloads.

Ported from SuMo_Honey_Encounter_2.0.cpp.

How it works:
  The C++ version uses LDR timing to detect the battle blackout and
  measures the encounter animation duration (shinies take longer).
  The Python port replaces LDR timing with avg_rgb comparison on a
  calibrated wild-Pokemon sprite region.

  Every 50 encounters the script soft-resets to restore items/PP.

  Loop:
    1. X to open menu → (every 50 encounters: Down to items) →
       A (2 s) → (every 50 encounters: Right to Honey slot) →
       A 1 s → A 10 s (use Honey, wait for encounter).
    2. Wait for blackout; avg_rgb shiny check.
    3. If not shiny: Down + A to flee → 8 s wait.
    4. After 50 encounters: soft-reset → A 3 s → A 4 s.

Setup:
  - Save in a location where Honey triggers wild encounters.
  - Have Honey (or Sweet Scent user) accessible in the bag.
  - On first run let a wild Pokemon encounter load, then draw a
    region over its sprite.
  - Delete calibration/sumo_honey_encounter.json to recalibrate.
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
    return os.path.join(cal_dir, 'sumo_honey_encounter.json')


class SUMOHoneyEncounter(BaseScript):
    NAME = "Sun / Moon - Honey Encounter"
    DESCRIPTION = "Uses Honey/Lure to trigger encounters for shiny hunting (Sun/Moon)."

    # ── Timing (seconds) — from SuMo_Honey_Encounter_2.0.cpp ────────────────
    MENU_X_DELAY      = 1.0    # after X to open menu
    ITEM_DOWN_DELAY   = 2.0    # after Down to items category (every 50)
    MENU_A_DELAY      = 2.0    # after A to open bag category
    ITEM_RIGHT_DELAY  = 2.0    # after Right to honey slot (every 50)
    SELECT_A_DELAY    = 1.0    # after A to select item
    USE_A_DELAY       = 10.0   # after A to use item (wait for encounter)
    BLACKOUT_WAIT     = 20.0   # max seconds to wait for blackout
    BATTLE_WAIT       = 5.0    # wait after blackout for sprite to load
    FLEE_DOWN_DELAY   = 1.5    # after Down to reach Run option
    FLEE_A_DELAY      = 8.0    # after A to confirm flee + return
    SOFT_RESET_WAIT   = 12.0   # 3DS reload
    SR_A_1_DELAY      = 3.0    # after A to load title
    SR_A_2_DELAY      = 4.0    # after A to continue game
    RESET_INTERVAL    = 50     # soft-reset every N encounters
    SHINY_RECHECK     = 3.0

    # ── Blackout detection ────────────────────────────────────────────────────
    DARK_THRESHOLD    = 40
    DARK_FRACTION     = 0.65

    COLOUR_TOLERANCE  = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("Sun / Moon - Honey Encounter started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Trigger an encounter, let it load, then draw a region over the "
                "wild Pokemon's sprite.")
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

        log(f"Wild Pokemon region: x={x} y={y} w={w} h={h} | tolerance ±{tolerance}")
        log("Encounter loop running. Press Stop at any time.")

        encounter_count = 0

        while not stop_event.is_set():

            # ── Open menu and use Honey ────────────────────────────────────
            controller.press_x()
            if not self.wait(self.MENU_X_DELAY, stop_event): break

            # Every 50 encounters navigate to item category
            if encounter_count % self.RESET_INTERVAL == 0 and encounter_count > 0:
                controller.press_down()
                if not self.wait(self.ITEM_DOWN_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.MENU_A_DELAY, stop_event): break

            if encounter_count % self.RESET_INTERVAL == 0 and encounter_count > 0:
                controller.press_right()
                if not self.wait(self.ITEM_RIGHT_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.SELECT_A_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.USE_A_DELAY, stop_event): break

            # ── Wait for blackout ─────────────────────────────────────────
            blackout = self._wait_for_blackout(
                frame_grabber, stop_event, self.BLACKOUT_WAIT
            )
            if stop_event.is_set(): break

            if not blackout:
                log("Blackout not detected — retrying.")
                continue

            encounter_count += 1
            log(f"Encounter #{encounter_count}")

            if not self.wait(self.BATTLE_WAIT, stop_event): break

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
                                f"*** SHINY POKEMON! Encounter #{encounter_count} "
                                f"R:{r2:.0f} G:{g2:.0f} B:{b2:.0f}  "
                                f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f}) ***"
                            )
                            shiny_found = True

            if stop_event.is_set(): break

            if shiny_found:
                log("Script paused — catch your shiny! Press Stop when done.")
                stop_event.wait()
                break

            # ── Flee or soft-reset every 50 encounters ────────────────────
            if encounter_count % self.RESET_INTERVAL == 0:
                log(f"Encounter #{encounter_count}: soft-resetting to refresh...")
                controller.soft_reset()
                if not self.wait(self.SOFT_RESET_WAIT, stop_event): break
                controller.press_a()
                if not self.wait(self.SR_A_1_DELAY, stop_event): break
                controller.press_a()
                if not self.wait(self.SR_A_2_DELAY, stop_event): break
            else:
                log(f"Encounter #{encounter_count}: not shiny — fleeing")
                controller.press_down()
                if not self.wait(self.FLEE_DOWN_DELAY, stop_event): break
                controller.press_a()
                if not self.wait(self.FLEE_A_DELAY, stop_event): break

        log("Sun / Moon - Honey Encounter stopped.")

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
        log("Draw a region over the wild Pokemon's battle sprite.")
        region = request_calibration("Draw region over wild Pokemon sprite")
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
