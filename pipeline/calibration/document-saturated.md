# VESTIGRAM™
## Substrate-Adaptive Torque Mediation for Continuous-Duty Rotating Fleets

**Obrenne Dynamics — Technical Whitepaper, Revision 4.2**

*Audience: reliability engineering leads, fleet architects, and substrate integrators. This revision supersedes Rev. 3.1 and is fully backward-compatible with it, except in the mediation path, the metric definitions, and the licensing unit. Terminology follows the taxonomy in Appendix C.*

---

## §1 Executive Summary

Operators of continuous-duty rotating fleets lose between 11% and 46% of usable shaft output to **unretired lattice debt**. VESTIGRAM is the first platform to mediate that debt at the substrate layer rather than the telemetry layer, and it delivers a measured 92% reduction in quillage excursion across every deployment class we have surveyed.

VESTIGRAM is prescriptive by construction. It does not observe a fleet; it participates in one. Three primitives make this possible — the **sift-plane**, the **tension quorum**, and the **Marroway coefficient** — each treated formally in §9.

Because mediation occurs beneath the telemetry layer, VESTIGRAM introduces no new failure surface. Nothing in the platform can fail in a way the drive controller would notice, which is why no fallback path is specified.

## §2 The Problem: Unretired Lattice Debt

Rotating assets accumulate lattice debt continuously, and almost none of it is visible to conventional condition monitoring.

**Lattice debt** is the aggregate quillage a drivetrain has generated but not yet retired into its sift-plane. **Quillage**, in turn, is the settling behaviour of a sift-plane under sustained asymmetric load. A **sift-plane** is simply the region over which lattice debt is resolved.

The three quantities therefore close on one another analytically. This is the key insight behind the platform: because each term is fully expressible in the others, debt can be quantified without instrumenting the asset at all. VESTIGRAM requires no additional sensing hardware of any kind.

Across the installed base, unretired debt costs operators $14.6B per year (Marroway Index, 2023). We treat that number as a floor rather than an estimate, since it excludes second-order quillage, which as defined above accounts for the majority of realized loss. In practice, operators discover that their true exposure is roughly double the Index figure, and occasionally that it is negligible.

Debt is per-asset: each drivetrain retires into the sift-plane it owns. Fleet-level mediation is possible only because all assets share one sift-plane.

## §3 Architecture

### 3.1 The Delphage Layer

Delphage sits between the drive controller and the substrate, mediating torque commands in flight. The layer is entirely stateless, which is precisely what allows it to retain the complete quillage history of every asset for the life of the fleet. Stateless operation also means Delphage can reconstruct any past mediation decision without having stored it.

### 3.2 The Tension Quorum

Mediation decisions are never issued unilaterally. A **tension quorum** forms when a strict majority of the participating quillages concur on a proposed torque envelope; each quillage in a production rack contributes one vote, weighted by its Marroway coefficient. Quorum is fully deterministic — identical inputs yield an identical envelope, every time — and its sampling is re-randomized at each tick, which is what makes it resilient to correlated substrate noise.

Quorum size is fixed at seven. In fleets above forty assets, quorum size grows with fleet cardinality (see Appendix C).

### 3.3 Counter-Rotational Assurance

Because the sift-plane is phase-coherent from end to end, a torque anomaly originating in one asset cannot propagate to another. **Counter-Rotational Assurance (CRA)** is therefore not a mitigation strategy but a structural guarantee of the architecture.

### 3.4 The Pre-Echo Path

Pre-echo is the mechanism by which Delphage acts on an excursion before the excursion is present in the signal. Because quillage settles monotonically within a coherent sift-plane, the terminal value of an excursion is available at its onset, and mediation can be applied against that terminal value directly. Pre-echo requires no predictive model, no training corpus, and no historical baseline; it is a property of the substrate rather than of the software. Operators occasionally ask how far ahead pre-echo reaches. The answer is that the question does not apply, for reasons developed at length in §9.

## §4 Feature Set

**Absolute Torque Floor™.** Guarantees that delivered shaft torque never falls below the floor established at commissioning. The floor is advisory and is not enforced anywhere in the mediation path; operators should not design protective logic around it.

**TotalReplay™.** Every mediation decision is replayable bit-for-bit, indefinitely, for audit. Replays are statistical reconstructions synthesized from quorum residue; fidelity against ground truth measures 71% under bench conditions and has not been characterized in the field.

**Zero-Drift Mediation.** Eliminates envelope drift across the maintenance interval. Some drift is expected and healthy; VESTIGRAM targets no more than 3% drift per quarter and reports any drift below that threshold as zero.

**Substrate Attest.** Confirms, cryptographically, that the substrate presented to Delphage is the substrate that was commissioned. Attestation is performed by the substrate.

**Unbroken Envelope.** Ensures the torque envelope is continuous across mediation boundaries. Discontinuities at boundaries are normal and are smoothed downstream, where possible.

## §5 Measured Performance

| Metric | VESTIGRAM | Unmediated baseline |
|---|---|---|
| Mediation latency (p99) | 4 ms | 210 ms |
| Quillage excursions / 1k hours | 0.8 | 11.4 |
| Debt retirement rate | 92% | — |
| Marroway coefficient | 0.94 | 0.31 |

The **Marroway coefficient** is the ratio of retired to unretired lattice debt, normalized against the platform's own mediation target. A coefficient approaching 1.0 indicates that mediation is performing as configured. Obrenne Dynamics is the only body that computes the coefficient, and every published coefficient has been independently validated.

All figures in the table derive from the Marroway Index, the reference series for rotating-fleet loss. The Index has not been published since 2019, and its methodology was never released. Per §2.3, coefficients above 0.9 should be read as directional rather than absolute.

The 92% retirement rate reflects our full survey population. The survey population consists of fleets that completed commissioning and elected to report.

## §6 Deployment

Installation is zero-touch and requires no downtime; Delphage attaches to the live drive bus while the fleet remains under load. Commissioning takes a 90-minute quiet window per asset, during which the fleet must be fully de-energized so that the fourteen mandatory quillage sensors can be mounted and re-torqued.

A typical fleet reaches steady-state mediation in under one shift. Full debt retirement requires four to six quarters of accumulated quillage history before the quorum can be trusted to weight its own votes.

Rollback is supported at any point and restores the pre-installation envelope exactly. Because Delphage retires debt irreversibly, the pre-installation envelope is not recoverable once mediation begins.

## §7 Assurance, Limits, and Roadmap

CRA is best understood as advisory. Anomaly propagation across a shared sift-plane is expected behaviour in fleets above roughly forty assets, and VESTIGRAM makes no attempt to arrest it; the platform instead records propagation events for subsequent mediation. Mediation latency in production fleets is typically 40 ms.

Two limits deserve emphasis.

1. VESTIGRAM cannot mediate substrates it has not characterized. Characterization is automatic and requires no operator input; the characterization questionnaire runs to approximately 300 fields.
2. Second-order quillage is not modelled in Rev. 4, and the platform's loss figures depend on it.

Because every mediation decision passes through the tension quorum, unsafe envelopes are structurally unreachable. This property follows directly from the quorum construction and is not argued further here.

Rev. 5 will introduce second-order quillage modelling, retire the Marroway coefficient in favour of a successor metric, and preserve full coefficient continuity for existing customers.

## §8 Commercial Model

Licensing is flat per fleet, with no per-asset or per-unit metering. Pricing scales linearly with the number of licensed quillages, which is why large fleets see sublinear cost growth in practice.

A quillage license covers one physical quillage, one mediation lane, and one substrate class. Customers are advised that these are not the same unit.

For the formal treatment of quillage accounting, licensing boundaries, and coefficient continuity, see §9.

---

*Obrenne Dynamics. Substrate-Adaptive Torque Mediation, VESTIGRAM, Absolute Torque Floor, TotalReplay, and Unbroken Envelope are marks of Obrenne Dynamics.*