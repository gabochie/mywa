DROP TABLE IF EXISTS leads;
CREATE TABLE leads (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  business TEXT DEFAULT '',
  phone TEXT NOT NULL,
  offer TEXT DEFAULT '',
  source TEXT DEFAULT 'direct',
  status TEXT DEFAULT 'waiting',   -- waiting | invited | onboarded | paid | dismissed
  score INTEGER DEFAULT 0,
  vertical TEXT DEFAULT '',
  ip TEXT DEFAULT '',
  ua TEXT DEFAULT '',
  visitor_id TEXT DEFAULT '',
  ts INTEGER NOT NULL,
  updated_at INTEGER DEFAULT 0
);
CREATE INDEX idx_leads_ts ON leads(ts);
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_visitor ON leads(visitor_id);

DROP TABLE IF EXISTS events;
CREATE TABLE events (
  id TEXT PRIMARY KEY,
  visitor_id TEXT,
  event TEXT,      -- view_pricing | return_visit | whatsapp_click | share
  ts INTEGER
);
CREATE INDEX idx_events_visitor ON events(visitor_id);
CREATE INDEX idx_events_event ON events(event);
