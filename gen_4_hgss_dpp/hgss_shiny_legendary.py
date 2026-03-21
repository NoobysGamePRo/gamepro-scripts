"""
HGSS - Shiny Legendary
Game: Pokemon HeartGold / SoulSilver (DS via 3DS)

Soft-resets for shiny static legendary encounters in HGSS.
Works for: Lugia, Ho-Oh, Raikou, Entei, Suicune, Groudon/Kyogre
(and other one-time legendary battles accessible from the save point).

Ported from HGSS_Shiny_Legendary_2.0.cpp.

How it works:
  The C++ version uses LDR timing — it measures the screen brightness
  transition when the battle intro starts. A shiny legendary takes longer
  to display the battle box text.

  This Python port uses avg_rgb comparison on the legendary's battle sprite.
  Calibrate the sprite region once; on subsequent runs the colour is compared
  against the baseline.

Setup:
  - Save directly in front of / approaching the legendary Pokemon.
  - On first run, start the battle manually, draw a region over the
    legendary's sprite when the battle screen is loaded.
  - Delete calibration/hgss_shiny_legendary.json to recalibrate.
  - Adjust timing constants if the script presses buttons too early/late.

Timing notes from C++:
  - 4 A presses to reach game from title screen:
      A → 4 s, A → 5 s, A → 5 s, A → 8 s
  - Wait for battle to fully load after last A: ~8–20 s (LDR-based in C++)
    Here we use a fixed BATTLE_LOAD_WAIT; tune if needed.
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
    return os.path.join(cal_dir, 'hgss_shiny_legendary.json')


class HGSSShinyLegendary(BaseScript):
    NAME = "HGSS - Shiny Legendary"
    DESCRIPTION = (
        "Soft-resets for shiny legendary encounters in HeartGold/SoulSilver "
        "(Lugia, Ho-Oh, beasts, etc.)."
    )

    # ── Timing (seconds) — derived from HGSS_Shiny_Legendary_2.0.cpp ─────────
    SOFT_RESET_WAIT    = 12.0   # DS reload after L+R+Start+Select
    MENU_A_1_DELAY     = 4.0    # after first A (title)
    MENU_A_2_DELAY     = 5.0    # after second A (continue)
    MENU_A_3_DELAY     = 5.0    # after third A (load world)
    APPROACH_A_DELAY   = 8.0    # after fourth A to approach/interact legend
    BATTLE_LOAD_WAIT   = 12.0   # wait for battle intro + sprite to appear
    SHINY_RECHECK_WAIT = 3.0

    COLOUR_TOLERANCE   = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("HGSS - Shiny Legendary started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Start the legendary battle manually, wait for the battle "
                "screen to load, then draw a region over the legendary's sprite.")
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
        log("Starting soft reset loop. Press Stop at any time.")
        log("Tip: Increase BATTLE_LOAD_WAIT if the sprite isn't loaded when "
            "the check runs.")

        sr_count = 0

        controller.soft_reset()
        if not self.wait(self.SOFT_RESET_WAIT, stop_event):
            return

        while not stop_event.is_set():

            # ── Title / continue / load / approach ────────────────────────
            controller.press_a()
            if not self.wait(self.MENU_A_1_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.MENU_A_2_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.MENU_A_3_DELAY, stop_event): break

            # This final A interacts with / approaches the legendary
            controller.press_a()
            if not self.wait(self.APPROACH_A_DELAY, stop_event): break

            # Wait for battle to fully load
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

        log("HGSS - Shiny Legendary stopped.")

    # ── Calibration ───────────────────────────────────────────────────────────

    def _calibrate(self, controller, frame_grabber, stop_event,
                   log, request_calibration):
        log("With the legendary battle screen loaded, draw a region over "
            "the legendary's sprite.")

        region = request_calibration("Draw region over the legendary's battle sprite")
        if stop_event.is_set():
            return None

        x, y, w, h = region
        time.sleep(0.1)
        frame = frame_grabber.get_latest_frame()
        if frame is None:
            log("No frame available — ensure webcam is connected.")
            return None

        r, g, b = self.avg_rgb(frame, x, y, w, h)
        log(f"Legendary baseline — R:{r:.1f}  G:{g:.1f}  B:{b:.1f}")
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
