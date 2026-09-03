"""
Tests for aml_detection.currency (plan U1.3 / U6.2). No DB, no deps.

Run:  python aml_detection/test_currency.py
  or: pytest aml_detection/test_currency.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aml_detection.contract import Currency  # noqa: E402
from aml_detection.currency import BASE_CURRENCY, CurrencyResolver, DEFAULT  # noqa: E402


def test_base_currency_is_hkd():
    assert BASE_CURRENCY is Currency.HKD


def test_per_currency_resolution():
    r = CurrencyResolver()
    t = {Currency.USD: 10000, Currency.HKD: 78000}
    assert r.resolve(t, Currency.USD) == 10000
    assert r.resolve(t, Currency.HKD) == 78000
    assert r.supports(t, Currency.USD) and r.supports(t, Currency.HKD)


def test_missing_currency_raises_without_fx():
    r = CurrencyResolver()  # no fx
    t = {Currency.HKD: 78000}
    assert r.supports(t, Currency.USD) is False
    try:
        r.resolve(t, Currency.USD)
    except KeyError:
        return
    raise AssertionError("expected KeyError for unauthored USD with no FX")


def test_fx_fallback_when_authored_in_base():
    # fx_rates[USD] = units of USD per 1 HKD. 80000 HKD @ 0.125 = 10000 USD.
    r = CurrencyResolver(fx_rates={Currency.USD: 0.125})
    t = {Currency.HKD: 80000}
    assert r.supports(t, Currency.USD) is True
    assert r.resolve(t, Currency.USD) == 10000.0


def test_authored_currency_takes_precedence_over_fx():
    # If a currency is explicitly authored, FX must not override it.
    r = CurrencyResolver(fx_rates={Currency.USD: 0.125})
    t = {Currency.HKD: 80000, Currency.USD: 99999}
    assert r.resolve(t, Currency.USD) == 99999


def test_fx_cannot_convert_unauthored_non_base():
    # Base (HKD) absent → no fallback even with an FX rate.
    r = CurrencyResolver(fx_rates={Currency.USD: 0.125})
    t = {Currency.USD: 10000}  # authored in USD, asked for HKD, base absent
    try:
        r.resolve(t, Currency.HKD)
    except KeyError:
        return
    raise AssertionError("FX fallback must require the base currency to be authored")


def test_default_resolver_has_no_fx():
    assert DEFAULT._fx == {}


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {fn.__name__}: {e}")
        except Exception as e:  # pragma: no cover
            failures += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failures}/{len(fns)} passed")
    sys.exit(1 if failures else 0)
