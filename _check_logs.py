import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('130.162.191.58', username='ubuntu', password='Stallion316##', timeout=30)

def run(cmd, timeout=30):
    _, out, err = client.exec_command(cmd, get_pty=False, timeout=timeout)
    return out.read().decode(), err.read().decode()

print("=== Container logs (last 80 lines) ===")
o, e = run('docker logs cti-dashboard-pro --tail 80 2>&1')
print(o or e)

print("\n=== Test API endpoints ===")
# Test from inside the container network
o, e = run('docker exec cti-dashboard-pro python -c "import app.backend.main; print(\'imports ok\')" 2>&1')
print("Import test:", o or e)

o, e = run('curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ 2>/dev/null || echo "curl failed"')
print("GET / HTTP status:", o)

o, e = run('curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/calculate/kavl -H "Content-Type: application/json" -d \'{"wbt":60,"hwt":95,"cwt":80,"lg":1.5}\' 2>/dev/null || echo "curl failed"')
print("POST /api/calculate/kavl HTTP status:", o)

o, e = run('curl -s -X POST http://localhost:8000/api/calculate/kavl -H "Content-Type: application/json" -d \'{"wbt":60,"hwt":95,"cwt":80,"lg":1.5}\' 2>/dev/null')
print("kavl response:", o[:500])

o, e = run('curl -s -X POST http://localhost:8000/api/calculate/curves -H "Content-Type: application/json" -d \'{"inputs":{"axXMin":50,"axXMax":85,"lgRatio":1.5,"constantC":2.0,"constantM":0.5,"designHWT":95,"designCWT":80},"flowPercent":100}\' 2>/dev/null')
print("\ncurves response (first 500 chars):", o[:500])

client.close()
