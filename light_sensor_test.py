"""
Light Sensor Test — reads the LDR (light sensor) every second and logs its value.

Use this script to verify the GamePRo hardware is connected and communicating
correctly before running a full automation script.

The raw value (0-1020) is returned by the Arduino. Values above BRIGHT_THRESHOLD
are considered bright (screen on / encounter active); below is dark (screen off /
black frame). Adjust BRIGHT_THRESHOLD to match your setup.
"""

from scripts.base_script import BaseScript


class LightSensorTest(BaseScript):
    NAME = "Light Sensor Test"
    DESCRIPTION = "Reads the LDR light sensor every second and logs the value (0-1020)."

    BRIGHT_THRESHOLD = 512  # values above this are considered bright

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("Light Sensor Test started.")
        log(f"Bright threshold: {self.BRIGHT_THRESHOLD}  (0 = dark, 1020 = bright)")
        log("Readings will appear below. Click - Stop to end.")

        count = 0
        while not stop_event.is_set():
            value = controller.read_light_value()
            state = "Bright" if value >= self.BRIGHT_THRESHOLD else "Dark"
            count += 1
            log(f"Reading {count:4d} - Value: {value:4d} / 1020   ({state})")
            if not self.wait(1.0, stop_event):
                break

        log("Light Sensor Test finished.")
