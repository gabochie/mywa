"""Quick data analysis of all mywa output datasets."""
import json
import sys
import io
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

def analyze(path, label):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    contacts = data["contacts"]
    print(f"\n{'='*60}")
    print(f"  {label}: {len(contacts)} contacts")
    print(f"{'='*60}")

    act = Counter(c["activity"] for c in contacts)
    print(f"Activity: {dict(act)}")

    country = Counter(c["country"] for c in contacts)
    print(f"Countries: {dict(country)}")

    origin = Counter(c["origin"] for c in contacts)
    print(f"Origin: {dict(origin)}")

    valid = sum(1 for c in contacts if c["valid"])
    print(f"Valid mobile: {valid}")

    biz = sum(1 for c in contacts if c["is_business"])
    print(f"Businesses: {biz}")

    tags = Counter()
    for c in contacts:
        for t in (c.get("group_tags", "") or "").split(";"):
            t = t.strip()
            if t:
                tags[t] += 1
    if tags:
        print(f"Group tags: {dict(tags)}")

    diaspora = sum(1 for c in contacts if c.get("diaspora"))
    print(f"Diaspora: {diaspora}")

    named = sum(1 for c in contacts if c.get("named"))
    print(f"Named: {named}")

    carrier = Counter(c["carrier"] for c in contacts)
    print(f"Carriers: {dict(carrier)}")

    has_email = sum(1 for c in contacts if c.get("email", "").strip())
    print(f"Has email: {has_email}")

    has_org = sum(1 for c in contacts if c.get("org", "").strip())
    print(f"Has org: {has_org}")

    has_website = sum(1 for c in contacts if c.get("website", "").strip())
    print(f"Has website: {has_website}")

    gc = Counter()
    for c in contacts:
        for g in (c.get("groups", "") or "").split(";"):
            g = g.strip()
            if g:
                gc[g] += 1
    print(f"Unique groups: {len(gc)}")
    print(f"Top 20 groups:")
    for g, n in gc.most_common(20):
        print(f"  {n:5d}  {g}")

    hot = [c for c in contacts if c["activity"] == "hot"]
    print(f"\nHot contacts ({len(hot)}):")
    for c in hot[:10]:
        print(f"  {c['name'][:25]:25s} | {c['phone']} | msgs:{c['msg_count']} | groups:{(c.get('groups','') or '')[:80]}")

    warm = [c for c in contacts if c["activity"] == "warm"]
    print(f"\nWarm contacts ({len(warm)}):")
    for c in warm[:10]:
        print(f"  {c['name'][:25]:25s} | {c['phone']} | msgs:{c['msg_count']} | groups:{(c.get('groups','') or '')[:80]}")

    dg = [c for c in contacts if c["origin"] == "direct_and_group"]
    print(f"\nDirect+Group contacts ({len(dg)}):")
    for c in dg[:10]:
        print(f"  {c['name'][:25]:25s} | {c['phone']} | msgs:{c['msg_count']}")

    print(f"\nBusinesses with details ({biz}):")
    for c in contacts:
        if c.get("is_business"):
            print(f"  {c['name'][:25]:25s} | org:{c.get('org','')[:30]} | city:{c.get('city','')} | web:{c.get('website','')[:40]}")

if __name__ == "__main__":
    analyze("real_out/contacts.json", "PRODUCTION (real_out)")
    analyze("gadata_out/contacts.json", "GADATA (Google businesses)")
