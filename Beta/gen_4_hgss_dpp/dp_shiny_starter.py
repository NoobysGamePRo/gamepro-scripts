"""
Diamond / Pearl Shiny Starter
Game: Pokemon Diamond / Pearl (DS via 3DS)

Uses the GamePRo light sensor (LDR) to detect the shiny animation.
The bottom DS screen brightness changes when the shiny sparkle plays —
the script reads the LDR 10 times and compares the first half against
the second half. A significant step change means a shiny was seen.

Setup:
  - Save in the player's room, in front of the TV / briefcase (before
    Professor Rowan gives the starter)
  - Position the LDR over the bottom DS screen
  - Choose your starter: Turtwig = no move, Chimchar = Right, Piplup = Right x2
"""

from scripts.base_script import BaseScript


class DPShinyStarter(BaseScript):
    NAME = "Diamond / Pearl – Shiny Starter"
    DESCRIPTION = "Uses the LDR light sensor to detect the shiny sparkle (Diamond/Pearl)."

    # ── Starter choice ──────────────────────────────────────────────────────
    # Set STARTER to 'turtwig', 'chimchar', or 'piplup'
    STARTER = 'turtwig'

    # ── Timing (seconds) ────────────────────────────────────────────────────
    SOFT_RESET_WAIT = 12.0   # after 'S' reset — DS game boot is slow
    MENU_DELAY_1    = 5.0    # after first A (title screen)
    MENU_DELAY_2    = 3.0    # after continue press
    MENU_DELAY_3    = 3.0    # after entering overworld
    WALK_DELAY      = 1.0    # hold Up to walk to starter table
    STARTER_DELAY   = 4.0    # wait after selecting starter bag
    CONFIRM_DELAY   = 3.0    # wait for confirmation screen
    BATTLE_DELAY    = 5.0    # wait for battle screen to load

    # ── LDR detection ───────────────────────────────────────────────────────
    LDR_SAMPLES   = 10       # readings per cycle
    STEP_LIMIT    = 30       # minimum brightness step to flag as shiny

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log(f"Diamond/Pearl Shiny Starter started. Starter: {self.STARTER}")
        log("The LDR must be positioned over the bottom DS screen.")

        sr_count = 0

        while not stop_event.is_set():
            # ── Soft reset ──────────────────────────────────────────────────
            controller.soft_reset()   # 'S' command
            sr_count += 1
            log(f"Soft reset #{sr_count} — waiting for game to boot...")
            if not self.wait(self.SOFT_RESET_WAIT, stop_event):
                break

            # ── Navigate title / continue ───────────────────────────────────
            controller.press_a()
            if not self.wait(self.MENU_DELAY_1, stop_event): break

            controller.press_a()
            if not self.wait(self.MENU_DELAY_2, stop_event): break

            controller.press_a()
            if not self.wait(self.MENU_DELAY_3, stop_event): break

            # ── Walk to the starter bag ─────────────────────────────────────
            controller.hold_up()
            if not self.wait(self.WALK_DELAY, stop_event): break
            controller.release_all()
            if not self.wait(0.2, stop_event): break

            # ── Select starter ──────────────────────────────────────────────
            controller.press_a()
            if not self.wait(self.STARTER_DELAY, stop_event): break

            if self.STARTER == 'chimchar':
                controller.press_right()
                if not self.wait(0.3, stop_event): break
            elif self.STARTER == 'piplup':
                controller.press_right()
                if not self.wait(0.3, stop_event): break
                controller.press_right()
                if not self.wait(0.3, stop_event): break

            controller.press_a()
            if not self.wait(self.CONFIRM_DELAY, stop_event): break

            # Confirm selection
            controller.press_a()
            if not self.wait(self.BATTLE_DELAY, stop_event): break

            # ── LDR detection loop ──────────────────────────────────────────
            shiny = self._check_ldr(controller, stop_event, log)
            if stop_event.is_set():
                break

            if shiny:
                log(f"*** SHINY {self.STARTER.title()}! Detected via LDR on reset #{sr_count} ***")
                stop_event.wait()
                break
            else:
                log(f"SR #{sr_count}: not shiny.")

        log("Diamond/Pearl Shiny Starter stopped.")

    def _check_ldr(self, controller, stop_event, log) -> bool:
        """
        Take LDR_SAMPLES readings, compare first half vs second half average.
        Returns True if step change > STEP_LIMIT (shiny sparkle detected).
        """
        readings = []
        for i in range(self.LDR_SAMPLES):
            if stop_event.is_set():
                return False
            val = controller.read_light_value()
            readings.append(val)
            self.wait(0.1, stop_event)

        n = len(readings)
        half = n // 2
        avg_first  = sum(readings[:half]) / half
        avg_second = sum(readings[half:]) / (n - half)
        step = abs(avg_second - avg_first)

        log(f"LDR: first_avg={avg_first:.1f}  second_avg={avg_second:.1f}  step={step:.1f}")
        return step > self.STEP_LIMIT
