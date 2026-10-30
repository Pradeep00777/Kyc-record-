"""Download every LEI record whose legal address is in India and whose entity category is FUND (GLEIF public API, no key)."""
import json, time, urllib.request, urllib.parse
BASE = "https://api.gleif.org/api/v1/lei-records"
out, page = [], 1
while True:
    q = {"filter[entity.legalAddress.country]": "IN", "filter[entity.category]": "FUND",
         "page[size]": "200", "page[number]": str(page)}
    url = BASE + "?" + urllib.parse.urlencode(q)
    for attempt in range(5):
        try:
            d = json.load(urllib.request.urlopen(url, timeout=60)); break
        except Exception as e:
            time.sleep(3 * (attempt + 1))
    out += d["data"]
    if page >= d["meta"]["pagination"]["lastPage"]: break
    page += 1
json.dump({"golden_copy": d["meta"]["goldenCopy"]["publishDate"], "records": out}, open("data/gleif_in_funds.json", "w"))
print(len(out), "records; golden copy", d["meta"]["goldenCopy"]["publishDate"])
