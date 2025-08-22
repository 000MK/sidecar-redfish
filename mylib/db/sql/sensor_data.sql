CREATE TABLE IF NOT EXISTS sensor_data(
    id   INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    time TEXT,
    created_at TEXT,
    updated_at TEXT
    {extra_cols}
);

CREATE OR REPLACE FUNCTION updated_time()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := to_char(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
IF NOT EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'updated_time_trigger'
) THEN
    CREATE TRIGGER updated_time_trigger
    BEFORE UPDATE ON sensor_data
    FOR EACH ROW
    EXECUTE FUNCTION updated_time();
END IF;
END;
$$;
