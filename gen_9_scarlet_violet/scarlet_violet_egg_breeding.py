"""
Scarlet / Violet Egg Breeding
Game: Pokemon Scarlet / Violet (Nintendo Switch)

Automates egg collection at a picnic. The player sets up a picnic with
two compatible Pokemon in their party. The script repeatedly:
  1. Checks the picnic basket for eggs (yellow pixel detection)
  2. Collects any egg present (A × 3 to confirm)
  3. Waits for another egg to appear if the basket is empty
  4. Stops once TARGET_EGGS have been collected

After collecting eggs, hatch them manually or use a separate hatching script.

Detection:
  - Yellow pixels in the basket area indicate an egg is ready to collect
    (the egg icon / notification is bright yellow against the green grass)

Setup:
  - Start a picnic with two compatible Pokemon (Masuda method works with
    a foreign Ditto)
  - Stand directly in front of the picnic basket
  - Calibrate the basket region (the area where the egg notification appears)
  - Set TARGET_EGGS to how many eggs you want to collect per run
"""

import time
from scripts.base_script import BaseScript


class ScarletVioletEggBreeding(BaseScript):
    NAME = "Scarlet / Violet – Egg Breeding"
    DESCRIPTION = "Automates egg collection at a picnic basket (Scarlet/Violet)."

    # ── Settings ──────────────────────────────────────────────────────────────
    TARGET_EGGS    = 30       # eggs to collect before stopping

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    EGG_CHECK_INTERVAL = 5.0    # how often to poll basket when no egg visible
    COLLECT_DELAY      = 1.3    # between A presses when collecting egg
    OPEN_BASKET_DELAY  = 0.8    # delay after pressing A to open basket
    POST_COLLECT_WAIT  = 2.0    # pause after collecting to let UI settle
    MAX_WAIT_PER_EGG   = 300.0  # max seconds to wait for one egg (5 min)

    # ── Pixel thresholds ─────────────────────────────────────────────────────
    YELLOW_PIXEL_THRESHOLD = 150   # yellow pixels in basket area = egg ready

    # ── Pixel colour limits (yellow egg notification) ─────────────────────────
    YELLOW_R_MIN = 200   # R high
    YELLOW_G_MIN = 200   # G high
    YELLOW_B_MAX = 100   # B low → distinctly yellow

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("Scarlet/Violet Egg Breeding started.")
        log(f"Target: {self.TARGET_EGGS} eggs.")
        log("Calibrate BASKET region — draw a rectangle around the picnic basket / egg notification area.")

        basket_region = request_calibration("Draw rectangle over the picnic basket / egg notification area")
        if stop_event.is_set():
            return

        bx, by, bw, bh = basket_region
        log(f"Basket region: x={bx} y={by} w={bw} h={bh}")
        log("Starting egg collection loop. Stand in front of the basket.")

        eggs_collected = 0

        while not stop_event.is_set():
            if eggs_collected >= self.TARGET_EGGS:
                log(f"Target reached: {eggs_collected} eggs collected.")
                break

            # ── Wait for egg to appear ────────────────────────────────────
            log(f"Eggs so far: {eggs_collected} / {self.TARGET_EGGS} — waiting for egg...")
            egg_ready = self._wait_for_egg(
                frame_grabber, stop_event, bx, by, bw, bh
            )

            if stop_event.is_set():
                break
            if not egg_ready:
                log("No egg appeared within timeout — stopping.")
                break

            # ── Collect the egg ───────────────────────────────────────────
            log(f"Egg detected — collecting (egg #{eggs_collected + 1})...")

            # Open basket / interact
            controller.press_a()
            if not self.wait(self.OPEN_BASKET_DELAY, stop_event):
                break

            # Confirm × 2 (select egg, confirm take)
            controller.press_a()
            if not self.wait(self.COLLECT_DELAY, stop_event):
                break
            controller.press_a()
            if not self.wait(self.COLLECT_DELAY, stop_event):
                break

            eggs_collected += 1
            log(f"Egg #{eggs_collected} collected.")

            if not self.wait(self.POST_COLLECT_WAIT, stop_event):
                break

        log(f"Scarlet/Violet Egg Breeding stopped. Total eggs: {eggs_collected}")

    def _wait_for_egg(self, frame_grabber, stop_event,
                      x, y, w, h) -> bool:
        """
        Polls the basket region until a yellow egg-ready notification appears,
        or until MAX_WAIT_PER_EGG seconds have passed.
        Returns True if an egg was detected, False on timeout.
        """
        deadline = time.time() + self.MAX_WAIT_PER_EGG
        while time.time() < deadline:
            if stop_event.is_set():
                return False
            frame = frame_grabber.get_latest_frame() if frame_grabber else None
            if frame is not None:
                region = frame[y:y + h, x:x + w]
                yellow = (
                    (region[:, :, 0] > self.YELLOW_R_MIN) &
                    (region[:, :, 1] > self.YELLOW_G_MIN) &
                    (region[:, :, 2] < self.YELLOW_B_MAX)
                )
                if yellow.sum() > self.YELLOW_PIXEL_THRESHOLD:
                    return True
            time.sleep(self.EGG_CHECK_INTERVAL)
        return False
