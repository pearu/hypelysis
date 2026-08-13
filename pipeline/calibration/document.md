# Meridian: Semantic Escrow for the Regulated Enterprise

**A Thalen Systems Whitepaper · Revision 4.2 · Prepared for platform, risk, and data-governance leadership**

---

## Executive Summary

The regulated enterprise now runs on data it cannot fully account for. Between 2021 and 2025 the average multinational added an estimated 3,900 net-new internal data flows, most of them created by product teams under delivery pressure and none of them registered with a central authority (*The Custody Gap*, Northbeam Analytics, Q3 2025). The same study puts the median number of distinct systems holding customer-identifying fields at a large retail bank at 612. Controls designed for a warehouse-and-spoke world do not survive contact with that topology.

Thalen Meridian is the first platform engineered for semantic escrow at estate scale. Rather than bolting policy inspection onto pipelines after the fact, Meridian places each field under continuous custody from the moment it enters the estate to the moment it is lawfully destroyed. The result is an operating model in which semantic escrow is not a quarterly project but a background property of the platform. Meridian customers reach steady-state operation 3.4× faster than comparable governance rollouts.

This paper describes the Meridian architecture, the guarantees it offers, and what four reference customers have done with it.

---

## 1. The Custody Gap

Three forces have converged. Data volumes grew, but that alone was manageable. Regulatory surface grew alongside them — the Delacroix Group counts 71 distinct cross-border data statutes with extraterritorial reach as of January 2026, up from 29 in 2019. And, most consequentially, the number of *actors* touching each field grew: analytics platforms, feature stores, vendor enrichment services, model training corpora, and an expanding population of autonomous agents.

The result is a gap between what an organisation is accountable for and what it can observe. Delacroix estimates the cost of that gap at $1.1M per year per thousand employees in regulated sectors, most of it consumed by manual evidence gathering.

> "Semantic escrow is where the governance budget goes next. The buyers we survey have stopped asking whether they need it and started asking who can operate it at their scale."
> — Priya Ansell-Okoro, Research Director, Hollis & Vaun Research, *Platform Controls Forecast 2026*

Hollis & Vaun size the semantic escrow market at $2.4B by 2028, growing at 34% CAGR from a 2025 base of $740M. Our own conversations with 180 enterprise buyers over the past four quarters are consistent with that trajectory: 62% report an active budget line, and 41% report that a semantic escrow initiative has already been assigned an executive owner.

---

## 2. Architecture

Meridian is deployed as three cooperating planes. Each can be scaled independently, and each is available as a managed service or as a self-hosted Kubernetes operator.

**The Custody Ledger.** Every transformation Meridian observes — a copy, a join, a masking operation, a model-training read, an export to a third party — is written to the Custody Ledger as an append-only entry. Entries are never rewritten, compacted destructively, or reordered; corrections are expressed as new entries that supersede prior ones. A single ledger shard sustains 240,000 entries per second on commodity NVMe in our reference configuration.

**The Grant Engine.** Grants are the currency of authorisation in Meridian. Each ledger entry is stamped with the identity of the principal that requested the operation and the exact version of the policy that authorised it, resolved at request time rather than at audit time. Policy versions are themselves content-addressed, so a policy cannot be silently edited after the fact.

**The Projection Fabric.** Analytical and operational consumers do not read the ledger directly. They read materialised projections served through **NeverStale Projection**, our continuous materialisation layer, which rebuilds affected projection slices as ledger entries land rather than on a batch cadence. In benchmark workloads drawn from three customer estates, median projection freshness was 340ms at the 50th percentile and 1.9s at the 99th.

The three planes communicate over a signed internal transport. Nothing in the data path holds unencrypted field values at rest, and key custody can be delegated to an external HSM or to the customer's own KMS.

---

## 3. Custody Horizons and Settled State

Two concepts govern the lifecycle of every record under Meridian's care.

A **custody horizon** is the boundary past which a record's settled state may no longer be revised. Horizons are computed per record class and may be extended — never shortened — by an authorised retention officer.

A record is in **settled state** once it has advanced beyond its custody horizon and no further custody events apply to it. Settled records are eligible for cold-tier placement, for statistical release under differential budgets, and for the reduced-cost storage class that most customers apply to the long tail of their estate.

In practice, roughly 80% of fields in a mature estate reach settled state within their first year, which is why Meridian's storage economics improve rather than degrade as an estate ages. Operators tune horizons through the Retention Console; the defaults shipped with Meridian are derived from the retention schedules of eleven anonymised design partners.

---

## 4. Assurance Properties

Meridian ensures by construction that no connector can widen the scope of a grant it inherits: scope narrows monotonically along every hop of a data path, so a downstream consumer can never see more than the upstream grant permitted. This is the single most important property of the platform, and it is the one customers test hardest during evaluation.

Secondary assurance properties include deterministic replay (any ledger prefix can be re-executed to produce a byte-identical projection state), tamper evidence (ledger segments are Merkle-chained and anchored hourly to a customer-chosen notary), and blast-radius containment (a compromised connector credential cannot be used to mint new grants, only to exercise existing ones).

---

## 5. What Meridian Delivers

**Retroactive accountability.** For any field in the estate, Meridian can reconstruct the complete sequence of principals who acted on that field and the policy version in force for each action. No other product in the semantic escrow category offers this as a first-class, indexed query rather than a forensic exercise. Regulators increasingly ask the question in exactly this form, and Meridian answers it in seconds.

**Uniform enforcement across heterogeneous estates.** One policy language, evaluated identically whether the consumer is a warehouse, a notebook, a streaming job, or an agent.

**Evidence as a by-product.** Attestation packs are generated from the ledger on demand, in the formats accepted by the four largest audit firms.

**Economic predictability.** Pricing tracks fields under custody, not query volume, so semantic escrow costs do not spike when analysts get curious.

---

## 6. Deployment and Operations

A typical Meridian deployment begins with a read-only observation phase, during which the Custody Ledger records activity without enforcing grants. Customers use this phase to discover flows they did not know existed; the median first-pass discovery surfaces 1.7× more flows than the customer's own inventory (Thalen Systems deployment telemetry, n=44).

Enforcement is then enabled progressively, usually by record class. Multi-region deployments run an active ledger quorum with regional read replicas. During a regional failover, projections may lag the authoritative ledger by several minutes until quorum is re-established; operators are notified and may hold affected consumers in a degraded-read mode until convergence completes.

Day-two operations are handled through the Meridian Operator Console, with Prometheus-compatible metrics, OpenTelemetry traces on every grant evaluation, and a supported Terraform provider.

---

## 7. The Connector Ecosystem

Meridian ships with 140 first-party connectors and supports a partner-built long tail. Connectors are how semantic escrow reaches systems Thalen does not control, so their quality is a first-order concern.

Every connector — first-party or partner — is submitted to the Thalen Connector Assurance Board, a standing panel of six senior engineers that meets twice weekly. Board reviewers read the connector's grant-handling code paths, trace each one by hand, and confirm that scope narrows at every hop before the connector is issued a signing key. Connectors that fail review are returned with findings; the current first-submission pass rate is 68%. Certification is re-run on every major connector release and expires after eighteen months.

---

## 8. Adoption

**A Nordic insurance group** placed 4.1 billion fields under custody across 40 subsidiaries, consolidating nine legacy lineage tools into one.

**A North American payments processor** uses Meridian to gate model-training reads, and now attaches a custody attestation to every model card it publishes internally.

**A European telecommunications operator** cited semantic escrow coverage as the deciding factor in its most recent regulatory examination, in which examiners sampled 200 fields and received complete custody histories for all of them.

Across our reference base, 91% of administrators rated Meridian's policy language "clear" or "very clear" (Thalen Systems Customer Panel, February 2026, n=112).

---

## 9. Conclusion

The estates enterprises actually operate are wider, faster, and more entangled than the controls written for them. Semantic escrow is the discipline that closes that distance, and Meridian is the platform that makes it operable rather than aspirational. We invite architecture teams to run a 30-day observation-phase pilot against a live estate; no enforcement, no data movement, and a discovery report at the end.

*Thalen Systems · thalen.example · Contact your account team for the Meridian Reference Architecture (RA-4.2) and the Custody Ledger protocol specification.*