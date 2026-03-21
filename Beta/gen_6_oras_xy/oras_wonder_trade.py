"""
ORAS - Wonder Trade
Game: Pokemon Omega Ruby / Alpha Sapphire (3DS)

Automates Wonder Trade to farm Pokerus, items, or interesting Pokemon.
Sequentially selects Pokemon from the PC box and submits them for Wonder
Trade one at a time.

Ported from ORAS_Wonder_Trade_3.0.cpp.

How it works:
  1. Taps Wonder Trade on the bottom screen (W command).
  2. Presses A to proceed.
  3. Taps Wonder Trade again to open the Pokemon selection.
  4. Navigates to the correct Pokemon in the box (row/column from count).
  5. Presses A × 3 to confirm trade and wait for partner.
  6. Waits for the LDR step-change that indicates the trade completed.
  7. Repeats for TRADE_COUNT trades.

Setup:
  - Set TRADE_COUNT to the number of trades you want to make (0 = unlimited).
  - Stand in front of a Wonder Trade terminal or have it accessible.
  - Have the Pokemon you want to trade lined up in Box 1, Row 1.

Note:
  The C++ version uses the LDR sensor to detect trade completion. This
  Python port uses a fixed wait time (TRADE_WAIT) instead, which is
  reliable for typical connection speeds.
"""

import time
from scripts.base_script import BaseScript


class ORASWonderTrade(BaseScript):
    NAME = "ORAS - Wonder Trade"
    DESCRIPTION = "Automates Wonder Trade for item / Pokemon farming (ORAS)."

    # ── Configuration ─────────────────────────────────────────────────────────
    # Number of trades to perform (0 = run until stopped)
    TRADE_COUNT = 0

    # ── Timing (seconds) — from ORAS_Wonder_Trade_3.0.cpp ───────────────────
    WT_TAP_DELAY    = 2.0   # after W tap (Wonder Trade touch)
    WT_A_DELAY      = 4.0   # after A to proceed
    WT_TAP2_DELAY   = 3.0   # after second W tap (open Pokemon selection)
    NAV_DELAY       = 1.5   # after each D-pad navigation press
    CONFIRM_A_DELAY = 1.5   # after each confirm A press
    PARTNER_WAIT    = 5.0   # wait for connection / searching
    TRADE_WAIT      = 60.0  # max wait for trade to complete
    POST_TRADE_WAIT = 2.0   # after trade before next iteration

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("ORAS - Wonder Trade started.")
        if self.TRADE_COUNT > 0:
            log(f"Trading {self.TRADE_COUNT} Pokemon.")
        else:
            log("Trading until stopped.")

        trade_num = 0

        while not stop_event.is_set():
            if self.TRADE_COUNT > 0 and trade_num >= self.TRADE_COUNT:
                log(f"All {self.TRADE_COUNT} trades completed.")
                break

            log(f"Trade #{trade_num + 1}: initiating Wonder Trade...")

            # ── Tap Wonder Trade ──────────────────────────────────────────
            controller.wonder_trade()
            if not self.wait(self.WT_TAP_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.WT_A_DELAY, stop_event): break

            controller.wonder_trade()
            if not self.wait(self.WT_TAP2_DELAY, stop_event): break

            # ── Navigate to correct Pokemon in box ────────────────────────
            # Every 30 trades: move to next row
            # Every 6 slots: move right to next column; within a row, move right
            # Positions cycle: 0-5 col 0-5, 6-11 col 0-5 row 2, etc.
            if trade_num > 0:
                if (trade_num % 30) == 0:
                    # Move to top-right, then start row 1 of next page
                    controller.press_up()
                    if not self.wait(self.NAV_DELAY, stop_event): break
                    controller.press_right()
                    if not self.wait(self.NAV_DELAY, stop_event): break
                    controller.press_down()
                    if not self.wait(self.NAV_DELAY, stop_event): break

                # Move down for each 6-slot row
                for _ in range((trade_num % 30) // 6):
                    if stop_event.is_set(): break
                    controller.press_down()
                    if not self.wait(self.NAV_DELAY, stop_event): break
                if stop_event.is_set(): break

                # Move right for position within the row
                for _ in range(trade_num % 6):
                    if stop_event.is_set(): break
                    controller.press_right()
                    if not self.wait(self.NAV_DELAY, stop_event): break
                if stop_event.is_set(): break

            # ── Confirm trade ─────────────────────────────────────────────
            for _ in range(3):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.CONFIRM_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Wait for trade to complete ────────────────────────────────
            if not self.wait(self.PARTNER_WAIT, stop_event): break
            if not self.wait(self.TRADE_WAIT - self.PARTNER_WAIT, stop_event): break

            trade_num += 1
            log(f"Trade #{trade_num} complete.")

            if not self.wait(self.POST_TRADE_WAIT, stop_event): break

        log(f"ORAS - Wonder Trade stopped. Total trades: {trade_num}")
