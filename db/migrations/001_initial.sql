CREATE TABLE IF NOT EXISTS tokens (id INTEGER PRIMARY KEY, access_token TEXT, refresh_token TEXT, expiry BIGINT, scope TEXT, updated_at BIGINT);
CREATE TABLE IF NOT EXISTS daily_metrics (date TEXT NOT NULL, metric TEXT NOT NULL, value DOUBLE PRECISION, updated_at BIGINT, PRIMARY KEY(date, metric));
CREATE TABLE IF NOT EXISTS exercises (id TEXT PRIMARY KEY, type TEXT, display_name TEXT, start_time TEXT, duration_s BIGINT, calories DOUBLE PRECISION, distance_mm DOUBLE PRECISION, steps INTEGER, avg_hr INTEGER, raw JSONB, updated_at BIGINT);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
