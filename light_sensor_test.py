"""
Light Sensor Test — reads the LDR (light sensor) every second and logs its value.

Use this script to verify the GamePRo hardware is connected and communicating
correctly before running a full automation script.
"""

import time
from scripts.base_script import BaseScript


class LightSensorTest(BaseScript):
    NAME = "Light Sensor Test"
    DESCRIPTION = "Reads the LDR light sensor every second and logs the value (0-255)."

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("Light Sensor Test started.")
        log("Readings will appear below. Click ■ Stop to end.")

        count = 0
        while not stop_event.is_set():
            value = controller.read_light_value()
            binary = controller.read_light_binary()
            count += 1
            log(f"Reading {count:4d} — Value: {value:3d}   State: {binary}  "
                f"({'Bright' if binary == 'H' else 'Dark' if binary == 'L' else '?'})")
            # Wait 1 second, checking stop_event every 50ms
            if not self.wait(1.0, stop_event):
                break

        log("Light Sensor Test finished.")
