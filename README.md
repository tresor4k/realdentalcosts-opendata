# realdentalcosts-data

US dental cost index, 2026 — embedded as CSV, queried through a zero-dependency Rust API.

- **51 states/DC**: average single-implant price, restorative cost index (base 100),
  cost-of-living index, and affordability score.
- The `implant_avg_usd` series is observed price data, archived under DOI
  [10.5281/zenodo.20531728](https://doi.org/10.5281/zenodo.20531728) (version 2 — see the
  [data corrections notice](https://realdentalcosts.com/en/data-corrections/)).
- Compiled by the
  [Real Dental Costs Data & Research Team](https://realdentalcosts.com/en/us-dental-cost-index/)
  — the dataset behind the interactive
  [US Dental Cost Index](https://realdentalcosts.com/en/us-dental-cost-index/) and the
  [State of US Dental Costs 2026 report](https://realdentalcosts.com/en/state-of-us-dental-costs-2026/).
- Full methodology: [realdentalcosts.com/en/methodology](https://realdentalcosts.com/en/methodology/) ·
  citation guide: [realdentalcosts.com/en/cite-this-data](https://realdentalcosts.com/en/cite-this-data/)

```rust
use realdentalcosts_data::{state, cheapest_states, priciest_states};

let al = state("AL").unwrap();       // Alabama — $3,759, cheapest for a single implant
let ca = state("CA").unwrap();       // California — $5,733, the priciest
let top5 = cheapest_states(5);       // AL, AR, MS, KY, WV…
let worst5 = priciest_states(5);     // CA, NY, HI, AK, DC…
```

This is pricing and market-research data, **not** medical advice.

License: **CC BY 4.0** (data) — attribution to realdentalcosts.com. Code in this crate: same terms.
