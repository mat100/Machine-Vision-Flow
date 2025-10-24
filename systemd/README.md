# Systemd Service Files

Production deployment configuration for Machine Vision Flow using systemd.

## Services

- **machinevisionflow-backend.service** - Python FastAPI backend
- **machinevisionflow-nodered.service** - Node-RED workflow engine (depends on backend)

## Installation

1. **Copy service files to systemd directory:**
   ```bash
   sudo cp systemd/*.service /etc/systemd/system/
   ```

2. **Reload systemd daemon:**
   ```bash
   sudo systemctl daemon-reload
   ```

3. **Enable services to start on boot:**
   ```bash
   sudo systemctl enable machinevisionflow-backend.service
   sudo systemctl enable machinevisionflow-nodered.service
   ```

4. **Start services:**
   ```bash
   sudo systemctl start machinevisionflow-backend.service
   sudo systemctl start machinevisionflow-nodered.service
   ```

## Management Commands

```bash
# Check status
sudo systemctl status machinevisionflow-backend.service
sudo systemctl status machinevisionflow-nodered.service

# View logs
sudo journalctl -u machinevisionflow-backend.service -f
sudo journalctl -u machinevisionflow-nodered.service -f

# Or view log files directly
tail -f /var/log/machinevisionflow/backend.log
tail -f /var/log/machinevisionflow/node-red.log

# Restart services
sudo systemctl restart machinevisionflow-backend.service
sudo systemctl restart machinevisionflow-nodered.service

# Stop services
sudo systemctl stop machinevisionflow-backend.service
sudo systemctl stop machinevisionflow-nodered.service

# Disable services from starting on boot
sudo systemctl disable machinevisionflow-backend.service
sudo systemctl disable machinevisionflow-nodered.service
```

## Runtime Directories

Systemd automatically creates these directories with correct permissions:

- `/var/log/machinevisionflow/` - Log files (via `LogsDirectory=`)
- `/run/machinevisionflow/` - PID files (via `RuntimeDirectory=`)

These directories are owned by `cnc:cnc` and are automatically created/removed by systemd.

## Configuration

### Backend Configuration

Edit environment variables in `machinevisionflow-backend.service`:
```ini
Environment="MV_CONFIG_FILE=/home/cnc/MachineVisionFlow/python-backend/config.yaml"
```

### User and Paths

If you installed the application in a different location or want to run as a different user, edit:
```ini
User=cnc
Group=cnc
WorkingDirectory=/home/cnc/MachineVisionFlow/python-backend
```

## Security Features

Both services include:
- `NoNewPrivileges=true` - Prevents privilege escalation
- `PrivateTmp=true` - Isolated /tmp directory
- Running as non-root user (`cnc`)
- Automatic restart on failure

## Dependencies

Node-RED service requires the backend service to be running:
```ini
After=machinevisionflow-backend.service
Requires=machinevisionflow-backend.service
```

This ensures the backend starts first and Node-RED stops if backend fails.

## Troubleshooting

### Service won't start

Check logs:
```bash
sudo journalctl -u machinevisionflow-backend.service -n 50
sudo systemctl status machinevisionflow-backend.service
```

### Permission issues

Ensure the user has access to:
- Application directory: `/home/cnc/MachineVisionFlow/`
- Python venv: `/home/cnc/MachineVisionFlow/python-backend/venv/`
- Node-RED config: `/home/cnc/.node-red/`

### Port conflicts

Check if ports 8000 and 1880 are available:
```bash
sudo lsof -i :8000
sudo lsof -i :1880
```
