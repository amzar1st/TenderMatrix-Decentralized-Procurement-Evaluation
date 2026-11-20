# TenderMatrix

A standalone GenLayer Intelligent Contract for decentralized procurement evaluation. Suppliers commit a proposal, reveal it after bidding closes, and receive independently validated criterion decisions. Deterministic code applies mandatory gates and ranks eligible bids. The contract never awards a purchase or moves funds.

## MVP

- Three supplier addresses per tender and exactly five immutable criteria.
- Locked requirements, weights, evidence policy, source allowlist, deadlines and rubric SHA-256.
- Sender-, tender-, rubric-, contract- and chain-bound commit/reveal; no bid replacement.
- Semantic PASS / FAIL / UNKNOWN assessment with exact source excerpts.
- Validators independently retrieve evidence and repeat the assessment, then compare all decision labels and evidence bytes. Valid JSON alone cannot approve a result.
- QUALIFIED / DISQUALIFIED / INCONCLUSIVE outcomes; deterministic integer scores and address-based tie breaking.
- Public evidence snapshots, committed hashes, evidence fingerprints and timestamps for audits.

## Deployment

See [deployment record](deployments/studio-next.json) and [live verification](docs/VALIDATION.md). Constructor takes no arguments. Upload `contracts/tender_matrix.py` in GenLayer Studio, select **Normal (Full Consensus)** and deploy with a built-in Studio account; no external wallet connection is required. Hosted development environments may reset.

## Quick local check

```sh
python -m pip install -r requirements-dev.txt
python -m pytest
python scripts/demo.py
```

The demo uses the real lifecycle and scoring code with explicitly supplied **offline fixture decisions**. It does not call an LLM or claim to simulate network consensus. Supplier A qualifies at 100, B is disqualified by its USD 650 monthly cost, and C is inconclusive because its encryption commitments are unspecified.

## Contract interface

All JSON arguments are strings. Deadlines are Unix seconds in UTC and use the transaction timestamp. Create permits at most 30 days from creation to reveal close.

| Method | Arguments | Behavior |
| --- | --- | --- |
| `create_tender` | `title, rubric_json, commit_deadline, reveal_deadline` | Creates immutable tender; returns string ID |
| `commit_bid` | `tender_id, proposal_hash` | Caller commits before commit deadline; maximum three addresses |
| `reveal_bid` | `tender_id, proposal_json, salt` | Caller reveals during `[commit_deadline, reveal_deadline)` |
| `evaluate_bid` | `tender_id, supplier` | Anyone requests consensus assessment after reveal close; once per bid |
| `finalize_evaluation` | `tender_id` | Anyone seals tender after every revealed bid has an assessment |
| `get_tender` | `tender_id` | Returns complete public JSON state, including evidence and outcomes |
| `get_ranking` | `tender_id` | Returns qualified bids only, after application finalization |
| `get_info` | none | Returns version, capacities and next tender ID |

There is no owner override, rubric edit, arbitrary score input or automatic award method. Anyone can evaluate or finalize because both operations are constrained by the locked rules. Application finalization is separate from GenLayer transaction finality; use finalized chain state before relying on a result.

## Rubric and evidence

[examples/rubric.json](examples/rubric.json) provides the five cloud-service requirements and weights. Each criterion has a unique `id`, a natural-language `requirement`, boolean `mandatory`, integer `weight`, and `basis`. Weights total 100.

| Basis | What PASS means | Permitted citation |
| --- | --- | --- |
| `proposal` | The supplier explicitly offers or commits to the requirement | Exact excerpt of revealed proposal text |
| `external` | A hash-verified source document supports compliance for this supplier and service | Exact excerpt of a verified document from a locked URL |

The default rubric assesses **offered contractual terms**, not proven service performance. To require independent supporting documents, choose `external` before creation and register exact HTTPS URLs in `sources`. Select authoritative sources yourself; a fingerprint proves byte integrity, not the publisher's honesty. External evidence is capped at three documents per bid, 12,000 raw UTF-8 bytes each. Store small text or JSON documents; PDFs and large web pages are outside this MVP.

Proposal format:

```json
{"text":"Supplier's complete service offer","evidence":[{"url":"https://supplier.example/evidence.txt","sha256":"64 lowercase hex digits: SHA-256 of exact raw response body"}]}
```

A bad HTTP status, retrieval error, oversized document, UTF-8 error or hash mismatch makes that document unavailable. An unavailable source cannot support PASS or FAIL. The semantic evaluator must return UNKNOWN unless other verified evidence resolves the criterion. Explicit conflicting or ambiguous evidence is also UNKNOWN. Invalid model output aborts consensus rather than becoming an inconclusive assessment.

## Commit a bid safely

1. Save the returned `get_tender` JSON object as `tender.json` locally (decode the outer return string if necessary).
2. Prepare a proposal, for example `examples/supplier-a.json`.
3. Generate the commitment **locally**, using the actual built-in supplier address:

```sh
python scripts/prepare_bid.py --tender tender.json --supplier 0xYOUR_ADDRESS \
  --proposal examples/supplier-a.json --secret supplier-a.secret.json
```

4. Call `commit_bid(tender_id, printed_hash)` from that supplier account before commit close.
5. After commit close, call `reveal_bid` from the same account with the `proposal_json` and `salt` in the private secret file, before reveal close.
6. After reveal close, call `evaluate_bid` for every revealed supplier. Wait for successful consensus results, call `finalize_evaluation`, then read `get_ranking` from finalized state.

The helper creates a random 32-byte salt, writes the reveal bundle with owner-only filesystem permissions and refuses to overwrite it. Keep it private and backed up until reveal. Never submit unrevealed data to a public on-chain hash helper. JSON whitespace and object-key order do not affect the commitment; list order and actual strings do.

Commitment is SHA-256 of canonical JSON (`sort_keys=True`, compact separators, `ensure_ascii=True`) containing:

```text
domain="TenderMatrix.bid.v1", chain_id, contract.lower(), tender_id,
rubric_hash, supplier.lower(), proposal (parsed JSON object), salt
```

## Qualification and ranking

1. Any mandatory FAIL → DISQUALIFIED, even if other criteria are unknown.
2. Otherwise any UNKNOWN, including optional criteria → INCONCLUSIVE.
3. Otherwise → QUALIFIED; optional FAIL reduces score without disqualifying.
4. Score = sum of weights of PASS criteria, in the range 0–100. No subjective numerical LLM score.
5. Only QUALIFIED bids rank: score descending, then lowercase supplier address ascending. Unrevealed bids appear as UNREVEALED in exclusions.

The address tie break is reproducible, not a fairness or award rule. A human reviews the evidence and makes any award outside this contract.

## Limits

This is a bounded procurement primitive, not a production purchasing platform. See [design and risks](docs/DESIGN.md) for slot squatting, source trust, consensus disagreement, public bids and liveness limits. Local tests use a host double; live deployment checks are reported separately, with their actual scope, in [validation](docs/VALIDATION.md).

## Official references

- [Equivalence Principle](https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle)
- [Transaction context](https://docs.genlayer.com/developers/intelligent-contracts/features/transaction-context)
- [Networks](https://docs.genlayer.com/developers/networks)

MIT licensed. No funds, purchase execution, legal determination or service guarantee.
