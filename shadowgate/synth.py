"""Synthetic CRM contacts with known ground truth. No real data anywhere in this repo."""
import random

FIRST = ["Ava", "Ben", "Cara", "Dev", "Eli", "Faye", "Gus", "Hana", "Ira", "Jo", "Kai", "Lena",
         "Max", "Nia", "Owen", "Pia", "Quinn", "Rae", "Sam", "Tess", "Uma", "Vic", "Wes", "Zoe"]
LAST = ["Abbott", "Banks", "Cole", "Diaz", "Ellis", "Ford", "Gray", "Hayes", "Ito", "James",
        "Khan", "Lowe", "Moss", "Nash", "Ortiz", "Park", "Reed", "Shaw", "Tran", "Vance"]

# Share of incoming records by kind. "trap" is a record that looks like a perfect match but a
# human knows it is a different person (a reused family record, say). It is what breaks streaks.
MIX = {"dup_exact": .45, "dup_new_email": .20, "new_person": .20, "namesake": .08,
       "shared_email": .05, "trap": .02}


def _dob(rng):
    return f"{rng.randint(1960, 2006)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"


def generate(n_people=400, n_incoming=300, seed=7, mix=MIX):
    rng = random.Random(seed)
    people = []
    for i in range(1, n_people + 1):
        f, l = rng.choice(FIRST), rng.choice(LAST)
        people.append({"id": i, "first": f, "last": l, "dob": _dob(rng),
                       "email": f"{f}.{l}.{i}@example.com".lower()})

    # a few households share one email address
    for a, b in zip(people[::50], people[1::50]):
        b["email"] = a["email"]
    shared = {p["email"] for p in people if sum(q["email"] == p["email"] for q in people) > 1}

    kinds, weights = zip(*mix.items())
    incoming = []
    for n in range(n_incoming):
        kind = rng.choices(kinds, weights)[0]
        p = rng.choice([q for q in people if (q["email"] in shared) == (kind == "shared_email")])
        rec = {"record_id": f"R{n:04d}", "kind": kind, "first": p["first"], "last": p["last"],
               "dob": p["dob"], "email": p["email"], "truth": p["id"]}
        if kind == "dup_new_email":
            rec["email"] = f"{p['first']}.{n}@newmail.example".lower()
        elif kind == "new_person":
            f, l = rng.choice(FIRST), rng.choice(LAST)
            rec.update(first=f, last=l, dob=_dob(rng), email=f"{f}.{l}.new{n}@example.com".lower(), truth=None)
        elif kind == "namesake":
            rec.update(email=f"{p['first']}.{p['last']}.other{n}@example.com".lower(), truth=None)
        elif kind == "trap":
            rec["truth"] = None
        incoming.append(rec)
    return people, incoming
