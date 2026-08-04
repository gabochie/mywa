# Audit model: what does it take to hit GHS 1M and GHS 10M/yr?
# Grounded in data: 15,739 businesses, 3,134 diaspora (728 RE-intent), 488 groups / 23,125 memberships

# ---- Channel assumptions (conservative, Ghana market rates) ----
MODEL = {
    # Retainers: WhatsApp CRM + campaign management for SMEs
    "B2B retainers":        {"units": "clients", "price": 1500, "margin": 0.6},
    # One-off broadcast/marketing campaigns
    "Campaigns":            {"units": "campaigns", "price": 800, "margin": 0.7},
    # Diaspora real estate: 1.5% referral commission on avg GHS 800k property
    "RE referrals":         {"units": "deals", "price": 12000, "margin": 0.5},
    # Lead packs / data / enrichment
    "Product services":     {"units": "packs", "price": 200, "margin": 0.9},
    # Group broadcast sponsorship
    "Group sponsorship":    {"units": "sponsors/mo", "price": 600, "margin": 0.7},
    # SaaS licensing of the toolkit itself
    "SaaS licenses":        {"units": "licenses", "price": 2500, "margin": 0.85},
}

def show(label, monthly_mix):
    total = sum(v * MODEL[k]["price"] for k, v in monthly_mix.items())
    print(f"\n=== {label}: {total:,.0f} GHS/month ({total*12:,.0f} GHS/yr) ===")
    for k, v in monthly_mix.items():
        m = MODEL[k]
        print(f"  {k:<18} {v:>6} {m['units']:<12} x {m['price']:>6,} = {v*m['price']:>10,.0f}")

# ---- GHS 1M/yr = ~83K/mo ----
show("TARGET 1 (GHS 1.0M/yr)", {
    "B2B retainers":   20,   # 20 SME clients x 1,500
    "Campaigns":       15,   # 15 one-offs
    "RE referrals":    2,    # 2 diaspora deals/mo
    "Product services": 40,  # 40 lead packs
    "Group sponsorship": 10, # 10 sponsors
})

# ---- GHS 10M/yr (7 figures) = ~833K/mo ----
show("TARGET 2 (GHS 10M/yr)", {
    "B2B retainers":   80,   # 80 clients
    "Campaigns":       60,
    "RE referrals":    20,   # 20 RE deals/mo
    "Product services": 200,
    "Group sponsorship": 30,
    "SaaS licenses":   50,
})

# ---- Conversion math: 15,739 businesses to 20 retainers ----
print("\n=== Conversion funnel for 20 retainers ===")
print("15,739 businesses available")
for step, pct in [("contacted", 0.30), ("replied", 0.25), ("qualified", 0.30), ("closed", 0.20)]:
    print(f"  {step:<10} conversion {pct*100:.0f}%")

c = 15739
for step, pct in [("contacted", 0.30), ("replied", 0.25), ("qualified", 0.30), ("closed", 0.20)]:
    c *= pct
    print(f"  -> {c:,.0f} {step}")

print("\n=== Conversion math for 2 diaspora RE deals/mo (728 RE-intent) ===")
c2 = 728
for step, pct in [("reachable", 0.50), ("engaged", 0.30), ("site-visit", 0.20), ("closed", 0.05)]:
    c2 *= pct
    print(f"  {step:<10} -> {c2:,.0f}")
print(f"  = {c2:.1f} deals from one full pass of the 728-person list")
