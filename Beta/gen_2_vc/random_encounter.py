"""
VC Gen 2 Random Encounter Shiny Hunter
Game: Pokemon Gold / Silver Virtual Console (3DS)

Walks the character back and forth in grass to trigger wild encounters.
Detects shininess by timing: a shiny Pokemon causes the encounter text
to appear noticeably later than normal (the extra shiny sparkle animation
adds ~800 ms or more to the encounter sequence).

Setup:
  - Save in a grass patch with a healed party
  - Run the script, calibrate the text-box detection region on screen
  - The script records normal encounter timing on the first encounter,
    then flags anything that takes significantly longer as a shiny
"""

import time
from scripts.base_script import BaseScript


class VCGen2RandomEncounter(BaseScript):
    NAME = "VC Gen 2 – Random Encounter"
    DESCRIPTION = "Walks in grass and detects shiny encounters by timing (Gold/Silver VC)."

    # ── Timing constants (seconds) ──────────────────────────────────────────
    STEP_DURATION   = 0.28   # time to walk one tile
    MENU_DELAY      = 1.4    # delay between A presses in menus after encounter
    SOFT_RESET_WAIT = 5.0    # wait after 'Z' soft reset
    MAX_ENCOUNTER_WAIT = 20.0  # give up waiting for encounter after this long
    SHINY_EXTRA_MS  = 800    # ms above normal time that flags a shiny

    # Dark-pixel threshold for text detection (R, G, B all below this = dark)
    DARK_THRESHOLD = 120

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("VC Gen 2 Random Encounter started.")
        log("Calibrate the text-box region — draw a rectangle over the battle"
            " text area on the lower half of the screen.")

        region = request_calibration("Draw rectangle over the battle text box area")
        if stop_event.is_set():
            return
        x, y, w, h = region
        log(f"Detection region: x={x} y={y} w={w} h={h}")

        steps = 5          # tiles to walk per direction
        step_count = 0
        encounter_count = 0
        normal_time_ms = None   # calibrated on first encounter

        log("Walking in grass. First encounter will calibrate normal timing.")

        while not stop_event.is_set():
            # ── Walk right N steps ──────────────────────────────────────────
            for _ in range(steps):
                if stop_event.is_set():
                    return
                controller.hold_right()
                if not self.wait(self.STEP_DURATION, stop_event):
                    return
                controller.release_all()
                if not self.wait(0.05, stop_event):
                    return

                # Check for encounter (screen goes dark)
                frame = frame_grabber.get_latest_frame() if frame_grabber else None
                if frame is not None and self._screen_dark(frame, x, y, w, h):
                    step_count = 0
                    encounter_time_ms = self._handle_encounter(
                        controller, frame_grabber, stop_event, log,
                        x, y, w, h, encounter_count, normal_time_ms
                    )
                    if stop_event.is_set():
                        return
                    if encounter_time_ms is None:
                        continue
                    encounter_count += 1
                    if normal_time_ms is None:
                        normal_time_ms = encounter_time_ms
                        log(f"Normal encounter time calibrated: {normal_time_ms:.0f} ms")
                    else:
                        excess = encounter_time_ms - normal_time_ms
                        if excess > self.SHINY_EXTRA_MS:
                            log(f"*** SHINY! Encounter took {encounter_time_ms:.0f} ms "
                                f"({excess:.0f} ms above normal) ***")
                            log(f"Encounters so far: {encounter_count}")
                            stop_event.wait()
                            return
                    # Flee / reset
                    controller.press_b()
                    self.wait(1.5, stop_event)
                    break

            # ── Walk left N steps ───────────────────────────────────────────
            for _ in range(steps):
                if stop_event.is_set():
                    return
                controller.hold_left()
                if not self.wait(self.STEP_DURATION, stop_event):
                    return
                controller.release_all()
                if not self.wait(0.05, stop_event):
                    return

                frame = frame_grabber.get_latest_frame() if frame_grabber else None
                if frame is not None and self._screen_dark(frame, x, y, w, h):
                    encounter_time_ms = self._handle_encounter(
                        controller, frame_grabber, stop_event, log,
                        x, y, w, h, encounter_count, normal_time_ms
                    )
                    if stop_event.is_set():
                        return
                    if encounter_time_ms is None:
                        continue
                    encounter_count += 1
                    if normal_time_ms is None:
                        normal_time_ms = encounter_time_ms
                        log(f"Normal encounter time calibrated: {normal_time_ms:.0f} ms")
                    else:
                        excess = encounter_time_ms - normal_time_ms
                        if excess > self.SHINY_EXTRA_MS:
                            log(f"*** SHINY! Encounter took {encounter_time_ms:.0f} ms "
                                f"({excess:.0f} ms above normal) ***")
                            log(f"Encounters so far: {encounter_count}")
                            stop_event.wait()
                            return
                    controller.press_b()
                    self.wait(1.5, stop_event)
                    break

        log("VC Gen 2 Random Encounter stopped.")

    def _handle_encounter(self, controller, frame_grabber, stop_event, log,
                          x, y, w, h, encounter_count, normal_time_ms):
        """
        Wait for the battle text to appear, time how long it takes.
        Returns elapsed_ms or None if timed out.
        """
        start = time.time()
        deadline = start + self.MAX_ENCOUNTER_WAIT

        # Wait for text to appear (dark pixels fill the text box)
        while time.time() < deadline:
            if stop_event.is_set():
                return None
            frame = frame_grabber.get_latest_frame() if frame_grabber else None
            if frame is not None and self._text_visible(frame, x, y, w, h):
                elapsed_ms = (time.time() - start) * 1000
                log(f"Encounter {encounter_count + 1}: text in {elapsed_ms:.0f} ms")
                return elapsed_ms
            time.sleep(0.02)

        log("Timed out waiting for encounter text.")
        return None

    def _screen_dark(self, frame, x, y, w, h) -> bool:
        """True if the region is mostly dark (encounter blackout)."""
        region = frame[y:y + h, x:x + w]
        dark = (region[:, :, 0] < 60) & (region[:, :, 1] < 60) & (region[:, :, 2] < 60)
        return dark.mean() > 0.7

    def _text_visible(self, frame, x, y, w, h) -> bool:
        """True when dark text pixels appear in the text box region."""
        region = frame[y:y + h, x:x + w]
        dark = ((region[:, :, 0] < self.DARK_THRESHOLD) &
                (region[:, :, 1] < self.DARK_THRESHOLD) &
                (region[:, :, 2] < self.DARK_THRESHOLD))
        return dark.mean() > 0.15
