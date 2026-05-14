import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('130.162.191.58', username='ubuntu', password='Stallion316##')

sftp = client.open_sftp()
with sftp.open('/home/ubuntu/cooling-tower_pro/auto_sync.sh', 'r') as f:
    content = f.read().decode('utf-8')

replacement = """docker compose up -d --build

echo "$LOG_TAG Reloading Nginx to update DNS cache..."
docker exec trading-nginx nginx -s reload
"""

if "nginx -s reload" not in content:
    content = content.replace("docker compose up -d --build", replacement)
    with sftp.open('/home/ubuntu/cooling-tower_pro/auto_sync.sh', 'w') as f:
        f.write(content)
    print("Successfully updated auto_sync.sh")
else:
    print("Already updated.")

client.close()
