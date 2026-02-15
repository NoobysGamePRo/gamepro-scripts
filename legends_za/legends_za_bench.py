"""
Legends ZA - Bench Automation
Game: Pokemon Legends: Z-A (Nintendo Switch)

Automates repeated interactions at a bench in Legends Z-A.
Presses A six times (navigating through prompts/menus), waits a
configurable delay for the animation to complete, then presses Down
to advance to the next item, and repeats.

Setup:
  - Stand at the bench and open the interaction menu
  - Adjust BENCH_WAIT to match how long the bench animation takes
    on your game (increase if the game hasn't finished animating
    before the next A press sequence starts)
"""

import time
from scripts.base_script import BaseScript


class LegendsZABench(BaseScript):
    NAME = "Legends ZA - Bench"
    DESCRIPTION = "Automates repeated bench interactions in Legends Z-A."

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    A_PRESS_DELAY = 1.2    # delay between each A press
    A_EXTRA_DELAY = 0.5    # extra pause mid-sequence
    BENCH_WAIT    = 5.0    # wait after A presses for animation to finish
                           # increase this if the game is still animating
    POST_DOWN     = 1.0    # pause after pressing Down before next loop

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("Legends ZA Bench started.")
        log(f"A press delay: {self.A_PRESS_DELAY}s | Bench wait: {self.BENCH_WAIT}s")
        log("Press Stop to end.")

        loop = 0

        while not stop_event.is_set():
            loop += 1
            log(f"Loop {loop}: pressing A x6...")

            # First set of 3 A presses
            for _ in range(3):
                if stop_event.is_set():
                    break
                controller.press_a()
                if not self.wait(self.A_PRESS_DELAY, stop_event):
                    break
                if not self.wait(self.A_EXTRA_DELAY, stop_event):
                    break

            if stop_event.is_set():
                break

            # Second set of 3 A presses
            for _ in range(3):
                if stop_event.is_set():
                    break
                controller.press_a()
                if not self.wait(self.A_PRESS_DELAY, stop_event):
                    break

            if stop_event.is_set():
                break

            # Wait for bench animation
            log(f"Loop {loop}: waiting {self.BENCH_WAIT}s for animation...")
            if not self.wait(self.BENCH_WAIT, stop_event):
                break

            # Press Down to advance
            controller.press_down()
            log(f"Loop {loop}: pressed Down")
            if not self.wait(self.POST_DOWN, stop_event):
                break

        log("Legends ZA Bench stopped.")
