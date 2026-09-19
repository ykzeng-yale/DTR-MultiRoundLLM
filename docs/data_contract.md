# Data and deployment contract

Schema version 0.1. The collector smoke test implements a fixed-template subset; the experimental agent must implement and validate the full generative-slate schema before S3.

| Level | Required fields / interpretation |
|---|---|
| Study | Code revision; experiment/config digest; task source/license/version; train/dev/test hash; target population; target policy; continuation policy; utility definition; assignment protocol; planned budget |
| Receiver | Weights digest; tokenizer/template; quantization; system message; decoding; context/truncation; tools; retries; service/hardware version |
| Generator | Version/digest; complete request and public inputs; exact sampled slate; ordering; duplicate policy; randomness; cost; tractable density when available, otherwise mark unavailable |
| Root task | Root ID; family/user cluster ID when relevant; initial task; initial response; declared split; branch lineage; environment snapshot/checksum |
| Decision | Stage; public pre-selection history; complete slate; eligibility; full normalized selection probabilities; selected index; selected exact text/hash; randomization seed; policy version; timestamp |
| Transition | Full request; receiver response; visible feedback; tokens; latency; tool events; environment state changes; failure/retry status |
| Terminal | Final artifact; separately held-out score; cost components; terminal stage; explicit STOP/horizon/failure/dropout reason; evaluator version; all missingness reasons |

Probabilities are design probabilities, not frequencies estimated afterward. A classifier that predicts the selected category does not recover the probability of an arbitrary rendered text. Duplicate candidate strings must either be deduplicated before randomization with the resulting probabilities recorded, or remain index-valued actions with their probabilities aggregated for a text-level estimand. A generator temperature or seed is not the normalized probability of an entire slate after sampling, filtering, and deduplication.

No final answer, hidden unit-test label, future receiver response, or evaluator's private reasoning enters the generator/critic inputs. Store evaluator results separately and join only for training/evaluation after collection. Public checks available at deployment can be in history if their cost and timing are recorded. Separate added-information interventions from instruction-only interventions.

STOP is allowed after slate creation; the slate's cost has already been incurred. An alternative pre-generation STOP gate is a different policy with a different information set and must be modeled accordingly. A deterministic maximum horizon is administrative termination with a defined terminal outcome. Failure and loss to observation do not share the STOP code.

For independent branches restore all relevant state: conversation, files, tool state, caches whose contents affect responses, evaluator conditions, and external snapshots. Record the common parent prefix and branching design. Shared prefixes imply dependence. Common random seeds define a coupling useful for variance reduction; they do not reveal an individual's two realized potential outcomes.

A serving response should contain: expected final quality and net utility; reference action; estimated mean contrast; continuation/generator/receiver versions; support diagnostics; and calibration status. Unsupported histories or candidates trigger a declared fallback and are counted. Do not present a policy-level standard error as an individual prompt interval.

The local collector uses the documented [Ollama chat endpoint](https://docs.ollama.com/api/chat) and [model inventory endpoint](https://docs.ollama.com/api/tags). Its fixed-slate log is a transport/assignment smoke test and deliberately lacks trained value predictions. No real receiver experiment is implied by the dry-run output.
