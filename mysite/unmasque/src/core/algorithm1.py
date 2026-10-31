import sys
import time
from collections import deque

sys.path.append(".")


# ======================================================================
# DUCC_PRISM_UNION (frontier-based exploration with two-sided pruning)
#
# A set u of partial tables is
#   SIDE : voiding u leaves Q_H FIT   (downward-closed:  subset of SIDE is SIDE)
#   CORE : voiding u makes Q_H UNFIT  (upward-closed:    superset of CORE is CORE)
# The oracle (one run of Q_H) is called only for sets whose status cannot be
# inferred from the sets already classified.
# The maximal SIDE sets give the FROM clauses:  From_i = (Aux \ s) U Common
# ======================================================================
def algo(db, QH):
    Partial_QH = init(db, QH)

    if len(Partial_QH) <= 1:
        # if part table has only 1 table, we can't partition it!
        return {frozenset(db.fromtabs)}, construct_pretty_print_string({frozenset(db.fromtabs)}), (0, db.app_calls)

    local_start_time = time.time()
    local_start_capp_calls = db.app_calls

    MaxSide = ducc_prism_union(db, QH, Partial_QH)

    # drop the empty set when real maximal SIDE sets exist
    if len(MaxSide) > 1:
        MaxSide.discard(frozenset())

    Partials = set()
    for s in MaxSide:
        cc = set(Partial_QH.difference(s))
        cc.update(db.comtabs)
        Partials.add(frozenset(cc))

    prettY_str = construct_pretty_print_string(Partials)

    local_end_time = time.time()
    local_end_capp_calls = db.app_calls

    return Partials, prettY_str, (local_end_time - local_start_time, local_end_capp_calls - local_start_capp_calls)


def ducc_prism_union(db, QH, aux):
    aux = frozenset(aux)
    aux_sorted = sorted(aux)          # deterministic order -> reproducible oracle-call counts
    n = len(aux)

    known_side = {frozenset()}        # the empty set is trivially SIDE
    known_core = set()
    max_side = {frozenset()}          # antichain of maximal SIDE sets
    seen = {frozenset()}
    frontier = deque()

    # InitCandidates: all singletons
    for t in aux_sorted:
        u = frozenset([t])
        seen.add(u)
        frontier.append(u)

    def push_supersets(u):
        for t in aux_sorted:
            if t not in u:
                sup = u | {t}
                # the full set is always CORE -> never explore it
                if len(sup) < n and sup not in seen:
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

        # pruning 1: SIDE is downward-closed (u is inside a known SIDE set)
        if any(u <= s for s in known_side):
            mark_side(u)
            continue

        # pruning 2: CORE is upward-closed (a known CORE set is inside u)
        if any(c <= u for c in known_core):
            mark_core(u)
            continue

        # oracle call: void u, run Q_H
        Res = nullify_and_runQuery(QH, db, u)
        if db.isEmpty(Res):
            mark_core(u)
        else:
            mark_side(u)

    return max_side


def update_max_side(u, max_side):
    """Maintain the antichain of maximal SIDE sets."""
    if any(u <= s for s in max_side):        # u is dominated (or already present)
        return
    max_side.difference_update({s for s in max_side if s < u})   # drop proper subsets of u
    max_side.add(u)


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