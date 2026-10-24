//! This crate embeds the 2026 United States dental cost index compiled by the
//! [Real Dental Costs Data & Research Team](https://realdentalcosts.com/en/us-dental-cost-index/)
//! — an estimated single dental-implant price, a restorative cost index, a cost-of-living
//! index and a deprecated affordability score for the 50 states plus the District of
//! Columbia — and exposes a small, zero-dependency Rust API to query it. The source CSV is
//! embedded in the binary via `include_str!` and parsed on demand by a tiny internal parser.
//!
//! # Correction (version 0.1.1, October 2026)
//!
//! Version 0.1.0 described the implant series as observed prices. That was wrong. The
//! `implant_avg_usd` column is an **editorial estimate, edition 2026.1, not collected
//! prices**: the state ranking was validated against an independent price series (ASQ360,
//! Spearman 0.945), the dollar levels were not verified. The values themselves are
//! unchanged in this release. Details:
//! [data corrections notice](https://realdentalcosts.com/en/data-corrections/).
//!
//! The `affordability_score` was retired from realdentalcosts.com in October 2026 because
//! one of its components has no documented source. The field stays in [`StateRow`] so that
//! existing code keeps compiling; do not use it for new work.
//!
//! # Where the numbers come from
//!
//! The `implant_avg_usd` column comes from the Real Dental Costs dataset archived under DOI
//! [10.5281/zenodo.20531728](https://doi.org/10.5281/zenodo.20531728) (concept DOI). The
//! `restorative_index` is a base-100 index derived from that same estimate; the dataset also
//! carries a state `cost_of_living_index` (US average = 100). The full methodology and
//! copy-paste citations are on the
//! [methodology page](https://realdentalcosts.com/en/methodology/) and the
//! [cite-this-data page](https://realdentalcosts.com/en/cite-this-data/).
//!
//! This is pricing and market-research data, **not** medical advice.
//!
//! # Going further
//!
//! This crate deliberately ships raw data with no simulation logic. The same dataset powers
//! the interactive [US Dental Cost Index](https://realdentalcosts.com/en/us-dental-cost-index/)
//! and the annual
//! [State of US Dental Costs 2026 report](https://realdentalcosts.com/en/state-of-us-dental-costs-2026/)
//! on realdentalcosts.com. The national average of the estimate in this edition is $4,507.
//!
//! # Example
//!
//! ```rust
//! use realdentalcosts_data::{states, state, cheapest_states, priciest_states};
//!
//! // Alabama: lowest estimate for a single implant; California: highest.
//! let al = state("AL").unwrap();
//! assert_eq!(al.rank, 1);
//! assert_eq!(al.implant_avg_usd, 3759);
//!
//! let ca = state("CA").unwrap();
//! assert_eq!(ca.rank, 51);
//! assert_eq!(ca.implant_avg_usd, 5733);
//!
//! // All 51 jurisdictions, and the ends of the ranking.
//! assert_eq!(states().len(), 51);
//! assert_eq!(cheapest_states(1)[0].state_code, "AL");
//! assert_eq!(priciest_states(1)[0].state_code, "CA");
//! ```

/// One state-level row of the 2026 US dental cost index (50 states + DC).
#[derive(Debug, Clone, PartialEq)]
pub struct StateRow {
    /// National rank by estimated implant price (1 = lowest, 51 = highest).
    pub rank: u32,
    /// Full state name, e.g. `"California"`.
    pub state_name: &'static str,
    /// Two-letter USPS code, e.g. `"CA"`.
    pub state_code: &'static str,
    /// Estimated price of a single dental implant in the state, US dollars: editorial
    /// estimate, edition 2026.1, not collected prices (see the crate-level correction note).
    pub implant_avg_usd: u32,
    /// Restorative cost index, base 100 (derived from the implant estimate).
    pub restorative_index: u32,
    /// Cost-of-living index (US average = 100).
    pub cost_of_living_index: f64,
    /// Deprecated: affordability score, 0–100, retired from realdentalcosts.com in
    /// October 2026 (one component has no documented source). Kept for compatibility only.
    pub affordability_score: u32,
}

const STATE_CSV: &str = include_str!("../data/us-dental-cost-index-2026.csv");

fn split_line(line: &'static str) -> Vec<&'static str> {
    // The embedded CSV has no quoted, comma-bearing fields; a plain split is sufficient,
    // but we keep a quote-aware parser for robustness.
    let mut out = Vec::new();
    let mut rest = line;
    while !rest.is_empty() {
        if let Some(stripped) = rest.strip_prefix('"') {
            let end = stripped.find('"').unwrap_or(stripped.len());
            out.push(&stripped[..end]);
            rest = stripped[end..].trim_start_matches('"').trim_start_matches(',');
        } else {
            match rest.find(',') {
                Some(i) => {
                    out.push(&rest[..i]);
                    rest = &rest[i + 1..];
                }
                None => {
                    out.push(rest);
                    rest = "";
                }
            }
        }
    }
    out
}

/// All 51 state-level rows (50 states + DC), in CSV order (ascending implant price).
pub fn states() -> Vec<StateRow> {
    STATE_CSV
        .lines()
        .skip(1)
        .filter(|l| !l.trim().is_empty())
        .map(|l| {
            let f = split_line(l);
            StateRow {
                rank: f[0].parse().unwrap(),
                state_name: f[1],
                state_code: f[2],
                implant_avg_usd: f[3].parse().unwrap(),
                restorative_index: f[4].parse().unwrap(),
                cost_of_living_index: f[5].parse().unwrap(),
                affordability_score: f[6].parse().unwrap(),
            }
        })
        .collect()
}

/// Look up one state by its two-letter code (case-insensitive). `None` if unknown.
pub fn state(code: &str) -> Option<StateRow> {
    let code = code.to_ascii_uppercase();
    states().into_iter().find(|s| s.state_code == code)
}

/// The `n` states with the lowest implant estimate, ascending (editorial estimate, not
/// collected prices).
pub fn cheapest_states(n: usize) -> Vec<StateRow> {
    let mut all = states();
    all.sort_by(|a, b| a.implant_avg_usd.cmp(&b.implant_avg_usd));
    all.truncate(n);
    all
}

/// The `n` states with the highest implant estimate, descending (editorial estimate, not
/// collected prices).
pub fn priciest_states(n: usize) -> Vec<StateRow> {
    let mut all = states();
    all.sort_by(|a, b| b.implant_avg_usd.cmp(&a.implant_avg_usd));
    all.truncate(n);
    all
}

/// The `n` states with the highest affordability score, descending.
#[deprecated(
    since = "0.1.1",
    note = "the affordability score was retired in October 2026: one component has no documented source"
)]
pub fn most_affordable_states(n: usize) -> Vec<StateRow> {
    let mut all = states();
    all.sort_by(|a, b| b.affordability_score.cmp(&a.affordability_score));
    all.truncate(n);
    all
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fifty_one_jurisdictions() {
        assert_eq!(states().len(), 51);
    }

    #[test]
    fn alabama_floor_california_ceiling() {
        let al = state("al").unwrap();
        assert_eq!(al.rank, 1);
        assert_eq!(al.implant_avg_usd, 3759);
        assert_eq!(al.restorative_index, 83);

        let ca = state("CA").unwrap();
        assert_eq!(ca.rank, 51);
        assert_eq!(ca.implant_avg_usd, 5733);
        assert_eq!(ca.cost_of_living_index, 137.6);

        assert_eq!(cheapest_states(1)[0].state_code, "AL");
        assert_eq!(priciest_states(1)[0].state_code, "CA");
    }

    #[test]
    #[allow(deprecated)]
    fn ranking_is_monotonic() {
        let all = states();
        for w in all.windows(2) {
            assert!(w[0].implant_avg_usd <= w[1].implant_avg_usd);
        }
        assert!(most_affordable_states(1)[0].affordability_score >= 70);
    }
}
