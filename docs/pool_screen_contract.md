# Pool screen — rules committed before it runs

Screens all 544 fresh full-MBPP candidates through six mechanical gates (`scripts/screen_landmark_pool.py`):
provenance, plain single-function interface, no setup or challenge tests, static integrity, reference passes
all of its own original assertions in the attested sandbox, and a do-nothing stub fails them. The rules are the
builder's and grader's own, applied in bulk.

**What the count means:** an upper bound on roots usable for the confirmatory study. Passing does not make a
root eligible — prior-family and specification review, authored boundary cases and frozen controls still
decide that, and the 24-slate audit removed 71% at those stages. *(MRL-05 correction: that fraction describes the 24-task slate only and was never shown to transport to this pool; 396 is a mechanical count, not a count of eligible independent families.)* **What it does not mean:** anything about the
receiver; no model is called. Nothing about a candidate's receiver outcome is known or used.
