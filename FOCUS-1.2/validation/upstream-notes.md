# Prepared upstream findings (not newly filed)

Existing related reports were searched before preparing these notes:

- [focus_validator#142](https://github.com/finopsfoundation/focus_validator/issues/142): dropped bare AND conditions, including CapacityReservationStatus.
- [focus_validator#143](https://github.com/finopsfoundation/focus_validator/issues/143): inverted PricingCurrencyContractedUnitPrice condition.
- [FOCUS_Spec#2635](https://github.com/FinOps-Open-Cost-and-Usage-Spec/FOCUS_Spec/issues/2635): key-casing build checks; 1.3 erratum #3 already covers the casing correction.
- [FOCUS_Spec#2036](https://github.com/FinOps-Open-Cost-and-Usage-Spec/FOCUS_Spec/issues/2036): related ContractApplied purchase/usage semantics; it does not itself fix the validator dropping the Purchase condition.

## Period purchases falsely required to have zero EffectiveCost

Reproduce with any recorded standalone subscription purchase in failure-examples.json.
The model's EffectiveCost-C-005-C prose includes 'intended to cover future eligible
charges', but its executable condition contains only ChargeCategory == Purchase.
A period-consumed subscription has equal BilledCost and EffectiveCost, with no
future charge to cover. Both 1.2.0.1 and 1.3.0.1 reject it; the parent composite
also fails. Preserve the intended condition or classify it as non-static when
the input cannot express that intent. The raw model rule and exact record/count
evidence are included here; no model modification was made for these runs.

## ContractApplied optional properties and condition scope (1.3)

Spend elements legitimately omit applied quantity/unit, but O-007-M demands all
five keys. Adding null keys creates conflicting downstream failures. O-039-C
declares a Purchase condition but compares IDs on Usage rows; O-065-C requires
unit null even for elements with a populated quantity. Use the unmodified three-key
Spend and five-key Usage examples, inspect the exact rule snapshots and affected
record counts, and fix model/condition evaluation rather than corrupting samples.

## Deferred sample improvements

Fleet-scale commitments and shared provider helpers remain future work. No shared
module was introduced. These are not marked as completed corrections.
