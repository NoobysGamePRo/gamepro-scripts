"""
SwSh - Auto Breeding
Game: Pokemon Sword / Shield (Nintendo Switch)

Automates egg collection and hatching on Route 5 (the Nursery near
Motostoke). The player must have a breeding pair deposited with the
Nursery lady on Route 5. Eggs are collected by talking to the Nursery
aide, then hatched by biking back and forth on the bridge east of the
Nursery. Once a batch of 5 eggs has hatched, the script checks each
hatchling's sprite via avg_rgb and alerts on a potential shiny.

Ported from SwordShield_Automatic_Breeding_2.0.cpp.

How it works:
  Egg collection phase (repeat until 5 eggs in party):
    1. Hold left (1.8 s) toward the west end of Route 5 while watching
       for egg-hatch text (dark pixel strip at bottom of screen).
    2. Hold NE right (4 s) back toward the Nursery aide.
    3. Every NURSERY_CHECK_EVERY passes, press A to talk to the
       Nursery aide; check for the egg-ready icon via white-pixel
       count; if ready: press A×2 to receive egg, add to party.
    4. Repeat until 5 eggs collected.

  Hatching phase (repeat until all 5 hatched):
    1. Bike right (6.5 s) then left (6 s), checking for hatch text
       on each pass.
    2. On hatch detection: press A (16 s for animation) → B (skip
       nickname 7 s) → confirm via avg_rgb on calibrated region
       (shiny hatch has different colours).
    3. After all 5 hatched, fly back to Nursery via X menu.

  Fly to Nursery (flyNursery):
    X(1.5s) → Down(1.5s) → A(3s) → NE_TAP(1s) → A(1.5s) → A(3s)

Setup:
  - Deposit two compatible Pokemon at the Route 5 Nursery.
  - Save on Route 5 near the Nursery with a Flame Body / Magma Armor
    Pokemon in the first party slot (or use Wooloo if just collecting).
  - On first run, let an egg hatch and draw a region over the
    hatchling's summary sprite (to detect shiny colouration).
  - Delete calibration/sword_shield_auto_breeding.json to recalibrate.
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
    return os.path.join(cal_dir, 'sword_shield_auto_breeding.json')


class SwordShieldAutoBreeding(BaseScript):
    NAME = "SwSh - Auto Breeding"
    DESCRIPTION = "Automates egg collection from the Nursery on Route 5 (Sword/Shield)."

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    WALK_LEFT_DURATION    = 1.8    # hold left toward west Route 5
    WALK_NE_DURATION      = 4.0    # hold NE to return to Nursery aide
    NURSERY_TALK_DELAY    = 2.0    # after pressing A to talk
    EGG_RECEIVE_DELAY     = 4.0    # after A to receive egg (×2)
    EGG_CONFIRM_DELAY     = 2.5    # after A to add egg to party
    DISMISS_B_DELAY       = 1.5    # between B presses to dismiss dialogue
    HATCH_ANIM_WAIT       = 16.0   # egg hatching animation
    HATCH_NICKNAME_WAIT   = 7.0    # after B to skip nickname
    HATCH_CONFIRM_WAIT    = 4.0    # after second B
    BIKE_RIGHT_DURATION   = 6.5    # biking right on bridge
    BIKE_LEFT_DURATION    = 6.0    # biking left on bridge
    BIKE_TURN_WAIT        = 0.2    # small wait on direction change
    FLY_X_WAIT            = 1.5    # after X to open menu
    FLY_DOWN_WAIT         = 1.5    # after Down to highlight Town Map
    FLY_A1_WAIT           = 3.0    # after A to open map
    FLY_NE_WAIT           = 1.0    # after NE tap to select Nursery
    FLY_A2_WAIT           = 1.5    # after A to confirm destination
    FLY_A3_WAIT           = 3.0    # after A to fly (landing wait)

    # ── Nursery interaction cadence ───────────────────────────────────────────
    NURSERY_CHECK_EVERY   = 3      # talk to Nursery aide every N walk passes
    SAFETY_RESET_EVERY    = 50     # flee + fly back every N passes as safety

    # ── Egg hatch text detection (dark horizontal strip) ──────────────────────
    HATCH_DARK_THRESHOLD  = 120    # pixels below this count as dark
    HATCH_DARK_MIN        = 800    # minimum dark pixels to detect hatch text
    HATCH_CONSEC_MIN      = 600    # minimum consecutive dark pixels

    # ── Nursery egg-ready icon detection (PNI — white + dark mix) ────────────
    EGG_WHITE_THRESHOLD   = 180    # R,G,B all > this = white
    EGG_WHITE_MIN         = 70     # white pixels in nursery icon region
    EGG_DARK_MIN          = 70     # dark pixels in nursery icon region

    # ── Post-hatch PCI confirmation (red hatch screen) ───────────────────────
    HATCH_B_AVE_MAX       = 140    # blue channel average must be below this
    HATCH_R_AVE_MIN       = 180    # red channel average must be above this

    COLOUR_TOLERANCE      = 15

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("SwSh - Auto Breeding started.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration found — starting first-run setup.")
            log("Let an egg hatch, then draw a region over the hatchling's "
                "sprite in the summary screen.")
            cal = self._calibrate(
                controller, frame_grabber, stop_event, log, request_calibration
            )
            if stop_event.is_set() or cal is None:
                return
            self._save_calibration(cal)
            log("Calibration saved.")
        else:
            log(f"Calibration loaded from {_cal_path()}")

        x, y, w, h = cal['region']
        br, bg, bb = cal['baseline']
        tolerance  = cal.get('tolerance', self.COLOUR_TOLERANCE)

        log(f"Hatchling region: x={x} y={y} w={w} h={h} | tolerance ±{tolerance}")
        log("Breeding loop running. Press Stop at any time.")

        total_hatched = 0

        while not stop_event.is_set():

            # ── Phase 1: collect 5 eggs ────────────────────────────────────
            party_eggs    = 0
            party_hatched = 0
            walk_pass     = 0

            log("Collecting eggs...")

            while party_eggs < 5 and not stop_event.is_set():

                # Walk left (checking for incidental hatch)
                controller.hold_left()
                hatched = self._walk_check_hatch(
                    controller, frame_grabber, stop_event,
                    self.WALK_LEFT_DURATION, log,
                    x, y, w, h, br, bg, bb, tolerance
                )
                controller.release_all()
                if stop_event.is_set(): break
                if hatched:
                    party_hatched += 1
                    total_hatched += 1
                    log(f"Egg hatched while walking! Total hatched: {total_hatched}")

                # Walk NE back toward Nursery aide (checking for hatch)
                # '9' = hold NE on the Switch joystick servo
                controller._send('9')
                hatched = self._walk_check_hatch(
                    controller, frame_grabber, stop_event,
                    self.WALK_NE_DURATION, log,
                    x, y, w, h, br, bg, bb, tolerance
                )
                controller.release_all()
                if stop_event.is_set(): break
                if hatched:
                    party_hatched += 1
                    total_hatched += 1
                    log(f"Egg hatched while walking! Total hatched: {total_hatched}")

                walk_pass += 1

                # Every NURSERY_CHECK_EVERY passes, talk to the Nursery aide
                if walk_pass % self.NURSERY_CHECK_EVERY == 0:
                    controller.press_a()
                    if not self.wait(self.NURSERY_TALK_DELAY, stop_event): break

                    # Check for egg-ready icon
                    frame = frame_grabber.get_latest_frame()
                    egg_ready = False
                    if frame is not None:
                        egg_ready = self._check_egg_ready(frame)

                    if egg_ready:
                        log("Egg ready — collecting.")
                        controller.press_a()
                        if not self.wait(self.EGG_RECEIVE_DELAY, stop_event): break
                        controller.press_a()
                        if not self.wait(self.EGG_RECEIVE_DELAY, stop_event): break

                        # Confirm collection via PCI (red screen)
                        frame = frame_grabber.get_latest_frame()
                        if frame is not None and self._check_hatch_screen(frame):
                            log(f"Egg collected! Party eggs: {party_eggs + 1}")
                            controller.press_a()
                            if not self.wait(self.EGG_CONFIRM_DELAY, stop_event): break
                            party_eggs += 1

                        for _ in range(2):
                            controller.press_b()
                            if not self.wait(self.DISMISS_B_DELAY, stop_event): break
                    else:
                        for _ in range(3):
                            controller.press_b()
                            if not self.wait(self.DISMISS_B_DELAY, stop_event): break

                # Safety: flee any accidental encounter and fly back
                if walk_pass >= self.SAFETY_RESET_EVERY:
                    log("Safety reset — flying back to Nursery.")
                    for _ in range(2):
                        controller.press_b()
                        if not self.wait(1.5, stop_event): break
                    controller.press_up()
                    if not self.wait(1.5, stop_event): break
                    controller.press_a()
                    if not self.wait(4.0, stop_event): break
                    self._fly_to_nursery(controller, stop_event, total_hatched)
                    walk_pass = 0

            if stop_event.is_set(): break

            log(f"5 eggs collected. Moving to bridge to hatch...")

            # ── Transition: move down then right to the bridge ────────────
            controller.hold_down()
            if not self.wait(0.2, stop_event): break
            controller.release_all()

            controller.hold_right()
            hatched = self._walk_check_hatch(
                controller, frame_grabber, stop_event,
                1.0, log, x, y, w, h, br, bg, bb, tolerance
            )
            controller.release_all()
            if stop_event.is_set(): break
            if hatched:
                party_hatched += 1
                total_hatched += 1

            controller.hold_up()
            if not self.wait(self.BIKE_TURN_WAIT, stop_event): break
            controller.release_all()

            controller.hold_right()
            hatched = self._walk_check_hatch(
                controller, frame_grabber, stop_event,
                8.0, log, x, y, w, h, br, bg, bb, tolerance
            )
            controller.release_all()
            if stop_event.is_set(): break
            if hatched:
                party_hatched += 1
                total_hatched += 1

            # ── Phase 2: bike back and forth until all 5 hatched ──────────
            lr_safety = 0
            while party_hatched < 5 and not stop_event.is_set():

                # Bike left
                controller.hold_left()
                hatched = self._walk_check_hatch(
                    controller, frame_grabber, stop_event,
                    self.BIKE_LEFT_DURATION, log,
                    x, y, w, h, br, bg, bb, tolerance
                )
                controller.release_all()
                if stop_event.is_set(): break
                if hatched:
                    party_hatched += 1
                    total_hatched += 1
                    log(f"Egg hatched! Total hatched: {total_hatched}")

                if party_hatched >= 5:
                    break

                # Brief up transition
                controller.hold_up()
                if not self.wait(self.BIKE_TURN_WAIT, stop_event): break
                controller.release_all()

                # Bike right
                controller.hold_right()
                hatched = self._walk_check_hatch(
                    controller, frame_grabber, stop_event,
                    self.BIKE_RIGHT_DURATION, log,
                    x, y, w, h, br, bg, bb, tolerance
                )
                controller.release_all()
                if stop_event.is_set(): break
                if hatched:
                    party_hatched += 1
                    total_hatched += 1
                    log(f"Egg hatched! Total hatched: {total_hatched}")

                lr_safety += 1
                if lr_safety > 25:
                    log("Bike safety limit reached — resetting hatching pass.")
                    break

                # Brief up transition
                controller.hold_up()
                if not self.wait(self.BIKE_TURN_WAIT, stop_event): break
                controller.release_all()

            if stop_event.is_set(): break

            log(f"Batch complete. Flying back to Nursery for next batch.")
            self._fly_to_nursery(controller, stop_event, total_hatched)

        log("SwSh - Auto Breeding stopped.")

    # ── Walk with hatch detection ─────────────────────────────────────────────

    def _walk_check_hatch(self, controller, frame_grabber, stop_event,
                           duration: float, log,
                           x, y, w, h, br, bg, bb, tolerance) -> bool:
        """
        Hold the current direction for `duration` seconds while checking for
        the egg hatch text strip (dark pixel bar at the bottom of the screen).
        If hatch is detected, handle the hatch animation and shiny check.
        Returns True if an egg hatched during this walk.
        """
        deadline = time.time() + duration
        while time.time() < deadline:
            if stop_event.is_set():
                return False
            frame = frame_grabber.get_latest_frame()
            if frame is not None:
                if self._detect_hatch_text(frame):
                    controller.release_all()
                    log("Hatch text detected!")
                    # A to start hatching animation
                    controller.press_a()
                    if not self.wait(self.HATCH_ANIM_WAIT, stop_event):
                        return True
                    # B to skip nickname
                    controller.press_b()
                    if not self.wait(self.HATCH_NICKNAME_WAIT, stop_event):
                        return True

                    # Shiny check on hatchling
                    frame2 = frame_grabber.get_latest_frame()
                    if frame2 is not None:
                        r, g, b = self.avg_rgb(frame2, x, y, w, h)
                        if (abs(r - br) > tolerance or
                                abs(g - bg) > tolerance or
                                abs(b - bb) > tolerance):
                            # Recheck
                            self.wait(3.0, stop_event)
                            frame3 = frame_grabber.get_latest_frame()
                            if frame3 is not None:
                                r2, g2, b2 = self.avg_rgb(frame3, x, y, w, h)
                                if (abs(r2 - br) > tolerance or
                                        abs(g2 - bg) > tolerance or
                                        abs(b2 - bb) > tolerance):
                                    log(
                                        f"*** SHINY HATCHLING! "
                                        f"R:{r2:.0f} G:{g2:.0f} B:{b2:.0f}  "
                                        f"(baseline R:{br:.0f} G:{bg:.0f} "
                                        f"B:{bb:.0f}) ***"
                                    )
                                    log("Script paused — catch your shiny! "
                                        "Press Stop when done.")
                                    stop_event.wait()
                                    return True

                    # B to dismiss hatchling screen
                    controller.press_b()
                    if not self.wait(self.HATCH_CONFIRM_WAIT, stop_event):
                        return True
                    return True
            time.sleep(0.03)
        return False

    # ── Detection helpers ─────────────────────────────────────────────────────

    def _detect_hatch_text(self, frame) -> bool:
        """
        Detect the hatch text bar: a horizontal strip near the bottom of the
        screen with many consecutive dark pixels (matches the dark dialogue
        box that appears when an egg is about to hatch).
        """
        # Check a thin horizontal strip near bottom of frame (y ~315)
        strip = frame[310:320, 145:395]   # approximate dialogue bar region
        dark = (
            (strip[:, :, 0] < self.HATCH_DARK_THRESHOLD) &
            (strip[:, :, 1] < self.HATCH_DARK_THRESHOLD) &
            (strip[:, :, 2] < self.HATCH_DARK_THRESHOLD)
        )
        dark_count = int(dark.sum())
        if dark_count < self.HATCH_DARK_MIN:
            return False

        # Check for consecutive dark pixels in the strip
        flat = dark.flatten()
        consec = 0
        max_consec = 0
        for v in flat:
            if v:
                consec += 1
                if consec > max_consec:
                    max_consec = consec
            else:
                consec = 0
        return max_consec > self.HATCH_CONSEC_MIN

    def _check_egg_ready(self, frame) -> bool:
        """
        Check whether the Nursery aide's egg-ready icon is visible.
        The C++ checks a small region (~455+left_x, ~260+top_y) for
        a mix of white AND dark pixels simultaneously (the egg icon).
        In the Python port we sample a fixed region of the frame.
        """
        # Region near Nursery aide's head / icon area (right side, mid-height)
        region = frame[255:258, 450:505]
        white = (
            (region[:, :, 0] > self.EGG_WHITE_THRESHOLD) &
            (region[:, :, 1] > self.EGG_WHITE_THRESHOLD) &
            (region[:, :, 2] > self.EGG_WHITE_THRESHOLD)
        )
        dark = (
            (region[:, :, 0] < 120) &
            (region[:, :, 1] < 120) &
            (region[:, :, 2] < 120)
        )
        return (int(white.sum()) > self.EGG_WHITE_MIN and
                int(dark.sum()) > self.EGG_DARK_MIN)

    def _check_hatch_screen(self, frame) -> bool:
        """
        Confirm collection / hatch by checking the summary or party screen
        background (pinkish-red). Matches C++ PCI check: Bave<140, Rave>180.
        Samples a region in the upper-right of the frame.
        """
        region = frame[100:130, 400:450]
        b_avg = float(region[:, :, 0].mean())
        r_avg = float(region[:, :, 2].mean())
        return b_avg < self.HATCH_B_AVE_MAX and r_avg > self.HATCH_R_AVE_MIN

    # ── Fly to Nursery ────────────────────────────────────────────────────────

    def _fly_to_nursery(self, controller, stop_event, total_hatched: int):
        """
        Open map and fly back to Route 5 Nursery.
        Matches flyNursery() in the C++ source.
        The first time (total_hatched < 6) press Down before A to reach
        Town Map; after that the cursor already rests on it.
        """
        controller.press_x()
        if not self.wait(self.FLY_X_WAIT, stop_event): return

        if total_hatched < 6:
            controller.press_down()
            if not self.wait(self.FLY_DOWN_WAIT, stop_event): return

        controller.press_a()
        if not self.wait(self.FLY_A1_WAIT, stop_event): return

        # NE tap to navigate to Route 5 / Nursery marker
        # 'r' = NE tap on the Switch joystick servo
        controller._send('r')
        if not self.wait(self.FLY_NE_WAIT, stop_event): return

        controller.press_a()
        if not self.wait(self.FLY_A2_WAIT, stop_event): return

        controller.press_a()
        if not self.wait(self.FLY_A3_WAIT, stop_event): return

    # ── Calibration helpers ───────────────────────────────────────────────────

    def _calibrate(self, controller, frame_grabber, stop_event,
                   log, request_calibration):
        log("Draw a region over the hatchling's battle/summary sprite.")
        region = request_calibration("Draw region over hatchling sprite")
        if stop_event.is_set():
            return None
        x, y, w, h = region
        time.sleep(0.1)
        frame = frame_grabber.get_latest_frame()
        if frame is None:
            log("No frame — ensure webcam is connected.")
            return None
        r, g, b = self.avg_rgb(frame, x, y, w, h)
        log(f"Baseline — R:{r:.1f}  G:{g:.1f}  B:{b:.1f}")
        return {'region': [x, y, w, h], 'baseline': [r, g, b], 'tolerance': 15}

    def _load_calibration(self):
        path = _cal_path()
        if not os.path.isfile(path):
            return None
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception:
            return None

    def _save_calibration(self, cal):
        with open(_cal_path(), 'w') as f:
            json.dump(cal, f, indent=2)
