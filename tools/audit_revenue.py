import json
from collections import Counter

def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["contacts"]

real = load("real_out/contacts.json")
gadata = load("gadata_out/contacts.json")
allc = real + gadata
print(f"total: {len(allc)}  (real_out={len(real)}, gadata={len(gadata)})")

# 1. Renewable contact channels (email/website) on businesses
biz = [c for c in allc if c.get("is_business")]
biz_email = [c for c in biz if (c.get("email") or "").strip()]
biz_web = [c for c in biz if (c.get("website") or "").strip()]
print(f"\nB2B surface: {len(biz)} businesses | {len(biz_email)} with email | {len(biz_web)} with website")

# 2. Diaspora real-estate-intent contacts
dia = [c for c in allc if c.get("diaspora")]
print(f"diaspora: {len(dia)}")
dia_re = [c for c in dia if any(k in ((c.get("groups") or '') + (c.get('group_tags') or '') + (c.get('org') or '')).lower()
                               for k in ['real_estate','estate','property','realtor','real estate'])]
print(f"diaspora with real-estate signal: {len(dia_re)}")

# 3. Group broadcast surface: group memberships
groups = Counter()
for c in allc:
    for g in (c.get("groups") or "").split(";"):
        g = g.strip()
        if g:
            groups[g] += 1
members_in_groups = sum(v for k, v in groups.items())
print(f"\ngroups: {len(groups)} distinct | {members_in_groups} total memberships")

# 4. Home-market hot/warm + businesses with engagement
hot_warm = [c for c in allc if c.get("activity") in ("hot", "warm")]
hw_biz = [c for c in hot_warm if c.get("is_business")]
hw_dia = [c for c in hot_warm if c.get("diaspora")]
print(f"\nengaged (hot+warm): {len(hot_warm)} | engaged businesses: {len(hw_biz)} | engaged diaspora: {len(hw_dia)}")

# 5. Named real-estate/construction agents on WhatsApp (GH)
gh_biz = [c for c in allc if c.get("country") == "GH" and c.get("is_business") and c.get("valid")]
print(f"GH valid business numbers: {len(gh_biz)}")

# 6. What do hot contacts look like (vertical distribution)
hv = Counter()
for c in hot_warm:
    g = (c.get("groups") or "") + " " + (c.get("org") or "")
    gl = g.lower()
    if any(k in gl for k in ["real_estate","estate"]): hv["real_estate"] += 1
    elif any(k in gl for k in ["construction","contractor"]): hv["construction"] += 1
    elif any(k in gl for k in ["wholesal","market","store","shop"]): hv["wholesale_retail"] += 1
    elif any(k in gl for k in ["hotel","restaurant","lodge"]): hv["hospitality"] += 1
    elif any(k in gl for k in ["pharma","hospital","clinic","medical"]): hv["healthcare"] += 1
    else: hv["general/unknown"] += 1
print(f"engaged by vertical: {dict(hv)}")
