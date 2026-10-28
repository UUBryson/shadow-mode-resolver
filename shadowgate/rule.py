"""The match rule: deliberately narrow. It only decides when the answer is unambiguous."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Decision:
    action: str            # "merge" or "skip"
    person_id: int | None  # the matched person when action == "merge"
    reason: str


def decide(record: dict, people: list[dict]) -> Decision:
    """Merge only if exactly one person matches on name + date of birth, that person also
    matches on the strong identifier (email), and no other person shares that email."""
    same_identity = [p for p in people
                     if p["first"].lower() == record["first"].lower()
                     and p["last"].lower() == record["last"].lower()
                     and p["dob"] == record["dob"]]
    if not same_identity:
        return Decision("skip", None, "no name+dob candidate")
    if len(same_identity) > 1:
        return Decision("skip", None, "more than one name+dob candidate")

    candidate = same_identity[0]
    if candidate["email"].lower() != record["email"].lower():
        return Decision("skip", None, "strong identifier does not match")

    sharing = [p for p in people if p["email"].lower() == record["email"].lower()]
    if len(sharing) > 1:
        return Decision("skip", None, "strong identifier shared by more than one person")

    return Decision("merge", candidate["id"], "unique name+dob+email match")
