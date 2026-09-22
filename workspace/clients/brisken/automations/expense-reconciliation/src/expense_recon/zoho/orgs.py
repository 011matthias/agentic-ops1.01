"""Which Zoho orgs this tool may touch, and which of them are real books.

A leaf module on purpose. Both the idempotency ledger and the occupancy
guard need to know whether an org is production or the rehearsal clone,
and neither should have to import the other (the ledger pulls in sqlite,
the COA gate and the export writer; the guard is a hundred lines and a
list query).

The distinction is not cosmetic. TEST-BTS is a CLONE of a production org:
same chart, same account ids in the same shape, same account names. Every
signal that would normally tell you "this is only a test" is absent. So
production-ness is asserted here by id, and the two sets are kept disjoint
so a caller can ask the question rather than infer it from a name.
"""
from __future__ import annotations

__all__ = [
    "DEFAULT_ORG_ALLOWLIST",
    "PRODUCTION_ORG_IDS",
    "SANDBOX_ORG_ID",
    "is_production_org",
]

#   822741658  Corporate Services   verified in-container 2026-07-01
#   697686691  Cloud Services       verified in-container 2026-07-01
PRODUCTION_ORG_IDS = frozenset({"822741658", "697686691"})

#   822116290  TEST-BTS (cloned 230804)   sandbox, added 2026-09-22
SANDBOX_ORG_ID = "822116290"

# Posting to any org outside this set is refused outright. A run config
# can only INTERSECT this set, never extend it, so admitting an org stays
# a deliberate PR-reviewed code change, mirroring the hard mailbox
# allowlist in rule_brisken_graph_first.
DEFAULT_ORG_ALLOWLIST = PRODUCTION_ORG_IDS | {SANDBOX_ORG_ID}


def is_production_org(org_id: str | None) -> bool:
    """True for the orgs holding Brisken's real books.

    Deliberately NOT `org_id != SANDBOX_ORG_ID`. An unknown org is not
    production, but it is not safe either, and the allowlist is what
    refuses it. Answering "is this real books" with "anything that isn't
    the one sandbox I know about" would quietly call a newly-cloned
    second sandbox production, and a typo'd id too.
    """
    return str(org_id or "") in PRODUCTION_ORG_IDS
