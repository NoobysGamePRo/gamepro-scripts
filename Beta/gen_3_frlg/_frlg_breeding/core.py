"""FRLG breeding loop (Four Island day care), driven by the settings chosen in GamePRo.

IV mode, per batch:
    collect eggs until the party is full (riding the lane; eggs hatch on the way) -> SAVE
    -> level each hatchling with Rare Candies just until it is known whether it is a keeper and
       whether it improves the parents (reset whenever candies run low)
    -> RESET (babies back to Lv5, candies back)
    -> keepers / shinies -> KEEP box, best improvement -> swapped in at the day care lady (old
       parent -> OLD-PARENT box): everything worth keeping has left the party BEFORE any release.
       Then the rest are released at the day care PC -> SAVE -> next batch.
Release safety: the party on screen must match the state file (count), and each release needs the
    summary to show a Lv5 MAGIKARP, no shiny star, and the same gender + nature line that was
    recorded when that hatchling was first checked.
Rare Candies: the item is checked by name before every use and the bag count is read, so any
    stock works (fewer candies = more resets).
Shiny mode, per batch: collect + hatch -> release each hatchling; the PC summary is checked for
    the shiny star right before every release and a shiny is never released -> SAVE.
Swap rule (rule D): a baby replaces its same-gender parent if the pair's chance of an egg meeting
the IV target goes up; tie -> the baby with more 31s.
State (party layout + parents' IVs) is kept in WORK/breed_state.json so a stopped run resumes.
"""
import json, os, time
import cv2
from .gpc import run, frame, WORK, recalibrate
from .fr import log, save_game
from .daycare_nav import go_to_man, go_to_lady, leave_daycare
from .evalbaby import evaluate, summary_check, party_count
from .reset import reset_game
from . import target, release, lady
from . import egg_explore_lib as eg

STATE = WORK + 'breed_state.json'
RESULTS = WORK + 'breed_log.jsonl'
STATS = ['HP', 'Atk', 'Def', 'SpA', 'SpD', 'Spe']
UNKNOWN = [list(range(32)) for _ in range(6)]

CFG = {'mode': 'iv', 'old_box': 5, 'keep_box': 6, 'shiny_action': 'stop', 'old_parents': 'release'}
MIN_LEFT = 20                       # reset before a baby if fewer candies are left (or fewer than
                                    # the whole bag holds, for small stocks)


# ── State ───────────────────────────────────────────────────────────────────
def new_state():
    return {'parents': {g: {'species': 'MAGIKARP', 'perfect': [], 'ivs': UNKNOWN} for g in 'MF'},
            'party': ['LEAD'], 'rec': [None], 'batches': 0, 'eggs': 0}


def load_state(fresh=False):
    if not fresh and os.path.exists(STATE):
        try:
            st = json.load(open(STATE))
            for g in 'MF':
                st['parents'][g].setdefault('ivs', UNKNOWN)
            st.setdefault('batches', 0)
            st.setdefault('eggs', 0)
            if len(st.get('rec') or []) != len(st['party']):
                st['rec'] = [None] * len(st['party'])     # unknown -> those babies are re-checked
            return st
        except Exception:
            pass
    return new_state()


def save_state(st):
    json.dump(st, open(STATE, 'w'), indent=1)


# party list helpers: st['rec'] runs alongside st['party'] (identity record of each hatchling)
def p_add(st, tag):
    st['party'].append(tag); st['rec'].append(None)


def p_pop(st, i):
    st['party'].pop(i); st['rec'].pop(i)


def p_record(st, slot, gender, img):
    path = WORK + 'rec_%d_%d.png' % (st['eggs'], slot)
    cv2.imwrite(path, img)
    st['rec'][slot - 1] = {'g': gender, 'img': path}


def p_rec(st, slot):
    r = st['rec'][slot - 1]
    if not r or not os.path.exists(r['img']):
        return None
    return {'g': r['g'], 'img': cv2.imread(r['img'])}


def perfects(res):
    return sorted(i for i, v in enumerate(res['verdict']) if v == '31')


def parent_ivs(st):
    return {g: st['parents'][g]['ivs'] for g in ('M', 'F')}


def describe(ivs):
    def one(s):
        return str(s[0]) if len(s) == 1 else ('?' if len(s) == 32 else f'{min(s)}-{max(s)}')
    return ' '.join(f'{STATS[i]} {one(s)}' for i, s in enumerate(ivs))


def odds_line(st):
    pv = parent_ivs(st)
    p = target.p_pair(pv['M'], pv['F'])
    nat = len(target.NATURES) / 25 if target.NATURES else 1.0
    if p <= 0:
        return 'current parents: target IVs impossible until a parent improves'
    return ('current parents: 1 egg in ~%.0f meets the IV target, ~%.0f with the nature; '
            '%.0f%% of eggs have 3+ perfect IVs' % (1 / p, 1 / (p * nat), 100 * target.p_perfect(pv['M'], pv['F'])))


# ── Rule D ──────────────────────────────────────────────────────────────────
def gain(res, st):
    g = res['gender']
    if g not in ('M', 'F'):
        return None
    pv = parent_ivs(st)
    ok, p_new, p_old = target.swap_status([set(x) for x in res['ivs']], pv[g],
                                          pv['F' if g == 'M' else 'M'])
    return (p_new, len(perfects(res))) if ok == 'yes' else None


def decided(st):
    pv = parent_ivs(st)

    def fn(readings, natures, sets, gender):
        k, s = target.decide(readings, natures, sets, gender, pv)
        # >= 2 readings: one misread that still fits a nature must not throw a good baby away
        return len(readings) >= 2 and k != 'maybe' and s != 'maybe'
    return fn


# ── Movement / PC ───────────────────────────────────────────────────────────
BIKE = {'on': False}


def bike(on):
    if BIKE['on'] != on:
        run(['y', 'w0.9'])
        BIKE['on'] = on


def collect_and_hatch(st, eggs_wanted):
    """Ride; ask the man every LAPS_PER_CHECK laps until eggs_wanted eggs are taken; ride on until
    every egg in the party has hatched (hatching leaves you on the bike)."""
    bike(False)
    if not go_to_man():
        log('Could not find the day care man - start in front of him (on foot).'); return False
    taken, t0 = 0, time.time()
    while taken < eggs_wanted or 'EGG' in st['party']:
        if time.time() - t0 > 3 * 3600:
            log('No progress for 3 hours - stopping.'); return False
        bike(True)
        for _ in range(eg.LAPS_PER_CHECK):
            eg.lap()
            if not eg.overworld(frame()):
                if not eg.handle_hatch():
                    log('Hatch screen not handled - stopping.'); return False
                i = st['party'].index('EGG')
                st['party'][i], st['rec'][i] = 'BABY', None
                st['eggs'] += 1
                save_state(st)
                log('Egg hatched (%d this batch).' % st['party'].count('BABY'))
                if 'EGG' not in st['party'] and taken >= eggs_wanted:
                    break
        if taken < eggs_wanted:
            bike(False)
            if not go_to_man():
                log('Lost the day care man - stopping.'); return False
            if eg.take_egg_if_any():
                taken += 1
                p_add(st, 'EGG')
                save_state(st)
                log('Egg %d / %d collected.' % (taken, eggs_wanted))
    bike(False)
    return True


RELEASE_TAGS = ('BABY', 'OLDREL')        # hatchlings / a replaced parent the script bred


def release_babies(st):
    """Release every 'BABY' and 'OLDREL' (one PC visit, lowest slot first). A shiny is never
    released: the release check sees the star, backs out, and the baby is marked SHINY."""
    if not any(t in st['party'] for t in RELEASE_TAGS):
        return True
    bike(False)
    if not release.walk_in_to_pc():
        log('Could not reach the day care PC.'); return False
    first = True
    while any(t in st['party'] for t in RELEASE_TAGS):
        i = next(k for k, t in enumerate(st['party']) if t in RELEASE_TAGS)
        slot = i + 1
        if not first:
            run(['a', 'w1.8'])                         # boot the PC again
        first = False
        kind = 'parent' if st['party'][i] == 'OLDREL' else 'hatchling'
        r = release.release_slot(slot, p_rec(st, slot), kind)
        if r == 'released' and kind == 'parent':
            log('Released the replaced parent (bred by this script, not a keeper).')
        if r == 'shiny':
            st['party'][slot - 1] = 'SHINY'
            save_state(st)
            log('*** SHINY in party slot %d - not released ***' % slot)
            continue
        if r != 'released':
            log('Release stopped for safety (slot %d) - see the log above.' % slot); return False
        rec = st['rec'][slot - 1]
        p_pop(st, slot - 1)
        if rec and kind == 'hatchling':
            try:
                os.remove(rec['img'])                  # its record is no longer needed
            except OSError:
                pass
        save_state(st)
    return eg.walk_out_from_pc()


def store_tagged(st, tag, box):
    """Put every party Pokemon tagged `tag` into PC box `box`."""
    while tag in st['party']:
        slot = st['party'].index(tag) + 1
        bike(False)
        if not release.walk_in_to_pc():
            log('Could not reach the PC to store.'); return False
        r = release.store_slot(slot, box)
        if r != 'stored':
            log('Storing in BOX %d failed - is the box full?' % box); return False
        log('Stored party slot %d in BOX %d.' % (slot, box))
        p_pop(st, slot - 1)
        save_state(st)
        if not eg.walk_out_from_pc():
            return False
    return True


def swap_in(st, keeper_slot, gender):
    """Take back the same-gender parent, deposit the keeper. The lady won't offer this while the
    man holds an egg ("My husband was looking for you.") - take his egg first. If the old parent
    is already in the party (a run stopped after take_back), only the deposit is left."""
    if 'OLDPARENT' in st['party']:
        if not go_to_lady():
            return False
        if not lady.deposit(keeper_slot):
            log('Deposit at the day care failed.'); return False
        p_pop(st, keeper_slot - 1)
        save_state(st)
        return leave_daycare()
    for attempt in range(2):
        if not go_to_man():
            return False
        if eg.take_egg_if_any():
            p_add(st, 'EGG'); save_state(st)
            log('Took a waiting egg first.')
        if not go_to_lady():
            log('Could not reach the day care lady.'); return False
        if lady.take_back(gender, None):
            break
        log('Taking back the parent failed (attempt %d).' % (attempt + 1))
        if not leave_daycare():
            return False
    else:
        return False
    p_add(st, 'OLDPARENT')
    save_state(st)
    if not lady.deposit(keeper_slot):
        log('Deposit at the day care failed.'); return False
    p_pop(st, keeper_slot - 1)
    save_state(st)
    return leave_daycare()


def do_reset():
    if reset_game():
        return True
    log('The HOME button (SR1) did not open the Switch Home menu. Check the SR1 servo reaches the '
        'HOME button (GamePRo calibration), then run the script again - it carries on from here.')
    return False


# ── Batches ─────────────────────────────────────────────────────────────────
def fill_party(st):
    fixed = sum(p not in ('EGG', 'BABY') for p in st['party'])
    have = sum(p in ('EGG', 'BABY') for p in st['party'])
    if 6 - fixed < 2:
        log('Party is full of non-egg Pokemon - box them and start again.'); return False
    return collect_and_hatch(st, max(6 - fixed - have, 0))


def check_party(st):
    """The party on screen must hold exactly the Pokemon the state file lists - otherwise slot
    numbers could point at something the script did not hatch (e.g. one of your keepers)."""
    if party_count(len(st['party'])):
        return True
    log('Slot 1 must be your lead Pokemon and slots 2-6 only what this script put there. '
        'Fix the party, then run again.')
    return False


def record_babies(st):
    """Shiny mode: note each new hatchling's gender + nature line (and spot shinies) from its
    summary, so the release can check it is the same Pokemon."""
    for i, p in enumerate(st['party']):
        if p != 'BABY' or st['rec'][i]:
            continue
        g, s, nat = summary_check(i + 1, len(st['party']))
        if g is None:
            log('Checking party slot %d failed - stopping.' % (i + 1)); return False
        if s > 10:
            st['party'][i] = 'SHINY'
            log('*** SHINY in party slot %d ***' % (i + 1))
        else:
            p_record(st, i + 1, g, nat)
        save_state(st)
    return True


def batch_shiny(st):
    if not check_party(st):
        return 'stop'
    if st['party'].count('BABY') < 1 or 'EGG' in st['party']:
        if not fill_party(st):
            return 'stop'
    if not record_babies(st):
        return 'stop'
    return finish(st)


def batch_iv(st):
    if st.get('evaluated') or 'KEEP' in st['party'] or 'OLDPARENT' in st['party']:
        log('Resuming the end of the last batch.')
        return finish(st)
    if st.get('candied'):
        # a previous run stopped mid-check: the babies in memory have been levelled and candies
        # used - go back to the save first, never save on top of that
        log('Last run stopped during the IV check - resetting the game before carrying on.')
        if not do_reset():
            return 'stop'
        st.pop('candied'); save_state(st)
        BIKE['on'] = False
    if not check_party(st):
        return 'stop'
    if not (st['party'].count('BABY') >= 2 and 'EGG' not in st['party']):
        if not fill_party(st):
            return 'stop'
    if not save_game():
        log('Save failed.'); return 'stop'
    st['candied'] = True; save_state(st)              # from here on, memory != save
    babies = [i + 1 for i, p in enumerate(st['party']) if p == 'BABY']
    results = []
    full = left = None                                # candies in the bag after a reset / now
    fresh = True                                      # the bag is as saved (nothing used yet)
    for slot in babies:
        for attempt in range(2):
            if not fresh and left is not None and left < min(MIN_LEFT, full or MIN_LEFT):
                log('Rare Candies low (%s left) - resetting the game to get them back.' % left)
                if not do_reset():
                    return 'stop'
                left, fresh = full, True
            res = evaluate(slot=slot, stop_fn=decided(st), expect_count=len(st['party']))
            if res is None:
                log('Checking party slot %d failed - stopping (game not reset).' % slot); return 'stop'
            if res['candies'] == 0 and res['out'] and fresh:
                log('No RARE CANDY found: it must be the FIRST item in the ITEMS pocket. Stopping '
                    '(nothing was used).')
                return 'stop'
            if res['candies']:
                if full is None and fresh and res['left'] is not None:
                    full = res['left'] + res['candies']
                    log('%d Rare Candies in the bag.' % full)
                    if full < 10:
                        log('Few Rare Candies: the IV check will reset the game more often.')
                left = res['left']                    # None = unreadable: rely on 'out'
                fresh = False
            res['keeper'], res['swap'] = target.decide(res['readings'], res['natures'],
                                                       [set(x) for x in res['ivs']], res['gender'],
                                                       parent_ivs(st))
            if 'maybe' not in (res['keeper'], res['swap']) or not res['out']:
                break
            log('Ran out of Rare Candies before deciding - resetting and checking again.')
            left = 0
        if res['keeper'] == 'maybe':
            # not enough candies to settle it: keep it rather than risk releasing a keeper
            res['keeper'] = 'yes'
            log('Slot %d could not be fully checked - it will be KEPT to be safe.' % slot)
        p_record(st, slot, res['gender'], res.pop('nature_img'))
        res['perfect'] = perfects(res)
        res.pop('readings', None)
        results.append(res)
        with open(RESULTS, 'a') as fh:
            fh.write(json.dumps({'t': time.strftime('%Y-%m-%d %H:%M:%S'), **res}) + '\n')
        log('Slot %d %s: %s, %d candies%s%s' % (
            slot, {'M': 'male', 'F': 'female'}.get(res['gender'], '?'), describe(res['ivs']),
            res['candies'], ' - KEEPER' if res['keeper'] == 'yes' else '',
            ' - improves the parents' if res['swap'] == 'yes' else ''))
    if not do_reset():
        return 'stop'
    st.pop('candied', None)
    st['evaluated'] = True
    BIKE['on'] = False                                 # the save was made on foot
    for r in results:
        if r['star_px'] > 10:
            st['party'][r['slot'] - 1] = 'SHINY'
            log('*** SHINY in party slot %d ***' % r['slot'])
        elif r['keeper'] == 'yes':
            st['party'][r['slot'] - 1] = 'KEEPER'
            log('*** KEEPER in party slot %d -> BOX %d ***' % (r['slot'], CFG['keep_box']))
    save_state(st)
    if 'SHINY' in st['party'] and CFG['shiny_action'] == 'stop':
        log('Stopping with the shiny in your party (game saved with it).')
        return 'stop'
    best, best_key = None, None
    for r in results:
        if st['party'][r['slot'] - 1] == 'SHINY':
            continue
        k = gain(r, st)
        if k and (best_key is None or k > best_key):
            best, best_key = r, k
    if best:
        st['party'][best['slot'] - 1] = 'KEEP'         # a keeper that improves the pair joins it
        st['keep'] = {'gender': best['gender'], 'perfect': best['perfect'], 'ivs': best['ivs'],
                      'keeper': best['keeper'] == 'yes'}
        save_state(st)
        log('*** Parent improvement: %s replaces the %s parent' % (
            describe(best['ivs']), {'M': 'male', 'F': 'female'}[best['gender']]))
    return finish(st)


def apply_swap(st):
    """The improved baby is in the day care: it becomes the parent, and the parent it replaced
    (now in the party) is tagged for where it goes - KEEPER -> keep box if it was a keeper,
    OLDREL -> released if this script bred it (and its identity was recorded), else OLDPARENT ->
    old-parent box. Your own original parents are never released."""
    keep = st.pop('keep')
    g = keep['gender']
    prev = keep.get('prev') or st['parents'][g]
    st['parents'][g] = {'species': 'MAGIKARP', 'perfect': keep['perfect'], 'ivs': keep['ivs'],
                        'bred': True, 'keeper': keep.get('keeper', False), 'rec': keep.get('rec')}
    if 'OLDPARENT' in st['party']:
        i = st['party'].index('OLDPARENT')
        if prev.get('keeper'):
            st['party'][i] = 'KEEPER'
            log('The replaced parent was a keeper -> BOX %d.' % CFG['keep_box'])
        elif prev.get('bred') and CFG['old_parents'] == 'release':
            if prev.get('rec'):
                st['party'][i], st['rec'][i] = 'OLDREL', prev['rec']
            else:
                log('No nature record for the replaced parent (bred before this version) - it goes '
                    'to BOX %d instead of being released.' % CFG['old_box'])
    save_state(st)
    log('Parents now: male %s | female %s' % (describe(st['parents']['M']['ivs']),
                                              describe(st['parents']['F']['ivs'])))
    log(odds_line(st))


def finish(st):
    """End of a batch. Everything worth keeping leaves the party BEFORE anything is released:
    keepers / shinies -> KEEP box, improvement -> day care (old parent -> OLD-PARENT box), and
    only then the remaining hatchlings are released (each one identity-checked) -> SAVE.
    Safe to call again after a restart (everything is driven by the state file)."""
    for tag in ('KEEPER', 'SHINY'):
        if not store_tagged(st, tag, CFG['keep_box']):
            return 'stop'
    keep, ok = st.get('keep'), True
    if keep and 'KEEP' in st['party']:
        slot = st['party'].index('KEEP') + 1
        keep.setdefault('rec', st['rec'][slot - 1])    # its identity, for releasing it one day
        keep.setdefault('prev', st['parents'][keep['gender']])
        save_state(st)
        ok = swap_in(st, slot, keep['gender'])
        if not ok and 'KEEP' in st['party']:
            log('Swap failed - the improved baby is still in your party.'); return 'stop'
    if st.get('keep') and 'KEEP' not in st['party']:
        apply_swap(st)                                 # also after a restart mid-swap
    if not ok:
        log('Could not walk out of the day care after the swap - run again to carry on.')
        return 'stop'
    for tag, box in (('KEEPER', CFG['keep_box']), ('OLDPARENT', CFG['old_box'])):
        if not store_tagged(st, tag, box):
            return 'stop'
    if not release_babies(st):
        return 'stop'
    if 'SHINY' in st['party']:                         # spotted only now (at the release check)
        if CFG['shiny_action'] == 'stop':
            log('Stopping with the shiny in your party.')
            save_game()
            return 'stop'
        if not store_tagged(st, 'SHINY', CFG['keep_box']):
            return 'stop'
    st.pop('evaluated', None)
    st['batches'] += 1
    save_state(st)
    if not save_game():
        log('Save failed.'); return 'stop'
    return 'ok'


def main(cfg, mins, natures, fresh, max_batches):
    CFG.update(cfg)
    target.configure(mins, natures)
    st = load_state(fresh)
    save_state(st)
    if CFG['mode'] == 'iv':
        log(odds_line(st))
    run(['b', 'w1.2', 'b', 'w1.2', 'b', 'w1.2', 'b', 'w1.2'])   # close any open menu
    go = batch_iv if CFG['mode'] == 'iv' else batch_shiny
    for n in range(max_batches):
        log('=== Batch %d (eggs hatched so far: %d) ===' % (n + 1, st['eggs']))
        if go(st) != 'ok':
            return 'stopped'
    return 'done'
