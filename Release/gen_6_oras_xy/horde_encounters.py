"""
XY - Horde Encounter
Game: Pokemon X / Y (3DS) — also works in ORAS

Uses Sweet Scent to trigger horde encounters for shiny hunting. A Pokemon
in the party must know Sweet Scent.

How it works:
  1. Asks you to click the 4 corners of the 3DS screen for a perspective-
     corrected video view.
  2. Opens the Pokemon menu (X → A → A → Down → A → A) to use Sweet Scent.
  3. Waits for the LDR to detect TWO dark phases:
       Phase 1 (brief): Sweet Scent animation blackout — skipped.
       Phase 2 (long):  Battle load blackout — timed from dark until bright.
  4. First encounter: records the dark-duration as the baseline, then gives
     you a 10-second window to press Stop if it might already be a shiny.
     Threshold is set to baseline + SHINY_EXTRA_SECONDS.
  5. Subsequent encounters: if dark-duration >= threshold → shiny detected,
     script pauses so you can catch it.
  6. If not shiny: flees with Down → Right → A and repeats.

Setup:
  - Save in a location with hordes of the Pokemon you want to hunt.
  - Ensure the first Pokemon in your party knows Sweet Scent.
  - Position the LDR so it faces the 3DS bottom screen.
  - Tune LDR_DARK_THRESHOLD using the Live button on the Light Sensor dial
    in the app. It should be above the value when the screen is dark and
    below the value when the screen is bright.
"""

import time
from scripts.base_script import BaseScript


class HordeEncounters(BaseScript):
    NAME = "XY - Horde Encounter"
    DESCRIPTION = "Uses Sweet Scent to trigger horde encounters for shiny hunting (X/Y)."

    # ── Menu / Sweet Scent timing (seconds) ──────────────────────────────────
    MENU_X_DELAY        = 1.75  # after X to open menu
    MENU_A_DELAY        = 2.43  # after A to open Pokemon list
    SELECT_MON_DELAY    = 2.90  # after A to select first Pokemon
    FIELD_MOVE_DELAY    = 1.20  # after Down to navigate to field moves
    SWEET_SCENT_A_DELAY = 0.99  # after A to select Sweet Scent
    # Final A (confirm Sweet Scent) has no delay — LDR detection follows

    # ── Flee timing (seconds) ─────────────────────────────────────────────────
    FLEE_PRE_DELAY      = 1.0   # pause after LDR detection, before fleeing
    FLEE_DOWN_DELAY     = 1.3   # after Down in battle menu
    FLEE_RIGHT_DELAY    = 0.8   # after Right to highlight Run
    FLEE_A_DELAY        = 2.0   # after A to confirm Run
    FLEE_RETURN_DELAY   = 7.5   # after Run confirmed — wait for overworld to reload

    # ── LDR (light sensor) thresholds ────────────────────────────────────────
    LDR_DARK_THRESHOLD  = 200   # LDR below this = screen dark
    LDR_STEP_CHANGE     = 40    # minimum rise from floor = battle brightening
    LDR_POLL_INTERVAL   = 0.1   # seconds between LDR reads
    DARK_WAIT_TIMEOUT   = 25.0  # max seconds to wait for screen to go dark
    BRIGHT_WAIT_TIMEOUT = 40.0  # max seconds to wait for screen to go bright

    # ── Shiny detection ───────────────────────────────────────────────────────
    SHINY_EXTRA_SECONDS    = 1.2   # threshold = baseline + this
    BASELINE_STOP_WINDOW   = 10.0  # seconds to press Stop after first baseline

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("XY - Horde Encounter started.")

        # ── Screen calibration (4-corner perspective warp) ────────────────────
        log("Click the four corners of the 3DS screen: "
            "Top-Left → Top-Right → Bottom-Right → Bottom-Left.")
        warp_info = request_calibration(
            "Click the 4 corners of the 3DS screen", mode='corners'
        )
        if stop_event.is_set():
            log("XY Horde Encounter stopped.")
            return
        if warp_info is None:
            log("Screen calibration cancelled — stopping.")
            return
        log(f"Screen calibrated ({warp_info['out_w']}×{warp_info['out_h']} px).")

        log(
            f"LDR dark threshold: {self.LDR_DARK_THRESHOLD}  "
            f"step change: {self.LDR_STEP_CHANGE}  "
            f"shiny margin: +{self.SHINY_EXTRA_SECONDS}s"
        )
        log("Horde encounter loop running. Press Stop at any time.")

        threshold = None
        encounter_count = 0

        while not stop_event.is_set():

            # ── Use Sweet Scent: X→A→A→Down→A→A ─────────────────────────────
            controller.press_x()
            if not self.wait(self.MENU_X_DELAY, stop_event): break

            controller.press_a()                  # open Pokemon list
            if not self.wait(self.MENU_A_DELAY, stop_event): break

            controller.press_a()                  # select first Pokemon
            if not self.wait(self.SELECT_MON_DELAY, stop_event): break

            controller.press_down()               # navigate to field moves
            if not self.wait(self.FIELD_MOVE_DELAY, stop_event): break

            controller.press_a()                  # select Sweet Scent
            if not self.wait(self.SWEET_SCENT_A_DELAY, stop_event): break

            controller.press_a()                  # confirm / use Sweet Scent

            # ── Phase 1: brief Sweet Scent animation blackout — skip it ───────
            if not self._ldr_wait_dark(controller, stop_event):
                if stop_event.is_set(): break
                log("Phase 1 dark not detected (timeout) — retrying.")
                continue

            if not self._ldr_wait_not_dark(controller, stop_event):
                if stop_event.is_set(): break
                log("Phase 1 bright not detected (timeout) — retrying.")
                continue

            log("Phase 1 done. Waiting for battle load blackout...")

            # ── Phase 2: battle load blackout — time it ───────────────────────
            if not self._ldr_wait_dark(controller, stop_event):
                if stop_event.is_set(): break
                log("Phase 2 dark not detected (timeout) — retrying.")
                continue

            dark_start = time.time()

            if not self._ldr_wait_bright(controller, stop_event, log):
                if stop_event.is_set(): break
                log("Phase 2 bright not detected (timeout) — retrying.")
                continue

            elapsed = time.time() - dark_start
            encounter_count += 1
            log(f"Encounter #{encounter_count}: dark phase = {elapsed:.2f}s")

            # ── First encounter: establish baseline ───────────────────────────
            if threshold is None:
                threshold = elapsed + self.SHINY_EXTRA_SECONDS
                log(
                    f"Baseline: {elapsed:.2f}s → shiny threshold: {threshold:.2f}s "
                    f"(+{self.SHINY_EXTRA_SECONDS:.1f}s)"
                )
                log(
                    f"If this first encounter is shiny, press Stop now "
                    f"({self.BASELINE_STOP_WINDOW:.0f}s window)."
                )
                stop_event.wait(timeout=self.BASELINE_STOP_WINDOW)
                if stop_event.is_set():
                    log("Stopped during baseline window.")
                    break
                log("Baseline confirmed — continuing hunt.")
                if not self._flee(controller, stop_event): break
                continue

            # ── Shiny check ───────────────────────────────────────────────────
            if elapsed >= threshold:
                log(
                    f"*** SHINY DETECTED! Encounter #{encounter_count} — "
                    f"{elapsed:.2f}s >= {threshold:.2f}s ***"
                )
                log("Script paused — catch your shiny! Press Stop when done.")
                stop_event.wait()
                break

            # ── Not shiny — flee ──────────────────────────────────────────────
            log(
                f"Encounter #{encounter_count}: not shiny "
                f"({elapsed:.2f}s < {threshold:.2f}s) — fleeing."
            )
            if not self._flee(controller, stop_event): break

        log("XY - Horde Encounter stopped.")

    # ── LDR helpers ────────────────────────────────────────────────────────────

    def _ldr_wait_dark(self, controller, stop_event) -> bool:
        """Wait for LDR to drop below LDR_DARK_THRESHOLD."""
        deadline = time.time() + self.DARK_WAIT_TIMEOUT
        while time.time() < deadline:
            if stop_event.is_set():
                return False
            if controller.read_light_value() < self.LDR_DARK_THRESHOLD:
                return True
            time.sleep(self.LDR_POLL_INTERVAL)
        return False

    def _ldr_wait_not_dark(self, controller, stop_event) -> bool:
        """Wait for LDR to rise back above LDR_DARK_THRESHOLD (end of phase 1)."""
        deadline = time.time() + self.BRIGHT_WAIT_TIMEOUT
        while time.time() < deadline:
            if stop_event.is_set():
                return False
            if controller.read_light_value() >= self.LDR_DARK_THRESHOLD:
                return True
            time.sleep(self.LDR_POLL_INTERVAL)
        return False

    def _ldr_wait_bright(self, controller, stop_event, log) -> bool:
        """
        Wait for LDR to rise LDR_STEP_CHANGE above its floor since going dark.
        Handles gradual rises across multiple polls.
        """
        deadline = time.time() + self.BRIGHT_WAIT_TIMEOUT
        floor = controller.read_light_value()
        while time.time() < deadline:
            if stop_event.is_set():
                return False
            time.sleep(self.LDR_POLL_INTERVAL)
            curr = controller.read_light_value()
            if curr < floor:
                floor = curr
            if curr - floor >= self.LDR_STEP_CHANGE:
                log(f"LDR rise: floor={floor} → {curr} (+{curr - floor})")
                return True
        log(f"LDR bright timeout — floor={floor}, last={curr}")
        return False

    # ── Flee ───────────────────────────────────────────────────────────────────

    def _flee(self, controller, stop_event) -> bool:
        """Pause → Down → Right → A to select Run, then wait for overworld to reload."""
        if not self.wait(self.FLEE_PRE_DELAY, stop_event): return False
        controller.press_down()
        if not self.wait(self.FLEE_DOWN_DELAY, stop_event): return False
        controller.press_right()
        if not self.wait(self.FLEE_RIGHT_DELAY, stop_event): return False
        controller.press_a()
        if not self.wait(self.FLEE_A_DELAY, stop_event): return False
        if not self.wait(self.FLEE_RETURN_DELAY, stop_event): return False
        return True
