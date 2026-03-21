"""
Friend Safari Shiny Encounter
Game: Pokemon X/Y

Walks back and forth in the Friend Safari to trigger encounters.
Uses the LDR sensor to detect the shiny sparkle (brightness change
on the bottom 3DS screen during the encounter animation).

Setup:
  - Enter your chosen Friend Safari and stand in the grass
  - Position the LDR over the bottom 3DS screen
  - Set STEP_RANGE to the number of tiles to walk each direction
"""

from scripts.base_script import BaseScript


class FriendSafari(BaseScript):
    NAME = "Gen 6 – Friend Safari Encounter"
    DESCRIPTION = "Walks in Friend Safari and uses LDR to detect shiny encounters (X/Y)."

    STEP_RANGE      = 5       # tiles to walk per direction
    STEP_MS         = 80      # ms per tile step (0.08 s)
    ENCOUNTER_WAIT  = 8.0     # wait after triggering encounter before LDR check
    LDR_SAMPLES     = 10
    LDR_STEP_LIMIT  = 40
    POST_BATTLE     = 6.0     # wait after pressing B to flee

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("Friend Safari started.")
        log(f"Walking {self.STEP_RANGE} tiles per direction. LDR must face bottom screen.")

        enc_count = 0

        while not stop_event.is_set():
            for direction, hold_cmd, release_cmd in [
                ('right', controller.hold_right, controller.release_all),
                ('left',  controller.hold_left,  controller.release_all),
            ]:
                for step in range(self.STEP_RANGE):
                    if stop_event.is_set():
                        return
                    hold_cmd()
                    if not self.wait(self.STEP_MS / 1000, stop_event):
                        return
                    release_cmd()
                    if not self.wait(0.02, stop_event):
                        return

                    # Brief pause — check for battle (screen dark)
                    frame = frame_grabber.get_latest_frame() if frame_grabber else None
                    if frame is not None and self._screen_dark(frame):
                        enc_count += 1
                        log(f"Encounter {enc_count}: waiting for LDR window...")
                        if not self.wait(self.ENCOUNTER_WAIT, stop_event):
                            return

                        shiny = self._check_ldr(controller, stop_event, log)
                        if stop_event.is_set():
                            return

                        if shiny:
                            log(f"*** SHINY on encounter {enc_count}! ***")
                            stop_event.wait()
                            return

                        log(f"Encounter {enc_count}: not shiny — fleeing")
                        # Flee
                        for _ in range(10):
                            controller.press_b()
                            self.wait(0.6, stop_event)
                        self.wait(self.POST_BATTLE, stop_event)
                        break

        log("Friend Safari stopped.")

    def _screen_dark(self, frame) -> bool:
        sample = frame[200:280, 200:440]
        dark = (sample[:, :, 0] < 60) & (sample[:, :, 1] < 60) & (sample[:, :, 2] < 60)
        return dark.mean() > 0.6

    def _check_ldr(self, controller, stop_event, log) -> bool:
        readings = []
        for _ in range(self.LDR_SAMPLES):
            if stop_event.is_set():
                return False
            readings.append(controller.read_light_value())
            self.wait(0.1, stop_event)
        half = self.LDR_SAMPLES // 2
        step = abs(sum(readings[half:]) / half - sum(readings[:half]) / half)
        log(f"LDR step: {step:.1f}")
        return step > self.LDR_STEP_LIMIT
