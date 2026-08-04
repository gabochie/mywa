// mywa cloud API - public landing, smart waitlist validation, admin proxy.
// Public routes:
//   POST /api/lead         - join waiting list (scored, positioned)
//   POST /api/track        - engagement events (pricing view, return, share)
//   GET  /api/health       - liveness
// Admin routes (x-admin-token required):
//   GET  /api/waitlist         - full list with position + score
//   GET  /api/waitlist/stats   - cards, daily series, vertical/source mix
//   POST /api/waitlist/status  - update {id, status}
//   GET  /api/leads/count      - quick counter (legacy)

const RATE_LIMIT_PER_IP = 5;
const rateBuckets = new Map();
const HIGH_VALUE_VERTICALS = new Set([
  "real_estate", "agency", "construction", "hospitality", "finance",
]);

const VERTICAL_KEYWORDS = [
  ["real_estate", ["real estate", "property", "estate", "land", "housing", "agent"]],
  ["agency", ["agency", "marketing", "advert", "digital", "media", "brand"]],
  ["construction", ["construction", "contractor", "building", "civil", "engineer"]],
  ["hospitality", ["hotel", "restaurant", "food", "lodge", "cater", "bar"]],
  ["retail", ["shop", "store", "clothing", "cosmetics", "beauty", "retail", "salon", "fashion"]],
  ["healthcare", ["health", "pharma", "hospital", "clinic", "medical", "doctor", "dentist"]],
  ["finance", ["finance", "insurance", "loan", "bank", "fintech", "investment"]],
];

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Access-Control-Allow-Origin": "*" },
  });
}

function classifyVertical(offer, business) {
  const hay = `${offer || ""} ${business || ""}`.toLowerCase();
  for (const [key, kws] of VERTICAL_KEYWORDS) {
    if (kws.some((k) => hay.includes(k))) return key;
  }
  return "other";
}

function isGhanaMobile(phone) {
  const d = phone.replace(/\D/g, "");
  if (d.length === 12 && d.startsWith("233")) return ["5", "2", "1", "7"].includes(d[3]);
  if (d.length === 10 && d.startsWith("0")) return ["5", "2", "1", "7"].includes(d[1]);
  return false;
}

function isRateLimited(ip) {
  const now = Date.now();
  const bucket = rateBuckets.get(ip) || { window: now, count: 0 };
  if (now - bucket.window > 60_000) {
    bucket.window = now;
    bucket.count = 0;
  }
  bucket.count += 1;
  rateBuckets.set(ip, bucket);
  return bucket.count > RATE_LIMIT_PER_IP;
}

async function trackEvent(env, visitorId, event, ts) {
  if (!visitorId || !event) return;
  await env.mywa_db
    .prepare("INSERT INTO events (id, visitor_id, event, ts) VALUES (?, ?, ?, ?)")
    .bind(crypto.randomUUID(), visitorId, event, ts)
    .run();
}

async function engagementScore(env, visitorId) {
  if (!visitorId) return 0;
  const row = await env.mywa_db
    .prepare("SELECT COUNT(*) AS c FROM events WHERE visitor_id = ?")
    .bind(visitorId)
    .first();
  return Math.min((row.c || 0), 1);
}

async function handleLead(request, env) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ ok: false, error: "invalid request" }, 400);
  }
  const name = String(body.name || "").trim();
  const business = String(body.business || "").trim();
  const phone = String(body.phone || "").trim();
  const offer = String(body.offer || "").trim();
  const source = String(body.source || "direct").trim().slice(0, 40) || "direct";
  const visitorId = String(body.visitor_id || "").slice(0, 64);

  if (!name || !phone) return json({ ok: false, error: "name and phone are required" }, 400);
  if (phone.replace(/\D/g, "").length < 9) {
    return json({ ok: false, error: "enter a valid WhatsApp number" }, 400);
  }
  if (isRateLimited(request.headers.get("cf-connecting-ip") || "unknown")) {
    return json({ ok: false, error: "too many requests, try again later" }, 429);
  }

  const ts = Date.now();
  const vertical = classifyVertical(offer, business);
  const eng = await engagementScore(env, visitorId);

  // Smart demand score (0-5): verified business + offer + high-value vertical
  // + Ghana mobile + demonstrated engagement.
  let score = 0;
  if (business) score += 1;
  if (offer) score += 1;
  if (HIGH_VALUE_VERTICALS.has(vertical)) score += 1;
  if (isGhanaMobile(phone)) score += 1;
  score += eng;
  score = Math.min(score, 5);

  const id = crypto.randomUUID();
  await env.mywa_db
    .prepare(
      `INSERT INTO leads (id, name, business, phone, offer, source, status, score, ip, ua, visitor_id, ts, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, 'waiting', ?, ?, ?, ?, ?, ?)`
    )
    .bind(
      id, name, business, phone, offer, source, score,
      request.headers.get("cf-connecting-ip") || "",
      (request.headers.get("user-agent") || "").slice(0, 200),
      visitorId, ts, ts,
    )
    .run();
  await trackEvent(env, visitorId, "joined", ts);

  const pos = await env.mywa_db
    .prepare("SELECT COUNT(*) AS c FROM leads WHERE ts < ?").bind(ts).first();
  return json({ ok: true, id, position: (pos.c || 0) + 1, score, vertical });
}

async function handleTrack(request, env) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ ok: false, error: "invalid request" }, 400);
  }
  await trackEvent(env, String(body.visitor_id || ""), String(body.event || ""), Date.now());
  return json({ ok: true });
}

function authorized(request, env) {
  return env.ADMIN_TOKEN && request.headers.get("x-admin-token") === env.ADMIN_TOKEN;
}

async function handleWaitlist(env) {
  const rows = await env.mywa_db
    .prepare(
      `SELECT id, name, business, phone, offer, source, status, score, ts, updated_at,
              ROW_NUMBER() OVER (ORDER BY ts) AS position
       FROM leads ORDER BY ts DESC`
    )
    .all();
  return json({ ok: true, leads: rows.results, count: rows.results.length });
}

async function handleStats(env) {
  const total = await env.mywa_db.prepare("SELECT COUNT(*) AS c FROM leads").first();
  const today = await env.mywa_db
    .prepare("SELECT COUNT(*) AS c FROM leads WHERE ts >= ?")
    .bind(Date.now() - 86400000).first();
  const byStatus = (await env.mywa_db
    .prepare("SELECT status, COUNT(*) AS n FROM leads GROUP BY status").all()).results;
  const byVertical = (await env.mywa_db
    .prepare("SELECT vertical_class AS v, COUNT(*) AS n FROM (SELECT CASE WHEN offer LIKE '%estate%' OR offer LIKE '%property%' OR offer LIKE '%land%' THEN 'real_estate' WHEN offer LIKE '%agency%' OR offer LIKE '%market%' THEN 'agency' ELSE 'other' END AS vertical_class FROM leads) GROUP BY vertical_class").all()).results;
  const daily = (await env.mywa_db
    .prepare(
      `SELECT strftime('%Y-%m-%d', ts/1000, 'unixepoch') AS day, COUNT(*) AS n
       FROM leads WHERE ts >= ?
       GROUP BY day ORDER BY day ASC`
    )
    .bind(Date.now() - 14 * 86400000).all()).results;
  const bySource = (await env.mywa_db
    .prepare("SELECT source, COUNT(*) AS n FROM leads GROUP BY source ORDER BY n DESC").all()).results;
  const byScore = (await env.mywa_db
    .prepare("SELECT score, COUNT(*) AS n FROM leads GROUP BY score ORDER BY score ASC").all()).results;
  const invited = await env.mywa_db
    .prepare("SELECT COUNT(*) AS c FROM leads WHERE status IN ('invited','onboarded','paid')").first();
  const converted = await env.mywa_db
    .prepare("SELECT COUNT(*) AS c FROM leads WHERE status IN ('onboarded','paid')").first();
  return json({
    ok: true,
    total: total.c || 0,
    today: today.c || 0,
    invited: invited.c || 0,
    converted: converted.c || 0,
    by_status: byStatus,
    by_vertical: byVertical,
    by_source: bySource,
    by_score: byScore,
    daily,
  });
}

async function handleStatus(request, env) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ ok: false, error: "invalid request" }, 400);
  }
  const id = String(body.id || "");
  const status = String(body.status || "");
  if (!id || !["waiting", "invited", "onboarded", "paid", "dismissed"].includes(status)) {
    return json({ ok: false, error: "invalid id or status" }, 400);
  }
  await env.mywa_db
    .prepare("UPDATE leads SET status = ?, updated_at = ? WHERE id = ?")
    .bind(status, Date.now(), id)
    .run();
  return json({ ok: true });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: { "Access-Control-Allow-Origin": "*" } });
    }
    if (request.method === "POST" && path === "/api/lead") return handleLead(request, env);
    if (request.method === "POST" && path === "/api/track") return handleTrack(request, env);
    if (request.method === "GET" && path === "/api/health") return json({ ok: true });

    if (path.startsWith("/api/waitlist")) {
      if (!authorized(request, env)) return json({ error: "unauthorized" }, 401);
      if (request.method === "GET" && path === "/api/waitlist/stats") return handleStats(env);
      if (request.method === "GET" && path === "/api/waitlist") return handleWaitlist(env);
      if (request.method === "POST" && path === "/api/waitlist/status") return handleStatus(request, env);
      return json({ error: "not found" }, 404);
    }
    if (request.method === "GET" && path === "/api/leads/count") {
      const row = await env.mywa_db.prepare("SELECT COUNT(*) AS c FROM leads").first();
      return json({ count: row.c || 0 });
    }
    return env.ASSETS.fetch(request);
  },
};
