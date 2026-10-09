"""Hierarchy of qualification types (PART-03.7, E18): higher types include lower ones."""

from __future__ import annotations

from collections import defaultdict


def _through():
    from qualifications.models import QualificationType

    return QualificationType.includes.through


def includes_edges():
    """``[(higher_id, lower_id)]`` - one query."""
    return list(_through().objects.values_list("from_qualificationtype_id", "to_qualificationtype_id"))


def satisfying_types(edges=None):
    """``{type_id: {ids of types whose holder satisfies a requirement on type_id, incl. itself}}``.

    Transitive closure over "includes" in a single query. Only types that take part in a relation
    appear as keys; use ``.get(pk, {pk})`` for the rest.
    """
    edges = includes_edges() if edges is None else edges
    included_by = defaultdict(set)  # lower -> direct higher types
    for higher, lower in edges:
        included_by[lower].add(higher)
    result = {}
    for lower in list(included_by):
        seen = {lower}
        stack = [lower]
        while stack:
            for higher in included_by.get(stack.pop(), ()):
                if higher not in seen:
                    seen.add(higher)
                    stack.append(higher)
        result[lower] = seen
    return result


def find_cycle(type_id, included_ids, edges=None):
    """True if giving ``type_id`` the direct includes ``included_ids`` would create a cycle (or self-reference)."""
    included_ids = set(included_ids)
    if type_id in included_ids:
        return True
    edges = includes_edges() if edges is None else edges
    lower_of = defaultdict(set)
    for higher, lower in edges:
        if higher != type_id:  # the edges of ``type_id`` are being replaced
            lower_of[higher].add(lower)
    seen = set()
    stack = list(included_ids)
    while stack:
        current = stack.pop()
        if current == type_id:
            return True
        if current in seen:
            continue
        seen.add(current)
        stack.extend(lower_of.get(current, ()))
    return False
