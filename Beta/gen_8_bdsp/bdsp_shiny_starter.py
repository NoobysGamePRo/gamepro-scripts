"""
BDSP Shiny Starter
Game: Pokemon Brilliant Diamond / Shining Pearl (Nintendo Switch)

Soft-resets for a shiny Turtwig, Chimchar, or Piplup at Lake Verity.
Uses two detection stages:
  1. Black pixels (battle blackout) to confirm the wild Starly battle started
  2. White pixels in the dialogue area to time the starter's battle entry text

A shiny starter causes a significantly longer delay before the battle box
text appears (the shiny sparkle animation plays first).

Setup:
  - Save at the entrance to Lake Verity (just before the cutscene)
  - Calibrate the dialogue/text region (lower portion of screen)
  - Set STARTER to 'turtwig', 'chimchar', or 'piplup'
"""

import time
from scripts.base_script import BaseScript


class BDSPShinyStarter(BaseScript):
    NAME = "BDSP – Shiny Starter"
    DESCRIPTION = "Soft-resets for a shiny starter at Lake Verity (Brilliant Diamond/Pearl)."

    # ── Starter choice ────────────────────────────────────────────────────────
    # 'turtwig' = no navigation, 'chimchar' = Right x1, 'piplup' = Right x2
    STARTER = 'turtwig'

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    SOFT_RESET_WAIT   = 25.0   # Switch game reload (BDSP is slower than SwSh)
    MENU_DELAY        = 2.0    # between title A presses
    NUM_MENU_A        = 3      # A presses to reach overworld
    OVERWORLD_WAIT    = 3.0    # extra wait after last menu A (world loads)
    WALK_DELAY        = 2.0    # hold Up into the lake cutscene area
    CUTSCENE_WAIT     = 10.0   # cutscene / Starly battle
    STARLY_WAIT       = 5.0    # wait after Starly battle ends
    BRIEFCASE_WAIT    = 3.0    # wait after opening the briefcase
    CONFIRM_DELAY     = 2.0    # wait between confirmation presses
    BATTLE_LOAD_WAIT  = 8.0    # wait for starter battle screen to load

    # ── Pixel thresholds ─────────────────────────────────────────────────────
    BLACK_PIXEL_THRESHOLD = 0.70   # fraction of dark pixels = blackout
    WHITE_PIXEL_THRESHOLD = 500    # white pixels in dialogue = text appeared
    SHINY_DELAY_MS        = 3000   # threshold — shiny sparkle adds ~2-3 s

    # ── Pixel colour limits ───────────────────────────────────────────────────
    BLACK_MAX  = 50    # R, G, B all below this for dark pixel
    WHITE_MIN  = 200   # R, G, B all above this for white pixel

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("BDSP Shiny Starter started.")
        log(f"Starter: {self.STARTER.title()}")
        log("Calibrate DIALOGUE region (lower text area of screen).")

        dialogue_region = request_calibration("Draw rectangle over the dialogue / text area")
        if stop_event.is_set():
            return

        dx, dy, dw, dh = dialogue_region
        log(f"Dialogue region: x={dx} y={dy} w={dw} h={dh}")
        log("Starting soft reset loop...")

        sr_count = 0

        while not stop_event.is_set():
            # ── Soft reset ────────────────────────────────────────────────
            controller.soft_reset_z()
            sr_count += 1
            log(f"SR #{sr_count} — reloading game...")
            if not self.wait(self.SOFT_RESET_WAIT, stop_event):
                break

            # ── Navigate past title / continue screen ─────────────────────
            for _ in range(self.NUM_MENU_A):
                if stop_event.is_set():
                    break
                controller.press_a()
                self.wait(self.MENU_DELAY, stop_event)
            if stop_event.is_set():
                break

            if not self.wait(self.OVERWORLD_WAIT, stop_event):
                break

            # ── Walk north into Lake Verity ───────────────────────────────
            controller.hold_up()
            if not self.wait(self.WALK_DELAY, stop_event):
                controller.release_all()
                break
            controller.release_all()

            # ── Wait for cutscene / Starly encounter blackout ─────────────
            log(f"SR #{sr_count}: waiting for Starly battle blackout...")
            starly_started = self._wait_for_blackout(frame_grabber, stop_event)
            if stop_event.is_set():
                break
            if not starly_started:
                log(f"SR #{sr_count}: blackout timed out — retrying")
                continue

            log(f"SR #{sr_count}: Starly battle detected")
            if not self.wait(self.CUTSCENE_WAIT, stop_event):
                break
            if not self.wait(self.STARLY_WAIT, stop_event):
                break

            # ── Open briefcase and select starter ────────────────────────
            controller.press_a()          # open briefcase / bag
            if not self.wait(self.BRIEFCASE_WAIT, stop_event):
                break

            if self.STARTER == 'chimchar':
                controller.press_right()
                if not self.wait(0.3, stop_event):
                    break
            elif self.STARTER == 'piplup':
                controller.press_right()
                if not self.wait(0.3, stop_event):
                    break
                controller.press_right()
                if not self.wait(0.3, stop_event):
                    break

            controller.press_a()          # choose starter
            if not self.wait(self.CONFIRM_DELAY, stop_event):
                break
            controller.press_a()          # confirm
            if not self.wait(self.CONFIRM_DELAY, stop_event):
                break

            # ── Wait for battle load, then time shiny text delay ──────────
            t_start = time.time()
            log(f"SR #{sr_count}: waiting for starter battle text...")

            text_appeared = self._wait_for_white_pixels(
                frame_grabber, stop_event, dx, dy, dw, dh,
                timeout=self.BATTLE_LOAD_WAIT
            )
            if stop_event.is_set():
                break

            elapsed_ms = (time.time() - t_start) * 1000
            log(f"SR #{sr_count}: text appeared in {elapsed_ms:.0f} ms")

            if elapsed_ms > self.SHINY_DELAY_MS or not text_appeared:
                log(f"*** SHINY {self.STARTER.title()} DETECTED! "
                    f"Time: {elapsed_ms:.0f} ms | SR #{sr_count} ***")
                log(f"Total soft resets: {sr_count}")
                stop_event.wait()
                break
            else:
                log(f"SR #{sr_count}: not shiny — resetting")

        log("BDSP Shiny Starter stopped.")

    def _wait_for_blackout(self, frame_grabber, stop_event) -> bool:
        """Returns True when the majority of the screen is very dark (battle fade)."""
        deadline = time.time() + self.CUTSCENE_WAIT + 5.0
        while time.time() < deadline:
            if stop_event.is_set():
                return False
            frame = frame_grabber.get_latest_frame() if frame_grabber else None
            if frame is not None:
                sample = frame[100:400, 100:540]
                dark = (
                    (sample[:, :, 0] < self.BLACK_MAX) &
                    (sample[:, :, 1] < self.BLACK_MAX) &
                    (sample[:, :, 2] < self.BLACK_MAX)
                )
                if dark.mean() > self.BLACK_PIXEL_THRESHOLD:
                    return True
            time.sleep(0.03)
        return False

    def _wait_for_white_pixels(self, frame_grabber, stop_event,
                                x, y, w, h, timeout=8.0) -> bool:
        """Returns True when enough white pixels appear in the dialogue region."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if stop_event.is_set():
                return False
            frame = frame_grabber.get_latest_frame() if frame_grabber else None
            if frame is not None:
                region = frame[y:y + h, x:x + w]
                white = (
                    (region[:, :, 0] > self.WHITE_MIN) &
                    (region[:, :, 1] > self.WHITE_MIN) &
                    (region[:, :, 2] > self.WHITE_MIN)
                )
                if white.sum() > self.WHITE_PIXEL_THRESHOLD:
                    return True
            time.sleep(0.03)
        return False
