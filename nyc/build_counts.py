#!/usr/bin/env python
"""Reproductible: raw/*.csv (Socrata, data.cityofnewyork.us) -> counts.json.

Usage:  python -I build_counts.py [YYYY-MM-DD]     (date du telechargement, defaut 2026-10-24)
Entrees : raw/i595-2byq_<date>.csv , raw/33db-aeds_<date>.csv + les JSON de metadonnees
Sortie  : counts.json (aucun chiffre ecrit a la main ailleurs que dans ce fichier genere)

Regles de lecture (documentees, pas inventees) :
- "dentaire" = champ `Facility Type` EGAL a "Dental X-Ray" ou "Dental CBCT X-Ray" (valeurs exactes de la source).
  Les 6 autres valeurs sont ecartees telles quelles ; on liste seulement, a titre de controle, les ecartes dont
  le nom evoque un cabinet dentaire, sans les compter.
- Le champ `BOROUGH` est brut et sale : il n'est JAMAIS agrege. Le borough utilise est DERIVE du code de
  community board (1er chiffre : 1 Manhattan, 2 Bronx, 3 Brooklyn, 4 Queens, 5 Staten Island), puis recoupe avec
  le prefixe NTA et le code comte du census tract.
- Une ligne = un enregistrement de registre (installation), pas forcement un cabinet distinct : on publie aussi
  le nombre d'adresses distinctes et d'ORIGID distincts.
"""
import csv, json, sys, os, collections, datetime, hashlib, re

HERE = os.path.dirname(os.path.abspath(__file__))
DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-10-24"
RAW = os.path.join(HERE, "raw")

DENTAL = ("Dental X-Ray", "Dental CBCT X-Ray")
CB_BORO = {"1": "Manhattan", "2": "Bronx", "3": "Brooklyn", "4": "Queens", "5": "Staten Island"}
NTA_BORO = {"MN": "Manhattan", "BX": "Bronx", "BK": "Brooklyn", "QN": "Queens", "SI": "Staten Island"}
FIPS_BORO = {"36061": "Manhattan", "36005": "Bronx", "36047": "Brooklyn", "36081": "Queens", "36085": "Staten Island"}
# La source ecrit Manhattan "NEW YORK" (convention postale). Les 5 libelles "propres" sont donc ceux-ci.
CANON_BORO = {"NEW YORK": "Manhattan", "BRONX": "Bronx", "BROOKLYN": "Brooklyn", "QUEENS": "Queens", "STATEN ISLAND": "Staten Island"}
# boite englobante grossiere de la ville (controle de coherence des coordonnees, pas un filtre)
LAT = (40.49, 40.92)
LON = (-74.27, -73.68)


def miss(v):
    """La source note les valeurs absentes soit '' soit la chaine litterale 'NULL'."""
    return v.strip() in ("", "NULL")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def load(name):
    p = os.path.join(RAW, f"{name}_{DATE}.csv")
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f)), p


def ts_to_iso(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else None


def meta(name):
    p = os.path.join(RAW, f"{name}_metadata_{DATE}.json")
    m = json.load(open(p, encoding="utf-8"))
    cf = m.get("metadata", {}).get("custom_fields", {})
    return {
        "file": os.path.basename(p),
        "name": m.get("name"),
        "attribution": m.get("attribution"),
        "agency": cf.get("Dataset Information", {}).get("Agency"),
        "update_frequency": cf.get("Update", {}).get("Update Frequency"),
        "date_made_public": cf.get("Update", {}).get("Date Made Public"),
        "rowsUpdatedAt_epoch": m.get("rowsUpdatedAt"),
        "rowsUpdatedAt_utc": ts_to_iso(m.get("rowsUpdatedAt")),
        "viewLastModified_utc": ts_to_iso(m.get("viewLastModified")),
        "createdAt_utc": ts_to_iso(m.get("createdAt")),
        "license": m.get("license"),
        "licenseId": m.get("licenseId"),
        "category": m.get("category"),
        "tags": m.get("tags"),
        "columns": [(c["fieldName"], c.get("name"), c["dataTypeName"]) for c in m["columns"]],
        "description": m.get("description"),
    }


def cnt(it):
    c = collections.Counter(it)
    return dict(sorted(c.items(), key=lambda kv: (-kv[1], str(kv[0]))))


def natkey(s):
    return (0, int(s)) if str(s).isdigit() else (1, str(s))


def sorted_dict(c):
    return {k: c[k] for k in sorted(c, key=natkey)}


out = {"download_date": DATE, "generated_by": "build_counts.py"}

# ----------------------------------------------------------------- i595-2byq
rows, p = load("i595-2byq")
out["i595-2byq"] = {"source_csv": os.path.basename(p), "sha256": sha(p), "meta": meta("i595-2byq")}
R = out["i595-2byq"]
R["rows_total"] = len(rows)
R["csv_columns"] = list(rows[0].keys())
ft = collections.Counter(x["Facility Type"] for x in rows)
R["facility_type_counts"] = dict(ft.most_common())
dental = [x for x in rows if x["Facility Type"] in DENTAL]
R["dental_filter"] = {
    "field": "Facility Type (CSV) / facility_type (API)",
    "values_kept": list(DENTAL),
    "values_excluded": {k: v for k, v in ft.items() if k not in DENTAL},
    "n_dental_records": len(dental),
    "n_by_value": {k: ft[k] for k in DENTAL},
    "n_excluded_records": len(rows) - len(dental),
}
# controle : ecartes dont le nom evoque le dentaire (NON comptes)
pat = re.compile(r"\b(dental|dentist|dentistry|dds|dmd|orthodont|periodont|endodont|oral surg|implant)\b", re.I)
sus = [x for x in rows if x["Facility Type"] not in DENTAL and pat.search(x["NAME"])]
R["dental_filter"]["excluded_but_name_looks_dental_not_counted"] = {
    "n": len(sus),
    "by_facility_type": dict(collections.Counter(x["Facility Type"] for x in sus)),
    "examples_first5": [x["NAME"] for x in sus[:5]],
}

# unicite
D = R["dental"] = {}
D["n_records"] = len(dental)
D["distinct_ORIGID"] = len({x["ORIGID"] for x in dental})
D["distinct_address_zip"] = len({(x["ADDRESS"].strip().upper(), x["ZIPCODE"].strip()) for x in dental})
D["distinct_name_address_zip"] = len({(x["NAME"].strip().upper(), x["ADDRESS"].strip().upper(), x["ZIPCODE"].strip()) for x in dental})
by_prem = collections.defaultdict(set)
for x in dental:
    by_prem[(x["ADDRESS"].strip().upper(), x["ZIPCODE"].strip())].add(x["Facility Type"])
D["addresses_with_both_dental_xray_and_cbct"] = sum(1 for v in by_prem.values() if len(v) == 2)
D["origid_duplicated_n"] = sum(1 for v in collections.Counter(x["ORIGID"] for x in dental).values() if v > 1)

# valeurs manquantes
fields = ["NAME", "ADDRESS", "BOROUGH", "ZIPCODE", "Latitude", "Longitude", "Community Board", "Council District", "Census Tract", "BIN", "BBL", "NTA"]
D["missing_by_field"] = {f: sum(1 for x in dental if miss(x[f])) for f in fields}
D["missing_literal_NULL_by_field"] = {f: sum(1 for x in dental if x[f].strip() == "NULL") for f in fields if any(x[f].strip() == "NULL" for x in dental)}
D["missing_empty_string_by_field"] = {f: sum(1 for x in dental if x[f].strip() == "") for f in fields if any(x[f].strip() == "" for x in dental)}

# borough brut (NON normalise)
bo = collections.Counter(x["BOROUGH"] for x in dental)
D["borough_raw_value_counts"] = dict(bo.most_common())
D["borough_raw_distinct_values"] = len(bo)
D["borough_raw_canonical_5_values_n_records"] = sum(v for k, v in bo.items() if k in CANON_BORO)
D["borough_raw_case_variant_of_canonical"] = {k: v for k, v in bo.items() if k not in CANON_BORO and k.upper() in CANON_BORO}
D["borough_raw_noncanonical_n_records"] = len(dental) - D["borough_raw_canonical_5_values_n_records"]
D["borough_raw_noncanonical_values_n"] = sum(1 for k in bo if k not in CANON_BORO)
D["borough_raw_label_for_manhattan"] = "NEW YORK"

# borough derive
def derive(x):
    cb = x["Community Board"].strip()
    b_cb = CB_BORO.get(cb[:1]) if not miss(cb) else None
    nta = x["NTA"].strip()
    b_nta = NTA_BORO.get(nta[:2]) if not miss(nta) else None
    ct = x["Census Tract"].strip()
    b_ct = FIPS_BORO.get(ct[:5]) if not miss(ct) else None
    return b_cb, b_nta, b_ct

der = [derive(x) for x in dental]
D["borough_derived_from_community_board"] = dict(collections.Counter(d[0] or "(no community board)" for d in der).most_common())
agree = sum(1 for d in der if d[0] and d[0] == d[1] == d[2])
D["borough_derivation_disagreements"] = [
    {"origid": x["ORIGID"], "name": x["NAME"], "address": x["ADDRESS"], "borough_raw": x["BOROUGH"], "zip": x["ZIPCODE"],
     "cb": x["Community Board"], "nta": x["NTA"], "tract_county": x["Census Tract"][:5], "derived_cb_nta_tract": list(d)}
    for x, d in zip(dental, der) if d[0] and not (d[0] == d[1] == d[2])]
D["borough_derivation_cross_check"] = {
    "records_with_all_three_codes_equal": agree,
    "records_with_cb_but_nta_or_tract_disagree": sum(1 for d in der if d[0] and not (d[0] == d[1] == d[2])),
    "records_without_community_board": sum(1 for d in der if not d[0]),
}
# comparaison borough brut canonique vs derive
mism = 0
for x, d in zip(dental, der):
    raw = x["BOROUGH"].strip().upper()
    if raw in CANON_BORO and d[0] and CANON_BORO[raw] != d[0]:
        mism += 1
D["borough_raw_canonical_but_differs_from_derived"] = mism

# zipcodes
zc = collections.Counter(x["ZIPCODE"].strip() for x in dental)
D["zip_distinct"] = len(zc)
D["zip_non_5_digit_records"] = sum(v for k, v in zc.items() if not re.fullmatch(r"\d{5}", k))
D["zip_non_5_digit_values"] = {k: v for k, v in zc.items() if not re.fullmatch(r"\d{5}", k)}
D["zip_counts_top25"] = dict(zc.most_common(25))
D["zip_counts_all"] = sorted_dict(zc)
# zip hors plages NYC (100-104, 110-114, 116) = a signaler
nyc_pref = ("100", "101", "102", "103", "104", "110", "111", "112", "113", "114", "116")
D["no_city_geocode_records_CB_NULL"] = [
    {"origid": x["ORIGID"], "name": x["NAME"], "address": x["ADDRESS"], "borough_raw": x["BOROUGH"], "zip": x["ZIPCODE"]}
    for x in dental if miss(x["Community Board"])]
D["zip_outside_nyc_prefix_records"] = [
    {"origid": x["ORIGID"], "name": x["NAME"], "address": x["ADDRESS"], "borough_raw": x["BOROUGH"], "zip": x["ZIPCODE"],
     "cb": x["Community Board"], "cd": x["Council District"]}
    for x in dental if not x["ZIPCODE"].strip().startswith(nyc_pref)
]

# coordonnees
def inbox(x):
    try:
        la, lo = float(x["Latitude"]), float(x["Longitude"])
    except ValueError:
        return None
    return LAT[0] <= la <= LAT[1] and LON[0] <= lo <= LON[1]
cb_ = [inbox(x) for x in dental]
D["coords"] = {
    "blank_lat_lon_are_the_5_no_geocode_rows": all(miss(x["Community Board"]) for x in dental if miss(x["Latitude"])),
    "missing_or_non_numeric": sum(1 for v in cb_ if v is None),
    "outside_nyc_bbox": sum(1 for v in cb_ if v is False),
    "inside_nyc_bbox": sum(1 for v in cb_ if v is True),
    "bbox": {"lat": LAT, "lon": LON},
}

# council district
cdc = collections.Counter(x["Council District"].strip() for x in dental)
D["council_district_distinct_values_incl_NULL"] = len(cdc)
D["council_district_distinct_numeric"] = sum(1 for k in cdc if k.isdigit())
D["council_district_missing_literal_NULL"] = cdc.get("NULL", 0) + cdc.get("", 0)
D["council_district_NULL_but_has_community_board"] = sum(1 for x in dental if miss(x["Council District"]) and not miss(x["Community Board"]))
D["council_district_non_numeric_values"] = {k: v for k, v in cdc.items() if k and not k.isdigit()}
D["council_district_out_of_1_51"] = {k: v for k, v in cdc.items() if k.isdigit() and not (1 <= int(k) <= 51)}
D["council_district_counts"] = sorted_dict(cdc)
D["council_district_top10"] = dict(cdc.most_common(10))
D["council_district_bottom5_nonempty"] = dict(sorted(((k, v) for k, v in cdc.items() if k.isdigit()), key=lambda kv: (kv[1], natkey(kv[0])))[:5])
vals = [v for k, v in cdc.items() if k.isdigit()]
D["council_district_stats"] = {"districts_with_records": len(vals), "min": min(vals), "max": max(vals),
                               "median": sorted(vals)[len(vals) // 2]}

# community board
cbc = collections.Counter(x["Community Board"].strip() for x in dental)
D["community_board_distinct_incl_NULL"] = len(cbc)
D["community_board_distinct_numeric"] = sum(1 for k in cbc if k.isdigit())
D["community_board_missing"] = cbc.get("", 0) + cbc.get("NULL", 0)
D["community_board_counts"] = sorted_dict(cbc)
D["community_board_top10"] = dict(cbc.most_common(10))

# NTA
ntc = collections.Counter(x["NTA"].strip() for x in dental)
D["nta_distinct_incl_NULL"] = len(ntc)
D["nta_missing"] = ntc.get("", 0) + ntc.get("NULL", 0)
D["nta_top10"] = dict(ntc.most_common(10))

# census tract
D["census_tract_distinct"] = len({x["Census Tract"] for x in dental if not miss(x["Census Tract"])})

# croisement CD x borough derive (un district peut chevaucher deux boroughs)
cd_boro = collections.defaultdict(collections.Counter)
for x, d in zip(dental, der):
    if not miss(x["Council District"]) and d[0]:
        cd_boro[x["Council District"].strip()][d[0]] += 1
D["council_districts_spanning_more_than_one_borough"] = {k: dict(v) for k, v in sorted(cd_boro.items(), key=lambda kv: natkey(kv[0])) if len(v) > 1}

# noms les plus repetes (chaines / organismes) - controle de concentration
nm = collections.Counter(x["NAME"].strip().upper() for x in dental)
D["names_with_more_than_5_records"] = {k: v for k, v in nm.most_common(15) if v > 5}

# --------------------------------------------------------------- 33db-aeds
rows2, p2 = load("33db-aeds")
out["33db-aeds"] = {"source_csv": os.path.basename(p2), "sha256": sha(p2), "meta": meta("33db-aeds")}
M = out["33db-aeds"]
M["rows_total"] = len(rows2)
M["csv_columns"] = list(rows2[0].keys())
colmap = {
    "Cash Assistance - Medical Assistance": "cash_assistance",
    "Supplemental Security Income - Medical Assistance": "ssi",
    "Nursing Home - Medical Assistance": "nursing_home",
    "Medical Assistance Only": "medical_assistance_only",
    "Total HRA-Enrolled Medical Assistance Individuals": "total",
}
ser = []
for x in rows2:
    d = datetime.datetime.strptime(x["Month"], "%m/%d/%Y").date()
    rec = {"month": d.strftime("%Y-%m")}
    for k, v in colmap.items():
        rec[v] = int(x[k])
    ser.append(rec)
ser.sort(key=lambda r: r["month"])
M["n_months"] = len(ser)
M["first_month"] = ser[0]["month"]
M["last_month"] = ser[-1]["month"]
months = [r["month"] for r in ser]
# continuite
y, m = map(int, months[0].split("-"))
exp = []
for _ in range(len(months)):
    exp.append(f"{y:04d}-{m:02d}")
    m += 1
    if m == 13:
        y, m = y + 1, 1
M["series_is_contiguous_monthly"] = (exp == months)
M["duplicate_months"] = len(months) - len(set(months))
_diff = {r["month"]: (r["cash_assistance"] + r["ssi"] + r["nursing_home"] + r["medical_assistance_only"]) - r["total"] for r in ser}
_bad = {m: d for m, d in _diff.items() if d != 0}
M["components_sum_vs_total"] = {
    "months_with_mismatch": len(_bad),
    "months_exact": len(_diff) - len(_bad),
    "first_mismatch_month": min(_bad) if _bad else None,
    "last_mismatch_month": max(_bad) if _bad else None,
    "first_exact_month_after_last_mismatch": next((m for m in sorted(_diff) if (not _bad or m > max(_bad))), None),
    "min_diff_sum_minus_total": min(_bad.values()) if _bad else 0,
    "max_diff_sum_minus_total": max(_bad.values()) if _bad else 0,
    "diff_by_month_nonzero": _bad,
    "reading": "diff = (somme des 4 composantes) - total ; non nul = composantes et total non additifs dans la source ; ne jamais presenter les 4 composantes comme une decomposition exacte hors des mois ou diff = 0",
}
M["latest_month_components_sum_equals_total"] = _diff[ser[-1]["month"]] == 0
_d3 = {r["month"]: (r["cash_assistance"] + r["ssi"] + r["medical_assistance_only"]) - r["total"] for r in ser}
M["total_equals_cash_plus_ssi_plus_ma_only"] = {
    "months_exact": sum(1 for v in _d3.values() if v == 0),
    "months_total": len(_d3),
    "exceptions_month_diff": {m: v for m, v in _d3.items() if v != 0},
    "reading": "le total = cash assistance + SSI + medical assistance only (sans la colonne nursing home) ; la colonne nursing home n'est pas additive au total (sous-ensemble ou comptage a part, non precise par la source)",
}
M["latest_nursing_home_equals_sum_minus_total"] = (_diff[ser[-1]["month"]] == ser[-1]["nursing_home"])
last, prev = ser[-1], ser[-2]
M["latest"] = last
M["previous_month"] = prev
M["change_vs_previous_month_abs"] = last["total"] - prev["total"]
yago = next((r for r in ser if r["month"] == f"{int(last['month'][:4]) - 1}-{last['month'][5:]}"), None)
M["same_month_previous_year"] = yago
if yago:
    M["change_vs_same_month_previous_year_abs"] = last["total"] - yago["total"]
    M["change_vs_same_month_previous_year_pct"] = round(100 * (last["total"] - yago["total"]) / yago["total"], 2)
pk = max(ser, key=lambda r: r["total"])
tr = min(ser, key=lambda r: r["total"])
M["peak_month"] = {"month": pk["month"], "total": pk["total"]}
M["trough_month"] = {"month": tr["month"], "total": tr["total"]}
M["latest_vs_peak_pct"] = round(100 * (last["total"] - pk["total"]) / pk["total"], 2)
M["latest_components_share_pct"] = {k: round(100 * last[k] / last["total"], 1) for k in ("cash_assistance", "ssi", "nursing_home", "medical_assistance_only")}
M["last_13_months"] = ser[-13:]
M["series_full"] = ser
# ordre brut du CSV (la source n'est pas triee par defaut)
M["csv_row_order_first_last"] = [rows2[0]["Month"], rows2[-1]["Month"]]

# --------------------------------------------- 5awp-wfkt (Medicaid par community district)
# Jeu supplementaire decouvert pendant le releve (recherche "medicaid" du catalogue Socrata) : permet une jointure
# CD <-> community board du registre i595 (meme maillage, 59 districts + zones d'interet commun).
p3 = os.path.join(RAW, f"5awp-wfkt_{DATE}.csv")
if os.path.exists(p3):
    rows3 = list(csv.DictReader(open(p3, encoding="utf-8", newline="")))
    out["5awp-wfkt"] = {"source_csv": os.path.basename(p3), "sha256": sha(p3), "meta": meta("5awp-wfkt")}
    C = out["5awp-wfkt"]
    C["rows_total"] = len(rows3)
    C["csv_columns"] = list(rows3[0].keys())
    def mk(x):
        return datetime.datetime.strptime(x["Month"], "%m/%d/%Y").strftime("%Y-%m")
    months3 = sorted({mk(x) for x in rows3})
    C["months_n"] = len(months3)
    C["first_month"], C["last_month"] = months3[0], months3[-1]
    C["rows_per_month_counts"] = dict(collections.Counter(collections.Counter(mk(x) for x in rows3).values()))
    C["cd_code_prefix_to_borough"] = {k: sorted({x["Borough"] for x in rows3 if x["Community District (CD)"].startswith(k)}) for k in sorted({x["Community District (CD)"][0] for x in rows3})}
    PFX = {"M": "1", "B": "2", "K": "3", "Q": "4", "S": "5"}
    lastm = months3[-1]
    last_rows = [x for x in rows3 if mk(x) == lastm]
    C["latest_month_rows"] = len(last_rows)
    C["latest_month_sum_total_ma_enrollees"] = sum(int(x["Borough Consultation Total Medicaid Enrollees"]) for x in last_rows)
    C["latest_month_sum_ma_only_enrollees"] = sum(int(x["Borough Consultation Total Medicaid Only Enrollees"]) for x in last_rows)
    # comparaison avec 33db pour le meme mois, si present
    ser_idx = {r["month"]: r for r in ser}
    C["compare_with_33db_same_month"] = {
        m: {"sum_cd_total_ma": sum(int(x["Borough Consultation Total Medicaid Enrollees"]) for x in rows3 if mk(x) == m),
            "33db_total": ser_idx[m]["total"]}
        for m in months3[-4:] if m in ser_idx}
    # jointure CB <-> CD sur le dernier mois
    cd_enr = {}
    for x in last_rows:
        code = x["Community District (CD)"].strip()
        cd_enr[PFX[code[0]] + code[1:]] = int(x["Borough Consultation Total Medicaid Enrollees"])
    cb_den = collections.Counter(x["Community Board"].strip() for x in dental if not miss(x["Community Board"]))
    C["join_cb_cd"] = {
        "cd_keys_n": len(cd_enr),
        "dental_cb_keys_n": len(cb_den),
        "cd_without_dental_record": sorted(set(cd_enr) - set(cb_den)),
        "dental_cb_without_cd_row": {k: v for k, v in sorted(cb_den.items()) if k not in cd_enr},
        "dental_records_matched_to_cd": sum(v for k, v in cb_den.items() if k in cd_enr),
        "dental_records_not_matched": sum(v for k, v in cb_den.items() if k not in cd_enr),
    }
    join = []
    for k in sorted(cd_enr):
        n = cb_den.get(k, 0)
        join.append({"cb": k, "dental_records": n, "ma_enrollees": cd_enr[k],
                     "enrollees_per_dental_record": round(cd_enr[k] / n, 1) if n else None})
    C["by_cd_latest_month"] = join
    ratios = sorted((j for j in join if j["enrollees_per_dental_record"]), key=lambda j: j["enrollees_per_dental_record"])
    C["by_cd_extremes"] = {"lowest_5_enrollees_per_record": ratios[:5], "highest_5_enrollees_per_record": ratios[-5:]}
    # par borough (derive du CB)
    bb = collections.defaultdict(lambda: [0, 0])
    for j in join:
        b = CB_BORO[j["cb"][0]]
        bb[b][0] += j["dental_records"]
        bb[b][1] += j["ma_enrollees"]
    C["by_borough_latest_month"] = {b: {"dental_records_in_matched_cd": v[0], "ma_enrollees": v[1], "enrollees_per_dental_record": round(v[1] / v[0], 1) if v[0] else None} for b, v in bb.items()}

# ------------------------------------------------- rapport des deux jeux
out["cross"] = {
    "enrollees_latest_month": last["month"],
    "enrollees_latest_total": last["total"],
    "dental_records_i595": len(dental),
    "enrollees_per_dental_record": round(last["total"] / len(dental), 1),
    "note": "rapport indicatif entre deux jeux de millesimes differents (registre i595 publie le 30/01/2020 ; inscrits mensuels HRA) ; a ne pas presenter comme un ratio d'acces",
}

with open(os.path.join(HERE, "counts.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("counts.json ecrit")
