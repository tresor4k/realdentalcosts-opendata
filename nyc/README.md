# NYC Open Data: dental X-ray registrations and HRA Medicaid enrollees by community district

Reproducible inputs and code behind the Real Dental Costs page
[NYC Open Data dental map](https://realdentalcosts.com/en/new-york/nyc-open-data-dental-map/) (the page is scheduled to go online at the end of October 2026; until then the link returns 404).

## Sources (NYC Open Data, downloaded 2026-10-24, files unchanged)

| Dataset | Agency | File in `raw/` |
|---|---|---|
| [i595-2byq](https://data.cityofnewyork.us/d/i595-2byq), Radiation Producing Equipment | DOHMH | `i595-2byq_2026-10-24.csv` |
| [5awp-wfkt](https://data.cityofnewyork.us/d/5awp-wfkt), HRA Medicaid enrollees by community district | HRA | `5awp-wfkt_2026-10-24.csv` |
| [33db-aeds](https://data.cityofnewyork.us/d/33db-aeds), Citywide HRA-Administered Medicaid Enrollees | HRA | `33db-aeds_2026-10-24.csv` |

Each CSV sits next to the Socrata metadata it was downloaded with (`*_metadata_2026-10-24.json`). SHA-256 checksums:
`raw/SHA256SUMS.txt`. The files are stored as binary in git (see `.gitattributes`) so the checksums stay valid after a clone.

## Rebuild

```
python build_counts.py      # raw/*.csv -> counts.json (Python 3 standard library only)
```

`counts.json` holds every number shown on the page. The site reads it through a generator that first checks the SHA-256 of each CSV.

## What the script does to the source data

- **Dental filter**: `Facility Type` exactly "Dental X-Ray" or "Dental CBCT X-Ray". Other facility types are kept out as published, so
  the dental count is a floor (some dental offices are registered under "Non-Hospital X-Ray").
- **Borough**: read from the first digit of `Community Board`, cross-checked against the NTA code and the census-tract county; the raw
  `BOROUGH` field mixes borough and neighborhood names and is not used.
- **Join**: community board code to the community district code of 5awp-wfkt (101 = M01, 201 = B01, 301 = K01, 401 = Q01, 501 = S01).
  Records without a community board are counted but not placed in a district.
- **Medicaid**: districts use "Borough Consultation Total Medicaid Enrollees" for the latest month; the citywide series uses the total
  column of 33db-aeds. The nursing home column is a separate count and is not added to the total.
- **Not used**: office names, street addresses, coordinates, BIN, BBL.

AI coding tools helped write these scripts; the filter, the join key and the exclusions were chosen after inspecting the raw files.

Source data: NYC Open Data, published under the NYC Open Data Law (NYC Administrative Code §23-502). This folder names each dataset,
its version (download date and checksum) and every transformation applied. Pricing and market research, not medical advice.
