"""
USUM Battle Royal BP Farm
Game: Pokemon Ultra Sun / Ultra Moon (3DS)

Repeatedly enters and throws Battle Royal matches to farm Battle Points.
Uses three Pokemon that know Explosion (or Self-Destruct) so each match
ends in one round.

Ported from BattleRoyale_BP_3.0.cpp.

How it works:
  1. Talks to the Battle Royal Dome desk and enters a Normal-rank battle.
  2. Selects all three Pokemon from the party.
  3. Uses Explosion/Self-Destruct with each Pokemon in sequence.
  4. After the battle, declines to save the battle video and collects BP.
  5. Repeats indefinitely.

Setup:
  - Save standing in front of the Battle Royal Dome desk.
  - Have three Pokemon each knowing Explosion or Self-Destruct as their
    first move.
  - Timings assume Normal rank; increase BATTLE_END_WAIT if the script
    presses A before results are shown.
  - Adjust SEND_OUT_WAIT if the send-out screen takes longer.

Notes:
  - The script uses fixed timing in place of the original LDR sensor.
    If battles run long or short, tune the WAIT constants.
  - BP reward per battle is typically 1-3 depending on placement.
"""

import time
from scripts.base_script import BaseScript


class BattleRoyalBPS(BaseScript):
    NAME = "USUM – Battle Royal BP Farm"
    DESCRIPTION = (
        "Automates Battle Royal for BP farming using Explosion "
        "(Ultra Sun/Ultra Moon)."
    )

    # ── Timing (seconds) ─────────────────────────────────────────────────────
    INIT_B_DELAY          = 1.5    # between initial B presses to clear state
    DESK_A_DELAY          = 1.5    # between A presses at the desk
    RANK_A_DELAY          = 1.5    # between A presses to select Normal rank
    RANK_WAIT             = 4.0    # wait after confirming rank
    PARTY_SEL_A_DELAY     = 5.0    # after A to open party selection screen
    USE_PARTY_A_DELAY     = 1.5    # between A presses to select "Use party"
    USE_PARTY_WAIT        = 4.0    # wait after confirming use party
    MON_SELECT_A_DELAY    = 1.5    # between A presses per Pokemon selection
    MON2_NAV_DELAY        = 1.2    # after Right to navigate to second Pokemon
    MON3_L_DELAY          = 1.2    # after Left
    MON3_D_DELAY          = 1.2    # after Down to reach third Pokemon
    CONFIRM_WAIT          = 7.0    # wait after final confirm before entering
    ENTER_A_DELAY         = 35.0   # after A to enter battle (transition time)
    BATTLE_MENU_WAIT      = 50.0   # wait for first battle menu
    PRE_MOVE_WAIT         = 0.5    # brief pause before pressing moves
    MOVE_A_DELAY          = 1.5    # between A presses to select / use move
    BATTLE_END_WAIT       = 90.0   # wait for battle to end after explosion
    SEND_OUT_NAV_DELAY    = 1.0    # after direction press to navigate send-out
    SEND_OUT_A_DELAY      = 1.0    # between A presses to send out next Pokemon
    SEND_OUT_WAIT         = 30.0   # wait for next battle menu after send-out
    RESULTS_WAIT          = 20.0   # wait for battle results screen
    NO_SAVE_B_DELAY       = 2.0    # after B to decline save
    NO_SAVE_A_DELAY       = 6.0    # after A to confirm no-save
    BP_COLLECT_A_DELAY    = 1.5    # between A presses to collect BP
    BP_COLLECT_WAIT       = 3.5    # wait between BP collection A press groups

    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        log("USUM Battle Royal BP Farm started.")
        log("Using Explosion strategy — 3 Pokemon, 1 round each.")

        # Initial B presses to cancel any accidental state from connection
        for _ in range(4):
            if stop_event.is_set(): return
            controller.press_b()
            if not self.wait(self.INIT_B_DELAY, stop_event): return

        bp_total = 0

        while not stop_event.is_set():

            # ── Enter Battle Royal (desk dialogue) ────────────────────────────
            for _ in range(5):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.DESK_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Select Normal rank ────────────────────────────────────────────
            for _ in range(2):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.RANK_A_DELAY, stop_event): break
            if not self.wait(self.RANK_WAIT, stop_event): break

            # ── Confirm party entry ───────────────────────────────────────────
            controller.press_a()
            if not self.wait(self.PARTY_SEL_A_DELAY, stop_event): break

            for _ in range(2):   # "Use Pokemon from party"
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.USE_PARTY_A_DELAY, stop_event): break
            if not self.wait(self.USE_PARTY_WAIT, stop_event): break

            # ── Select first Pokemon ──────────────────────────────────────────
            for _ in range(2):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.MON_SELECT_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Select second Pokemon ─────────────────────────────────────────
            controller.press_right()
            if not self.wait(self.MON2_NAV_DELAY, stop_event): break
            for _ in range(2):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.MON_SELECT_A_DELAY, stop_event): break
            if stop_event.is_set(): break

            # ── Select third Pokemon ──────────────────────────────────────────
            controller.press_left()
            if not self.wait(self.MON3_L_DELAY, stop_event): break
            controller.press_down()
            if not self.wait(self.MON3_D_DELAY, stop_event): break
            for _ in range(3):   # select + confirm
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.MON_SELECT_A_DELAY, stop_event): break
            if not self.wait(self.CONFIRM_WAIT, stop_event): break

            # ── Enter tournament ──────────────────────────────────────────────
            controller.press_a()
            if not self.wait(self.ENTER_A_DELAY, stop_event): break

            # ── Wait for battle menu, use Explosion (first Pokemon) ───────────
            if not self.wait(self.BATTLE_MENU_WAIT, stop_event): break
            if not self.wait(self.PRE_MOVE_WAIT, stop_event): break

            for _ in range(3):   # Fight → select move → confirm
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.MOVE_A_DELAY, stop_event): break
            if not self.wait(self.BATTLE_END_WAIT, stop_event): break

            # ── Send out second Pokemon ───────────────────────────────────────
            controller.press_right()
            if not self.wait(self.SEND_OUT_NAV_DELAY, stop_event): break
            for _ in range(2):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.SEND_OUT_A_DELAY, stop_event): break
            if not self.wait(self.SEND_OUT_WAIT, stop_event): break

            for _ in range(3):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.MOVE_A_DELAY, stop_event): break
            if not self.wait(self.BATTLE_END_WAIT, stop_event): break

            # ── Send out third Pokemon ────────────────────────────────────────
            controller.press_down()
            if not self.wait(self.SEND_OUT_NAV_DELAY, stop_event): break
            for _ in range(2):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.SEND_OUT_A_DELAY, stop_event): break
            if not self.wait(self.SEND_OUT_WAIT, stop_event): break

            for _ in range(3):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.MOVE_A_DELAY, stop_event): break
            if not self.wait(self.BATTLE_END_WAIT, stop_event): break

            # ── Battle results ────────────────────────────────────────────────
            if not self.wait(self.RESULTS_WAIT, stop_event): break

            controller.press_b()   # decline to save battle video
            if not self.wait(self.NO_SAVE_B_DELAY, stop_event): break
            controller.press_a()   # confirm no save
            if not self.wait(self.NO_SAVE_A_DELAY, stop_event): break

            # ── Collect BP ────────────────────────────────────────────────────
            for _ in range(2):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.BP_COLLECT_A_DELAY, stop_event): break
            if not self.wait(self.BP_COLLECT_WAIT, stop_event): break
            for _ in range(2):
                if stop_event.is_set(): break
                controller.press_a()
                if not self.wait(self.BP_COLLECT_A_DELAY, stop_event): break

            bp_total += 1
            log(f"Battle #{bp_total} complete.")

        log("USUM Battle Royal BP Farm stopped.")
