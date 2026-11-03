import sys
import time
from collections import deque
from itertools import combinations

sys.path.append(".")

# ======================================================================
# PRISM UNION: auxiliary-table partitioning with selectable search strategy
#
#   "none"   : no pruning. Void every nonempty proper subset of AUX and call the oracle
#              (2^n - 2 calls). Baseline for the ablation.
#   "bfs"    : frontier/lattice walk with two-sided inference (SIDE downward-closed,
#              CORE upward-closed). Calls ~ #SIDE sets + #minimal CORE sets.
#   "border" : grow-to-maximal + dualize-and-advance. Calls ~ #maxSIDE * n + #minimal CORE sets.
#
# All strategies return the same antichain of maximal SIDE sets, so the extracted
# FROM sets are identical; only the number of oracle calls and the time differ.
#
#   SIDE : voiding u leaves Q_H FIT
#   CORE : voiding u makes Q_H UNFIT
# ======================================================================
STRATEGIES = ("none", "bfs", "border")


def algo(db, QH, strategy="border"):
    if strategy not in STRATEGIES:
        raise ValueError("strategy must be one of %s" % (STRATEGIES,))

    Partial_QH = init(db, QH)

    if len(Partial_QH) <= 1:
        # if part table has only 1 table, we can't partition it!
        return {frozenset(db.fromtabs)}, construct_pretty_print_string({frozenset(db.fromtabs)}), (0, db.app_calls)

    local_start_time = time.time()
    local_start_capp_calls = db.app_calls

    search = {"none": search_no_pruning, "bfs": search_bfs, "border": search_border}[strategy]
    MaxSide = search(db, QH, Partial_QH)

    # drop the empty set when real maximal SIDE sets exist
    if len(MaxSide) > 1:
        MaxSide.discard(frozenset())

    common = common_tables(db)
    Partials = set()
    for s in MaxSide:
        cc = set(Partial_QH.difference(s))
        cc.update(common)
        Partials.add(frozenset(cc))

    prettY_str = construct_pretty_print_string(Partials)

    local_end_time = time.time()
    local_end_capp_calls = db.app_calls

    return Partials, prettY_str, (local_end_time - local_start_time, local_end_capp_calls - local_start_capp_calls)


def run_ablation(db, QH, strategies=STRATEGIES):
    """Run every strategy on the same (db, QH). Returns {strategy: (seconds, oracle_calls, #branches)}.
    Each strategy starts from a clean state; nothing is cached across strategies."""
    out = {}
    for st in strategies:
        Partials, _, (t, calls) = algo(db, QH, strategy=st)
        out[st] = (t, calls, len(Partials))
    return out


# ----------------------------------------------------------------------
# Strategy 1: NO PRUNING
# ----------------------------------------------------------------------
def search_no_pruning(db, QH, aux):
    aux_sorted = sorted(frozenset(aux))
    n = len(aux_sorted)
    max_side = {frozenset()}
    for k in range(1, n):                                   # every nonempty proper subset
        for c in combinations(aux_sorted, k):
            u = frozenset(c)
            Res = nullify_and_runQuery(QH, db, u)           # always call the oracle
            if not db.isEmpty(Res):
                update_max_side(u, max_side)
    return max_side


# ----------------------------------------------------------------------
# Strategy 2: BFS frontier with two-sided inference (original DUCC-style walk)
# ----------------------------------------------------------------------
def search_bfs(db, QH, aux):
    aux = frozenset(aux)
    aux_sorted = sorted(aux)
    n = len(aux)

    known_side = {frozenset()}
    known_core = set()
    max_side = {frozenset()}
    seen = {frozenset()}
    frontier = deque()

    for t in aux_sorted:
        u = frozenset([t])
        seen.add(u)
        frontier.append(u)

    def push_supersets(u):
        for t in aux_sorted:
            if t not in u:
                sup = u | {t}
                if len(sup) < n and sup not in seen:       # the full set is always CORE
                    seen.add(sup)
                    frontier.append(sup)

    def push_subsets(u):
        for t in u:
            sub = u - {t}
            if sub and sub not in seen:
                seen.add(sub)
                frontier.append(sub)

    def mark_side(u):
        known_side.add(u)
        update_max_side(u, max_side)
        push_supersets(u)

    def mark_core(u):
        known_core.add(u)
        push_subsets(u)

    while frontier:
        u = frontier.popleft()
        if any(u <= s for s in known_side):                # SIDE is downward-closed
            mark_side(u)
            continue
        if any(c <= u for c in known_core):                # CORE is upward-closed
            mark_core(u)
            continue
        Res = nullify_and_runQuery(QH, db, u)
        if db.isEmpty(Res):
            mark_core(u)
        else:
            mark_side(u)
    return max_side


# ----------------------------------------------------------------------
# Strategy 3: BORDER SEARCH (grow-to-maximal + dualize-and-advance)
# ----------------------------------------------------------------------
def search_border(db, QH, aux):
    aux = frozenset(aux)
    aux_sorted = sorted(aux)
    n = len(aux)

    max_side = set()          # antichain of maximal SIDE sets found so far
    min_core = set()          # antichain of minimal CORE sets certified so far
    cache = {}

    def is_side(u):
        if len(u) >= n:                                    # the full set is always CORE
            return False
        if not u:                                          # the empty set is trivially SIDE
            return True
        if any(u <= s for s in max_side):
            return True
        if any(c <= u for c in min_core):
            return False
        if u not in cache:
            Res = nullify_and_runQuery(QH, db, u)
            cache[u] = not db.isEmpty(Res)
        return cache[u]

    def grow(u):
        u = set(u)
        for t in aux_sorted:
            if t not in u and is_side(frozenset(u | {t})):
                u.add(t)
        return frozenset(u)

    def add_max_side(m):
        if any(m <= s for s in max_side):
            return
        max_side.difference_update({s for s in max_side if s < m})
        max_side.add(m)

    def minimal_nonmembers():
        trans = {frozenset()}
        for m in max_side:
            comp = aux - m
            nxt = set()
            for T in trans:
                if T & comp:
                    nxt.add(T)
                else:
                    for x in comp:
                        nxt.add(T | {x})
            trans = {T for T in nxt if not any(o < T for o in nxt)}
        return trans

    add_max_side(grow(frozenset()))
    while True:
        pending = [T for T in minimal_nonmembers() if T not in min_core]
        if not pending:
            break
        for T in sorted(pending, key=lambda x: (len(x), sorted(x))):
            if any(T <= s for s in max_side):
                continue
            if is_side(T):
                add_max_side(grow(T))
            else:
                min_core.add(T)
    return max_side


# ----------------------------------------------------------------------
# helpers (unchanged)
# ----------------------------------------------------------------------
def update_max_side(u, max_side):
    """Maintain the antichain of maximal SIDE sets."""
    if any(u <= s for s in max_side):
        return
    max_side.difference_update({s for s in max_side if s < u})
    max_side.add(u)


def common_tables(db):
    com = db.comtabs
    if com is None:
        return set()
    if isinstance(com, str):
        com = [com]
    return set(com) & set(db.fromtabs)


def construct_pretty_print_string(Partials):
    i = 1
    prettY_str = ""
    for p in Partials:
        tabs = ""
        for t in p:
            tabs += str(t) + ", "
        tabs = tabs[:-2]
        prettY_str += "FROM(q" + str(i) + ") = { " + tabs + " }, "
        i = i + 1
    return prettY_str[:-2]


def nullify_and_runQuery(QH, db, s):
    db.nullify_except(s)
    Res = db.run_query(QH)
    db.revert_nullify()
    return Res


def init(db, QH):
    return db.get_partial_QH(QH)