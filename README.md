# mywa — WhatsApp Contact Intelligence Toolkit

Enterprise-grade tool that extracts **every contact from a WhatsApp account** —
including **group members** you never saved — normalizes them to international
format, deduplicates across sources, and **segments them into targeted
opportunity lists** for outreach.

Pure Python 3 standard library. **Zero dependencies, zero installs.**

## Quick start

```powershell
# 1. Put your data somewhere (any of the below, in any combination)
#    - msgstore.db / wa.db exported from a WhatsApp backup
#    - contacts.vcf exported from your phone's contacts app
#    - data\adb_contacts.tsv produced by adb_extract.ps1
#    - a folder containing any of the above (auto-recursed)

# 2. Run
python -m mywa -i testdata --opportunity-groups "real estate, wholesale, import" --out out
```

Or: `run.bat -i data --opportunity-groups "real estate" --out out`

## Outputs (written to `--out`)

| File | Contents |
|---|---|
| `contacts.csv` | Every deduplicated contact: name, phone (E.164), country, carrier, activity, origin, group membership, message stats |
| `contacts.vcf` | All contacts re-exported as vCard (import anywhere) |
| `contacts.json` | Machine-readable dump of the above |
| `opportunities.csv` | Filtered, ranked lead list for targeted outreach |
| `report.html` | Standalone visual report: segment breakdown + opportunity table |

## How it extracts contacts

| Source | What it recovers |
|---|---|
| `msgstore.db` (modern & legacy schemas) | Everyone you ever DM'd **plus every group member**, with message counts and last-seen times |
| `wa.db` (legacy) | Saved contacts table + group participants |
| `.vcf` | Your phone's exported address book |
| `.tsv` (via `adb_extract.ps1`) | All contacts read off a USB-connected Android phone |

Duplicates are merged by normalized number; a contact found in a saved list and
in group chats gets their group tags merged onto one record.

## Segmentation

- **Activity**: `hot` (50+ msgs), `warm` (10–49), `recent` (last 90 days), `cold`
- **Origin**: `saved` / `direct` / `group_only` / `direct_and_group`
- **Carrier** for Ghana numbers: MTN, Telecel, AirtelTigo, Expresso, Glo
- **Country** detection (US, GB, NG, ZA, IN, CN, …)
- **Opportunity groups**: contacts whose groups match your keywords
  (e.g. `--opportunity-groups "real estate, wholesale"`)
- **Lead ranking** in `opportunities.csv`: hot/warm + matching groups first

## Extracting contacts from your phone directly (Android)

1. Install [platform-tools](https://developer.android.com/tools/releases/platform-tools)
   (adb) and enable **Developer options → USB debugging**.
2. Connect your phone, accept the debugging prompt.
3. Run:

```powershell
.\adb_extract.ps1          # -> data\adb_contacts.tsv
python -m mywa -i data
```

The script queries the device's Contacts Provider (the same source WhatsApp
reads) and saves name/number pairs. If it returns nothing, export a VCF from
your contacts app and point the tool at that instead.

## Options

```
--input, -i        file(s) or folder(s) to scan (required)
--out, -o          output directory            (default: out)
--country-code     default region for local numbers (default: GH)
--country-number   E.164 dial code (default derived, e.g. GH=233)
--opportunity-groups  keywords for targeted opportunities
--min-activity     hot|warm|recent|cold threshold (default: cold)
--contacts-only    skip opportunities + report
--dry-run          summarize without writing
```

## Notes & compliance

- All processing is **local** — no data leaves your machine.
- Only process WhatsApp data you are authorized to access.
- Use extracted lists only where recipients have consented to outreach.
  Segmented lead lists are a business-analysis aid; check applicable privacy
  (DPDP/GDPR-style) rules before contacting people.

## Development

```powershell
python tools\make_testdata.py     # generate synthetic msgstore/wa/vcf/tsv
python -m mywa -i testdata --opportunity-groups "real estate, wholesale, founders" --out out
```

## Live Demo ✅ Verified Oct 16 2026
Live: https://mywa.gabochie.com — waitlist + GHS 999 founders pricing, MoMo.

## Case Study — Dead groups to pipeline
Problem: 5k contacts stuck in WhatsApp. Build: Python CLI + CF Worker + D1, E164 dedupe. Result: 3 segmented lists in 1 command. Service: $900 in 7 days.
