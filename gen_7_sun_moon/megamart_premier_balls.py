"""
USUM Megamart — Premier Ball Farm
Game: Pokemon Ultra Sun / Ultra Moon (3DS)

Repeatedly buys 10 Poke Balls from the Hau'oli City Megamart to receive
1 free Premier Ball each time, farming Premier Balls indefinitely.

How it works:
  1. Talks to the Megamart clerk and opens the Buy menu.
  2. Selects Poke Ball from the item list.
  3. Sets quantity to 10 (Up × 9 from the default of 1).
  4. Confirms the purchase and collects the Premier Ball bonus.
  5. Closes the shop and repeats.

Setup:
  - Save standing directly in front of the Poke Ball counter clerk
    at the Megamart in Hau'oli City.
  - Ensure you have enough Poke Dollars for repeated 10-ball purchases
    (200 per run at ₽20 each).
  - Make sure Poke Ball is the first item in the shop's item list.

Notes:
  - If the shop list is sorted differently, set POKEBALL_DOWN_PRESSES
    to the number of Down presses needed to reach Poke Ball.
  - Increase timing constants if the game is slower than expected.
"""

from scripts.base_script import BaseScript


class MegamartPremierBalls(BaseScript):
    NAME = "USUM – Megamart Premier Balls"
    DESCRIPTION = (
        "Farms Premier Balls by buying 10 Poke Balls per run at the "
        "Megamart (Ultra Sun/Ultra Moon)."
    )

    # ── Settings ──────────────────────────────────────────────────────────────
    POKEBALL_DOWN_PRESSES = 0    # Down presses to reach Poke Ball in shop list
    BALLS_PER_RUN         = 10   # Must be 10 to receive 1 Premier Ball bonus

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    TALK_A_DELAY          = 1.5  # between A presses to open shop / choose Buy
    SHOP_OPEN_DELAY       = 1.5  # after Buy is selected, before item list
    ITEM_NAV_DELAY        = 0.5  # between Down presses to navigate item list
    ITEM_SELECT_DELAY     = 1.0  # after A to select item, before qty screen
    QTY_UP_DELAY          = 0.3  # between Up presses to increase quantity
    QTY_CONFIRM_DELAY     = 1.0  # after A to confirm quantity
    PURCHASE_CONFIRM_DELAY= 1.5  # after A to confirm purchase (Yes)
    COLLECT_A_DELAY       = 1.5  # between A presses to close receipt screens
    SHOP_CLOSE_B_DELAY    = 1.5  # between B presses to exit shop menu

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("USUM Megamart Premier Ball Farm started.")
        log(
            f"Buying {self.BALLS_PER_RUN} Poke Balls per run "
            f"(1 Premier Ball bonus per run)."
        )

        run_count = 0

        while not stop_event.is_set():

            # ── Talk to clerk → Buy ───────────────────────────────────────────
            controller.press_a()              # talk to clerk
            if not self.wait(self.TALK_A_DELAY, stop_event): break
            controller.press_a()              # select "Buy"
            if not self.wait(self.SHOP_OPEN_DELAY, stop_event): break

            # ── Navigate to Poke Ball in item list ────────────────────────────
            for _ in range(self.POKEBALL_DOWN_PRESSES):
                if stop_event.is_set(): break
                controller.press_down()
                if not self.wait(self.ITEM_NAV_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Select Poke Ball ──────────────────────────────────────────────
            controller.press_a()
            if not self.wait(self.ITEM_SELECT_DELAY, stop_event): break

            # ── Set quantity to BALLS_PER_RUN (start at 1, press Up N-1 times)
            for _ in range(self.BALLS_PER_RUN - 1):
                if stop_event.is_set(): break
                controller.press_up()
                if not self.wait(self.QTY_UP_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Confirm quantity ──────────────────────────────────────────────
            controller.press_a()
            if not self.wait(self.QTY_CONFIRM_DELAY, stop_event): break

            # ── Confirm purchase ("Yes, please") ──────────────────────────────
            controller.press_a()
            if not self.wait(self.PURCHASE_CONFIRM_DELAY, stop_event): break

            # ── Collect / close receipt screens ───────────────────────────────
            for _ in range(3):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.COLLECT_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Close shop menu (back to overworld) ───────────────────────────
            for _ in range(2):
                if stop_event.is_set(): break
                controller.press_b()
                if not self.wait(self.SHOP_CLOSE_B_DELAY, stop_event): break
            if stop_event.is_set(): break

            run_count += 1
            log(
                f"Run #{run_count} complete — "
                f"{self.BALLS_PER_RUN} Poke Balls purchased, 1 Premier Ball earned. "
                f"Total: {run_count} Premier Balls."
            )

        log("USUM Megamart Premier Ball Farm stopped.")
