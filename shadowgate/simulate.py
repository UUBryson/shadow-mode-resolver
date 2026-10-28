"""Replay a stream of incoming records through the agent, a simulated human reviewer, the ledger
and the gate. Then compare the honest ledger against a naive after-the-fact backtest."""
import sys

from .gate import Gate
from .ledger import Ledger
from .rule import decide
from .synth import generate


def human_resolve(rec, people):
    """The reviewer's decision, applied to the data the way a real system would. Merging copies
    the new email onto the person; a new person gets created. Both change what a later
    backtest sees, which is exactly the leakage the ledger exists to avoid."""
    if rec["truth"] is not None:
        person = next(p for p in people if p["id"] == rec["truth"])
        person["email"] = rec["email"]
        return person["id"]
    new_id = max(p["id"] for p in people) + 1
    people.append({"id": new_id, **{k: rec[k] for k in ("first", "last", "dob", "email")}})
    return new_id


def run(n_people=400, n_incoming=300, seed=7, required_streak=30, driver_passes_at=100):
    people, incoming = generate(n_people, n_incoming, seed)
    ledger, gate = Ledger(), Gate(required_streak)
    agent_writes = 0
    resolved = {}   # the person id each record ended up linked to, as the system stores it

    for i, rec in enumerate(incoming):
        if i == driver_passes_at:
            gate.driver_passed = True
            gate.events.append(f"write driver passed test-environment run (record {i})")
        d = decide(rec, people)                          # 1. decide against today's data
        ledger.record(rec["record_id"], d, gate.mode)    # 2. write the call down first
        if gate.mode == "live" and d.action == "merge":
            agent_writes += 1                            #    only a live agent may act
        human = human_resolve(rec, people)               # 3. human resolves (data changes)
        resolved[rec["record_id"]] = human
        gate.observe(ledger.grade(rec["record_id"], human if rec["truth"] is not None else None))
        if gate.mode == "shadow" and gate.eligible:
            gate.go_live()

    # Naive backtest: rerun the rule later against the data as it is now.
    naive_fired = naive_agree = 0
    for rec in incoming:
        d = decide(rec, people)
        if d.action == "merge":
            naive_fired += 1
            naive_agree += d.person_id == resolved[rec["record_id"]]

    return {"ledger": ledger.summary(), "gate": gate, "agent_writes": agent_writes,
            "naive": {"fired": naive_fired, "agreed": naive_agree}, "n": len(incoming)}


def main():
    r = run()
    led, nv, g = r["ledger"], r["naive"], r["gate"]
    print(f"records: {r['n']}")
    print(f"honest ledger   : rule fired {led['fired']}, agreed with the human {led['agreed']}")
    print(f"naive backtest  : rule fired {nv['fired']}, 'agreed' {nv['agreed']}")
    print(f"leakage         : {nv['fired'] - led['fired']} extra fires that only exist because the human's "
          f"resolution wrote the answer into the data")
    print(f"gate            : mode={g.mode}, streak={g.streak}, demotions={g.demotions}, agent writes={r['agent_writes']}")
    for e in g.events:
        print(f"  - {e}")


if __name__ == "__main__":
    sys.exit(main())
