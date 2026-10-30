#!/usr/bin/env bash
# Pull the public inputs. GLEIF changes daily, OFAC SDN changes often: re-running gives slightly different counts.
set -e
mkdir -p data
python3 fetch_gleif.py                                   # ~31 API pages, 6,000+ India FUND LEI records
curl -sL -o data/sdn.csv https://www.treasury.gov/ofac/downloads/sdn.csv
curl -sL -o data/alt.csv https://www.treasury.gov/ofac/downloads/alt.csv
curl -sL -o data/add.csv https://www.treasury.gov/ofac/downloads/add.csv   # addresses, used only for alert disposition
