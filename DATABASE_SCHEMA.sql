-- ML Dashboard PostgreSQL Schema
-- Auto-created by SQLAlchemy ORM on app startup
-- Reference schema for documentation

-- Users table for authentication
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(255) UNIQUE NOT NULL,
  api_key VARCHAR(255) UNIQUE NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_api_key ON users(api_key);

-- Predictions with inference metrics
CREATE TABLE prediction_records (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  input_text TEXT NOT NULL,
  prediction VARCHAR(50) NOT NULL,  -- POSITIVE or NEGATIVE
  confidence FLOAT NOT NULL,         -- 0.0 to 1.0
  inference_time_ms FLOAT NOT NULL,  -- Model latency in milliseconds
  timestamp TIMESTAMP DEFAULT NOW() NOT NULL,
  request_id UUID NOT NULL DEFAULT gen_random_uuid(),
  archived BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_prediction_records_user_id ON prediction_records(user_id);
CREATE INDEX idx_prediction_records_timestamp ON prediction_records(timestamp);
CREATE INDEX idx_prediction_records_archived ON prediction_records(archived);
CREATE INDEX idx_prediction_records_request_id ON prediction_records(request_id);

-- Daily aggregate metrics for performance tracking
CREATE TABLE model_metrics (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  predictions_count INTEGER DEFAULT 0,
  avg_confidence FLOAT DEFAULT 0.0,
  avg_inference_time_ms FLOAT DEFAULT 0.0,
  date DATE NOT NULL
);

CREATE INDEX idx_model_metrics_user_id ON model_metrics(user_id);
CREATE INDEX idx_model_metrics_date ON model_metrics(date);
CREATE UNIQUE INDEX idx_model_metrics_user_date ON model_metrics(user_id, date);

-- View for recent predictions (last 7 days)
CREATE VIEW recent_predictions AS
SELECT
  pr.id,
  u.username,
  pr.input_text,
  pr.prediction,
  pr.confidence,
  pr.inference_time_ms,
  pr.timestamp
FROM prediction_records pr
JOIN users u ON pr.user_id = u.id
WHERE pr.timestamp > NOW() - INTERVAL '7 days'
  AND pr.archived = FALSE
ORDER BY pr.timestamp DESC;

-- View for daily statistics
CREATE VIEW daily_statistics AS
SELECT
  u.username,
  mm.date,
  mm.predictions_count,
  mm.avg_confidence,
  mm.avg_inference_time_ms
FROM model_metrics mm
JOIN users u ON mm.user_id = u.id
ORDER BY mm.date DESC;

-- Sample data: Default user for backward compatibility
INSERT INTO users (username, api_key)
VALUES ('default', '37c5288f74e43fe4e84b49dd7ac5a7e0b7e82f2f3f4e5e6e7e8e9e0e1e2e3e')
ON CONFLICT DO NOTHING;
