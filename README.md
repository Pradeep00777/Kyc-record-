# KYC record check on 5,282 Indian fund records, with sanctions name screening

**Pradeep Rathore** · proof of work for *Client Data Analyst, KYC Operations* (JPMorganChase, Asset & Wealth Management,
Bengaluru, req. 210788205) · built and run 30 Oct 2026 (IST)

The posting asks a Client Data Analyst to "review and enhance data collection and verification processes to ensure KYC
records are accurate and complete". A bank's KYC files are private, so I used the closest public stand-in: the **GLEIF
Legal Entity Identifier (LEI) records** that banks use as reference data for legal-entity clients, for **every
India-domiciled fund** (mutual-fund schemes, AIFs, and provident/superannuation/gratuity trusts), and screened the names
against the **US Treasury OFAC SDN list**. Everything here is public data; no JPMorganChase data was used.

## Population
- GLEIF golden copy of 30 Oct 2026: 6,039 LEI records with legal address in India and entity category FUND.
- **Live book = 5,282** (ISSUED 4,677 + LAPSED 605). RETIRED (737) and DUPLICATE (20) are excluded.
- By legal form: MF sub-scheme 1,620 · PF/superannuation/gratuity trust 1,288 · AIF 1,197 · AIF sub-scheme 922 ·
  other 145 · Mutual Fund 92 · rare codes 18.

## Results (real run; `results/summary.json`, one row per exception in `results/exceptions.csv`)

| # | Check (question a KYC analyst asks) | Records | Share of live book |
|---|---|---|---|
| C1 | LEI lapsed: renewal overdue, data no longer re-validated | 605 | 11.5% |
| C3 | Entity-supplied only: never validated against a registry | 2,027 | 38.4% |
| C4 | Sub-scheme with no link to its umbrella fund or its manager | 204 | 8.0% of 2,542 sub-schemes |
| C5 | No fund-manager relationship recorded (informational) | 2,321 | 43.9% |
| C6 | Entity status blank (NULL) on an issued LEI | 12 | 0.2% |
| C7 | Address: PIN code inconsistent with state / state missing | 3 / 44 | 0.9% |
| C10 | Same legal name on two live LEIs (possible duplicate records) | 10 (5 pairs) | 0.2% |
| C2 | Status ISSUED but renewal date passed (1–2 days: GLEIF timing lag) | 3 | n/a |
| C9 | Legal name with non-ASCII characters (en dash) | 11 | n/a |

**2,420 of 5,282 records (45.8%) fail at least one check that needs action** (C1, C3, C4, C6, C7, C8, C10) before the
record could be relied on as-is.

1. **Stale reference data.** 605 LEIs (11.5%) have lapsed; the median is 678 days past renewal, 418 are over a year
   overdue, the oldest 3,561 days. 355 of the lapsed records were also never registry-validated.
2. **Unverified identity is concentrated in trusts.** All 1,288 provident/superannuation/gratuity trusts are
   entity-supplied only (no public registry exists for them), so their KYC has to rest on the trust deed and trustee
   documents. Outside those trusts, 739 of 3,994 records (18.5%) are still entity-supplied only.
3. **Broken ownership chains.** 204 sub-schemes (202 AIF sub-schemes) link to neither an umbrella fund nor a manager,
   so the controlling party cannot be traced from the record.
4. **Possible duplicates.** e.g. *TATA MOTORS LIMITED SUPERANNUATION FUND* under two ISSUED LEIs
   (335800FT7Y5KD33EMD68, 335800K9ZHD3A8PQNM75); *Neo Special Credit Opportunities Fund II* under one ISSUED and one
   LAPSED LEI; two different LEIs whose entire legal name is "Scheme 1".
5. **Address errors a rule catches.** *Eximius Fund II*: PIN 122002 and city Sikandarpur (Gurugram, Haryana) but state
   recorded as Gujarat. 44 records carry no state at all.

### Sanctions name screening (OFAC SDN, entities incl. a.k.a. names: 21,389 names)
- **Naive fuzzy match** (token-set ratio ≥ 90 after removing legal suffixes): **2,228 alerts on 1,262 funds (23.9% of the
  book).** Almost all come from generic words: "T C CAPITAL CO LTD" reduces to "CAPITAL" and hits 316 funds; "Z AXIS LLC"
  (Russia) hits 118 Axis schemes; "SUN AND SUN LIMITED" hits 114 Aditya Birla Sun Life schemes.
- **Two-way distinctive-token guard** (every non-generic SDN word must match a client word at Jaro–Winkler ≥ 0.92, and
  ≥ 60% of the client's non-generic words must be explained by the SDN name): **18 alerts on 17 funds (−99.2%).**
- **All 18 reviewed: false positives** on name, entity type and jurisdiction (`results/alert_dispositions.csv`), e.g.
  ICI India Ltd staff funds vs the Iran-programme entity "ICI"; *India Office Assets Fund I* vs DPRK "Office 39".
- **Does the guard drop real hits?** Synthetic test on 300 random SDN entity names: kept 299/300 exact names (case and
  punctuation changed), 300/300 with "FUND I" appended, and 273/273 of the one-letter-swap variants the naive matcher
  itself caught (the naive matcher catches only 273/300 typos, a threshold limit worth knowing).

## Limits (stated plainly)
- LEI data is public reference data, not a bank's KYC file: no ID documents, beneficial owners, source of funds or
  transaction data. Checks are on what a record says, not on whether it is true.
- Screening is OFAC SDN only (no UN, EU, UK, India MHA lists, PEP or adverse media). The guard was tuned on this data;
  the recall test is synthetic. The 18 dispositions are on name, entity type and SDN address country only; a real
  review would also compare registration numbers and addresses and document the rationale in the case system.
- The PIN-to-state map uses the first two digits and is deliberately generous, so it under-flags.
- GLEIF and OFAC change daily; re-running gives slightly different counts.

## What I would do in week one on a real KYC queue
1. Run the same completeness and consistency rules on the team's own client records before periodic reviews, so
   analysts get a pre-sorted list (stale, unverified, broken ownership chain, duplicate) instead of finding gaps mid-review.
2. Measure the screening false-positive rate per list and per rule, and propose guard rules with a recall test like the
   one above, signed off by Compliance before any change.
3. Track the rework: how many records come back from QC and for which field, then fix the collection step that causes it.

## Run it
```bash
pip install -r requirements.txt
./fetch.sh            # GLEIF API (no key) + OFAC SDN files
python3 kyc_checks.py # ~40 s on 2 vCPUs; writes results/
```
Files: `fetch_gleif.py`, `kyc_checks.py`, `results/summary.json`, `results/exceptions.csv`,
`results/screening_review.csv` (all 2,228 alerts with the guard's decision), `results/alert_dispositions.csv`.
