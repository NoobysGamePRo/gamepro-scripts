"""
Let's Go — Shiny Legendary Hunter
Game: Pokemon Let's Go Pikachu / Eevee (Nintendo Switch)

Soft-resets for a shiny Zapdos, Moltres, or Articuno.
Detection: avg_rgb comparison on the legendary's sprite region.

Ported from LetsGo_Shiny_Legendary_1.3.cpp.

How it works:
  1. Soft-resets via Home → X (close game) → A (reopen) → A (player).
  2. Waits for the screen to go dark (Switch loading) then bright again.
  3. Selects controller, waits for game to load (18 s).
  4. Enters the game, waits for the last loading blackout, then continues.
  5. Presses A (approach legendary) → + (skip cutscene) → waits
     ANIMATION_DELAY for the encounter animation to settle.
  6. Samples avg_rgb at the calibrated sprite region.
  7. First run: calibrates baseline. Subsequent: compares vs baseline —
     outside ±COLOUR_TOLERANCE means shiny!

Setup:
  - Save just before the legendary (in the room / on the platform).
  - Set ANIMATION_DELAY to the encounter animation length for your
    legendary (Zapdos ≈ 15 s, Moltres ≈ 18 s, Articuno ≈ 15 s).
  - On first run, draw a region over the legendary's sprite when prompted.
  - Calibration saved to calibration/lets_go_shiny_legendary.json.
  - Delete that file to recalibrate.
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
    return os.path.join(cal_dir, 'lets_go_shiny_legendary.json')


class LetsGoShinyLegendary(BaseScript):
    NAME = "Let's Go – Shiny Legendary"
    DESCRIPTION = (
        "Soft-resets for a shiny Zapdos, Moltres, or Articuno "
        "(Let's Go Pikachu/Eevee)."
    )

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    HOME_DELAY          = 1.5    # after S (Home button)
    CLOSE_X_DELAY       = 1.5    # after x (X to close software)
    CLOSE_A_DELAY       = 3.0    # after A to confirm close
    SELECT_GAME_DELAY   = 1.5    # after A to select game icon
    SELECT_USER_DELAY   = 2.0    # after A to select user profile
    DARK_POLL_INTERVAL  = 0.1    # seconds between screen brightness polls
    DARK_WAIT_TIMEOUT   = 20.0   # max wait for screen to go dark
    BRIGHT_WAIT_TIMEOUT = 20.0   # max wait for screen to go bright
    BRIGHT_EXTRA_DELAY  = 0.5    # brief pause after screen turns bright
    CONTROLLER_DELAY    = 2.0    # after A to choose controller
    CONFIRM_CTRL_DELAY  = 18.0   # after A to confirm controller (game loads)
    ENTER_GAME_DELAY    = 1.5    # after A to enter game
    DARK2_EXTRA_DELAY   = 1.5    # brief pause after second dark wait
    CONTINUE_DELAY      = 6.0    # after A to continue in-game
    APPROACH_DELAY      = 4.0    # after A to approach legendary
    ANIMATION_DELAY     = 15.0   # wait for encounter animation to settle
    SHINY_RECHECK_WAIT  = 2.0    # recheck delay before confirming shiny

    # ── Detection ─────────────────────────────────────────────────────────────
    BRIGHTNESS_REGION   = (150, 150, 200, 100)  # (x, y, w, h)
    BRIGHTNESS_DARK     = 100    # avg RGB below = screen dark
    BRIGHTNESS_BRIGHT   = 100    # avg RGB above = screen bright
    COLOUR_TOLERANCE    = 15     # ±tolerance per channel

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("Let's Go Shiny Legendary started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration — will prompt for sprite region on first encounter.")

        log("Performing initial soft reset...")
        if not self._soft_reset_and_boot(controller, frame_grabber, stop_event, log):
            return

        # ── First encounter: calibrate ────────────────────────────────────────
        if cal is None:
            log("Approaching legendary for calibration...")
            if not self._approach_legendary(controller, stop_event):
                return
            log("Draw a region over the legendary Pokemon's sprite.")
            region = request_calibration("Draw region over the legendary's sprite")
            if stop_event.is_set():
                return
            rx, ry, rw, rh = region
            frame = frame_grabber.get_latest_frame()
            if frame is None:
                log("No frame — ensure webcam is connected.")
                return
            r, g, b = self.avg_rgb(frame, rx, ry, rw, rh)
            log(f"Baseline — R:{r:.1f} G:{g:.1f} B:{b:.1f}")
            cal = {
                'region': [rx, ry, rw, rh],
                'baseline': [r, g, b],
                'tolerance': self.COLOUR_TOLERANCE,
            }
            self._save_calibration(cal)
            log("Calibration saved. Resetting for first real attempt...")
            controller.soft_reset()
            if not self.wait(1.0, stop_event): return
            if not self._soft_reset_and_boot(controller, frame_grabber, stop_event, log):
                return

        rx, ry, rw, rh = cal['region']
        br, bg, bb = cal['baseline']
        tol = cal.get('tolerance', self.COLOUR_TOLERANCE)
        sr_count = 0

        log(f"Shiny hunting loop started. Tolerance ±{tol}")

        while not stop_event.is_set():
            if not self._approach_legendary(controller, stop_event):
                break

            frame = frame_grabber.get_latest_frame()
            if frame is not None:
                r, g, b = self.avg_rgb(frame, rx, ry, rw, rh)
                log(
                    f"SR #{sr_count + 1}: "
                    f"R:{r:.0f} G:{g:.0f} B:{b:.0f}  "
                    f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f})"
                )

                if (abs(r - br) > tol or abs(g - bg) > tol or abs(b - bb) > tol):
                    if not self.wait(self.SHINY_RECHECK_WAIT, stop_event): break
                    frame2 = frame_grabber.get_latest_frame()
                    if frame2 is not None:
                        r2, g2, b2 = self.avg_rgb(frame2, rx, ry, rw, rh)
                        if (abs(r2 - br) > tol or
                                abs(g2 - bg) > tol or
                                abs(b2 - bb) > tol):
                            log(
                                f"*** SHINY LEGENDARY! "
                                f"R:{r2:.0f} G:{g2:.0f} B:{b2:.0f} ***"
                            )
                            log(f"Soft resets before shiny: {sr_count}")
                            controller.soft_reset()
                            log("Script stopped — catch your shiny! "
                                "Press ■ Stop when done.")
                            stop_event.wait()
                            return

            sr_count += 1
            log(f"Not shiny. Soft reset #{sr_count}...")
            if not self._soft_reset_and_boot(controller, frame_grabber, stop_event, log):
                break

        log("Let's Go Shiny Legendary stopped.")

    # ── Soft reset + boot ─────────────────────────────────────────────────────

    def _soft_reset_and_boot(self, controller, frame_grabber, stop_event, log) -> bool:
        """Home → close game → reopen → wait for load → continue."""
        controller.soft_reset()   # 'S' = Home button
        if not self.wait(self.HOME_DELAY, stop_event): return False
        controller.press_x()     # close software
        if not self.wait(self.CLOSE_X_DELAY, stop_event): return False
        controller.press_a()     # confirm close
        if not self.wait(self.CLOSE_A_DELAY, stop_event): return False
        controller.press_a()     # select game icon
        if not self.wait(self.SELECT_GAME_DELAY, stop_event): return False
        controller.press_a()     # select user profile
        if not self.wait(self.SELECT_USER_DELAY, stop_event): return False

        self._wait_for_brightness(frame_grabber, stop_event, dark=True,
                                  timeout=self.DARK_WAIT_TIMEOUT, log=log)
        if stop_event.is_set(): return False
        if not self.wait(5.0, stop_event): return False  # loading pause

        self._wait_for_brightness(frame_grabber, stop_event, dark=False,
                                  timeout=self.BRIGHT_WAIT_TIMEOUT, log=log)
        if stop_event.is_set(): return False
        if not self.wait(self.BRIGHT_EXTRA_DELAY, stop_event): return False

        controller.press_a()  # choose controller
        if not self.wait(self.CONTROLLER_DELAY, stop_event): return False
        controller.press_a()  # confirm controller
        if not self.wait(self.CONFIRM_CTRL_DELAY, stop_event): return False  # loads

        controller.press_a()  # enter game
        if not self.wait(self.ENTER_GAME_DELAY, stop_event): return False

        # Second loading blackout when entering game world
        self._wait_for_brightness(frame_grabber, stop_event, dark=True,
                                  timeout=self.DARK_WAIT_TIMEOUT, log=None)
        if stop_event.is_set(): return False
        if not self.wait(self.DARK2_EXTRA_DELAY, stop_event): return False

        controller.press_a()  # continue game
        if not self.wait(self.CONTINUE_DELAY, stop_event): return False
        return True

    def _approach_legendary(self, controller, stop_event) -> bool:
        """A to approach + + to skip cutscene, then wait for animation."""
        controller.press_a()
        if not self.wait(self.APPROACH_DELAY, stop_event): return False
        controller.press_plus()   # + to skip movie / start encounter
        if not self.wait(self.ANIMATION_DELAY, stop_event): return False
        return True

    def _wait_for_brightness(self, frame_grabber, stop_event, dark: bool,
                              timeout: float, log) -> bool:
        """Poll avg_rgb until screen is dark or bright. Returns True on match."""
        bx, by, bw, bh = self.BRIGHTNESS_REGION
        deadline = time.time() + timeout
        while time.time() < deadline:
            if stop_event.is_set():
                return False
            frame = frame_grabber.get_latest_frame() if frame_grabber else None
            if frame is not None:
                r, g, b = self.avg_rgb(frame, bx, by, bw, bh)
                avg = (r + g + b) / 3
                if dark and avg < self.BRIGHTNESS_DARK:
                    return True
                if not dark and avg > self.BRIGHTNESS_BRIGHT:
                    return True
            time.sleep(self.DARK_POLL_INTERVAL)
        if log:
            log("Screen brightness timeout — continuing.")
        return not stop_event.is_set()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_calibration(self):
        path = _cal_path()
        if not os.path.isfile(path):
            return None
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception:
            return None

    def _save_calibration(self, cal: dict):
        with open(_cal_path(), 'w') as f:
            json.dump(cal, f, indent=2)
