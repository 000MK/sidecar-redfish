CREATE TABLE IF NOT EXISTS error_logs (
    log_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    log_time TEXT,
    log_msg TEXT,
    log_others JSONB
);