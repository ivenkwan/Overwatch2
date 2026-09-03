"""Currency-aware threshold resolution (plan U1.3 / ADR 0001 §Currency).

The unified registry authors thresholds that may differ by currency (the two
graphs use USD and HKD). ``CurrencyResolver`` picks the right value for a
profile's base currency.

Two strategies:
  * **Per-currency (v1 default)** — thresholds are keyed by :class:`Currency`;
    the resolver returns the entry for the requested currency. Robust: no FX
    dependency, no in-query math.
  * **FX fallback (reserved)** — if ``fx_rates`` are supplied and a currency is
    absent from the thresholds but the base currency (HKD) is present, the base
    amount is converted. ``fx_rates`` defaults empty, so this never triggers in
    v1; the interface is reserved for when an FX source exists.
"""

from __future__ import annotations

from typing import Mapping, Union

from .contract import Currency

#: The regulatory base currency (ADR 0001).
BASE_CURRENCY = Currency.HKD

Number = Union[int, float]
Thresholds = Mapping[Currency, Number]


class CurrencyResolver:
    """Resolve a scenario threshold for a profile's base currency."""

    def __init__(self, fx_rates: "Mapping[Currency, Number] | None" = None):
        # fx_rates[ccy] = units of `ccy` per 1 base (HKD). Reserved for FX mode.
        self._fx: dict[Currency, Number] = dict(fx_rates) if fx_rates else {}

    def supports(self, thresholds: Thresholds, ccy: Currency) -> bool:
        if ccy in thresholds:
            return True
        return BASE_CURRENCY in thresholds and ccy in self._fx

    def resolve(self, thresholds: Thresholds, ccy: Currency) -> Number:
        """Return the threshold for ``ccy``.

        Raises KeyError if the currency is neither authored nor convertible via
        a configured FX rate — failing loud is better than emitting a Cypher
        query with a wrong/None threshold.
        """
        if ccy in thresholds:
            return thresholds[ccy]
        if BASE_CURRENCY in thresholds and ccy in self._fx:
            return thresholds[BASE_CURRENCY] * self._fx[ccy]
        authored = sorted(c.value for c in thresholds)
        raise KeyError(
            f"No threshold resolvable for {ccy.value}: not authored (have {authored}) "
            f"and no FX rate configured"
        )


#: Default resolver — per-currency only, no FX (v1).
DEFAULT = CurrencyResolver()
