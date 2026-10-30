#!/usr/bin/env python3
"""KYC reference-data checks on India-domiciled fund LEI records (GLEIF), plus OFAC SDN name screening.

Population: every GLEIF LEI record with legal address in India and entity category FUND
(mutual-fund schemes, AIFs, provident/superannuation funds), pulled by fetch_gleif.py.
"Live book" = LEIs with registration status ISSUED or LAPSED (RETIRED and DUPLICATE are excluded,
because a KYC team would not onboard against them).

Each check mirrors a question a KYC analyst asks of a client record before relying on it.
Outputs: results/summary.json, results/exceptions.csv (one row per record per failed check),
results/screening_review.csv (every name-screening alert, with the guard's decision).
"""
import csv, json, re, collections, datetime as dt, os
from rapidfuzz import fuzz, process
import numpy as np
from rapidfuzz.distance import JaroWinkler

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(f"{HERE}/data/gleif_in_funds.json"))
RECS = D["records"]
TODAY = dt.date(2026, 10, 30)   # run date (IST); GLEIF golden copy published the same morning
os.makedirs(f"{HERE}/results", exist_ok=True)

LEGAL_FORMS = {"VX5J": "Mutual Fund sub-scheme", "U8NM": "Mutual Fund", "EX8U": "Alternative Investment Fund",
               "HBQK": "AIF sub-scheme", "JKJX": "Provident/Superannuation/Gratuity fund", "8888": "Other (free text)",
               "9999": "Not given"}
SUB_SCHEMES = {"VX5J", "HBQK"}

def day(s):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", s or "")
    return dt.date.fromisoformat(m.group(1)) if m else None

# --- India PIN code: first two digits -> states/UTs (ISO 3166-2:IN codes), deliberately generous
PIN2 = {}
def addpins(codes, prefixes):
    for p in prefixes:
        PIN2.setdefault(p, set()).update(codes)
addpins({"IN-DL"}, [11]); addpins({"IN-HR"}, [12, 13]); addpins({"IN-PB", "IN-CH"}, [14, 15, 16])
addpins({"IN-HP"}, [17]); addpins({"IN-JK", "IN-LA"}, [18, 19]); addpins({"IN-UP", "IN-UT", "IN-UK"}, range(20, 29))
addpins({"IN-RJ"}, range(30, 35)); addpins({"IN-GJ"}, range(36, 40)); addpins({"IN-DH", "IN-DN", "IN-DD"}, [39])
addpins({"IN-MH"}, range(40, 45)); addpins({"IN-GA"}, [40]); addpins({"IN-MP"}, range(45, 49)); addpins({"IN-CT", "IN-CG"}, [49])
addpins({"IN-TG", "IN-TS", "IN-AP"}, range(50, 54)); addpins({"IN-KA"}, range(56, 60)); addpins({"IN-TN"}, range(60, 65))
addpins({"IN-PY"}, [53, 60, 67]); addpins({"IN-KL", "IN-LD"}, range(67, 70)); addpins({"IN-WB", "IN-SK", "IN-AN"}, range(70, 75))
addpins({"IN-OR", "IN-OD"}, range(75, 78)); addpins({"IN-AS", "IN-AR", "IN-MN", "IN-ML", "IN-MZ", "IN-NL", "IN-TR"}, [78, 79])
addpins({"IN-BR", "IN-JH"}, range(80, 86))

def norm_name(s):
    s = s.upper().replace("&", " AND ")
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

exceptions = []   # (lei, name, legal_form, reg_status, check, detail)
def flag(a, check, detail=""):
    e = a["entity"]
    exceptions.append((a["lei"], e["legalName"]["name"], LEGAL_FORMS.get(e["legalForm"]["id"], e["legalForm"]["id"]),
                       a["registration"]["status"], check, detail))

reg_status = collections.Counter(r["attributes"]["registration"]["status"] for r in RECS)
live = [r for r in RECS if r["attributes"]["registration"]["status"] in ("ISSUED", "LAPSED")]
lapsed_days = []
by_form = collections.Counter()
for r in live:
    a, e, g, rel = r["attributes"], r["attributes"]["entity"], r["attributes"]["registration"], r["relationships"]
    form = e["legalForm"]["id"]; by_form[form] += 1
    # C1 LEI lapsed: renewal overdue, so the record's reference data is no longer being re-validated
    if g["status"] == "LAPSED":
        d = (TODAY - day(g["nextRenewalDate"])).days
        lapsed_days.append(d); flag(a, "C1 LEI lapsed (renewal overdue)", f"{d} days past renewal date {day(g['nextRenewalDate'])}")
    # C2 status says ISSUED but renewal date already passed (internal inconsistency)
    if g["status"] == "ISSUED" and day(g["nextRenewalDate"]) and day(g["nextRenewalDate"]) < TODAY:
        flag(a, "C2 ISSUED but renewal date passed", str(day(g["nextRenewalDate"])))
    # C3 identity never checked against an authoritative register
    if g["corroborationLevel"] == "ENTITY_SUPPLIED_ONLY":
        flag(a, "C3 Entity-supplied only: not validated against a registry",
             f"registeredAt={e['registeredAt']['id']}; registeredAs={e['registeredAs']}")
    # C4 sub-scheme with no link to its umbrella scheme or its manager: the controlling party cannot be traced from the record
    if form in SUB_SCHEMES and "fund-manager" not in rel and "umbrella-fund" not in rel:
        flag(a, "C4 Sub-scheme with no umbrella-fund and no fund-manager link")
    # C5 any fund with no fund-manager relationship
    if "fund-manager" not in rel:
        flag(a, "C5 No fund-manager relationship recorded")
    # C6 entity status not ACTIVE on a live LEI
    if e["status"] != "ACTIVE":
        flag(a, "C6 Entity status not ACTIVE", e["status"])
    # C7 address: PIN format and PIN vs state consistency; missing state
    la = e["legalAddress"]; pc = (la.get("postalCode") or "").replace(" ", "")
    if not re.fullmatch(r"[1-9]\d{5}", pc):
        flag(a, "C7a Legal-address PIN missing or malformed", repr(la.get("postalCode")))
    elif la.get("region") and la["region"] not in PIN2.get(int(pc[:2]), set()):
        flag(a, "C7b PIN code inconsistent with state", f"PIN {pc} vs {la['region']}, city {la.get('city')}")
    if not la.get("region"):
        flag(a, "C7c Legal-address state missing", f"city {la.get('city')}")
    # C8 successor entity recorded on a live LEI (merged/rolled into another fund?)
    if e.get("successorEntity", {}).get("lei") or e.get("successorEntities"):
        flag(a, "C8 Successor entity recorded on a live LEI", str(e.get("successorEntity", {}).get("lei")))
    # C9 name hygiene
    raw = e["legalName"]["name"]
    if raw != raw.strip() or "  " in raw or re.search(r"[^\x20-\x7E]", raw):
        flag(a, "C9 Legal name has stray spaces or non-ASCII characters", repr(raw))

# C10 possible duplicate client records: identical normalised legal name on two or more live LEIs
names = collections.defaultdict(list)
for r in live:
    names[norm_name(r["attributes"]["entity"]["legalName"]["name"])].append(r)
dup_groups = {k: v for k, v in names.items() if len(v) > 1}
for k, v in dup_groups.items():
    for r in v:
        flag(r["attributes"], "C10 Same normalised legal name as another live LEI",
             "; ".join(x["attributes"]["lei"] for x in v if x is not r))

# ---------------- Sanctions name screening vs OFAC SDN (entities, incl. a.k.a./f.k.a. names)
sdn_type, sdn_name, sdn_prog = {}, {}, {}
for row in csv.reader(open(f"{HERE}/data/sdn.csv", encoding="latin-1")):
    if len(row) < 4: continue
    uid = row[0]; sdn_type[uid] = row[2].strip(); sdn_name[uid] = row[1]; sdn_prog[uid] = row[3]
targets = [(u, n) for u, n in sdn_name.items() if sdn_type[u] == "-0-"]   # -0- = entity (not individual/vessel/aircraft)
for row in csv.reader(open(f"{HERE}/data/alt.csv", encoding="latin-1")):
    if len(row) >= 4 and sdn_type.get(row[0]) == "-0-":
        targets.append((row[0], row[3]))
LEGAL_SUFFIX = {"LTD", "LIMITED", "PVT", "PRIVATE", "LLC", "INC", "CO", "COMPANY", "CORP", "CORPORATION", "SA", "JSC",
                "OOO", "GMBH", "FZE", "FZCO", "PLC", "AG", "BV", "LLP", "THE", "OF", "AND"}
GENERIC = {"FUND", "FUNDS", "TRUST", "SCHEME", "INDIA", "INDIAN", "CAPITAL", "INVESTMENT", "INVESTMENTS", "GROWTH",
           "EQUITY", "PLAN", "SERIES", "OPPORTUNITIES", "OPPORTUNITY", "PARTNERS", "VENTURES", "VENTURE", "ETF", "INDEX",
           "MUTUAL", "GLOBAL", "INTERNATIONAL", "ASSET", "ASSETS", "MANAGEMENT", "HOLDING", "HOLDINGS", "GROUP",
           "FINANCE", "FINANCIAL", "BANK", "EMPLOYEES", "PROVIDENT", "SUPERANNUATION", "GRATUITY", "BENEFIT",
           "PENSION", "TRADING", "INDUSTRIES", "ENTERPRISES", "DEBT", "CREDIT", "INCOME", "VALUE", "STRATEGIC", "FIRST",
           "NATIONAL", "DEVELOPMENT", "INFRASTRUCTURE", "ENERGY", "REAL", "ESTATE", "INVESTMENT", "SECURITIES",
           "STAFF", "WELFARE", "ALTERNATIVE", "EMERGING", "MARKETS", "FUTURE", "NEW", "TECHNOLOGY", "TECHNOLOGIES",
           "OIL", "GAS", "SHIPPING", "AIR", "POWER", "EXPORT", "IMPORT", "GENERAL", "SERVICES", "TRADE", "BHARAT"}
def toks(s):
    return [t for t in norm_name(s).split() if t not in LEGAL_SUFFIX and not t.isdigit() and len(t) > 1]
T = [(u, n, " ".join(toks(n)), [t for t in toks(n) if t not in GENERIC]) for u, n in targets]
T = [t for t in T if t[2]]
def guard(nd, sd):
    """Escalate only if every distinctive SDN token matches a distinctive client token (Jaro-Winkler >= 0.92)
    and at least 60% of the client's distinctive tokens are explained by the SDN name (two-way coverage)."""
    if not sd or not nd: return False
    sdn_cov = all(any(JaroWinkler.similarity(x, y) >= 0.92 for y in nd) for x in sd)
    cli_cov = sum(any(JaroWinkler.similarity(y, x) >= 0.92 for x in sd) for y in nd) / len(nd)
    return sdn_cov and cli_cov >= 0.6

alerts = []
client = []
for r in live:
    a = r["attributes"]; nm = a["entity"]["legalName"]["name"]
    client.append((a["lei"], nm, " ".join(toks(nm)), [t for t in toks(nm) if t not in GENERIC]))
M = process.cdist([c[2] for c in client], [t[2] for t in T], scorer=fuzz.token_set_ratio, score_cutoff=90, workers=-1)
for i, j in zip(*np.nonzero(M)):
    lei, nm, nt, nd = client[i]; u, sn, st, sd = T[j]
    if not nt: continue
    ok = guard(nd, sd)
    alerts.append((lei, nm, sn, sdn_prog[u], u, round(float(M[i, j]), 1), "ESCALATE" if ok else "auto-cleared: generic-word match"))

# ---------------- Does the guard still catch real hits? Synthetic recall test on known SDN entity names.
import random
random.seed(7)
pool = [t for t in T if t[3] and len(t[2]) >= 6]
sample = random.sample(pool, 300)
def typo(w):
    i = random.randrange(1, len(w) - 1) if len(w) > 2 else 0
    return w[:i] + w[i + 1] + w[i] + w[i + 2:] if len(w) > 3 else w
variants = {
    "exact name, punctuation/case changed": lambda t: t[1].lower().replace(".", "").replace(",", ""),
    "name + ' FUND I' appended": lambda t: t[1] + " FUND I",
    "one adjacent-letter swap in the longest distinctive word": lambda t: " ".join(typo(w) if w == max(t[3], key=len) else w for w in toks(t[1])),
}
recall = {}
for label, fn in variants.items():
    q = [fn(t) for t in sample]
    qt = [" ".join(toks(x)) for x in q]
    MM = process.cdist(qt, [t[2] for t in T], scorer=fuzz.token_set_ratio, score_cutoff=90, workers=-1)
    naive_hit = guard_hit = 0
    for i, t in enumerate(sample):
        js = [j for j in np.nonzero(MM[i])[0] if T[j][0] == t[0]]
        if js: naive_hit += 1
        nd = [x for x in toks(q[i]) if x not in GENERIC]
        if any(guard(nd, T[j][3]) for j in js): guard_hit += 1
    recall[label] = {"n": len(sample), "naive_caught": naive_hit, "guard_caught": guard_hit}

with open(f"{HERE}/results/exceptions.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["lei", "legal_name", "legal_form", "lei_status", "check", "detail"]); w.writerows(exceptions)
with open(f"{HERE}/results/screening_review.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["lei", "client_name", "sdn_name", "sdn_program", "sdn_uid", "token_set_score", "guard_decision"]); w.writerows(alerts)

by_check = collections.Counter(c for *_, c, _ in [(x[0], x[4], x[5]) for x in exceptions])
by_check = collections.Counter(x[4] for x in exceptions)
recs_with_any = len({x[0] for x in exceptions})
# exceptions that need action before relying on the record (exclude C5 which is informational for non-sub-schemes)
action = {"C1 LEI lapsed (renewal overdue)", "C3 Entity-supplied only: not validated against a registry",
          "C4 Sub-scheme with no umbrella-fund and no fund-manager link", "C6 Entity status not ACTIVE",
          "C7a Legal-address PIN missing or malformed", "C7b PIN code inconsistent with state", "C7c Legal-address state missing",
          "C10 Same normalised legal name as another live LEI", "C8 Successor entity recorded on a live LEI"}
recs_action = len({x[0] for x in exceptions if x[4] in action})
# overlap: lapsed AND entity-supplied-only
lapsed_set = {x[0] for x in exceptions if x[4].startswith("C1")}
eso_set = {x[0] for x in exceptions if x[4].startswith("C3")}
form_c3 = collections.Counter(x[2] for x in exceptions if x[4].startswith("C3"))
form_live = {LEGAL_FORMS.get(k, k): v for k, v in by_form.items()}
lapsed_days.sort()
summary = {
    "run_date": str(TODAY), "gleif_golden_copy": D["golden_copy"],
    "population_all_statuses": len(RECS), "registration_status": dict(reg_status),
    "live_book_issued_or_lapsed": len(live), "live_by_legal_form": form_live,
    "exceptions_by_check": dict(sorted(by_check.items())),
    "records_with_any_exception": recs_with_any, "records_needing_action": recs_action,
    "lapsed_days_overdue": {"median": lapsed_days[len(lapsed_days)//2] if lapsed_days else None,
                             "over_365": sum(d > 365 for d in lapsed_days), "max": max(lapsed_days) if lapsed_days else None},
    "lapsed_and_entity_supplied_only": len(lapsed_set & eso_set),
    "entity_supplied_only_by_form": dict(form_c3),
    "duplicate_name_groups": len(dup_groups), "records_in_duplicate_groups": sum(len(v) for v in dup_groups.values()),
    "sdn_entity_names_screened": len(T),
    "screening_alerts_naive": len(alerts), "screening_alerts_after_guard": sum(a[-1] == "ESCALATE" for a in alerts),
    "clients_with_naive_alert": len({a[0] for a in alerts}),
    "clients_with_guarded_alert": len({a[0] for a in alerts if a[-1] == "ESCALATE"}),
    "guard_recall_test_on_known_sdn_names": recall,
}
json.dump(summary, open(f"{HERE}/results/summary.json", "w"), indent=1)
print(json.dumps(summary, indent=1))
