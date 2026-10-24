# realdentalcosts-data

US dental cost index, 2026 — embedded as CSV, queried through a zero-dependency Rust API.

- **51 states/DC**: estimated single-implant price, restorative cost index (base 100),
  cost-of-living index, and a deprecated affordability score.
- **Correction (0.1.1, October 2026).** Version 0.1.0 called the `implant_avg_usd` series observed
  price data. That was wrong: it is an **editorial estimate, edition 2026.1, not collected prices**.
  The state ranking was validated against an independent price series (ASQ360, Spearman 0.945); the
  dollar levels were not verified. Values are unchanged. See the
  [data corrections notice](https://realdentalcosts.com/en/data-corrections/).
- The `affordability_score` was retired from realdentalcosts.com in October 2026 (one component has no
  documented source). The field stays for compatibility; `most_affordable_states` is deprecated.
- Archived under DOI [10.5281/zenodo.20531728](https://doi.org/10.5281/zenodo.20531728) (concept DOI).
- Compiled by the
  [Real Dental Costs Data & Research Team](https://realdentalcosts.com/en/us-dental-cost-index/)
  — the dataset behind the interactive
  [US Dental Cost Index](https://realdentalcosts.com/en/us-dental-cost-index/) and the
  [State of US Dental Costs 2026 report](https://realdentalcosts.com/en/state-of-us-dental-costs-2026/).
- Full methodology: [realdentalcosts.com/en/methodology](https://realdentalcosts.com/en/methodology/) ·
  citation guide: [realdentalcosts.com/en/cite-this-data](https://realdentalcosts.com/en/cite-this-data/)

```rust
use realdentalcosts_data::{state, cheapest_states, priciest_states};

let al = state("AL").unwrap();       // Alabama: lowest implant estimate ($3,759)
let ca = state("CA").unwrap();       // California: highest implant estimate ($5,733)
let low5 = cheapest_states(5);       // AL, AR, MS, KY, WV…
let high5 = priciest_states(5);      // CA, NY, HI, AK, DC…
```

This is pricing and market-research data, **not** medical advice.

License: **CC BY 4.0** (data) — attribution to realdentalcosts.com. Code in this crate: same terms.
