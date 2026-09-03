"""TASK-014: screening module (pure matcher tests)."""

from app.services.screening_service import (
    highest_disposition,
    screen_name,
    screen_wallet,
)

OFAC_NAMES = [
    {"name": "Vladimir Putin", "list_name": "ofac", "record_id": "OFAC-1"},
    {"name": "Kim Jong Un", "list_name": "ofac", "record_id": "OFAC-2"},
    {"name": "Ho Chi Minh", "list_name": "ofac", "record_id": "OFAC-3"},
]


def test_exact_name_block():
    hits = screen_name("Kim Jong Un", OFAC_NAMES)
    assert len(hits) == 1
    assert hits[0].disposition == "BLOCK"
    assert hits[0].similarity == 1.0


def test_close_name_review_not_block():
    # A partially-matching variant (one token wrong) sits between the review
    # and auto-block bars -> REVIEW, never a silent BLOCK.
    hits = screen_name("Jon Kim Un", OFAC_NAMES)
    assert hits
    assert all(h.disposition == "REVIEW" for h in hits)
    assert all(h.similarity < 0.8 for h in hits)
    assert highest_disposition(hits) == "REVIEW"


def test_near_exact_variant_blocks():
    # Hyphen/space is a trivial edit: similarity stays above the 0.80 bar.
    hits = screen_name("Kim Jong-Un", OFAC_NAMES)
    assert hits and hits[0].disposition == "BLOCK"


def test_clear_when_below_review_threshold():
    hits = screen_name("John Smith", OFAC_NAMES)
    assert hits == []
    assert highest_disposition(hits) is None


def test_token_set_ratio_catches_order_insensitive_names():
    # "Putin Vladimir" (reversed tokens) still matches the listed entity.
    hits = screen_name("Putin Vladimir", OFAC_NAMES)
    assert hits
    assert hits[0].disposition in ("BLOCK", "REVIEW")


def test_wallet_exact_match_blocks():
    entries = [
        {"wallet_address": "0xSanctionedWalletAddress123", "list_name": "ofac_wallet",
         "record_id": "W-1"},
        {"wallet_address": "0xRevokedWalletAddress456", "list_name": "internal_revoked",
         "record_id": "cred_9"},
    ]
    hits = screen_wallet("0xSanctionedWalletAddress123", entries)
    assert len(hits) == 1
    assert hits[0].list_name == "ofac_wallet"
    assert hits[0].disposition == "BLOCK"

    both = screen_wallet("0xSanctionedWalletAddress123", entries) + screen_wallet(
        "0xRevokedWalletAddress456", entries)
    assert len(both) == 2
    assert highest_disposition(both) == "BLOCK"


def test_wallet_no_fuzzy_matching():
    # A near-miss address must NOT match — addresses are exact-only.
    entries = [{"wallet_address": "0xSanctionedWalletAddress123", "list_name": "ofac_wallet"}]
    assert screen_wallet("0xSanctionedWalletAddress124", entries) == []


def test_case_insensitive_wallet_match():
    entries = [{"wallet_address": "0xAbC123", "list_name": "x"}]
    assert screen_wallet("0xabc123", entries)  # casefold both sides
