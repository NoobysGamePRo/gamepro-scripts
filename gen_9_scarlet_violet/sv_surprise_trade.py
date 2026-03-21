"""
SV — Surprise Trade
Game: Pokemon Scarlet / Violet (Nintendo Switch)

Automates Surprise Trade in Poke Portal, repeatedly trading Pokemon
for random ones received from other players over the internet.

How it works:
  1. Presses Y to open Poke Portal.
  2. Navigates down to Surprise Trade and presses A.
  3. Selects the first Pokemon in Box 1 (A).
  4. Confirms the trade offer (A).
  5. Waits TRADE_WAIT seconds for a partner to be found and the trade
     to complete automatically in the background.
  6. Presses A to collect the received Pokemon and close the result
     screen.
  7. Closes Poke Portal (B) and repeats.

Setup:
  - Connect to the internet / local wireless in-game before starting.
  - Save with Poke Portal accessible (Y button).
  - Fill Box 1 with the Pokemon you want to trade away; the script
    always picks position 1 (top-left) of the current box.
  - Adjust TRADE_WAIT to the typical time it takes to find a partner
    in your region (default 90 s — increase if trades time out).

Notes:
  - If the Poke Portal layout changes (DLC, updates), adjust
    SURPRISE_TRADE_DOWN_PRESSES to reach the Surprise Trade option.
  - PORTAL_OPEN_DELAY may need increasing on slower hardware.
"""

from scripts.base_script import BaseScript


class SVSurpriseTrade(BaseScript):
    NAME = "SV – Surprise Trade"
    DESCRIPTION = (
        "Automates Surprise Trade for item / Pokemon farming "
        "(Scarlet/Violet)."
    )

    # ── Settings ──────────────────────────────────────────────────────────────
    SURPRISE_TRADE_DOWN_PRESSES = 1   # Down presses from top of Poke Portal menu
                                       # to reach Surprise Trade

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    PORTAL_OPEN_DELAY     = 2.0   # after Y, before menu is ready
    PORTAL_NAV_DELAY      = 0.8   # between Down presses in Poke Portal menu
    SURPRISE_OPEN_DELAY   = 2.0   # after A on Surprise Trade
    BOX_OPEN_DELAY        = 2.0   # after Box opens
    SELECT_MON_DELAY      = 1.5   # after A to select Pokemon
    CONFIRM_DELAY         = 1.5   # after A to confirm trade offer
    TRADE_WAIT            = 90.0  # wait for partner + trade animations
    COLLECT_A_DELAY       = 1.5   # between A presses to collect / close screens
    PORTAL_CLOSE_B_DELAY  = 1.5   # between B presses to close portal

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("SV Surprise Trade started.")
        log(
            f"Trading indefinitely. TRADE_WAIT = {self.TRADE_WAIT}s. "
            "Press ■ Stop at any time."
        )

        trade_count = 0

        while not stop_event.is_set():

            # ── Open Poke Portal ──────────────────────────────────────────────
            controller.press_y()
            if not self.wait(self.PORTAL_OPEN_DELAY, stop_event): break

            # ── Navigate to Surprise Trade ────────────────────────────────────
            for _ in range(self.SURPRISE_TRADE_DOWN_PRESSES):
                if stop_event.is_set(): break
                controller.press_down()
                if not self.wait(self.PORTAL_NAV_DELAY, stop_event): break
            if stop_event.is_set(): break

            controller.press_a()                  # open Surprise Trade
            if not self.wait(self.SURPRISE_OPEN_DELAY, stop_event): break

            # ── Open box and select first Pokemon ─────────────────────────────
            if not self.wait(self.BOX_OPEN_DELAY, stop_event): break
            controller.press_a()                  # select first Pokemon (Box 1 pos 1)
            if not self.wait(self.SELECT_MON_DELAY, stop_event): break

            # ── Confirm trade offer ───────────────────────────────────────────
            controller.press_a()                  # "Offer this Pokemon?"
            if not self.wait(self.CONFIRM_DELAY, stop_event): break
            controller.press_a()                  # confirm
            if not self.wait(self.CONFIRM_DELAY, stop_event): break

            # ── Wait for trade to complete ────────────────────────────────────
            log(
                f"Trade #{trade_count + 1} offered. "
                f"Waiting up to {self.TRADE_WAIT}s for partner..."
            )
            if not self.wait(self.TRADE_WAIT, stop_event): break

            # ── Collect received Pokemon ──────────────────────────────────────
            for _ in range(4):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.COLLECT_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Close Poke Portal ─────────────────────────────────────────────
            for _ in range(2):
                if stop_event.is_set(): break
                controller.press_b()
                if not self.wait(self.PORTAL_CLOSE_B_DELAY, stop_event): break
            if stop_event.is_set(): break

            trade_count += 1
            log(f"Trade #{trade_count} complete.")

        log("SV Surprise Trade stopped.")
