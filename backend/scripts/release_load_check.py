"""Bounded HTTP load check. Creates a dedicated test tenant; never use customer data."""
import argparse
import asyncio
import json
import math
import time
import uuid
from collections import Counter
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx


async def run(args, *, emit=True, enforce_budget=True):
    metrics = {}
    async with httpx.AsyncClient(base_url=args.base_url.rstrip("/") + "/api/v1", timeout=60,
                                 limits=httpx.Limits(max_connections=30)) as client:
        async def request(method, path, expected=200, **kwargs):
            response = await client.request(method, path, **kwargs)
            if response.status_code != expected:
                raise RuntimeError(f"{method} {path}: {response.status_code} {response.text[:200]}")
            return response.json()

        suffix = uuid.uuid4().hex[:10]
        def phone():
            return "09" + str(uuid.uuid4().int)[:8]
        auth = await request("POST", "/auth/register-tenant", 201,
                             json={"tenant_name": "Load check " + suffix, "tenant_slug": "load-" + suffix,
                                   "admin_full_name": "Load Admin", "phone_number": phone(),
                                   "password": uuid.uuid4().hex})
        slug = "load-" + suffix
        admin = {"Authorization": "Bearer " + auth["access_token"]}
        await request("PATCH", "/tenants/me", headers=admin,
                      json={"open_time": "09:00:00", "close_time": "20:00:00", "buffer_minutes": 10})
        for i in range(10):
            staff = await request("POST", "/staff", 201, headers=admin,
                                  json={"full_name": f"Load Staff {i}", "phone_number": phone(), "password": uuid.uuid4().hex})
            await request("PUT", f"/staff/{staff['id']}/schedules", headers=admin,
                          json={"schedules": [{"day_of_week": d, "start_time": "09:00:00", "end_time": "20:00:00"} for d in range(7)]})
        service = await request("POST", "/services", 201, headers=admin,
                                json={"name": "Load 60", "duration_minutes": 60, "price": 100000})
        customers = []
        for _ in range(20):
            account = await request("POST", "/auth/register", 201, headers={"X-Tenant-Slug": slug},
                                    json={"full_name": "Load Customer", "phone_number": phone(), "password": uuid.uuid4().hex})
            customers.append({"Authorization": "Bearer " + account["access_token"]})
        day = (datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")) + timedelta(days=7)).date().isoformat()
        params = {"date": day, "service_ids": [service["id"]]}
        async def timed(label, method, path, **kwargs):
            start = time.perf_counter()
            response = await client.request(method, path, **kwargs)
            metrics.setdefault(label, []).append((response.status_code, (time.perf_counter()-start)*1000))
            return response

        # 20 customers contend for 10 staff in one timeslot, without explicit staff.
        bookings = await asyncio.gather(*[
            timed("booking_burst", "POST", "/bookings", headers=h,
                  json={"start_time": day + "T10:00:00+07:00", "staff_id": None,
                        "items": [{"service_id": service["id"]}]}) for h in customers])
        statuses = Counter(r.status_code for r in bookings)
        assert statuses == {201: 10, 409: 10}, dict(statuses)
        successful = [r.json() for r in bookings if r.status_code == 201]
        assert len({r["staff_id"] for r in successful}) == 10
        # Bounded mixed reads: 10 concurrent users; includes background notifications from burst.
        semaphore = asyncio.Semaphore(10)
        async def read(i):
            async with semaphore:
                choice = i % 4
                if choice == 0:
                    return await timed("slots", "GET", "/bookings/available-slots", headers={"X-Tenant-Slug": slug}, params=params)
                if choice == 1:
                    return await timed("calendar", "GET", "/bookings", headers=admin, params={"date_from": day, "date_to": day})
                if choice == 2:
                    return await timed("report", "GET", "/reports/staff-performance", headers=admin,
                                       params={"start_date": day, "end_date": day})
                return await timed("notifications", "GET", "/notifications", headers=admin)
        responses = await asyncio.gather(*[read(i) for i in range(args.reads)])
        assert all(r.status_code == 200 for r in responses), Counter(r.status_code for r in responses)
        slots = await request("GET", "/bookings/available-slots", headers={"X-Tenant-Slug": slug}, params=params)
        assert not any(s["start_time"].startswith(day + "T10:00:00") for s in slots["slots"])
        # Retain dedicated tenant for inspection, cancel its successful bookings.
        for booking in successful:
            await request("POST", f"/bookings/{booking['id']}/cancel", headers=admin)
        result = {"tenant_slug": slug, "staff_count": 10, "read_concurrency": 10, "read_requests": args.reads, "metrics": {}}
        for label, samples in metrics.items():
            times = sorted(t for _, t in samples)
            result["metrics"][label] = {"requests": len(samples),
                "status_counts": dict(Counter(s for s, _ in samples)),
                "p50_ms": round(times[math.ceil(len(times)*.5)-1], 1),
                "p95_ms": round(times[math.ceil(len(times)*.95)-1], 1),
                "max_ms": round(times[-1], 1)}
        if emit:
            print(json.dumps(result, indent=2))
        result["within_budget"]=all(m["p95_ms"] <= args.max_p95_ms for m in result["metrics"].values())
        if enforce_budget:assert result["within_budget"], "p95 exceeded budget"
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--reads", type=int, default=200, choices=range(20, 2001))
    parser.add_argument("--max-p95-ms", type=float, default=2000)
    asyncio.run(run(parser.parse_args()))
