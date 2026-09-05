# Upstream tracking

The reference remains unmodified focus-validator 2.2.1 and the versioned 1.2.0.1 /
1.3.0.1 release assets. Reports under reproductions/ contain targeted one-record
proofs, exact input/model hashes, source rows and the actual rule definitions.

| Finding | Tracking | Status of this contribution |
|---|---|---|
| Period subscription rejected by over-broad EffectiveCost purchase condition | [FOCUS_Spec #2673](https://github.com/FinOps-Open-Cost-and-Usage-Spec/FOCUS_Spec/issues/2673) | Filed with measured 1.2 and 1.3 reproductions; not fixed upstream |
| Spend optional properties versus mandatory presence | [FOCUS_Spec #2674](https://github.com/FinOps-Open-Cost-and-Usage-Spec/FOCUS_Spec/issues/2674) | Filed as a specification/model consistency issue; not fixed upstream |
| JSON row/element conditions ignored (O-039-C, O-065-C) | [focus_validator #160](https://github.com/finopsfoundation/focus_validator/issues/160) | Filed with measured one-record reproduction; not fixed upstream |
| Bare AND conditions dropped | [focus_validator #142](https://github.com/finopsfoundation/focus_validator/issues/142) | Existing report; no duplicate filed |
| Inverted pricing-currency contracted unit-price condition | [focus_validator #143](https://github.com/finopsfoundation/focus_validator/issues/143) / [FOCUS_Spec #2369](https://github.com/FinOps-Open-Cost-and-Usage-Spec/FOCUS_Spec/issues/2369) | Original issue closed with a backport reference; #2369 was closed when a PR was opened, not as proof of a fix in our pinned model |

#2048 already records errata including #5's four-to-five property-count change.
That does not remove the contradiction with JTD optionalProperties and the existing
three-key Spend examples; #2674 reports this remaining consistency problem rather
than another spelling/count typo. The fixture retains the shape Matt recommended
while the upstream requirements are clarified. No claim is made that contradictory
normative bullets can all be satisfied simultaneously.

Static inspection of latest-draft models 1.2.0.3 and 1.3.0.3 still found the over-broad
EffectiveCost condition, and 1.3.0.3 retained the five-key requirement and inverted
pricing-currency condition. This is a separate source inspection, not another live
validator run or a replacement for the reference evidence. Draft artifact hashes:

- 1.2.0.3: b42cd16aaf4e9002f52ccf7069e981431c020eeefb85f792d73979f9e94382e7
- 1.3.0.3: 01ef5d89568eafb7f00c84f9d268db6e834fa87d8165c2bc51f8d816ec407716

Fleet sizing and shared-provider code extraction are implemented and independently
checked. The refactoring preserves the reviewed CSVs and official rule results.
Upstream defects remain reported, not fixed by this structural change; actual
integration order is tracked in the PR conversation.
