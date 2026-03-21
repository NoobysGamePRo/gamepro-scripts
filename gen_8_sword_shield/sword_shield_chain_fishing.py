"""
SwSh - Chain Fishing
Game: Pokemon Sword / Shield (Nintendo Switch)

Fishes repeatedly in one spot on Route 2 (or any fishing spot) to
encounter wild Pokemon. Detects a bite via white pixel count (the
exclamation mark that appears), hooks the fish, waits for the
battle to load, then checks for shininess via avg_rgb on a
calibrated region of the wild Pokemon's battle sprite.

Ported from SwordShield_ChainFishing_2.0.cpp.

How it works:
  1. Press A to cast the rod.
  2. Wait up to 15 s for >500 white pixels in the upper frame
     (the "!" exclamation mark from a fish bite).
  3. Press A to hook the fish; wait 5 s for battle to load.
  4. avg_rgb check on calibrated region vs baseline ± tolerance.
  5. If not shiny: Up + A to flee (Run), wait FLEE_WAIT s to return
     to overworld; repeat.
  6. Safety: after MISS_LIMIT casts with no bite, press B×2, Up, A
     to escape a possible stale encounter, then continue.

Setup:
  - Stand at a fishing spot (ripples in the water).
  - Save while facing the water.
  - On first run let an encounter load, then draw a region over the
    wild Pokemon's battle sprite.
  - Delete calibration/sword_shield_chain_fishing.json to recalibrate.
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
    return os.path.join(cal_dir, 'sword_shield_chain_fishing.json')


class SwordShieldChainFishing(BaseScript):
    NAME = "SwSh - Chain Fishing"
    DESCRIPTION = "Fishes repeatedly in one spot to encounter shiny Pokemon (Sword/Shield)."

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    CAST_WAIT          = 1.0    # after casting rod (A)
    BITE_WAIT          = 15.0   # max wait for exclamation / fish bite
    HOOK_WAIT          = 5.0    # after hooking (A) for battle to load
    BATTLE_WAIT        = 8.0    # extra wait after hook for sprite to appear
    SHINY_RECHECK_WAIT = 3.0
    FLEE_UP_DELAY      = 1.5    # after Up to reach Run
    FLEE_A_DELAY       = 1.5    # after A to confirm flee
    FLEE_RETURN_WAIT   = 9.0    # wait after flee for overworld to resume
    MISS_LIMIT         = 2      # casts without bite before escape sequence

    # ── White pixel detection (exclamation mark) ──────────────────────────────
    WHITE_THRESHOLD    = 200    # R, G, B all > this to count as white
    WHITE_COUNT_MIN    = 500    # minimum white pixels to count as bite

    COLOUR_TOLERANCE   = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("SwSh - Chain Fishing started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Cast the rod, let an encounter load, then draw a region "
                "over the wild Pokemon's battle sprite.")
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

        log(f"Pokemon region: x={x} y={y} w={w} h={h} | tolerance ±{tolerance}")
        log("Fishing loop running. Press Stop at any time.")

        encounter_count = 0
        miss_streak     = 0

        while not stop_event.is_set():

            # ── Cast the rod ───────────────────────────────────────────────
            controller.press_a()
            if not self.wait(self.CAST_WAIT, stop_event):
                break

            # ── Wait for fish bite (white pixels = exclamation) ────────────
            bite = self._wait_for_bite(frame_grabber, stop_event, self.BITE_WAIT)

            if stop_event.is_set():
                break

            if not bite:
                miss_streak += 1
                log(f"No bite (miss #{miss_streak}).")
                if miss_streak >= self.MISS_LIMIT:
                    log("Miss limit reached — running escape sequence.")
                    controller.press_b()
                    if not self.wait(1.5, stop_event): break
                    controller.press_b()
                    if not self.wait(1.5, stop_event): break
                    controller.press_up()
                    if not self.wait(1.5, stop_event): break
                    controller.press_a()
                    if not self.wait(self.FLEE_RETURN_WAIT, stop_event): break
                    miss_streak = 0
                continue

            miss_streak = 0

            # ── Hook the fish ──────────────────────────────────────────────
            controller.press_a()
            if not self.wait(self.HOOK_WAIT, stop_event):
                break

            if not self.wait(self.BATTLE_WAIT, stop_event):
                break

            encounter_count += 1
            log(f"Encounter #{encounter_count}: battle loaded")

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
                                f"*** SHINY WILD POKEMON! Encounter #{encounter_count} "
                                f"R:{r2:.0f} G:{g2:.0f} B:{b2:.0f}  "
                                f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f}) ***"
                            )
                            shiny_found = True

            if stop_event.is_set():
                break

            if shiny_found:
                log("Script paused — catch your shiny! Press Stop when done.")
                stop_event.wait()
                break

            # ── Flee ───────────────────────────────────────────────────────
            log(f"Encounter #{encounter_count}: not shiny — fleeing")
            controller.press_up()
            if not self.wait(self.FLEE_UP_DELAY, stop_event): break
            controller.press_a()
            if not self.wait(self.FLEE_A_DELAY, stop_event): break
            if not self.wait(self.FLEE_RETURN_WAIT, stop_event): break

        log("SwSh - Chain Fishing stopped.")

    # ── Wait for fish bite ────────────────────────────────────────────────────

    def _wait_for_bite(self, frame_grabber, stop_event, timeout: float) -> bool:
        """
        Poll the frame for the white exclamation mark above the player.
        Returns True if >WHITE_COUNT_MIN bright pixels found within timeout.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            if stop_event.is_set():
                return False
            frame = frame_grabber.get_latest_frame()
            if frame is not None:
                # Sample the full frame — exclamation can appear anywhere above player
                sample = frame[0:240, 0:640]
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
