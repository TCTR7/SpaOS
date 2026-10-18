"""Create a binary backup and restore to an isolated disposable PostgreSQL.
Run from repo root with Docker Compose and PostgreSQL 16 image available.
Never restores over the running database. Dump contains sensitive customer data.
"""
import argparse
import json
import pathlib
import subprocess
import time
import uuid

COMPOSE = ["docker-compose"]
INVENTORY = """
SELECT format('SELECT json_build_object(''table'', %L, ''rows'', count(*), ''rls'', %L, ''force_rls'', %L) FROM %I.%I;',
              c.relname, c.relrowsecurity, c.relforcerowsecurity, n.nspname, c.relname)
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND c.relkind='r' ORDER BY c.relname;
"""
SOURCE_SQL = 'exec psql -X -q -A -t -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'


def capture(command, **kwargs):
    return subprocess.run(command, check=True, stdout=subprocess.PIPE, **kwargs).stdout


def source_sql(sql):
    return capture(COMPOSE + ["exec", "-T", "db", "sh", "-c", SOURCE_SQL], input=sql.encode()).decode()


def inventory(sql):
    statements = sql(INVENTORY)
    return [json.loads(line) for line in sql(statements).splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser()
    global COMPOSE
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--compose-project", help="Compose project của đúng khách hàng")
    parser.add_argument("--env-file", type=pathlib.Path, help="File cấu hình riêng của khách hàng")
    args = parser.parse_args()
    COMPOSE = ["docker-compose"]
    if args.env_file:
        COMPOSE += ["--env-file", str(args.env_file)]
    if args.compose_project:
        COMPOSE += ["-p", args.compose_project]
    target = args.output.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    # Require a quiescent source: inventories before/after dump must match.
    before = inventory(source_sql)
    with target.open("xb") as stream:
        subprocess.run(COMPOSE + ["exec", "-T", "db", "sh", "-c",
                       'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc'],
                       stdout=stream, check=True)
    after = inventory(source_sql)
    if before != after:
        raise RuntimeError("Source changed during backup; stop writes and repeat with a new output path.")
    if not any(row["table"] == "bookings" for row in before):
        raise RuntimeError("Source is missing expected SpaOS tables.")
    name = "spaos-restore-check-" + uuid.uuid4().hex[:10]
    started = False
    try:
        capture(["docker", "run", "-d", "--name", name, "--network", "none",
                 "-e", "POSTGRES_HOST_AUTH_METHOD=trust", "postgres:16"])
        started = True
        for _ in range(60):
            ready = subprocess.run(["docker", "exec", name, "pg_isready", "-U", "postgres"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if ready.returncode == 0:
                break
            time.sleep(.5)
        else:
            raise RuntimeError("Temporary PostgreSQL did not become ready.")
        subprocess.run(["docker", "exec", name, "createdb", "-U", "postgres", "restore_check"], check=True)
        with target.open("rb") as stream:
            subprocess.run(["docker", "exec", "-i", name, "pg_restore", "-U", "postgres",
                            "-d", "restore_check", "--exit-on-error", "--no-owner", "--no-privileges"],
                           stdin=stream, check=True)
        def restored_sql(sql):
            return capture(["docker", "exec", "-i", name, "psql", "-X", "-q", "-A", "-t",
                            "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", "restore_check"],
                           input=sql.encode()).decode()
        restored = inventory(restored_sql)
        if restored != before:
            raise RuntimeError("Restored table counts/RLS flags differ from source.")
        # Confirm tenant policies restored, in addition to RLS flags and row counts.
        policies = "SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check FROM pg_policies ORDER BY schemaname, tablename, policyname;"
        if source_sql(policies) != restored_sql(policies):
            raise RuntimeError("Restored RLS policies differ from source.")
        business = ["users", "services", "staff_schedules", "customer_packages", "bookings",
                    "booking_items", "push_subscriptions", "notifications",
                    "payment_invoices", "payment_entries", "audit_logs", "branch_memberships", "owner_provisions"]
        assert all(any(r["table"] == t and r["rls"] == "t" and r["force_rls"] == "t"
                       for r in restored) for t in business + ["login_accounts", "deployment_operators", "deployment_branding"])
        restored_sql("CREATE ROLE restore_probe NOLOGIN NOSUPERUSER NOBYPASSRLS; "
                     "GRANT USAGE ON SCHEMA public TO restore_probe; "
                     "GRANT SELECT ON ALL TABLES IN SCHEMA public TO restore_probe;")
        no_context = "SET ROLE restore_probe; " + "; ".join(
            f"SELECT count(*) FROM {t}" for t in business + ["login_accounts", "deployment_operators"]) + ";"
        assert all(line == "0" for line in restored_sql(no_context).splitlines()), "RLS leaked without context"
        tenant = restored_sql("SELECT tenant_id FROM users ORDER BY id LIMIT 1;").strip()
        uuid.UUID(tenant)
        counts = "; ".join(f"SELECT count(*) FROM {t} WHERE tenant_id='{tenant}'" for t in business) + ";"
        expected = restored_sql(counts)
        visible = restored_sql(f"SET ROLE restore_probe; SET app.current_tenant_id='{tenant}'; " +
                               "; ".join(f"SELECT count(*) FROM {t}" for t in business) + ";")
        assert expected == visible, "RLS visible rows differ from selected tenant"
        expected_branding = restored_sql("SELECT count(*) FROM deployment_branding;")
        public_branding = restored_sql("SET ROLE restore_probe; SELECT count(*) FROM deployment_branding;")
        assert expected_branding == public_branding, "Public branding visibility differs after restore"
        account = restored_sql("SELECT id FROM login_accounts ORDER BY id LIMIT 1;").strip()
        if account:
            uuid.UUID(account)
            expected_account = restored_sql(f"SELECT count(*) FROM branch_memberships WHERE account_id='{account}';")
            visible_account = restored_sql(f"SET ROLE restore_probe; SET app.current_account_id='{account}'; SELECT count(*) FROM branch_memberships;")
            assert expected_account == visible_account, "Membership account scope differs"
            assert restored_sql(f"SET ROLE restore_probe; SET app.current_account_id='{account}'; SELECT count(*) FROM login_accounts;").strip() == "1"
            assert restored_sql(f"SET ROLE restore_probe; SET app.current_account_id='{account}'; SELECT count(*) FROM users;").strip() == "0", "Account context leaked business data"
            phone = restored_sql(f"SELECT phone_number FROM login_accounts WHERE id='{account}';").strip().replace("'", "''")
            assert restored_sql(f"SET ROLE restore_probe; SET app.login_phone='{phone}'; SELECT count(*) FROM login_accounts;").strip() == "1"
        operator = restored_sql("SELECT id FROM deployment_operators ORDER BY id LIMIT 1;").strip()
        if operator:
            uuid.UUID(operator)
            assert restored_sql(f"SET ROLE restore_probe; SET app.current_operator_id='{operator}'; SELECT count(*) FROM deployment_operators;").strip() == "1"
            expected_provisions = restored_sql(f"SELECT count(*) FROM owner_provisions WHERE operator_id='{operator}';")
            visible_provisions = restored_sql(f"SET ROLE restore_probe; SET app.current_operator_id='{operator}'; SELECT count(*) FROM owner_provisions;")
            assert expected_provisions == visible_provisions
            assert restored_sql(f"SET ROLE restore_probe; SET app.current_operator_id='{operator}'; SELECT count(*) FROM users;").strip() == "0"
        print(json.dumps({"backup": str(target), "bytes": target.stat().st_size,
                          "tables": restored, "policies_match": True, "rls_probe": "PASS (no context, tenant, account and phone scopes)",
                          "restore": "PASS", "note": "Roles/grants are excluded from this rehearsal restore."}, indent=2))
    finally:
        if started:
            subprocess.run(["docker", "rm", "-f", "-v", name], check=True, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
