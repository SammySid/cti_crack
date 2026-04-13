import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('130.162.191.58', username='ubuntu', password='Stallion316##', timeout=20)

# First check what the file looks like now
_, out, _ = client.exec_command('cat /home/ubuntu/cooling-tower_pro/auto_sync.sh')
current = out.read().decode()
print('=== CURRENT auto_sync.sh ===')
print(current)
print('=== END ===')
client.close()
