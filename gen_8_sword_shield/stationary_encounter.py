"""
Sword / Shield Stationary Encounter Shiny Hunter
Game: Pokemon Sword / Shield (Nintendo Switch)

Soft-resets a stationary overworld Pokemon (e.g. Snorlax, starter gifts,
gift Pokemon). Detects the encounter via white pixel counting in the
dialogue area, then confirms shiny by measuring the delay before the
battle box appears (shiny sparkle adds time).

Detection uses three stages:
  1. White pixels in dialogue area — encounter triggered
  2. Standard deviation change in text box — text appeared/disappeared
  3. Red pixels in battle box area — battle fully loaded

Setup:
  - Save directly in front of the stationary Pokemon
  - Calibrate two regions: the dialogue/text area and the battle box area
"""

import time
from scripts.base_script import BaseScript


class SwordShieldStationaryEncounter(BaseScript):
    NAME = "Sword / Shield – Stationary Encounter"
    DESCRIPTION = "Soft-resets a stationary overworld Pokemon and detects shininess (SwSh)."

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    SOFT_RESET_WAIT = 15.0    # Switch game reload is slow
    MENU_DELAY      = 1.5     # between menu A presses
    NUM_MENU_A      = 3       # A presses to get past title
    WALK_DELAY      = 1.5     # hold Up to approach Pokemon
    ENCOUNTER_WAIT  = 60.0    # max wait for encounter to start
    TEXT_WAIT       = 5.0     # max wait for text to appear/disappear
    BATTLE_WAIT     = 10.0    # max wait for battle box to load
    SHINY_DELAY_MS  = 2000    # time threshold for shiny sparkle

    # ── Pixel thresholds ─────────────────────────────────────────────────────
    WHITE_PIXEL_THRESHOLD = 1000   # white pixels in dialogue to flag encounter
    RED_PIXEL_THRESHOLD   = 200    # red pixels in battle box to confirm loaded

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("SwSh Stationary Encounter started.")
        log("Calibrate DIALOGUE region (text area, lower portion of screen).")
        dialogue_region = request_calibration("Draw rectangle over the dialogue / text area")
        if stop_event.is_set():
            return

        log("Now calibrate BATTLE BOX region (where the Pokemon name appears in battle).")
        battle_region = request_calibration("Draw rectangle over the battle name box")
        if stop_event.is_set():
            return

        dx, dy, dw, dh = dialogue_region
        bx, by, bw, bh = battle_region
        log("Calibration done. Starting soft reset loop.")

        sr_count = 0

        while not stop_event.is_set():
            # ── Soft reset (Home → close → reopen) ────────────────────────
            controller.soft_reset_z()
            sr_count += 1
            log(f"SR #{sr_count} — reloading game...")
            if not self.wait(self.SOFT_RESET_WAIT, stop_event):
                break

            # ── Navigate title / continue ──────────────────────────────────
            for _ in range(self.NUM_MENU_A):
                if stop_event.is_set():
                    break
                controller.press_a()
                self.wait(self.MENU_DELAY, stop_event)

            if stop_event.is_set():
                break

            # ── Walk up to Pokemon ─────────────────────────────────────────
            controller.hold_up()
            self.wait(self.WALK_DELAY, stop_event)
            controller.release_all()
            self.wait(0.3, stop_event)

            # ── Press A to interact ────────────────────────────────────────
            t_start = time.time()
            controller.press_a()

            # ── Wait for encounter (white pixels in dialogue) ──────────────
            encountered = self._wait_for_encounter(frame_grabber, stop_event,
                                                    dx, dy, dw, dh)
            if stop_event.is_set():
                break
            if not encountered:
                log(f"SR #{sr_count}: encounter timed out — retrying")
                continue

            # ── Wait for battle box to load, measure time ─────────────────
            battle_ready = self._wait_for_battle(frame_grabber, stop_event,
                                                   bx, by, bw, bh)
            if stop_event.is_set():
                break

            elapsed_ms = (time.time() - t_start) * 1000
            log(f"SR #{sr_count}: battle loaded in {elapsed_ms:.0f} ms")

            if elapsed_ms > self.SHINY_DELAY_MS or not battle_ready:
                log(f"*** SHINY DETECTED! Time: {elapsed_ms:.0f} ms ***")
                log(f"Total soft resets: {sr_count}")
                stop_event.wait()
                break

        log("SwSh Stationary Encounter stopped.")

    def _wait_for_encounter(self, frame_grabber, stop_event, x, y, w, h) -> bool:
        deadline = time.time() + self.ENCOUNTER_WAIT
        while time.time() < deadline:
            if stop_event.is_set():
                return False
            frame = frame_grabber.get_latest_frame() if frame_grabber else None
            if frame is not None:
                region = frame[y:y + h, x:x + w]
                white = ((region[:, :, 0] > 200) &
                         (region[:, :, 1] > 200) &
                         (region[:, :, 2] > 200))
                if white.sum() > self.WHITE_PIXEL_THRESHOLD:
                    return True
            time.sleep(0.03)
        return False

    def _wait_for_battle(self, frame_grabber, stop_event, x, y, w, h) -> bool:
        deadline = time.time() + self.BATTLE_WAIT
        while time.time() < deadline:
            if stop_event.is_set():
                return False
            frame = frame_grabber.get_latest_frame() if frame_grabber else None
            if frame is not None:
                region = frame[y:y + h, x:x + w]
                red = ((region[:, :, 2] > 150) & (region[:, :, 1] < 120))
                if red.sum() > self.RED_PIXEL_THRESHOLD:
                    return True
            time.sleep(0.03)
        return False
