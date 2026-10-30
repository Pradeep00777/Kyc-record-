from weasyprint import HTML
H = """<!doctype html><html><head><meta charset="utf-8"><title>Pradeep Rathore - JPMC KYC proof of work</title><style>
@page{size:A4;margin:11mm 13mm 10mm 13mm}
body{font-family:'Nimbus Sans','DejaVu Sans',sans-serif;font-size:8.75pt;line-height:1.3;color:#111;margin:0}
h1{font-size:14pt;margin:0 0 1pt}
.sub{font-size:8.4pt;color:#333;margin:0 0 4pt}
h2{font-size:9.4pt;text-transform:uppercase;letter-spacing:.6pt;margin:6pt 0 2pt;border-bottom:.7pt solid #333;padding-bottom:1pt}
p{margin:0 0 3pt}
table{border-collapse:collapse;width:100%;margin:2pt 0 3pt;font-size:8.3pt}
th,td{border:.5pt solid #999;padding:1.6pt 4pt;text-align:left;vertical-align:top}
th{background:#eee}
td.n{text-align:right;white-space:nowrap}
ol,ul{margin:1pt 0 2pt;padding-left:13pt} li{margin:.8pt 0}
.big{font-size:10pt;font-weight:bold}
.foot{font-size:7.8pt;color:#333;margin-top:4pt}
</style></head><body>
<h1>KYC record check: 5,282 Indian fund records, plus sanctions name screening</h1>
<p class="sub"><b>Pradeep Rathore</b> &middot; proof of work for Client Data Analyst, KYC Operations (JPMorganChase Asset &amp; Wealth Management, Bengaluru, req. 210788205) &middot; built and run 30 Oct 2026 &middot; code: github.com/Pradeep00777/Kyc-record-</p>
<p>The posting asks the analyst to &ldquo;review and enhance data collection and verification processes to ensure KYC records are accurate and complete.&rdquo; Bank KYC files are private, so I used the closest public stand-in: the <b>GLEIF LEI records</b> banks use as reference data for legal-entity clients, for <b>every India-domiciled fund</b> (mutual-fund schemes, AIFs, provident/superannuation/gratuity trusts), screened against the <b>OFAC SDN list</b>. Live book: <b>5,282</b> LEIs (4,677 issued + 605 lapsed; 757 retired/duplicate excluded).</p>
<h2>Completeness and consistency checks</h2>
<table><tr><th>Check (the question a KYC analyst asks of the record)</th><th>Records</th><th>Share</th></tr>
<tr><td>C1 LEI lapsed: renewal overdue, so the data is no longer re-validated</td><td class="n">605</td><td class="n">11.5%</td></tr>
<tr><td>C3 Entity-supplied only: identity never validated against a registry</td><td class="n">2,027</td><td class="n">38.4%</td></tr>
<tr><td>C4 Sub-scheme linked to neither its umbrella fund nor its manager</td><td class="n">204</td><td class="n">8.0% of sub-schemes</td></tr>
<tr><td>C6 Entity status blank on an issued LEI</td><td class="n">12</td><td class="n">0.2%</td></tr>
<tr><td>C7 PIN code inconsistent with state / state missing</td><td class="n">3 / 44</td><td class="n">0.9%</td></tr>
<tr><td>C10 Same legal name on two live LEIs (possible duplicate records)</td><td class="n">5 pairs</td><td class="n">0.2%</td></tr>
<tr><td><b>Records failing at least one check that needs action</b></td><td class="n"><b>2,420</b></td><td class="n"><b>45.8%</b></td></tr></table>
<ol>
<li><b>Stale data:</b> lapsed LEIs are a median <b>678 days</b> past renewal; 418 are over a year overdue; 355 of them were also never registry-validated.</li>
<li><b>Unverified identity sits in trusts:</b> all 1,288 PF/superannuation/gratuity trusts are entity-supplied only (no public registry exists), so their KYC must rest on the trust deed and trustee documents. Outside them, 739 of 3,994 (18.5%) are still unverified.</li>
<li><b>Broken ownership chains:</b> 204 sub-schemes (202 of them AIF sub-schemes) cannot be traced to a controlling party from the record.</li>
<li><b>Duplicates and errors a rule catches:</b> <i>Tata Motors Limited Superannuation Fund</i> under two issued LEIs; two different LEIs whose whole legal name is &ldquo;Scheme 1&rdquo;; <i>Eximius Fund II</i> with PIN 122002, city Sikandarpur (Gurugram, Haryana) but state recorded as Gujarat.</li>
</ol>
<h2>Sanctions name screening: cutting false positives without dropping real hits</h2>
<table><tr><th>Stage (21,389 OFAC SDN entity names and aliases)</th><th>Alerts</th><th>Funds alerted</th></tr>
<tr><td>Naive fuzzy match (token-set &ge; 90 after removing legal suffixes)</td><td class="n">2,228</td><td class="n">1,262 (23.9%)</td></tr>
<tr><td>Two-way distinctive-token guard (Jaro&ndash;Winkler &ge; 0.92 on non-generic words, both directions)</td><td class="n">18</td><td class="n">17</td></tr>
<tr><td>After my review of all 18 (name, entity type, SDN address country)</td><td class="n">0 true matches</td><td class="n">&minus;99.2% alerts</td></tr></table>
<ul>
<li>Why naive fails: &ldquo;T C CAPITAL CO LTD&rdquo; reduces to &ldquo;CAPITAL&rdquo; and hits 316 funds; &ldquo;Z AXIS LLC&rdquo; (Russia) hits 118 Axis schemes; &ldquo;SUN AND SUN LIMITED&rdquo; hits 114 Aditya Birla Sun Life schemes.</li>
<li>Recall test, 300 random SDN entity names: the guard kept <b>299/300</b> exact names (case/punctuation changed), 300/300 with &ldquo;FUND I&rdquo; appended, and 273/273 of the one-letter typos the naive matcher caught (naive itself catches only 273/300 typos).</li>
</ul>
<h2>Limits, and what I would do in week one</h2>
<p><b>Limits:</b> LEI data is reference data, not a KYC file: no ID documents, beneficial owners or transactions, and checks test what a record says, not whether it is true. Screening is OFAC SDN only (no UN/EU/UK/MHA lists, PEP or adverse media); the guard was tuned on this data and the recall test is synthetic; my 18 dispositions used name, entity type and country, where a real review would also compare registration numbers and addresses.</p>
<p><b>Week one:</b> (1) run the same rules on the team&rsquo;s records ahead of periodic reviews so analysts start from a sorted list (stale, unverified, broken chain, duplicate); (2) measure screening false positives per list and rule, and propose guard rules with a recall test, for Compliance sign-off; (3) track which fields come back from QC and fix the collection step that causes them.</p>
<p class="foot">Sources: GLEIF API (api.gleif.org, golden copy 30 Oct 2026); OFAC SDN, ALT and ADD files (treasury.gov/ofac/downloads). Python, rapidfuzz; ~40 s run. All counts reproducible from the code; public data only, no JPMorganChase data used.</p>
</body></html>"""
open("proof.html","w").write(H)
d = HTML(string=H).render(); print("pages", len(d.pages)); d.write_pdf("Pradeep_Rathore_JPMC_Proof.pdf")
