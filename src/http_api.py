from aiohttp import web
from .metrics import METRICS
import json
import asyncio
from pathlib import Path

# Path to /static folder (project_root/static)
STATIC_DIR = (Path(__file__).resolve().parent.parent / "static").resolve()

async def stats(request):
    return web.json_response(METRICS.snapshot())


async def metrics_prom(request):
    snap = METRICS.snapshot()
    lines = []
    lines.append(f"broker_uptime_sec {snap['uptime_sec']}")
    lines.append(f"broker_connects_total {snap['connects_total']}")
    lines.append(f"broker_disconnects_total {snap['disconnects_total']}")
    lines.append(f"broker_subscribes_total {snap['subscribes_total']}")
    lines.append(f"broker_publishes_total {snap['publishes_total']}")
    lines.append(f"broker_bytes_in_total {snap['bytes_in_total']}")
    lines.append(f"broker_bytes_out_total {snap['bytes_out_total']}")
    for k, v in snap["packet_count"].items():
        lines.append(f'broker_packet_count{{type="{k}"}} {v}')
    for k, v in snap["packet_avg_ms"].items():
        lines.append(f'broker_packet_avg_ms{{type="{k}"}} {v}')
    for k, v in snap["packet_max_ms"].items():
        lines.append(f'broker_packet_max_ms{{type="{k}"}} {v}')
    return web.Response(text="\n".join(lines) + "\n", content_type="text/plain")


# ---------------- Dashboard (UI) ----------------
async def dashboard(request):
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return web.Response(
            text="Dashboard not found. Create static/index.html",
            status=404
        )
    return web.FileResponse(index_file)


# ---------------- Live events (SSE) ----------------
async def events(request):
    """
    Server-Sent Events endpoint.
    Browser connects to /events and receives JSON stats every second.
    """
    resp = web.StreamResponse(
        status=200,
        reason="OK",
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
    await resp.prepare(request)

    try:
        while True:
            snap = METRICS.snapshot()

            # Add message-rate field if you want later.
            # For now, UI can still plot publishes_total deltas.
            data = json.dumps(snap)

            await resp.write(f"data: {data}\n\n".encode("utf-8"))
            await resp.drain()
            await asyncio.sleep(1)

    except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
        # Client disconnected
        pass

    return resp


def make_app():
    app = web.Application()

    # Existing APIs
    app.router.add_get("/stats", stats)
    app.router.add_get("/metrics", metrics_prom)

    # Dashboard routes
    app.router.add_get("/", dashboard)
    app.router.add_get("/events", events)

    # Static file serving: /static/app.js , /static/styles.css ...
    if STATIC_DIR.exists():
        app.router.add_static("/static/", path=str(STATIC_DIR), name="static")
    else:
        print(f"[WARN] Static folder not found: {STATIC_DIR}")

    return app
