"""
VC Gold / Silver Shiny Starter
Game: Pokemon Gold / Silver (3DS Virtual Console)

Soft-resets for a shiny Chikorita, Cyndaquil or Totodile.
Follows VC_GS_Shiny_Starter_4.0 (the C++ program) step for step.

Setup:
  - Save inside Prof. Elm's lab, standing in front of the Poke Ball of the
    starter you want (start of the game, empty party).
  - The soft reset uses the GamePRo's reset rod (command Z).

How it works:
  - Soft reset, take the starter, skip the nickname, go through Elm's text,
    register Elm's phone number, then open the starter's summary screen (X, A, A, A).
  - First attempt of every run: you draw a small box in the WHITE space next
    to the gender symbol at the top right of the summary screen. That is
    where the shiny star appears. Don't include any black pixels.
  - Every attempt after that counts dark pixels in the box. The star adds
    dark pixels; a shiny is confirmed when the star is seen 3 times in a row
    (the summary is closed and re-opened between checks).
  - Every button press gets a random extra 1-100 ms, like the original.
"""

import random

from scripts.base_script import BaseScript


class GSShinyStarter(BaseScript):
    NAME = "VC Gold/Silver – Shiny Starter"
    DESCRIPTION = (
        "Soft-resets Pokemon Gold/Silver (3DS VC) for a shiny starter. Save in front of "
        "the Poke Ball; on the first attempt draw a box in the white space next to "
        "the gender symbol on the summary screen."
    )
    GAME = "Gold/Silver"

    # ── Timing (seconds), from VC_GS_Shiny_Starter_4.0 ──────────────────────
    START_WAIT       = 1.5    # before the first soft reset
    RESET_WAIT       = 5.0    # after Z (soft reset) for the game to restart
    TITLE_A_DELAY    = 1.4    # x4: title screen, Continue
    INTERACT_DELAY   = 2.5    # A at the Poke Ball
    MOVE_DELAY       = 1.6    # A: starter picture
    ADD_PARTY_DELAY  = 1.3    # x2: take this Pokemon?
    RECEIVE_DELAY    = 1.3    # x2: received text
    PRE_NICKNAME     = 2.4
    NICKNAME_DELAY   = 1.5    # x2: nickname prompt
    NO_NICKNAME      = 3.0    # B: no nickname
    MR_POKEMON_DELAY = 1.3    # x4: Elm talks about Mr. Pokemon
    PRE_HEAL         = 0.5
    HEAL_DELAY       = 1.3    # x2
    HEAL_WAIT        = 5.0
    NUMBER_DELAY     = 1.8    # x2: Elm gives his phone number
    PRE_REGISTER     = 2.8
    REGISTER_DELAY   = 1.5    # A: number registered
    MENU_X_DELAY     = 1.3    # X: open menu
    MENU_A_DELAY     = 1.4    # x3: Pokemon, starter, summary
    CHECK_WAIT       = 0.5    # before reading the box
    CLOSE_B_DELAY    = 1.4    # x3: back out of the summary
    JITTER_MS        = 100    # random 1..100 ms added after each press

    # ── Shiny check, from the C++ ───────────────────────────────────────────
    DARK_MARGIN      = 30     # dark = R, G and B each 30+ below the white baseline
    MIN_DARK_PIXELS  = 15     # more than this = star seen
    MAX_DARK_SHARE   = 0.9    # 90 %+ of the box dark = wrong screen, not a star
    CONFIRMATIONS    = 3      # star seen this many times in a row = shiny
    WRONG_SCREEN_MAX = 3      # wrong screen this many times = reset

    def _get_starter(self, controller, stop_event):
        """From the title screen to registering Elm's number, as in the C++."""
        return self._run_steps(controller, stop_event, [
            ('a', 4, self.TITLE_A_DELAY),
            ('a', 1, self.INTERACT_DELAY),
            ('a', 1, self.MOVE_DELAY),
            ('a', 2, self.ADD_PARTY_DELAY),
            ('a', 2, self.RECEIVE_DELAY),
            ('wait', self.PRE_NICKNAME),
            ('a', 2, self.NICKNAME_DELAY),
            ('b', 1, self.NO_NICKNAME),
            ('a', 4, self.MR_POKEMON_DELAY),
            ('wait', self.PRE_HEAL),
            ('a', 2, self.HEAL_DELAY),
            ('wait', self.HEAL_WAIT),
            ('a', 2, self.NUMBER_DELAY),
            ('wait', self.PRE_REGISTER),
            ('a', 1, self.REGISTER_DELAY),
        ])

    # ── Everything below is the same in the Crystal script ──────────────────

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log(f"VC {self.GAME} Shiny Starter started.")
        log("Save in front of the Poke Ball of your starter. On the first attempt you'll "
            "be asked to draw a box on the summary screen.")
        self._region = None
        self._baseline = None
        sr_count = 0

        if self.wait(self.START_WAIT, stop_event):
            controller.soft_reset_z()
            self.wait(self.RESET_WAIT, stop_event)

        while not stop_event.is_set():
            if not self._get_starter(controller, stop_event):
                break
            result = self._check(controller, frame_grabber, stop_event, log,
                                 request_calibration, sr_count)
            if result is None:
                break
            if result == 'shiny':
                log(f"Soft resets before shiny: {sr_count}")
                log("Script paused — catch your shiny! Press ■ Stop when done.")
                stop_event.wait()
                break

            sr_count += 1
            log(f"No shiny. Soft reset #{sr_count}...")
            controller.soft_reset_z()
            if not self._press_wait(stop_event, self.RESET_WAIT):
                break

        clear = getattr(frame_grabber, 'clear_detect_overlay', None)
        if clear:
            clear()
        log(f"VC {self.GAME} Shiny Starter stopped.")

    def _press_wait(self, stop_event, seconds):
        """The C++ waits a fixed time plus a random 1-100 ms after each press."""
        return self.wait(seconds + random.randint(1, self.JITTER_MS) / 1000.0, stop_event)

    def _presses(self, controller, stop_event, button, times, delay):
        for _ in range(times):
            getattr(controller, 'press_' + button)()
            if not self._press_wait(stop_event, delay):
                return False
        return True

    def _run_steps(self, controller, stop_event, steps):
        for step in steps:
            if step[0] == 'wait':
                ok = self._press_wait(stop_event, step[1])
            else:
                ok = self._presses(controller, stop_event, *step)
            if not ok:
                return False
        return True

    def _open_summary(self, controller, stop_event):
        controller.press_x()
        if not self._press_wait(stop_event, self.MENU_X_DELAY):
            return False
        return self._presses(controller, stop_event, 'a', 3, self.MENU_A_DELAY)

    def _check(self, controller, frame_grabber, stop_event, log, request_calibration, sr_count):
        """Open the summary and look for the star. Returns 'shiny', 'reset' or None (stopped)."""
        seen = wrong = 0
        while not stop_event.is_set():
            if not self._open_summary(controller, stop_event):
                return None

            if self._region is None:                  # first attempt of the run: set up the box
                if not self._calibrate(frame_grabber, stop_event, log, request_calibration):
                    return None
                return 'reset'

            if not self.wait(self.CHECK_WAIT, stop_event):
                return None
            dark = self._dark_pixels(frame_grabber)
            if dark is None:
                log("No frame — ensure webcam is connected.")
                return 'reset'
            x, y, w, h = self._region
            log(f"SR #{sr_count + 1}: {dark} dark px in the star box "
                f"(star if over {self.MIN_DARK_PIXELS})")

            if dark <= self.MIN_DARK_PIXELS:
                return 'reset'                        # no star
            if dark < self.MAX_DARK_SHARE * w * h:
                seen += 1
            else:
                wrong += 1
            if seen >= self.CONFIRMATIONS:
                log(f"*** SHINY STARTER! Star seen {seen} times in a row ({dark} dark px) ***")
                return 'shiny'
            if wrong >= self.WRONG_SCREEN_MAX:
                log("The star box is almost all dark — not the summary screen. Resetting.")
                return 'reset'
            if not self._presses(controller, stop_event, 'b', 3, self.CLOSE_B_DELAY):
                return None                           # close the summary and look again
        return None

    def _calibrate(self, frame_grabber, stop_event, log, request_calibration):
        log("Set up the star box: draw a small box in the WHITE space next to the gender "
            "symbol (top right of the summary screen). This is where the shiny star "
            "appears. Don't include any black pixels.")
        region = request_calibration(
            "Draw a small box in the white space next to the gender symbol (no black pixels)")
        if stop_event.is_set() or region is None:
            return False
        x, y, w, h = [int(v) for v in region]
        frame = frame_grabber.get_latest_frame()
        if w < 2 or h < 2 or frame is None:
            log("Couldn't set the star box — it will be asked for again on the next attempt.")
            return True
        self._region = (x, y, w, h)
        self._baseline = self.avg_rgb(frame, x, y, w, h)
        r, g, b = self._baseline
        log(f"Star box set: x={x} y={y} w={w} h={h}, baseline R:{r:.0f} G:{g:.0f} B:{b:.0f}")
        if min(self._baseline) < 120:
            log("Warning: that box doesn't look white. If it never finds a shiny, press Stop, "
                "then Run again and draw the box in the white space only.")
        overlay = getattr(frame_grabber, 'set_detect_overlay', None)
        if overlay:
            overlay(x, y, w, h)
        log("Soft reset loop running. Press ■ Stop at any time.")
        return True

    def _dark_pixels(self, frame_grabber):
        """Pixels in the box whose R, G and B are each DARK_MARGIN below the white baseline."""
        frame = frame_grabber.get_latest_frame()
        if frame is None:
            return None
        x, y, w, h = self._region
        r0, g0, b0 = self._baseline
        box = frame[y:y + h, x:x + w].astype(int)          # BGR
        dark = ((box[:, :, 0] < b0 - self.DARK_MARGIN) &
                (box[:, :, 1] < g0 - self.DARK_MARGIN) &
                (box[:, :, 2] < r0 - self.DARK_MARGIN))
        return int(dark.sum())
