"""
Chain Fishing Shiny Hunter
Game: Pokemon X/Y and ORAS

Casts the fishing rod repeatedly without moving to build a chain.
Detects the fishing exclamation mark via pixel colour (white/red pixels
above the trainer), then uses the LDR sensor to detect the shiny sparkle
during the battle.

Setup:
  - Stand on a fishing tile facing water, rod in bag
  - Position LDR over bottom 3DS screen
  - Calibrate the exclamation mark detection region
"""

import time
from scripts.base_script import BaseScript


class ChainFishing(BaseScript):
    NAME = "Gen 6 – Chain Fishing"
    DESCRIPTION = "Builds a fishing chain to hunt shiny encounters (X/Y / ORAS)."

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    CAST_WAIT       = 1.5    # after pressing A to cast
    HOOK_WINDOW     = 15.0   # max wait for exclamation mark
    AFTER_HOOK      = 1.0    # delay after hooking (A press)
    BATTLE_WAIT     = 2.0    # wait for battle to load after hooking
    LDR_MONITOR    = 25.0    # time window to monitor LDR for shiny sparkle
    POST_BATTLE     = 6.0    # delay after fleeing before next cast
    MOVE_L          = 1.5    # briefly press left to "reset" rod position
    MOVE_R          = 1.5    # briefly press right to return

    # ── Detection thresholds ─────────────────────────────────────────────────
    WHITE_MIN       = 200    # R,G,B above this = white pixel (exclamation mark)
    RED_MIN_R       = 180    # R above for red dot
    RED_MAX_G       = 100    # G below for red dot
    LDR_STEP_LIMIT  = 40     # brightness step to flag as shiny

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("Chain Fishing started.")
        log("Calibrate the exclamation mark area — draw a rectangle above your trainer.")

        region = request_calibration("Draw rectangle above trainer's head (exclamation mark)")
        if stop_event.is_set():
            return
        x, y, w, h = region
        log(f"Detection region set: x={x} y={y} w={w} h={h}")
        log("LDR must be over the bottom 3DS screen.")

        chain = 0
        sr_count = 0

        while not stop_event.is_set():
            # ── Cast the fishing rod ────────────────────────────────────────
            controller.press_a()
            if not self.wait(self.CAST_WAIT, stop_event):
                break

            # ── Wait for exclamation mark ───────────────────────────────────
            hooked = self._wait_for_exclamation(frame_grabber, stop_event,
                                                 x, y, w, h)
            if stop_event.is_set():
                break

            if not hooked:
                # Missed the window — move left/right to reset rod, try again
                log(f"Chain {chain}: missed hook — resetting rod")
                controller.press_left()
                self.wait(0.4, stop_event)
                controller.press_right()
                self.wait(0.4, stop_event)
                continue

            # ── Hook the Pokemon ────────────────────────────────────────────
            controller.press_a()
            if not self.wait(self.AFTER_HOOK, stop_event):
                break
            if not self.wait(self.BATTLE_WAIT, stop_event):
                break

            # ── Monitor LDR for shiny sparkle ───────────────────────────────
            shiny = self._monitor_ldr_for_shiny(controller, stop_event, log)
            if stop_event.is_set():
                break

            chain += 1
            sr_count += 1

            if shiny:
                log(f"*** SHINY on chain {chain}! Catch it! ***")
                stop_event.wait()
                break

            log(f"Chain {chain}: not shiny — fleeing")

            # ── Flee from battle ────────────────────────────────────────────
            controller.press_right()   # select "Run"
            self.wait(0.4, stop_event)
            controller.press_a()
            if not self.wait(self.POST_BATTLE, stop_event):
                break

        log("Chain Fishing stopped.")

    def _wait_for_exclamation(self, frame_grabber, stop_event, x, y, w, h) -> bool:
        """Returns True when white/red exclamation mark pixels appear."""
        deadline = time.time() + self.HOOK_WINDOW
        while time.time() < deadline:
            if stop_event.is_set():
                return False
            frame = frame_grabber.get_latest_frame() if frame_grabber else None
            if frame is not None:
                region = frame[y:y + h, x:x + w]
                white = ((region[:, :, 0] > self.WHITE_MIN) &
                         (region[:, :, 1] > self.WHITE_MIN) &
                         (region[:, :, 2] > self.WHITE_MIN))
                red   = ((region[:, :, 2] > self.RED_MIN_R) &
                         (region[:, :, 1] < self.RED_MAX_G))
                if white.sum() > 20 or red.sum() > 10:
                    return True
            time.sleep(0.02)
        return False

    def _monitor_ldr_for_shiny(self, controller, stop_event, log) -> bool:
        """Take 10 LDR readings split into two halves; return True on step change."""
        readings = []
        for _ in range(10):
            if stop_event.is_set():
                return False
            readings.append(controller.read_light_value())
            self.wait(self.LDR_MONITOR / 10, stop_event)

        avg_first  = sum(readings[:5]) / 5
        avg_second = sum(readings[5:]) / 5
        step = abs(avg_second - avg_first)
        log(f"LDR step: {step:.1f} (limit {self.LDR_STEP_LIMIT})")
        return step > self.LDR_STEP_LIMIT
