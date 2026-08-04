import json

with open("revenue_out/revenue.json", "r", encoding="utf-8") as f:
    r = json.load(f)
s = r["summary"]
print("=== CHANNELS ===")
for k, v in s["channels"].items():
    print(f"  {k}: {v}")

print("\n=== COUNTRY (top 8) ===")
for cname, c in sorted(r["segments"]["by_country"].items(), key=lambda x: -x[1]["count"])[:8]:
    print(f"  {cname:8s} {c['count']:6d} biz:{c['businesses']:6d} emails:{c['emails']:5d} web:{c['with_website']:5d} tier:{c['tier']}")

print("\n=== VERTICALS ===")
for vid, v in sorted(r["segments"]["by_vertical"].items(), key=lambda x: -x[1]["count"]):
    print(f"  {vid:18s} {v['count']:5d} engaged:{v['engaged']:4d} pipeline:{v['pipeline']:>9,} sell:{', '.join(v['products'])}")

print("\n=== PLAYBOOK (top 15) ===")
for p in r["playbook"][:15]:
    print(f"  {p['rank']:3d}. {p['name'][:28]:28s} {p['phone']} {p['activity']:6s} {p['vertical']:15s} score:{p['value_score']:.2f} sell:{p['sell'][0]}")
