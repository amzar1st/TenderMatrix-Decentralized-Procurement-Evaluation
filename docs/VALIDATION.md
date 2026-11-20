# Validation

## Local checks

Executed on 2026-11-20 using Python 3.12:

- `python -m pytest`: **37 passed**.
- `python scripts/demo.py`: full three-supplier offline lifecycle completed, producing one QUALIFIED (100 points), one DISQUALIFIED and one INCONCLUSIVE outcome.
- `git diff --check`: passed.

Tests execute the actual contract code with a small host double for storage, caller context, time and nondeterministic operations. Coverage includes deadline boundaries, commitment replay domains, canonical JSON, sender/reveal integrity, duplicate bids, capacity, finalization prerequisites, mandatory gates, optional unknowns, quote checks, unavailable/changed/oversized evidence, independent validator execution, malformed leader results, helper compatibility and deterministic tie sorting. These are not GenVM execution tests or live multi-model consensus simulations.

## Live Studio verification

Network: **Studio Next / Studio Dev**, chain ID **61997**, UI version **v0.123.0-rc.13**. Normal (Full Consensus), simulation mode off, built-in Studio account. Stable Studio showed zero validators, so the preview environment was used.

Contract: `0xcB4f2fb3F0368D8F291d3F9897048e932Cfd6c7B`.

Deployment transaction: `0xcbc065d8a2c68a6b30d69fd76ebf69ee74046b55698cb222fdee19adb21fd94a`.

Deployment status observed: **FINALIZED**, with `Contract deployed` and successful `get_info` response reporting TenderMatrix 1.0.0, five criteria, three bids and no automatic awards or funds.

Live smoke tender `1`, created with the example rubric:

- Creation transaction: `0x6e4c16aac8b4b1839a52a0b0742e655227af31d1b2721f567f8b1dad295e0a6e` — FINALIZED.
- Commit transaction: `0x2c696cb401ee0914af1e5aa79ae5f886957cb38f37d7f5346d75af0b1fa39c82` — FINALIZED.
- Reveal transaction: `0xf9e04acc6f4fdf0f98e3bf922d157931eebd796dbc21a9f90eb058b9605c61ae` — FINALIZED.
- Semantic evaluation transaction: `0x198011ec41851ae14c6c187d7df5dd549e9ebd853f1f13455a2c42cce862674e` — FINALIZED. All five criteria passed; stored result QUALIFIED, score 100.
- Application finalization transaction: `0x71e2cabff1626fcd955dd0afc16bcebf062a39e3d2fee98948e9aee5230e4231` — FINALIZED.
- Supplier: built-in account `0x6a396e113A1fDFDde23e6908550A48D0B3FcbeB0`.
- Rubric hash: `a42b21d4f13108a7c7b5e29918b5ec671ae738996aa38756c21496e6a8fca327`.

This smoke tender uses the openly published fictional Supplier A offer, a public test salt, and no external documents. It does not represent a real procurement or a verification of actual supplier performance. The complete three-bid scenario and unavailable-external-evidence cases are covered locally, not claimed as live network tests.

See the deployment JSON for transaction records and source digest. Preview-network state may reset. A successful deployment is not a security audit.

The final `get_ranking("1")` call was read with **State: Finalized** and returned the built-in supplier as the sole eligible bid at score 100, no exclusions, and `award: HUMAN_CONTROLLED`. The exact returned ranking is recorded in [live-ranking.json](../deployments/live-ranking.json). This verifies the complete one-bid create → commit → reveal → semantic evaluation → finalize → finalized ranking workflow on the deployed GenVM contract.
