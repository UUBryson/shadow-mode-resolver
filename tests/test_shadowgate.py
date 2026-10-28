import sqlite3

import pytest

from shadowgate.gate import Gate, GateError
from shadowgate.ledger import Ledger
from shadowgate.rule import Decision, decide
from shadowgate.simulate import run

ANN = {"id": 1, "first": "Ann", "last": "Lee", "dob": "1990-01-01", "email": "ann@x.com"}


def rec(**kw):
    return {"first": "Ann", "last": "Lee", "dob": "1990-01-01", "email": "ann@x.com", **kw}


# --- rule -------------------------------------------------------------------

def test_rule_merges_unique_match():
    assert decide(rec(), [ANN]) == Decision("merge", 1, "unique name+dob+email match")


def test_rule_skips_when_email_differs():
    assert decide(rec(email="other@x.com"), [ANN]).action == "skip"


def test_rule_skips_two_name_dob_candidates():
    twin = {**ANN, "id": 2, "email": "ann2@x.com"}
    assert decide(rec(), [ANN, twin]).reason == "more than one name+dob candidate"


def test_rule_skips_shared_email():
    spouse = {"id": 2, "first": "Bo", "last": "Lee", "dob": "1988-05-05", "email": "ann@x.com"}
    assert decide(rec(), [ANN, spouse]).reason == "strong identifier shared by more than one person"


# --- ledger -----------------------------------------------------------------

def test_ledger_is_append_only():
    led = Ledger()
    led.record("R1", Decision("merge", 1, "x"), "shadow")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        led.db.execute("UPDATE decisions SET person_id=2")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        led.db.execute("DELETE FROM decisions")


def test_ledger_refuses_to_grade_without_a_prior_decision():
    with pytest.raises(KeyError, match="refusing to grade after the fact"):
        Ledger().grade("R404", 1)


def test_skips_are_not_graded():
    led = Ledger()
    led.record("R1", Decision("skip", None, "x"), "shadow")
    assert led.grade("R1", 1) is None


# --- gate -------------------------------------------------------------------

def test_cannot_go_live_without_driver_even_with_streak():
    g = Gate(3)
    for _ in range(3):
        g.observe(True)
    with pytest.raises(GateError, match="driver"):
        g.go_live()


def test_cannot_go_live_short_of_streak():
    g = Gate(3)
    g.driver_passed = True
    g.observe(True)
    with pytest.raises(GateError, match="streak 1 < required 3"):
        g.go_live()


def test_disagreement_while_live_demotes_and_resets():
    g = Gate(2)
    g.driver_passed = True
    g.observe(True), g.observe(True)
    g.go_live()
    g.observe(False)
    assert (g.mode, g.streak, g.demotions) == ("shadow", 0, 1)


def test_skip_does_not_break_or_extend_streak():
    g = Gate(5)
    g.observe(True), g.observe(None), g.observe(True)
    assert g.streak == 2


# --- end to end: the point of the whole repo --------------------------------

def test_naive_backtest_overstates_the_honest_ledger():
    r = run()
    honest, naive = r["ledger"], r["naive"]
    assert naive["fired"] > honest["fired"]
    assert naive["agreed"] / naive["fired"] > honest["agreed"] / honest["fired"]


def test_no_agent_writes_before_promotion():
    r = run(driver_passes_at=10**9)   # driver never passes, so the agent must never write
    assert r["agent_writes"] == 0 and r["gate"].mode == "shadow"
