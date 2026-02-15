"""
Colour Detection — interactive calibration tool.

Lets you click and drag a region on the live video feed, then continuously
logs the average R, G, B values of that region. A red box is drawn over the
selected region on the preview.

Use this to find the correct colour values and tolerance for shiny detection
before writing a new automation script.
"""

import time
from scripts.base_script import BaseScript


class ColourDetection(BaseScript):
    NAME = "Colour Detection"
    DESCRIPTION = "Click a region on the video feed and monitor its average RGB values."

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("Colour Detection started.")
        log("Draw a rectangle on the video feed to select a detection region.")

        # Ask user to draw a region
        region = request_calibration("Click and drag to select a region")

        if stop_event.is_set():
            return

        x, y, w, h = region
        log(f"Region selected: x={x}  y={y}  w={w}  h={h}")
        log("Logging average RGB values every 0.5 seconds...")

        # Draw a persistent red box overlay on the video panel
        def draw_overlay(canvas):
            canvas.draw_rect(x, y, w, h, colour='red')

        # The video panel overlay callback is set via request_calibration's canvas ref.
        # We reach it through the request_calibration closure — but since we can't
        # directly access the panel here, we draw the box via a trick:
        # request a second calibration isn't appropriate, so we instruct the
        # frame grabber to annotate frames directly.
        # Instead, we annotate each captured frame using OpenCV and store it back.
        # The FrameGrabber's get_latest_frame() already provides a copy, so we
        # can annotate in-place for display by drawing on the copy we pass back.
        # However, VideoPanel reads directly from the grabber. Simplest approach:
        # use OpenCV to draw the box on each frame before it is displayed.

        import cv2

        count = 0
        while not stop_event.is_set():
            frame = frame_grabber.get_latest_frame()
            if frame is None:
                if not self.wait(0.1, stop_event):
                    break
                continue

            # Draw rectangle on a working copy stored back into the grabber's frame
            # so the VideoPanel shows it (the grabber stores our annotated copy)
            annotated = frame.copy()
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 0, 255), 2)
            # Patch the grabber's internal frame so VideoPanel picks it up
            with frame_grabber._lock:
                frame_grabber._frame = annotated

            # Compute average RGB
            r, g, b = self.avg_rgb(frame, x, y, w, h)
            count += 1
            log(f"Sample {count:4d} — R: {r:6.1f}  G: {g:6.1f}  B: {b:6.1f}")

            if not self.wait(0.5, stop_event):
                break

        log("Colour Detection finished.")
