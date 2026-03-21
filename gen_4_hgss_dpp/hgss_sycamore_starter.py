"""
HGSS Kanto Starter Gift — Shiny Hunter
Game: Pokemon HeartGold / SoulSilver (DS / 3DS)

Soft-resets for a shiny Kanto starter (Bulbasaur, Charmander, or
Squirtle) received as a gift from Professor Oak in Pallet Town.

Detection: avg_rgb comparison — a shiny starter has noticeably
different colours from the normal sprite.

How it works:
  1. Soft-resets with L+R+Start+Select ('S').
  2. Navigates through title screen and Continue.
  3. Talks to Prof. Oak and navigates to the chosen starter.
  4. Checks the starter sprite region via avg_rgb.
  5. If outside ±COLOUR_TOLERANCE: shiny — script pauses.
  6. Otherwise: repeats.

Setup:
  - Save inside Prof. Oak's lab in Pallet Town, standing directly in
    front of the table where starters are offered.
  - On first run, the script navigates to the starter selection and asks
    you to draw a region over each starter's sprite in turn.
  - Calibration is saved so subsequent runs skip setup.
  - Set STARTER_CHOICE to the starter you want:
      1 = Bulbasaur, 2 = Charmander, 3 = Squirtle
  - Delete calibration/hgss_kanto_starter.json to recalibrate.

Notes:
  - Timing is tuned for HGSS on a 3DS. Increase delays if presses
    happen too early.
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
    return os.path.join(cal_dir, 'hgss_kanto_starter.json')


class HGSSSycamoreStarter(BaseScript):
    NAME = "HGSS – Kanto Starter Gift"
    DESCRIPTION = (
        "Soft-resets for a shiny Kanto starter from Professor Oak "
        "(HeartGold/SoulSilver)."
    )

    # ── Settings ──────────────────────────────────────────────────────────────
    STARTER_CHOICE = 1   # 1 = Bulbasaur, 2 = Charmander, 3 = Squirtle

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    SOFT_RESET_WAIT    = 12.0  # after S reset for game to reload
    MENU_A_DELAY       = 5.0   # between A presses through title/continue
    APPROACH_DELAY     = 3.0   # after interact / approach table
    OFFER_DELAY        = 2.0   # after table dialogue opens
    NAV_RIGHT_DELAY    = 1.5   # between right presses to scroll starters
    SELECT_DELAY       = 1.5   # between A presses to select/confirm
    SPRITE_APPEAR_WAIT = 4.0   # wait after selecting before sprite shows
    LEFT_MOVE_DELAY    = 1.5   # between starters when pressing Left
    SHINY_RECHECK_WAIT = 3.0   # recheck wait before confirming shiny

    COLOUR_TOLERANCE   = 15    # ±tolerance per channel

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("HGSS Kanto Starter Gift started.")

        starter_names = ['Bulbasaur', 'Charmander', 'Squirtle']
        chosen = starter_names[self.STARTER_CHOICE - 1]
        log(f"Hunting shiny {chosen} (slot {self.STARTER_CHOICE}).")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration — starting first-run setup.")
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

        controller.soft_reset()
        if not self.wait(self.SOFT_RESET_WAIT, stop_event):
            return

        while not stop_event.is_set():

            # ── Title / continue screen ───────────────────────────────────────
            for _ in range(3):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.MENU_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Talk to Prof. Oak → starter appears ───────────────────────────
            controller.press_a()   # approach / talk
            if not self.wait(self.APPROACH_DELAY, stop_event): break
            controller.press_a()   # advance to offer
            if not self.wait(self.OFFER_DELAY, stop_event): break
            controller.press_a()   # confirm / starter table opens
            if not self.wait(self.SPRITE_APPEAR_WAIT, stop_event): break

            # ── Check starters ────────────────────────────────────────────────
            shiny_found = False
            for i in range(NUM_STARTERS):
                if stop_event.is_set(): break

                x, y, w, h = regions[i]
                br, bg, bb = baselines[i]

                frame = frame_grabber.get_latest_frame()
                if frame is None:
                    if i < NUM_STARTERS - 1:
                        controller.press_right()
                        self.wait(self.NAV_RIGHT_DELAY, stop_event)
                    continue

                r, g, b = self.avg_rgb(frame, x, y, w, h)

                if (abs(r - br) > tolerance or
                        abs(g - bg) > tolerance or
                        abs(b - bb) > tolerance):
                    if not self.wait(self.SHINY_RECHECK_WAIT, stop_event): break
                    frame = frame_grabber.get_latest_frame()
                    if frame is None:
                        if i < NUM_STARTERS - 1:
                            controller.press_right()
                            self.wait(self.NAV_RIGHT_DELAY, stop_event)
                        continue
                    r2, g2, b2 = self.avg_rgb(frame, x, y, w, h)

                    if (abs(r2 - br) > tolerance or
                            abs(g2 - bg) > tolerance or
                            abs(b2 - bb) > tolerance):
                        log(
                            f"*** SHINY {starter_names[i]}! "
                            f"R:{r2:.0f} G:{g2:.0f} B:{b2:.0f}  "
                            f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f}) ***"
                        )
                        log(f"Soft resets before shiny: {sr_count}")
                        shiny_found = True
                        break

                if i < NUM_STARTERS - 1:
                    controller.press_right()
                    if not self.wait(self.NAV_RIGHT_DELAY, stop_event): break

            if stop_event.is_set(): break

            if shiny_found:
                log("Script paused — catch your shiny! Press ■ Stop when done.")
                stop_event.wait()
                break

            sr_count += 1
            log(f"No shiny. Soft reset #{sr_count}...")
            controller.soft_reset()
            if not self.wait(self.SOFT_RESET_WAIT, stop_event): break

        log("HGSS Kanto Starter Gift stopped.")

    # ── Calibration ───────────────────────────────────────────────────────────

    def _calibrate(self, controller, frame_grabber, stop_event,
                   log, request_calibration):
        STARTER_NAMES = ['Bulbasaur', 'Charmander', 'Squirtle']
        regions, baselines = [], []

        log("Navigate to Prof. Oak's starter table so sprites are visible.")

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
                log("Moving to next starter — pressing Right...")
                controller.press_right()
                self.wait(self.NAV_RIGHT_DELAY, stop_event)

        log("Calibration complete. Default tolerance ±15 applied.")
        log(f"Edit {_cal_path()} to change 'tolerance'.")
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
