import psycopg2
import os
from psycopg2 import sql 
from psycopg2.extras import RealDictCursor
from mylib.models.sensor_log_model_factory import SensorLogModelFactory
from contextlib import contextmanager
from typing import List
from pathlib import Path
SQL_DIR = Path(__file__).with_suffix('').parent / '..' / 'db' / 'sql'

class PostgresAdapter():
    def __init__(self, dbname=None):
        user = os.getenv("POSTGRES_USER", "")
        password = os.getenv("POSTGRES_PASSWORD", "")
        host = os.getenv("POSTGRES_HOST_MASTER", "localhost")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.PG = dict(host=host, port=port, user=user, password=password)
        self.DB_NAME = dbname
    
    @staticmethod
    def load_sql(name: str) -> str:
        return (SQL_DIR / name).read_text(encoding='utf-8')

    def _get_dynamic_cols(self, cols):
        METRIC_TYPE_MAP = {
            "String": "TEXT",
            "Decimal": "NUMERIC(10,2)",
        }
        dynamic_cols = []
        for item in cols:
            name = item.get("FieldName")
            mtype = item.get("MetricDataType", "String")
            if not name or name == 'time':
                continue
            pg_type = METRIC_TYPE_MAP.get(mtype, "TEXT")
            dynamic_cols.append((name, pg_type))
        return dynamic_cols
    
    @contextmanager
    def get_connection(self, dbname: str | None = None, autocommit: bool = False):
        conn = psycopg2.connect(dbname=dbname or self.DB_NAME, **self.PG)
        conn.autocommit = autocommit
        try:
            yield conn
            if not autocommit:
                conn.commit()
        except Exception:
            if not autocommit:
                conn.rollback()
            raise
        finally:
            conn.close()

    def query(self, sql_string: str, params=None, *, dbname: str | None = None) -> List[dict]:
        with self.get_connection(dbname=dbname) as conn, conn.cursor() as cur:
            cur.execute(sql_string, params)
            try:
                return cur.fetchall()
            except psycopg2.ProgrammingError:
                return []

    def insert(self, sql_string: str, params=None, *, dbname: str | None = None) -> int:
        with self.get_connection(dbname=dbname) as conn, conn.cursor() as cur:
            cur.execute(sql_string, params)
            resp = cur.rowcount
        return resp

    def exec(self, sql_string: str, params=None, *, dbname: str | None = None, autocommit: bool = False) -> dict:
        resp = {}
        with self.get_connection(dbname=dbname, autocommit=autocommit) as conn, conn.cursor() as cur:
            try:
                cur.execute(sql_string, params)
                resp = {
                    'rowcount': cur.rowcount
                }
                rows = cur.fetchone()
            except psycopg2.ProgrammingError:
                rows = None
            resp['rows'] = rows
        return resp

    def ensure_database(self):
        query_resp = self.query("SELECT 1 FROM pg_database WHERE datname = %s", (self.DB_NAME, ), dbname="postgres")
        if not query_resp:
            create_sql = sql.SQL("CREATE DATABASE {}").format(sql.Identifier(self.DB_NAME))
            self.exec(create_sql, dbname="postgres", autocommit=True)

    def ensure_tables(self):
        try:
            create_sql = sql.SQL(self.load_sql('error_log.sql'))
            self.exec(create_sql)

            sensor_model = SensorLogModelFactory.create_model()
            cols = sensor_model.to_metric_definitions()
            dynamic_cols = self._get_dynamic_cols(cols)

            create_sql = sql.SQL(self.load_sql('sensor_data.sql')).format(
                extra_cols=(
                    sql.SQL(", ").join(
                        [sql.SQL("")] + [
                            sql.SQL("{} {}").format(sql.Identifier(n), sql.SQL(t))
                            for n, t in dynamic_cols
                        ]
                    ) if dynamic_cols else sql.SQL("")
                )
            )
            self.exec(create_sql)

        except psycopg2.Error as e:
            print(f"[DB ERROR] {type(e).__name__}: {e}")
            raise
        except Exception as e:
            print(f"[GENERAL ERROR] {type(e).__name__}: {e}")
            raise
