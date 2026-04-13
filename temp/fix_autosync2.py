import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('130.162.191.58', username='ubuntu', password='Stallion316##', timeout=20)

print('=== Current rsync block in auto_sync.sh ===')
_, out, _ = client.exec_command('grep -n "" /home/ubuntu/cooling-tower_pro/auto_sync.sh | head -40')
print(out.read().decode())

# Remove the leftover blank line (between docker-compose.yml exclude and auto_sync.sh exclude)
# The sed left an empty line that breaks bash line-continuation
fix_cmd = r"""
python3 - <<'PYEOF'
import re

path = '/home/ubuntu/cooling-tower_pro/auto_sync.sh'
with open(path, 'r') as f:
    content = f.read()

# Replace the broken sequence: "docker-compose.yml" \ \n \n    --exclude with clean version
fixed = re.sub(
    r'(--exclude="docker-compose.yml" \\)\n\n(\s+--exclude="auto_sync.sh")',
    r'\1\n\2',
    content
)

with open(path, 'w') as f:
    f.write(fixed)

print("Fixed. Verifying rsync block:")
for i, line in enumerate(fixed.splitlines()[20:35], 21):
    print(f"  {i}: {line}")
PYEOF
"""
_, out2, err2 = client.exec_command(fix_cmd)
print(out2.read().decode())
print(err2.read().decode())

print()
print('=== Updated rsync block ===')
_, out3, _ = client.exec_command('grep -n "" /home/ubuntu/cooling-tower_pro/auto_sync.sh | head -40')
print(out3.read().decode())

client.close()
