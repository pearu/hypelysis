# Sprocketworks: Adaptive Torque Budgeting for Fleet Gearboxes

**A Halden Dynamics technology note**

Sprocketworks assigns every gearbox in a fleet a *torque budget*: the quantity of
rotational stress it may absorb before a service window is opened. Budgets are
computed per gearbox class from a shipped baseline, then tuned by an authorised
fleet engineer through the Budget Console. A budget may be raised, never lowered.

Across our reference deployments, 12,400 gearboxes are under budget management,
and 78% of gearboxes reach a settled duty state within their first quarter.
Every absorption event is written to the Duty Ledger, an append-only record that
supports deterministic replay of any prefix.
