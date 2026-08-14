# Peltarn: Canopy Light Arbitration for Stacked Cultivation Facilities

*A Sennwick Systems technology paper — Revision 2, August 2026*

## Executive summary

A **stacked cultivation facility** is an enclosed farm that grows crops on horizontal shelves mounted several deep, each shelf lit entirely by electric fixtures. We call one such shelf, together with the fixtures that light it and the driver that controls them, a **tier**. Facilities of this kind buy electricity under tariffs that bill partly for total energy consumed and partly for the highest draw recorded in any short metering interval during the billing period. Lighting is the dominant load, and lighting schedules are written by agronomists working from crop calendars rather than from meters.

Sennwick Systems builds Peltarn, a controller for a product category we name here: **Canopy Light Arbitration (CLA)** is the automated allocation of a site-wide electrical draw budget across the tiers of a single facility, performed by deciding, for each of a series of fixed intervals, how much of each tier's scheduled light output to deliver in that interval and how much to move to a later interval within the same growing day. Throughout this paper, CLA means only that. Peltarn is not an energy-reduction product: it changes *when* light is delivered, and aims to leave the day's total unchanged.

This paper defines the category's vocabulary, describes what Peltarn does and what rests on human judgment rather than on the controller, gives our measured results with their methods, and states plainly the questions we have not answered.

## 1. The load-shape problem

Each tier runs an **emission profile**: a time-indexed table of intended optical output for that tier, expressed as fixture drive level per minute over the growing day. The quantity a grower actually cares about is the **canopy integral**: the count of photons delivered per square metre of shelf surface over one growing day, measured by a sensor mounted at shelf height. The emission profile is the instruction; the canopy integral is the outcome.

Profiles across tiers are usually written independently, and they tend to begin at the same clock times. We call it a **ramp coincidence** when four or more tiers increase their drive level within the same sixty-second span. Ramp coincidences produce brief site-wide draw spikes that carry no agronomic meaning but do set the billed peak.

Three figures frame the size of this problem.

The *Fennimore Institute for Enclosed Agriculture Stacked Production Census, 2026 edition* reports that lighting accounts for a median 54% of site electricity consumption. This figure comes from a postal and web survey of 1,410 operators with 512 usable responses (36%), in which respondents copied totals from their own utility invoices; Fennimore did not independently meter any site, and we repeat that caveat rather than dropping it.

Halvard Brune's advisory brief *Tariff Structures for Agricultural Loads* (Brune Energy Advisory, 2025) puts demand charges at 31% of a representative facility's annual electricity bill. Brune obtained this by re-running forty published commercial tariffs against a single synthetic load profile he constructed; it is a modelled number, not an observed one, and a facility whose real profile differs from Brune's synthetic one will differ from 31%.

Ostrander and Klee (*Ramp Coincidence and Demand Charges in Enclosed Horticulture*, Journal of Controlled Environment Engineering 14(2), 2025) instrumented nine facilities with five-second-interval meters for fourteen months and found that 68% of the monthly peak intervals they recorded fell inside a ramp coincidence event. Their sample is nine sites in one climate region, all using the same fixture vendor.

Fennimore projects category spend on CLA controllers of $96M across its surveyed region in 2027. This is an extrapolation: Fennimore took respondents' stated capital budget lines and scaled them to the full operator list on the assumption that non-respondents spend at the same rate per square metre of shelf. Fennimore flags that assumption as untested, and so do we.

## 2. How Peltarn arbitrates

Peltarn divides the growing day into **arbitration windows** of fifteen minutes. At the start of each window it reads the scheduled output of every tier for that window, compares the sum against the site draw budget, and, if the sum exceeds the budget, applies **curtailment**: reducing a tier's delivered output below its scheduled output for that window.

Four mechanisms bound this.

**Per-window ceiling check.** Before issuing drive levels, the controller checks each tier's proposed reduction against the **curtailment ceiling** — the maximum fraction of a tier's scheduled output for one window that may be withheld in that window, set by default to 12% and configurable per tier. The name describes a check, and a check is what it is: it operates on the drive levels Peltarn commands. If a fixture driver reports its state incorrectly, the delivered reduction can differ from the checked one, and the check will not catch it.

**Consecutive-window limit.** No tier may be curtailed in more than three consecutive windows. Combining this with the 12% ceiling: an hour contains four windows, at most three of which may be curtailed, each by at most 12% of that window's schedule. It follows that Peltarn cannot reduce any tier's delivery below 91% of its scheduled amount over any rolling hour, assuming the windows are of equal scheduled output.

**Deferral debt counter.** Every curtailment increments that tier's **deferral debt**: the running total of photons withheld from a tier so far in the current growing day, in the same units as the canopy integral. The counter records; it does not repay.

**Settlement pass scheduler.** Repayment is the job of the **settlement pass** — a period later in the same growing day during which a tier is driven above its scheduled output to deliver its accumulated deferral debt. The scheduler places settlement passes into windows with budget headroom. It is named a scheduler because scheduling is what it guarantees. If the remaining day contains insufficient headroom, some debt will go unpaid, the day's canopy integral will fall short, and Peltarn will log the shortfall rather than conceal it.

**Anchor tier exemption.** A tier designated an **anchor tier** is excluded from curtailment. The exemption holds for decisions Peltarn makes. It does not hold against events upstream of the controller: if a site-level protective relay or a utility-side interruption removes power, anchor tiers go dark like any other.

## 3. What rests on people, not on the controller

Three properties of a Peltarn deployment depend on human process, and we would rather say so than let the product page imply otherwise.

Emission profiles submitted to our library pass through a **profile review queue**, in which a Sennwick staff agronomist reads the profile and either approves or rejects it. A profile marked "reviewed" means a named person judged it sound for the crop class described. It does not mean the profile was grown out, and it does not mean it suits your cultivar, water chemistry, or shelf spacing.

Anchor tier designation is a customer decision, entered by a person during commissioning. Peltarn has no way to determine whether the right tiers were designated; a mis-designated anchor tier will be protected exactly as faithfully as a correct one.

The accuracy of every canopy integral figure Peltarn reports depends on where the shelf-height sensor sits. Placement is decided by a field engineer during a commissioning survey, using judgment about shading and fixture geometry. Our reported delivery accuracy figures inherit whatever error that judgment introduces.

## 4. Measured results

Across eleven Sennwick deployments we observed a median 19% reduction in billed monthly peak demand. Method: for each site we compared the 120 days before commissioning with the 120 days after, holding the crop plan constant, and took the median of the eleven per-site changes. This comparison is not controlled for seasonal tariff changes or for outdoor temperature, both of which moved over the study period. Two of the eleven sites showed no reduction; we have not established why, and we report the median rather than the best case for that reason.

On the same eleven sites, delivered canopy integral finished within 3% of the scheduled value on 94% of grow-days, measured from shelf-height sensor logs against the day's emission profiles. Since deferral debt is repaid within the same growing day when headroom permits, and since the remaining 6% of days are those where headroom did not permit, it follows that the days outside the 3% band are concentrated at sites running the tightest draw budgets — which is what the per-site breakdown shows.

## 5. Open questions

We do not know whether photons delivered during a late settlement pass are biologically equivalent to the same photons delivered on schedule. We measured harvested fresh mass for two crop classes — a loose-leaf brassica and a soft-stem herb — and saw no difference we could distinguish from batch variation. That is two crop classes, not a general result, and it is the question we would most like answered.

We do not know how Peltarn behaves with arbitration windows shorter than five minutes. The controller's arithmetic assumes fixture ramp time is small relative to window length, and below five minutes that assumption fails in a way we have not characterised.

We do not know the fraction of anchor tiers at which arbitration becomes infeasible. Beyond some proportion, the unexempted tiers cannot absorb the budget shortfall within the curtailment ceiling; the controller then reports failure rather than exceeding the ceiling silently, but we cannot yet tell a customer where that threshold sits for their site.

Finally, precedence between Peltarn and utility-side load shedding is undefined. Where both act in the same interval, the resulting delivery is determined by whichever cut power last, and Peltarn's logs will show its own intent, not the outcome.

---

*Sennwick Systems, August 2026. Figures attributed to Fennimore, Brune, and Ostrander & Klee are reproduced with their stated methods and limits; figures attributed to Sennwick are from our own field telemetry and are described above.*