"""Create / rotate the least-privilege MySQL user the backend runs as.

Run ONCE against Azure (and again whenever the app password is rotated)
from the laptop, connected as the server administrator:

    $env:MYSQL_HOST         = terraform -chdir=infra-azure output -raw mysql_fqdn
    $env:MYSQL_USER         = "appadmin"
    $env:MYSQL_PASSWORD     = terraform -chdir=infra-azure output -raw mysql_password
    $env:MYSQL_DATABASE     = "reapit_demo"
    $env:MYSQL_SSL          = "true"
    $env:MYSQL_APP_PASSWORD = terraform -chdir=infra-azure output -raw mysql_app_password
    uv run python scripts/create_app_user.py

Grants are the minimum the running app needs:
  SELECT on everything          (API reads, ETL to DuckDB on boot)
  UPDATE on leads               (status transitions)
  INSERT on lead_events         (audit rows)
  INSERT on agent_runs          (activity feed)
Schema changes and seeding stay with the admin account via the scripts.
"""

from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, text

APP_USER = os.getenv("MYSQL_APP_USER", "app")


def _engine_url() -> str:
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_PORT", "3306")
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "rootpw")
    db = os.getenv("MYSQL_DATABASE", "reapit_demo")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}?charset=utf8mb4"


def _connect_args() -> dict[str, object]:
    if os.getenv("MYSQL_SSL", "").lower() in ("1", "true", "yes"):
        return {"ssl_verify_cert": True, "ssl_verify_identity": True}
    return {}


def main() -> int:
    app_password = os.getenv("MYSQL_APP_PASSWORD", "")
    if not app_password:
        print("MYSQL_APP_PASSWORD is required", file=sys.stderr)
        return 2
    db = os.getenv("MYSQL_DATABASE", "reapit_demo")
    require_ssl = "REQUIRE SSL" if _connect_args() else ""

    engine = create_engine(_engine_url(), future=True, connect_args=_connect_args())
    with engine.begin() as conn:
        conn.execute(text(f"CREATE USER IF NOT EXISTS '{APP_USER}'@'%' IDENTIFIED BY :pw"), {"pw": app_password})
        conn.execute(text(f"ALTER USER '{APP_USER}'@'%' IDENTIFIED BY :pw {require_ssl}"), {"pw": app_password})
        conn.execute(text(f"REVOKE ALL PRIVILEGES, GRANT OPTION FROM '{APP_USER}'@'%'"))
        conn.execute(text(f"GRANT SELECT ON `{db}`.* TO '{APP_USER}'@'%'"))
        conn.execute(text(f"GRANT UPDATE ON `{db}`.`leads` TO '{APP_USER}'@'%'"))
        conn.execute(text(f"GRANT INSERT ON `{db}`.`lead_events` TO '{APP_USER}'@'%'"))
        conn.execute(text(f"GRANT INSERT ON `{db}`.`agent_runs` TO '{APP_USER}'@'%'"))
        conn.execute(text("FLUSH PRIVILEGES"))
        grants = [row[0] for row in conn.execute(text(f"SHOW GRANTS FOR '{APP_USER}'@'%'"))]
    print(f"User '{APP_USER}' ready. Grants:")
    for g in grants:
        print("  " + g)
    return 0


if __name__ == "__main__":
    sys.exit(main())
