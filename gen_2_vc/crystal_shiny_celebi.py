"""
VC Crystal Shiny Celebi
Game: Pokemon Crystal Virtual Console (3DS)

Soft-resets for a shiny Celebi. Detection is timing-based: the shiny
sparkle animation causes the battle text to appear ~700 ms later than
a normal Celebi encounter.

Setup:
  - Save directly in front of the GS Ball shrine in Ilex Forest
  - Calibrate the battle text region on first run
"""

import time
from scripts.base_script import BaseScript


class VCCrystalShinyCelebi(BaseScript):
    NAME = "VC Crystal – Shiny Celebi"
    DESCRIPTION = "Times the Celebi encounter to detect the shiny sparkle delay (Crystal VC)."

    SOFT_RESET_WAIT  = 5.0    # seconds after 'Z' reset before pressing A
    MENU_A_DELAY     = 1.4    # seconds between A presses through opening menus
    NUM_MENU_PRESSES = 4      # A presses to get past title/continue screen
    ENCOUNTER_WAIT   = 8.0    # max seconds to wait for encounter text
    NORMAL_TIME_MS   = 1600   # expected ms from A press to text appearance (non-shiny)
    SHINY_THRESHOLD  = 2200   # if text takes longer than this → shiny
    DARK_THRESHOLD   = 120

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("VC Crystal Shiny Celebi started.")
        log("Calibrate the battle text region — draw over the bottom text box area.")

        region = request_calibration("Draw rectangle over the battle text box")
        if stop_event.is_set():
            return
        x, y, w, h = region
        log(f"Detection region set. Shiny threshold: >{self.SHINY_THRESHOLD} ms")

        sr_count = 0

        while not stop_event.is_set():
            # ── Soft reset ──────────────────────────────────────────────────
            controller.soft_reset_z()
            if not self.wait(self.SOFT_RESET_WAIT, stop_event):
                break

            # ── Navigate through title / continue screens ───────────────────
            for _ in range(self.NUM_MENU_PRESSES):
                if stop_event.is_set():
                    break
                controller.press_a()
                if not self.wait(self.MENU_A_DELAY, stop_event):
                    break

            if stop_event.is_set():
                break

            # ── Press A to interact with the shrine ─────────────────────────
            t_start = time.time()
            controller.press_a()

            # ── Wait for battle text to appear ──────────────────────────────
            elapsed_ms = self._wait_for_text(frame_grabber, stop_event,
                                              x, y, w, h, t_start)
            if stop_event.is_set():
                break

            sr_count += 1

            if elapsed_ms is None:
                log(f"SR #{sr_count}: timed out — retrying")
                continue

            log(f"SR #{sr_count}: text appeared in {elapsed_ms:.0f} ms")

            if elapsed_ms > self.SHINY_THRESHOLD:
                log(f"*** SHINY CELEBI! Timing: {elapsed_ms:.0f} ms "
                    f"(threshold: {self.SHINY_THRESHOLD} ms) ***")
                log(f"Total soft resets: {sr_count}")
                stop_event.wait()
                break

        log("VC Crystal Shiny Celebi stopped.")

    def _wait_for_text(self, frame_grabber, stop_event, x, y, w, h, t_start):
        deadline = time.time() + self.ENCOUNTER_WAIT
        while time.time() < deadline:
            if stop_event.is_set():
                return None
            frame = frame_grabber.get_latest_frame() if frame_grabber else None
            if frame is not None:
                region = frame[y:y + h, x:x + w]
                dark = ((region[:, :, 0] < self.DARK_THRESHOLD) &
                        (region[:, :, 1] < self.DARK_THRESHOLD) &
                        (region[:, :, 2] < self.DARK_THRESHOLD))
                if dark.mean() > 0.15:
                    return (time.time() - t_start) * 1000
            time.sleep(0.02)
        return None
