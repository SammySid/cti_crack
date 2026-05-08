import sqlite3
import urllib.request
import json
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

DB_PATH = Path(__file__).resolve().parent.parent / "analytics.db"

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            ip_address TEXT,
            location TEXT,
            user_agent TEXT,
            method TEXT,
            path TEXT,
            query_params TEXT,
            status_code INTEGER,
            process_time_ms REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

IP_CACHE = {}
def get_ip_details(ip):
    if ip in ["127.0.0.1", "localhost", "0.0.0.0", "unknown"] or ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172."):
        return "Local Network"
    if ip in IP_CACHE:
        return IP_CACHE[ip]
    try:
        req = urllib.request.Request(f"http://ip-api.com/json/{ip}", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode())
            if data.get("status") == "success":
                info = f"{data.get('city')}, {data.get('countryCode')} ({data.get('isp')})"
                IP_CACHE[ip] = info
                return info
    except Exception:
        pass
    IP_CACHE[ip] = "Unknown Location"
    return "Unknown Location"

def log_request(ip, user_agent, method, path, query, status, process_time):
    def _write():
        try:
            location = get_ip_details(ip)
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            
            # Use Indian Standard Time (IST) which is UTC + 5:30
            IST = timezone(timedelta(hours=5, minutes=30))
            current_time = datetime.now(IST).strftime('%I:%M %p, %d %b %Y').lstrip("0")
            
            c.execute('''
                INSERT INTO access_logs (timestamp, ip_address, location, user_agent, method, path, query_params, status_code, process_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (current_time, ip, location, user_agent, method, path, query, status, process_time))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Analytics logging error: {e}")
    threading.Thread(target=_write, daemon=True).start()

async def analytics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    
    # Ignore static files and high-frequency calculation API calls to prevent log spam
    noisy_routes = (
        "/css", 
        "/js", 
        "/api/calculate/curves", 
        "/api/calculate/kavl", 
        "/api/calculate/psychro", 
        "/api/calculate/predict"
    )
    
    # Exclude admin IP address from analytics
    IGNORED_IPS = ["103.187.229.87"]
    
    if not request.url.path.startswith(noisy_routes) and "/analytics" not in request.url.path:
        ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
            
        if ip not in IGNORED_IPS:
            user_agent = request.headers.get("user-agent", "unknown")
            
            log_request(
                ip, user_agent, request.method, request.url.path, 
                str(request.query_params), response.status_code, process_time
            )
        
    return response

@router.get("/analytics")
def get_analytics(limit: int = 500):
    """Admin endpoint to view a powerful HTML analytics dashboard."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM access_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        
        # Calculate some summary stats for the dashboard
        total_hits = len(rows)
        unique_ips = len(set(r['ip_address'] for r in rows))
        
        paths = [r['path'] for r in rows]
        top_path = max(set(paths), key=paths.count) if paths else "N/A"
        
        conn.close()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>CTI Live Analytics</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                :root {{ --bg: #0f172a; --card: #1e293b; --text: #f8fafc; --accent: #3b82f6; --accent-hover: #60a5fa; --border: #334155; }}
                body {{ font-family: 'Inter', -apple-system, sans-serif; background-color: var(--bg); color: var(--text); padding: 20px; margin: 0; }}
                .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }}
                h2 {{ margin: 0; font-weight: 600; color: #fff; }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px; }}
                .stat-card {{ background: var(--card); padding: 20px; border-radius: 8px; border: 1px solid var(--border); text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
                .stat-card h3 {{ margin: 0 0 10px 0; font-size: 14px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }}
                .stat-card .value {{ font-size: 28px; font-weight: bold; color: var(--accent); }}
                table {{ width: 100%; border-collapse: collapse; background: var(--card); border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
                th, td {{ padding: 12px 15px; text-align: left; font-size: 14px; border-bottom: 1px solid var(--border); }}
                th {{ background-color: #0f172a; color: #cbd5e1; font-weight: 600; }}
                tr:hover {{ background-color: #2a3b54; }}
                .badge {{ background: #059669; color: white; padding: 2px 6px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
                .path {{ font-family: monospace; color: #fbbf24; }}
                .agent {{ max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #94a3b8; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>⚡ CTI Dashboard Analytics</h2>
                <div style="color: #94a3b8; font-size: 14px;">Live Server Data</div>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Recent Requests</h3>
                    <div class="value">{total_hits}</div>
                </div>
                <div class="stat-card">
                    <h3>Unique Visitors (IPs)</h3>
                    <div class="value">{unique_ips}</div>
                </div>
                <div class="stat-card">
                    <h3>Most Active Path</h3>
                    <div class="value" style="font-size: 18px; line-height: 32px;">{top_path}</div>
                </div>
            </div>

            <table>
                <tr>
                    <th>Time (IST)</th>
                    <th>IP Address</th>
                    <th>Location & ISP</th>
                    <th>Method</th>
                    <th>Path</th>
                    <th>Status</th>
                    <th>User Agent</th>
                </tr>
        """
        
        for r in rows:
            path_display = r['path']
            if r['query_params']:
                path_display += f"?{r['query_params']}"
                
            status_color = "#059669" if r['status_code'] < 400 else "#dc2626"
            
            html += f"""
                <tr>
                    <td style="color: #94a3b8;">{r['timestamp']}</td>
                    <td style="font-weight: 500;">{r['ip_address']}</td>
                    <td>{r['location']}</td>
                    <td><span class="badge" style="background: var(--accent);">{r['method']}</span></td>
                    <td class="path">{path_display}</td>
                    <td><span class="badge" style="background: {status_color};">{r['status_code']}</span></td>
                    <td class="agent" title="{r['user_agent']}">{r['user_agent']}</td>
                </tr>
            """
            
        html += """
            </table>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
    except Exception as e:
        return {"error": str(e)}
