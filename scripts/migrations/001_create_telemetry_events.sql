-- Migration: 001_create_telemetry_events.sql
-- Description: Creates the telemetry_events table with 8 columns and required indexes.

CREATE TABLE IF NOT EXISTS telemetry_events (
    event_id VARCHAR(64) PRIMARY KEY,
    timestamp VARCHAR(64) NOT NULL,
    session_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64),
    event_type VARCHAR(64) NOT NULL,
    service VARCHAR(64) NOT NULL DEFAULT 'backoffice',
    request_id VARCHAR(64) NOT NULL,
    tags JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Required indexes
CREATE INDEX IF NOT EXISTS idx_telemetry_events_timestamp ON telemetry_events (timestamp);
CREATE INDEX IF NOT EXISTS idx_telemetry_events_event_type ON telemetry_events (event_type);
CREATE INDEX IF NOT EXISTS idx_telemetry_events_tags ON telemetry_events USING GIN (tags);
