"""
Sun / Moon — SOS Chaining
Game: Pokemon Sun / Moon / Ultra Sun / Ultra Moon (3DS)

Automates SOS chaining to raise shiny odds. Each turn the script uses
an Adrenaline Orb (from the Bag) to keep the call rate high, then
KOs any ally that appears, checks it for shiny, and repeats.

Detection: avg_rgb comparison on the ally Pokemon's sprite region.

How it works:
  1. On each player turn: opens Bag → uses Adrenaline Orb on player.
  2. After the turn's animations settle, checks the ally sprite region
     via avg_rgb against the calibrated baseline.
  3. If ally colours differ by more than ±COLOUR_TOLERANCE: suspected
     shiny — waits SHINY_RECHECK then confirms. Script pauses.
  4. If not shiny (or no ally): uses the configured attack move to KO
     the ally (or the original if no ally called — False Swipe keeps
     it alive at 1 HP).
  5. Repeats indefinitely until a shiny is found or Stop is pressed.

Setup:
  - Start inside a battle with the target Pokemon already at 1 HP and
    Adrenaline Orb active (or let the script apply the first orb).
  - Party lead should know:
      Move slot 1 = False Swipe (keeps target at 1 HP)
      Move slot 2 = attack to KO the ally
  - Adrenaline Orb must be the FIRST item in the Bag's Items pocket.
  - On first run, the script applies one Adrenaline Orb and asks you
    to draw a region over the ally Pokemon's sprite.
  - Calibration saved to calibration/sos_chaining.json.
  - Delete that file to recalibrate.

Notes:
  - ATTACK_MOVE_SLOT: slot 1 = top-left, 2 = top-right,
    3 = bottom-left, 4 = bottom-right.
  - Increase TURN_ANIMATION_WAIT if animations run slowly.
  - The chain count is not tracked by the game if the lead Pokemon
    faints — ensure it survives.
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
    return os.path.join(cal_dir, 'sos_chaining.json')


# Move slot → (right_presses, down_presses) from top-left of move grid
_MOVE_NAV = {1: (0, 0), 2: (1, 0), 3: (0, 1), 4: (1, 1)}


class SOSChaining(BaseScript):
    NAME = "Sun / Moon – SOS Chaining"
    DESCRIPTION = (
        "Chains SOS calls to raise shiny odds in Sun/Moon/USUM."
    )

    # ── Settings ──────────────────────────────────────────────────────────────
    ATTACK_MOVE_SLOT = 2    # move slot to KO the ally (1–4)

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    BAG_OPEN_DELAY        = 1.5   # after opening Bag (right from Fight)
    ITEM_SELECT_DELAY     = 1.0   # after navigating to / selecting item
    ITEM_USE_TARGET_DELAY = 1.5   # after choosing self as target
    TURN_ANIMATION_WAIT   = 6.0   # wait for turn animations to settle
    FIGHT_MENU_DELAY      = 1.0   # after pressing A to open Fight menu
    MOVE_NAV_DELAY        = 0.5   # between directional presses in move grid
    MOVE_CONFIRM_DELAY    = 1.0   # after selecting move
    ATTACK_ANIMATION_WAIT = 5.0   # wait for KO animation
    SHINY_RECHECK_WAIT    = 3.0   # recheck delay before confirming shiny

    COLOUR_TOLERANCE = 20

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("Sun/Moon SOS Chaining started.")
        log(f"Attack move slot: {self.ATTACK_MOVE_SLOT}.")

        cal = self._load_calibration()
        if cal is None:
            log("No calibration — applying Adrenaline Orb and calibrating ally region.")
            cal = self._calibrate(
                controller, frame_grabber, stop_event, log, request_calibration
            )
            if stop_event.is_set() or cal is None:
                return
            self._save_calibration(cal)
            log("Calibration saved.")
        else:
            log(f"Calibration loaded from {_cal_path()}")

        rx, ry, rw, rh = cal['region']
        br, bg, bb = cal['baseline']
        tol = cal.get('tolerance', self.COLOUR_TOLERANCE)
        chain_count = 0

        log(f"SOS chain loop running. Tolerance ±{tol}. Press ■ Stop at any time.")

        while not stop_event.is_set():

            # ── Use Adrenaline Orb (keeps SOS call rate high) ─────────────────
            if not self._use_adrenaline_orb(controller, stop_event):
                break

            # ── Wait for turn animations ──────────────────────────────────────
            if not self.wait(self.TURN_ANIMATION_WAIT, stop_event):
                break

            # ── Check ally sprite for shiny ───────────────────────────────────
            frame = frame_grabber.get_latest_frame()
            shiny_found = False

            if frame is not None:
                r, g, b = self.avg_rgb(frame, rx, ry, rw, rh)
                log(
                    f"Chain #{chain_count + 1}: ally "
                    f"R:{r:.0f} G:{g:.0f} B:{b:.0f}  "
                    f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f})"
                )

                if (abs(r - br) > tol or abs(g - bg) > tol or abs(b - bb) > tol):
                    if not self.wait(self.SHINY_RECHECK_WAIT, stop_event):
                        break
                    frame2 = frame_grabber.get_latest_frame()
                    if frame2 is not None:
                        r2, g2, b2 = self.avg_rgb(frame2, rx, ry, rw, rh)
                        if (abs(r2 - br) > tol or
                                abs(g2 - bg) > tol or
                                abs(b2 - bb) > tol):
                            log(
                                f"*** SHINY ALLY! "
                                f"R:{r2:.0f} G:{g2:.0f} B:{b2:.0f}  "
                                f"(baseline R:{br:.0f} G:{bg:.0f} B:{bb:.0f}) ***"
                            )
                            log(f"Chain length before shiny: {chain_count}")
                            shiny_found = True

            if stop_event.is_set():
                break

            if shiny_found:
                log("Script paused — catch your shiny! Press ■ Stop when done.")
                stop_event.wait()
                break

            # ── KO the ally (attack move) ─────────────────────────────────────
            if not self._use_attack_move(controller, stop_event):
                break

            if not self.wait(self.ATTACK_ANIMATION_WAIT, stop_event):
                break

            chain_count += 1
            log(f"Chain count: {chain_count}.")

        log("Sun/Moon SOS Chaining stopped.")

    # ── Battle actions ─────────────────────────────────────────────────────────

    def _use_adrenaline_orb(self, controller, stop_event) -> bool:
        """Open Bag (right from Fight) → select first item → use on self."""
        controller.press_right()                     # Fight → Bag
        if not self.wait(self.BAG_OPEN_DELAY, stop_event): return False
        controller.press_a()                         # open Items pocket
        if not self.wait(self.ITEM_SELECT_DELAY, stop_event): return False
        controller.press_a()                         # select first item (Adrenaline Orb)
        if not self.wait(self.ITEM_SELECT_DELAY, stop_event): return False
        controller.press_a()                         # use → auto-selects player
        if not self.wait(self.ITEM_USE_TARGET_DELAY, stop_event): return False
        return True

    def _use_attack_move(self, controller, stop_event) -> bool:
        """Open Fight menu and select the configured attack move slot."""
        right_presses, down_presses = _MOVE_NAV.get(
            self.ATTACK_MOVE_SLOT, (0, 0)
        )
        controller.press_a()                         # open Fight menu
        if not self.wait(self.FIGHT_MENU_DELAY, stop_event): return False

        for _ in range(right_presses):
            if stop_event.is_set(): return False
            controller.press_right()
            if not self.wait(self.MOVE_NAV_DELAY, stop_event): return False

        for _ in range(down_presses):
            if stop_event.is_set(): return False
            controller.press_down()
            if not self.wait(self.MOVE_NAV_DELAY, stop_event): return False

        controller.press_a()                         # select move
        if not self.wait(self.MOVE_CONFIRM_DELAY, stop_event): return False
        controller.press_a()                         # confirm (target ally)
        if not self.wait(self.MOVE_CONFIRM_DELAY, stop_event): return False
        return True

    # ── Calibration ───────────────────────────────────────────────────────────

    def _calibrate(self, controller, frame_grabber, stop_event,
                   log, request_calibration):
        """Apply one Adrenaline Orb then let user draw the ally sprite region."""
        log("Applying first Adrenaline Orb — wait for turn to complete...")
        if not self._use_adrenaline_orb(controller, stop_event):
            return None
        if not self.wait(self.TURN_ANIMATION_WAIT, stop_event):
            return None

        log("Ally Pokemon should be on screen. Draw a region over its sprite.")
        region = request_calibration("Draw region over the ally Pokemon's sprite")
        if stop_event.is_set():
            return None

        time.sleep(0.1)
        frame = frame_grabber.get_latest_frame()
        if frame is None:
            log("No frame — ensure webcam is connected.")
            return None

        rx, ry, rw, rh = region
        r, g, b = self.avg_rgb(frame, rx, ry, rw, rh)
        log(f"Baseline — R:{r:.1f}  G:{g:.1f}  B:{b:.1f}")
        log("Calibration complete. Default tolerance ±20 applied.")
        return {
            'region': [rx, ry, rw, rh],
            'baseline': [r, g, b],
            'tolerance': self.COLOUR_TOLERANCE,
        }

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
