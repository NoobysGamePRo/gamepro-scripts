"""
FRLG Breeding — Switch / Switch 2 (NSO GBA), Four Island day care

Breeds the Magikarp line at the Four Island day care and keeps the eggs you want:
  • IV mode    – each hatchling's IVs and nature are worked out with Rare Candies (the game is then
                 reset so the candies come back). Babies that meet your target go to the KEEP box,
                 babies that improve the parents are swapped into the day care, the rest are released.
  • Shiny mode – hatch and release; the shiny star is checked before every release, a shiny is kept.

Before you start
  Party:  slot 1 = any Pokémon (not an egg). Slots 2-6 EMPTY (eggs and hatchlings go there).
  Bag:    BICYCLE registered to Y.  IV mode: RARE CANDY must be the FIRST item in the ITEMS pocket
          (any number; 20+ is quicker. They are never used up - the game is reset).
  Day care: a male and a female from the Magikarp line (Magikarp / Gyarados) are in the day care.
  PC:     the OLD-PARENT box and the KEEP box (set below) must have free space.
  Game:   SAVE the game, then stand ON FOOT, OUTDOORS, in front of the old man outside the day care.
  Text speed FAST is recommended.  IV mode uses SR1 (HOME) to close and restart the game.

When the script starts, click the 4 corners of the game picture (inside the black border) while
the game is on an outdoor screen.

Safety: Pokémon are only ever released from the DEPOSIT party view (boxes are never shown).
Keepers, shinies and parents leave the party before any release, and each release needs the
summary to show a Lv5 MAGIKARP with no shiny star and the same gender and nature the script
recorded for that hatchling.  The script stops if the party is not what it expects.
A replaced parent is released only if this script bred it, it was not a keeper, and its summary
still shows the gender and nature recorded when it hatched (and "Hatched: FOUR ISLAND").
"""

import os
import sys

from scripts.base_script import BaseScript

_NATURES = ['Hardy', 'Lonely', 'Brave', 'Adamant', 'Naughty', 'Bold', 'Docile', 'Relaxed', 'Impish',
            'Lax', 'Timid', 'Hasty', 'Serious', 'Jolly', 'Naive', 'Modest', 'Mild', 'Quiet',
            'Bashful', 'Rash', 'Calm', 'Gentle', 'Sassy', 'Careful', 'Quirky']
_STATS = [('HP', 'hp'), ('Atk', 'atk'), ('Def', 'def'), ('SpA', 'spa'), ('SpD', 'spd'), ('Spe', 'spe')]
_MODE_IV, _MODE_SHINY = 'IV breeding (Rare Candy check)', 'Shiny only'
_IV_ONLY = ('mode', [_MODE_IV])
_OLD_RELEASE, _OLD_BOX = 'Release (bred by the script, not keepers)', 'Put in the old-parent box'
_SIM = {}                     # estimate cache: (mins, natures) -> eggs


def _pkg():
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import _frlg_breeding.core as core
    return core


class FrlgBreeding(BaseScript):
    NAME = 'FRLG Breeding (Magikarp)'
    DESCRIPTION = ('Four Island day care: breeds for chosen IVs / nature (Rare Candy check + reset) '
                   'or shinies, improving the parents as it goes. Start on foot in front of the '
                   'day care man.')

    SETTINGS = [
        {'type': 'section', 'label': 'What to breed for'},
        {'key': 'mode', 'type': 'choice', 'label': 'Mode', 'choices': [_MODE_IV, _MODE_SHINY],
         'default': _MODE_IV,
         'help': 'Shiny only skips the IV check (no Rare Candies, no resets) and is much faster per egg.'},
        {'type': 'section', 'label': 'Keeper IVs  (minimum per stat, 0 = don\'t care)', 'show_if': _IV_ONLY},
    ] + [
        {'key': 'min_' + k, 'type': 'int', 'label': 'Minimum ' + s, 'min': 0, 'max': 31,
         'default': {'hp': 31, 'atk': 31, 'def': 20, 'spa': 0, 'spd': 20, 'spe': 31}[k],
         'show_if': _IV_ONLY}
        for s, k in _STATS
    ] + [
        {'key': 'natures', 'type': 'multi', 'label': 'Keeper natures (none selected = any)',
         'choices': _NATURES, 'default': ['Adamant', 'Jolly'], 'show_if': _IV_ONLY,
         'help': 'Natures are not passed on to eggs in FireRed/LeafGreen, so each one you allow '
                 'helps a lot.'},
        {'type': 'section', 'label': 'Game setup'},
        {'key': 'old_parents', 'type': 'choice', 'label': 'Replaced parents',
         'choices': [_OLD_RELEASE, _OLD_BOX], 'default': _OLD_RELEASE, 'show_if': _IV_ONLY,
         'help': 'Only parents this script bred and swapped in are ever released (and never one '
                 'that was a keeper - those go to the keep box). The parents you put in the day '
                 'care yourself always go to the old-parent box.'},
        {'key': 'old_box', 'type': 'int', 'label': 'PC box for old parents', 'min': 1, 'max': 14,
         'default': 5, 'show_if': _IV_ONLY},
        {'key': 'keep_box', 'type': 'int', 'label': 'PC box for keepers / shinies', 'min': 1,
         'max': 14, 'default': 6},
        {'key': 'shiny_action', 'type': 'choice', 'label': 'When a shiny hatches',
         'choices': ['Stop with it in the party', 'Put it in the keep box and carry on'],
         'default': 'Stop with it in the party'},
        {'key': 'max_batches', 'type': 'int', 'label': 'Stop after this many batches (5 eggs each)',
         'min': 1, 'max': 5000, 'default': 500},
        {'key': 'fresh', 'type': 'bool', 'label': 'New parents in the day care',
         'default': False, 'show_if': _IV_ONLY,
         'help': 'Tick if you changed the day care parents yourself since the last run - the '
                 'script then forgets the parents\' IVs it learned before.'},
    ]

    # ── Estimate shown in the settings dialog ───────────────────────────
    @staticmethod
    def estimate(v):
        if v.get('mode') == _MODE_SHINY:
            return ('Shiny odds 1 in 8,192 eggs (FRLG has no Shiny Charm or Masuda method).\n'
                    'At roughly 12 eggs an hour that is ~680 hours on average.')
        core = _pkg()
        t = core.target
        mins = {s: (v.get('min_' + k) or None) for s, k in _STATS}
        t.configure(mins, [n.upper() for n in v.get('natures') or []])
        nat = len(t.NATURES) / 25 if t.NATURES else 1.0
        rnd = t.p_pair(core.UNKNOWN, core.UNKNOWN)
        best = [[31] if m else list(range(32)) for m in t.MINS]
        ideal = t.p_pair(best, best)
        lines = []
        if ideal <= 0:
            return 'This target cannot be met.'
        st = core.load_state(bool(v.get('fresh')))
        cur = t.p_pair(st['parents']['M']['ivs'], st['parents']['F']['ivs'])
        def eggs(p):
            return 'never (until a parent improves)' if p <= 0 else '~{:,.0f} eggs'.format(1 / (p * nat))
        key = (tuple(t.MINS), tuple(sorted(t.NATURES)))
        if key not in _SIM:
            _SIM[key] = t.simulate_from_scratch(time_budget=0.8, seed=1)[0]
        sim = _SIM[key]
        lines.append('Average eggs per keeper (IVs + nature), about 8-9 eggs an hour:')
        if sim:
            lines.append('  starting from wild parents, improving them as it goes: ~{:,.0f} eggs '
                         '(~{:,.0f} h)'.format(sim, sim / 8.5))
        if st['parents']['M']['ivs'] != core.UNKNOWN or st['parents']['F']['ivs'] != core.UNKNOWN:
            lines.append('  with your current parents, if they never improved: %s' % eggs(cur))
        lines.append('  once both parents meet the target: %s' % eggs(ideal))
        return '\n'.join(lines)

    # ════════════════════════════════════════════════════════════════════
    def run(self, controller, frame_grabber, stop_event, log, request_calibration):
        v = dict((e['key'], e.get('default')) for e in self.SETTINGS if 'key' in e)
        v.update(getattr(self, 'settings', None) or {})
        if not getattr(self, 'settings', None):
            log('(This GamePRo version has no settings window - using the default settings. '
                'Update GamePRo to choose your own target.)')
        log('FRLG Breeding started: %s.' % v['mode'])
        core = _pkg()
        from _frlg_breeding import gpc, fr
        for attempt in range(3):
            try:
                controller.press_b()        # wakes a Switch screen dimmed after sitting idle
            except Exception:
                pass
            stop_event.wait(1.5)
            log('Click the 4 corners of the GAME picture (inside the black border). The game must '
                'be outdoors with no menu or message open.')
            warp = request_calibration('Click the 4 corners of the GBA game picture', mode='corners')
            if stop_event.is_set() or warp is None:
                log('Script stopped.')
                return
            gpc.set_backend(controller, frame_grabber, stop_event, warp)
            try:
                if gpc.recalibrate():       # the whole lit game picture is where it should be
                    break
            except gpc.Stopped:
                log('Script stopped.')
                return
            log('Those corners do not match the game picture - close any menu, stand outdoors '
                'and click the corners again (exactly on the edge of the picture).')
        else:
            log('Could not line up the game picture - script stopped.')
            return
        detail_file = open(gpc.WORK + 'run.log', 'a', encoding='utf-8')

        def log_filtered(msg):
            # everything goes to run.log; per-level readings stay out of the GamePRo log window
            import time as _t
            detail_file.write(_t.strftime('%Y-%m-%d %H:%M:%S ') + msg + '\n')
            detail_file.flush()
            if not msg.startswith(('Lv ', '   ', 'gender ', 'hatched after', 'egg received')):
                log(msg)
        fr.LOG_FN[0] = log_filtered
        core.BIKE['on'] = False
        cfg = {'mode': 'iv' if v['mode'] == _MODE_IV else 'shiny', 'old_box': int(v['old_box']),
               'keep_box': int(v['keep_box']),
               'shiny_action': 'stop' if v['shiny_action'].startswith('Stop') else 'box',
               'old_parents': 'box' if v.get('old_parents') == _OLD_BOX else 'release'}
        mins = {s: (int(v['min_' + k]) or None) for s, k in _STATS}
        natures = [n.upper() for n in v.get('natures') or []]
        if cfg['mode'] == 'iv':
            want = ', '.join('%s %s' % (s, '31' if m == 31 else '>= %d' % m)
                             for s, m in mins.items() if m) or 'any IVs'
            log('Keeper target: %s; nature: %s.' % (want, ', '.join(natures) or 'any'))
        result = 'stopped'
        try:
            result = core.main(cfg, mins, natures, bool(v.get('fresh')), int(v['max_batches']))
        except gpc.Stopped:
            pass
        finally:
            fr.LOG_FN[0] = None
            detail_file.close()
            try:
                controller.release_all()
            except Exception:
                pass
            if result == 'done':
                log('Finished %d batches - the game is saved.' % int(v['max_batches']))
            else:
                log('Script stopped. Progress is saved - to carry on, close any menu, walk OUTSIDE '
                    'on foot (in front of the day care man) and run the script again. Do not save '
                    'or reset the game yourself.')
