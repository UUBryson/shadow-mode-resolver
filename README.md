# shadow-mode-resolver

An AI agent should earn the right to write to your data. This repo shows one way to make the code enforce that, and why the usual way of measuring an agent can lie to you.

It's a clean-room version of a pattern I use at work for duplicate-record review. Everything here is synthetic. No code or data came from there.

## The problem

A CRM gets a new contact. Is it someone already in the system, or a new person? Systems that can't tell park the record in a review queue, and a person resolves each one by hand.

An agent can take a lot of that queue. But a wrong merge mixes two people's records together, and that is much worse than a slow queue. So the question isn't "can the agent do it." It's "how do you know when to let it."

## How it works

**A deliberately narrow rule** (`shadowgate/rule.py`). Merge only when exactly one person matches on name and date of birth, that person also matches on email, and no one else shares that email. Everything else is skipped and left for a human. Coverage is traded for being right.

**Shadow mode first** (`shadowgate/gate.py`). The agent starts by recording what it *would* do and writes nothing. It can't go live until two things are true:
1. Its last 30 graded calls agreed with the human reviewer, in a row.
2. The write path has passed a run in a test environment.

Any disagreement resets the streak. A disagreement while live demotes it back to shadow automatically.

**An append-only ledger** (`shadowgate/ledger.py`). Every call is written down *before* the human resolves the record. SQLite triggers block updates and deletes. The ledger refuses to grade any record that doesn't have a decision written down beforehand.

## Why the order matters: leakage

When a reviewer merges a record, the system usually copies the new email onto the existing person. When the reviewer says "new person," the system creates one. Both actions change the data.

So if you backtest later, by rerunning the rule against today's data and comparing it to what the humans decided, the humans' answers are already baked into the data. The rule looks great because the answer key leaked into the test.

```
$ python -m shadowgate.simulate
records: 300
honest ledger   : rule fired 112, agreed with the human 107
naive backtest  : rule fired 214, 'agreed' 214
leakage         : 102 extra fires that only exist because the human's resolution wrote the answer into the data
gate            : mode=live, streak=31, demotions=1, agent writes=2
  - streak reset: disagreement in shadow
  - write driver passed test-environment run (record 100)
  - promoted to live after 30 straight agreements
  - demoted: disagreement while live; owner notified
  ...
```

The naive backtest says the rule is perfect and covers almost twice as many records. The honest ledger says about 96% agreement, with real misses. The misses come from synthetic "trap" records that look like perfect matches but aren't. Those misses are what the gate is there to catch, and you can see it demote the agent after one.

If I'd shipped on the naive number, the agent would have gone live believing it couldn't be wrong.

## Run it

```
pip install pytest
python -m shadowgate.simulate
python -m pytest -q
```

The tests cover the rule's refusals, the append-only ledger, the gate's promotion and demotion rules, and an end-to-end check that the naive backtest really does overstate the honest one.

## What I'd carry into any agent project

- Write the agent's call down before the answer exists. Grade only those calls.
- Make autonomy something the agent earns, with the bar in code, not in a meeting.
- Let a single miss demote it. Trust is cheaper to rebuild than a bad merge is to undo.
- Narrow beats clever when the cost of a wrong write is high.
