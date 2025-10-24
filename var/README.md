# Runtime Files Directory

This directory contains runtime files following Linux FHS (Filesystem Hierarchy Standard).

## Structure

```
var/
├── log/          # Log files
│   ├── backend.log
│   └── node-red.log
└── run/          # PID files
    ├── backend.pid
    └── node-red.pid
```

## Development vs Production

The application uses environment variables to support both development and production deployments:

**Development (default):**
- Logs: `$PROJECT_ROOT/var/log/`
- PIDs: `$PROJECT_ROOT/var/run/`

**Production (systemd service):**
Set environment variables in systemd unit file:
```ini
[Service]
Environment="LOG_DIR=/var/log/machinevisionflow"
Environment="RUN_DIR=/run/machinevisionflow"
```

Or override in Makefile:
```bash
LOG_DIR=/var/log/machinevisionflow RUN_DIR=/run/machinevisionflow make start
```

## Note

All files in this directory are runtime-generated and should not be committed to version control.
