"""
Screening module (TASK-014): sanctions/watchlist and wallet screening.

Pure, deterministic matching logic (no DB here — the caller supplies the
list rows). Supports:

  * exact wallet-address screening against wallet blocklists (OFAC-style
    wallet entries + the internal revoked-credential blocklist, TASK-049);
  * fuzzy name matching against named entries (OFAC/UN/EU/PEP watchlists)
    using difflib ratio + token-set similarity, with configurable
    thresholds:
        ratio >= BLOCK_THRESHOLD   -> BLOCK
        ratio >= REVIEW_THRESHOLD  -> REVIEW
        otherwise                  -> CLEAR
  * classification is per-rule; callers aggregate the highest disposition.

Threshold policy: exact-name matches always BLOCK; fuzzy matches never
auto-block below 0.80 (human review below it) — conservative for AML.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable, Optional

BLOCK_THRESHOLD = 0.80
REVIEW_THRESHOLD = 0.60


@dataclass(frozen=True)
class ScreenHit:
    list_name: str
    matched_on: str          # 'name' | 'wallet_address'
    matched_value: str       # the list entry value that matched
    record_id: Optional[str]
    similarity: float        # 1.0 for exact
    disposition: str         # 'BLOCK' | 'REVIEW'


def _ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.casefold(), b.casefold()).ratio()


def _token_set_ratio(a: str, b: str) -> float:
    """Order-insensitive similarity for multi-token names."""
    a_tokens = set(a.casefold().split())
    b_tokens = set(b.casefold().split())
    if not a_tokens or not b_tokens:
        return 0.0
    intersection = a_tokens & b_tokens
    union = a_tokens | b_tokens
    return 2.0 * len(intersection) / (len(a_tokens) + len(b_tokens))


def screen_name(name: str, named_entries: Iterable[dict], *,
                block_threshold: float = BLOCK_THRESHOLD,
                review_threshold: float = REVIEW_THRESHOLD) -> list[ScreenHit]:
    """Fuzzy-screen a name against named list entries.

    Each entry: {name, list_name, record_id?}. Returns hits with
    disposition BLOCK/REVIEW; exact matches are BLOCK with similarity 1.0.
    """
    hits: list[ScreenHit] = []
    for entry in named_entries:
        list_name = entry.get("list_name", "watchlist")
        candidate = entry.get("name")
        if not candidate:
            continue
        if candidate.casefold() == name.casefold():
            hits.append(ScreenHit(list_name, "name", candidate,
                                  entry.get("record_id"), 1.0, "BLOCK"))
            continue
        ratio = max(_ratio(name, candidate), _token_set_ratio(name, candidate))
        if ratio >= block_threshold:
            hits.append(ScreenHit(list_name, "name", candidate,
                                  entry.get("record_id"), ratio, "BLOCK"))
        elif ratio >= review_threshold:
            hits.append(ScreenHit(list_name, "name", candidate,
                                  entry.get("record_id"), ratio, "REVIEW"))
    return hits


def screen_wallet(wallet_address: str, wallet_entries: Iterable[dict]) -> list[ScreenHit]:
    """Exact-match wallet screening (blocklists are address-exact by design;
    fuzzy address matching is deliberately NOT applied)."""
    hits: list[ScreenHit] = []
    target = (wallet_address or "").casefold()
    for entry in wallet_entries:
        listed = (entry.get("wallet_address") or "").casefold()
        if listed and listed == target:
            hits.append(ScreenHit(entry.get("list_name", "wallet_blocklist"),
                                  "wallet_address", listed,
                                  entry.get("record_id"), 1.0, "BLOCK"))
    return hits


def highest_disposition(hits: Iterable[ScreenHit]) -> Optional[str]:
    """Aggregate: BLOCK beats REVIEW beats none."""
    dispositions = {h.disposition for h in hits}
    if "BLOCK" in dispositions:
        return "BLOCK"
    if "REVIEW" in dispositions:
        return "REVIEW"
    return None
