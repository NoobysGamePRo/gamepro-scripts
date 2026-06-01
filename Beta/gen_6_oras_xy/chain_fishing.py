"""
Chain Fishing Shiny Hunter
Game: Pokemon X/Y and ORAS

Casts the fishing rod repeatedly without moving to build a chain.

Setup sequence (runs once at start):
  1. Draw a rectangle above your trainer's head — this is where the red
     exclamation mark on white appears when a fish bites.
  2. The script presses Y to open the shortcut menu.
  3. Press a direction button in the Manual Controls panel that matches
     your rod's Y-menu slot (up/down/left/right). That direction is
     remembered for every cast from then on.

Then for each attempt:
  - Y + direction → cast rod
  - Wait for ! → press A to hook
  - LDR times the battle-load dark phase; shiny stays dark longer
  - Not shiny → flee → repeat

Hardware:
  - Position LDR over the bottom 3DS screen for shiny detection
  - Tune LDR_DARK_THRESHOLD using the Live button on the Light Sensor
    dial in the app (should sit between dark and bright screen values)
"""

import time
from scripts.base_script import BaseScript


class ChainFishing(BaseScript):
    NAME = "Gen 6 – Chain Fishing"
    DESCRIPTION = "Builds a fishing chain to hunt shiny encounters (X/Y / ORAS)."

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    BAG_OPEN_WAIT   = 1.2    # after pressing Y before pressing direction
    CAST_WAIT       = 1.5    # after pressing direction to cast
    HOOK_WINDOW     = 15.0   # max wait for exclamation mark
    AFTER_HOOK      = 1.0    # delay after pressing A to hook

    # ── Flee timing (seconds) ────────────────────────────────────────────────
    FLEE_PRE_DELAY      = 1.0   # pause after LDR detection, before fleeing
    FLEE_DOWN_DELAY     = 1.3   # after Down in battle menu
    FLEE_RIGHT_DELAY    = 0.8   # after Right to highlight Run
    FLEE_A_DELAY        = 2.0   # after A to confirm Run
    FLEE_RETURN_DELAY   = 7.5   # after Run confirmed — wait for overworld to reload

    # ── Exclamation mark detection thresholds ────────────────────────────────
    WHITE_MIN       = 200    # B,G,R all above this = white pixel
    RED_MIN_R       = 180    # R above this = red pixel
    RED_MAX_G       = 100    # G below this = red pixel

    # ── LDR (light sensor) ──────────────────────────────────────────────────
    LDR_DARK_THRESHOLD  = 200   # LDR below this = screen dark
    LDR_STEP_CHANGE     = 40    # minimum rise from floor = screen brightening
    LDR_POLL_INTERVAL   = 0.1   # seconds between LDR reads
    DARK_WAIT_TIMEOUT   = 20.0  # max seconds to wait for screen to go dark
    BRIGHT_WAIT_TIMEOUT = 40.0  # max seconds to wait for screen to brighten

    # ── Shiny detection ──────────────────────────────────────────────────────
    SHINY_EXTRA_SECONDS  = 1.2   # threshold = baseline + this
    BASELINE_STOP_WINDOW = 10.0  # seconds to press Stop after first baseline

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("Chain Fishing started.")

        # ── Step 1: calibrate exclamation mark detection region ─────────────
        log("Draw a rectangle above your trainer's head (where ! appears).")
        region = request_calibration("Draw rectangle above trainer's head (exclamation mark)")
        if stop_event.is_set():
            return
        x, y, w, h = region
        log(f"Detection region set: x={x} y={y} w={w} h={h}")

        # ── Step 2 & 3: press Y then ask which direction slot the rod is in ─
        rod_direction = self._select_rod_direction(controller, stop_event, log)
        if stop_event.is_set() or rod_direction is None:
            return
        log(f"Rod direction: {rod_direction}. LDR must be positioned over the bottom screen.")
        log(
            f"LDR dark threshold: {self.LDR_DARK_THRESHOLD}  "
            f"shiny margin: +{self.SHINY_EXTRA_SECONDS}s"
        )

        threshold = None
        chain = 0

        while not stop_event.is_set():
            # ── Cast the rod (Y already pressed on first cast during setup) ──
            if chain > 0:
                self._cast_rod(controller, rod_direction, stop_event)
                if stop_event.is_set():
                    break

            # ── Wait for exclamation mark ───────────────────────────────────
            hooked = self._wait_for_exclamation(frame_grabber, stop_event, x, y, w, h)
            if stop_event.is_set():
                break

            if not hooked:
                log(f"Chain {chain}: missed hook window — casting again")
                self._cast_rod(controller, rod_direction, stop_event)
                continue

            # ── Press A to hook the fish ────────────────────────────────────
            controller.press_a()
            if not self.wait(self.AFTER_HOOK, stop_event):
                break

            # ── Wait for battle-load dark phase and time it ─────────────────
            if not self._ldr_wait_dark(controller, stop_event):
                if stop_event.is_set():
                    break
                log(f"Chain {chain}: dark phase not detected — casting again")
                self._cast_rod(controller, rod_direction, stop_event)
                continue

            dark_start = time.time()

            if not self._ldr_wait_bright(controller, stop_event, log):
                if stop_event.is_set():
                    break
                log(f"Chain {chain}: bright phase not detected — casting again")
                self._cast_rod(controller, rod_direction, stop_event)
                continue

            elapsed = time.time() - dark_start
            chain += 1
            log(f"Chain {chain}: dark phase = {elapsed:.2f}s")

            # ── First encounter: establish baseline ─────────────────────────
            if threshold is None:
                threshold = elapsed + self.SHINY_EXTRA_SECONDS
                log(
                    f"Baseline: {elapsed:.2f}s → shiny threshold: {threshold:.2f}s "
                    f"(+{self.SHINY_EXTRA_SECONDS:.1f}s)"
                )
                log(
                    f"If this first encounter looks shiny, press Stop now "
                    f"({self.BASELINE_STOP_WINDOW:.0f}s window)."
                )
                stop_event.wait(timeout=self.BASELINE_STOP_WINDOW)
                if stop_event.is_set():
                    log("Stopped during baseline window.")
                    break
                log("Baseline confirmed — continuing chain.")
                if not self._flee(controller, stop_event):
                    break
                continue

            # ── Shiny check ─────────────────────────────────────────────────
            if elapsed >= threshold:
                log(
                    f"*** SHINY detected on chain {chain}! "
                    f"{elapsed:.2f}s >= {threshold:.2f}s — Catch it! ***"
                )
                stop_event.wait()
                break

            log(
                f"Chain {chain}: not shiny "
                f"({elapsed:.2f}s < {threshold:.2f}s) — fleeing."
            )
            if not self._flee(controller, stop_event):
                break

        log("Chain Fishing stopped.")

    # ── Setup helpers ─────────────────────────────────────────────────────────

    def _select_rod_direction(self, controller, stop_event, log):
        """Press Y to open the shortcut menu, then wait for the user to press
        a D-pad button in the Manual Controls panel to select the rod slot."""
        log("Pressing Y to open shortcut menu...")
        controller.press_y()
        if not self.wait(self.BAG_OPEN_WAIT, stop_event):
            return None

        log("=" * 50)
        log("  Rod slot selection:")
        log("  Press a direction button in the Manual Controls")
        log("  panel that matches your rod's Y-menu slot.")
        log("=" * 50)

        direction = controller.wait_for_direction(stop_event)
        if stop_event.is_set() or direction is None:
            return None

        log(f"Rod direction set to: {direction} — casting first rod.")
        self._press_direction(controller, direction)
        self.wait(self.CAST_WAIT, stop_event)
        return direction

    def _cast_rod(self, controller, direction, stop_event):
        """Y → direction to cast the rod."""
        controller.press_y()
        if not self.wait(self.BAG_OPEN_WAIT, stop_event):
            return
        self._press_direction(controller, direction)
        self.wait(self.CAST_WAIT, stop_event)

    def _press_direction(self, controller, direction):
        {'up': controller.press_up, 'down': controller.press_down,
         'left': controller.press_left, 'right': controller.press_right}[direction]()

    # ── Exclamation mark detection ────────────────────────────────────────────

    def _wait_for_exclamation(self, frame_grabber, stop_event, x, y, w, h) -> bool:
        """Poll the detection region until white/red ! pixels appear."""
        deadline = time.time() + self.HOOK_WINDOW
        while time.time() < deadline:
            if stop_event.is_set():
                return False
            frame = frame_grabber.get_latest_frame() if frame_grabber else None
            if frame is not None:
                roi = frame[y:y + h, x:x + w]
                white = ((roi[:, :, 0] > self.WHITE_MIN) &
                         (roi[:, :, 1] > self.WHITE_MIN) &
                         (roi[:, :, 2] > self.WHITE_MIN))
                red   = ((roi[:, :, 2] > self.RED_MIN_R) &
                         (roi[:, :, 1] < self.RED_MAX_G))
                if white.sum() > 20 or red.sum() > 10:
                    return True
            time.sleep(0.02)
        return False

    # ── LDR helpers ───────────────────────────────────────────────────────────

    def _ldr_wait_dark(self, controller, stop_event) -> bool:
        """Wait for LDR to drop below LDR_DARK_THRESHOLD (battle load starting)."""
        deadline = time.time() + self.DARK_WAIT_TIMEOUT
        while time.time() < deadline:
            if stop_event.is_set():
                return False
            if controller.read_light_value() < self.LDR_DARK_THRESHOLD:
                return True
            time.sleep(self.LDR_POLL_INTERVAL)
        return False

    def _ldr_wait_bright(self, controller, stop_event, log) -> bool:
        """Wait for LDR to rise LDR_STEP_CHANGE above its floor (battle fully loaded)."""
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

    # ── Flee ──────────────────────────────────────────────────────────────────

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
