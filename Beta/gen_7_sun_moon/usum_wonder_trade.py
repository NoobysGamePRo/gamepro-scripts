"""
USUM - Wonder Trade
Game: Pokemon Ultra Sun / Ultra Moon (3DS)

Automates Wonder Trade to farm Pokemon, items, or Pokerus.
Sequentially trades Pokemon from the PC Box and waits for each
trade to complete before moving on.

Ported from SuMo_Wondertrade_2.0.cpp (also used for USUM).

How it works:
  1. Taps Wonder Trade on the bottom screen (W command × 2).
  2. Presses A to proceed through menus.
  3. A × 2 to select Pokemon and confirm.
  4. A to say Yes.
  5. Waits a fixed time for the trade to complete.
  6. Repeats for TRADE_COUNT trades (0 = unlimited).

Setup:
  - Stand at a Wonder Trade terminal or have it accessible via menu.
  - Have the Pokemon you want to trade ready in Box 1, Row 1.
  - Set TRADE_COUNT to 0 for unlimited trades.
"""

import time
from scripts.base_script import BaseScript


class USUMWonderTrade(BaseScript):
    NAME = "USUM - Wonder Trade"
    DESCRIPTION = "Automates Wonder Trade for item / Pokemon farming (Ultra Sun/Ultra Moon)."

    # ── Configuration ─────────────────────────────────────────────────────────
    # Number of trades to perform (0 = run until stopped)
    TRADE_COUNT = 0

    # ── Timing (seconds) — from SuMo_Wondertrade_2.0.cpp ────────────────────
    WT_TAP_1_DELAY  = 1.5   # after first W tap
    WT_TAP_2_DELAY  = 3.0   # after second W tap (open Pokemon selection)
    WT_A_1_DELAY    = 3.0   # after A to proceed
    WT_A_2_DELAY    = 1.5   # after A to select Pokemon
    WT_A_3_DELAY    = 1.5   # after A to select trade
    WT_YES_DELAY    = 5.0   # after A to say Yes (searching for partner)
    TRADE_WAIT      = 60.0  # max wait for trade to complete
    POST_TRADE_WAIT = 2.0   # brief pause after trade before next iteration

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("USUM - Wonder Trade started.")
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

            # ── Tap Wonder Trade × 2 ──────────────────────────────────────
            controller.wonder_trade()
            if not self.wait(self.WT_TAP_1_DELAY, stop_event): break

            controller.wonder_trade()
            if not self.wait(self.WT_TAP_2_DELAY, stop_event): break

            # ── Proceed through menus ─────────────────────────────────────
            controller.press_a()
            if not self.wait(self.WT_A_1_DELAY, stop_event): break

            # ── Select Pokemon and confirm ────────────────────────────────
            controller.press_a()
            if not self.wait(self.WT_A_2_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.WT_A_3_DELAY, stop_event): break

            controller.press_a()
            if not self.wait(self.WT_YES_DELAY, stop_event): break

            # ── Wait for trade to complete ────────────────────────────────
            if not self.wait(self.TRADE_WAIT - self.WT_YES_DELAY, stop_event): break

            trade_num += 1
            log(f"Trade #{trade_num} complete.")

            if not self.wait(self.POST_TRADE_WAIT, stop_event): break

        log(f"USUM - Wonder Trade stopped. Total trades: {trade_num}")
