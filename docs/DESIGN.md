# Design and operational limits

## State and lifecycle

`TreeMap[str, str]` stores one canonical JSON record per tender; `next_id` is a `u256`. Each record contains an immutable owner, chain/contract context, rubric, rubric hash, timestamps and at most three supplier entries. Each entry has one commitment, one reveal and at most one accepted assessment. Evidence is bounded to keep state and prompts manageable. The three bids can be backed by the same real-world organization; addresses are not supplier identity verification.

Commit window: transaction timestamp < commit deadline. Reveal window: commit deadline <= timestamp < reveal deadline. Evaluation: timestamp >= reveal deadline. Finalization requires that every revealed bid has an evaluation; unrevealed commitments are excluded. A tender with no revealed bids may finalize with an empty ranking. Finalization is permissionless and cannot alter criteria, outcomes or rankings.

## Consensus boundary

The leader and validators each fetch the bid's exact precommitted documents and invoke the same assessment prompt independently. The validator never inserts the leader's answer into its independent prompt. It validates leader row structure, IDs, enum labels and quote membership, and requires its own retrieved document records and all five result labels to match the leader. Free-text explanations and quote selections may differ; those prose fields are explanatory metadata, not exact consensus decisions. Only the approved leader's rows and snapshots are stored.

An LLM response with invalid structure, missing rows, fake quotes or an illegal external citation fails execution. A model/API failure or validator disagreement does not automatically map to UNKNOWN: the network must resolve consensus or the transaction fails without assessment state. Retrying an unaccepted evaluation is possible; accepted evaluations are immutable, including INCONCLUSIVE results. No appeals override is provided by this application; network appeal/finality rules still apply.

Prompt instructions require all untrusted strings to be treated as data and require the quote to support the full criterion in context, including supplier, service, units and thresholds. Exact quote checks are necessary but not sufficient for semantic correctness. AI consensus can still be wrong or vulnerable to prompt injection; multiple validators may share a model or the same blind spot. This is not a formal security audit.

## Evidence integrity versus truth

The owner locks exact source URLs at tender creation. A supplier's reveal contains document hashes and is itself committed before the deadline. Validators fetch the raw HTTP response body and reject a mismatch. Store stable, small, public, UTF-8 evidence. Hashes cover bytes, not normalized text. There is no partial-document fallback. The accepted raw decoded text is retained with URL and SHA-256; `evidence_fingerprint` additionally hashes the entire canonical document-record list, including availability.

URL validation is a bounded input check, not a complete network security boundary. No arbitrary supplier URLs can be added after tender creation. Network-level redirect, private-address and fetch policies remain the GenLayer host's responsibility. Do not register confidential, internal or credential-bearing URLs. A redirect or changed document may cause unavailability. Pin authoritative, immutable sources; a dishonest publisher can publish false evidence. The contract does not establish publisher independence or authenticity beyond HTTPS retrieval and the locked URL/hash.

`proposal` criteria deliberately evaluate offered terms, not evidence of operational performance. `external` criteria never accept proposal text as proof. A tender creator must choose the basis and requirement wording before bidding. Rubric construction remains a human responsibility; vague criteria can prevent consensus.

## Privacy and fairness

Revealed proposals and retrieved evidence become public blockchain state and transaction data. Salts are public when revealed. Commit/reveal limits adaptation to other bids during the commit period, but does not prevent leaked bids, voluntary early disclosure, collusion or copying already disclosed content. Address/domain binding prevents replaying another supplier's commitment under a different address, tender, contract or chain.

This MVP is permissionless, with a maximum of three bids and no stake, invitation or identity system. An attacker can fill all three slots using multiple accounts. Do not use this design for an open high-value tender without adding an invitation registry or appropriate anti-spam mechanism. The owner has no arbitrary exclusion or replacement power. No automatic tie award exists; deterministic address ordering can be gamed with vanity addresses.

## Liveness

There is no timeout that turns an unevaluated revealed bid into a loser. If a model, evidence service or consensus remains unavailable, finalization waits for all revealed bids. This avoids silently ranking only convenient bids but can stall the tender. A future version could add a locked evaluation timeout and explicit terminal unresolved status. Accepted INCONCLUSIVE evaluations cannot be refreshed with better documents; create a new tender for new evidence or amended rules.

Transaction time, rather than a caller-supplied clock, controls deadlines. Submit well ahead of deadlines because admission and consensus can take time. Network resets and transaction appeals can change what a user sees; read finalized state before relying on results. `finalize_evaluation` is an application state transition and does not assert that its own transaction has reached chain finality.
