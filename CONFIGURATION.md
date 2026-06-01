# Plugin Configuration Guide

**How to configure the MRV Teraka QGIS plugin with custom API URLs and paths.**

---

## 📍 Configuration Directory

The plugin stores its configuration in a user-accessible directory (not hidden in AppData):

### Windows
```
C:\Users\<YourUsername>\AppData\Local\Teraka\
├── config/
│   ├── plugin_config.json        ← Edit this!
│   └── layer_table_mapping.json  ← API endpoint mappings
├── projects/                      ← Your QGIS projects
├── exports/                       ← Exported data (CSV, Shapefile)
├── logs/                          ← Plugin logs
└── cache/                         ← Temporary files
```

### Linux/Mac
```
~/.config/Teraka/
├── config/
│   ├── plugin_config.json        ← Edit this!
│   └── layer_table_mapping.json
├── projects/
├── exports/
├── logs/
└── cache/
```

### Finding Your Config Directory

**In QGIS Python Console:**
```python
from mrv_teraka import ConfigManager
config_dir = ConfigManager.get_config_dir()
print(f"Config directory: {config_dir}")
```

Or use the menu:
- Plugin > MRV Teraka > Open Config Directory (if implemented)

---

## 🔧 Configuration File: `plugin_config.json`

Created automatically on first use with default values:

```json
{
  "api": {
    "django_url": "http://localhost:8000",
    "postgrest_url": "http://localhost:3000",
    "timeout_seconds": 30
  },
  "features": {
    "enable_offline_mode": false,
    "auto_sync_interval_minutes": 60
  },
  "_comment": "Edit this file to configure MRV Teraka. Override with env vars: TERAKA_API_URL, TERAKA_POSTGREST_URL, TERAKA_API_TIMEOUT"
}
```

### Configuration Options

#### `api.django_url`
- **Description**: Django backend API URL
- **Default**: `http://localhost:8000`
- **Examples**:
  - Local development: `http://localhost:8000`
  - Remote server: `https://api.teraka.example.com`
  - Custom port: `http://192.168.1.100:8000`
- **Note**: Must be reachable from your machine

#### `api.postgrest_url`
- **Description**: PostgREST REST API URL
- **Default**: `http://localhost:3000`
- **Examples**:
  - Local Docker: `http://localhost:3000`
  - Remote server: `https://api.teraka.example.com/postgrest`
  - Custom host: `http://data.teraka.local:3000`
- **Note**: Same server as Django URL usually

#### `api.timeout_seconds`
- **Description**: HTTP request timeout
- **Default**: `30`
- **Range**: `5` to `600` seconds
- **Note**: Increase if network is slow or server is far away

#### `features.enable_offline_mode`
- **Description**: Allow working without server connection
- **Default**: `false`
- **Note**: Not yet fully implemented (placeholder for future)

#### `features.auto_sync_interval_minutes`
- **Description**: Auto-sync interval when offline mode enabled
- **Default**: `60`
- **Range**: `5` to `1440` minutes (1 day)

---

## ⚙️ How to Configure

### Method 1: Edit Configuration File Directly

1. **Open the config file**:
   - Windows: Open `C:\Users\<YourUsername>\AppData\Local\Teraka\config\plugin_config.json`
   - Linux/Mac: Open `~/.config/Teraka/config/plugin_config.json`

2. **Edit with text editor** (Notepad, VS Code, etc.):
   ```json
   {
     "api": {
       "django_url": "https://api.your-server.com",
       "postgrest_url": "https://api.your-server.com:3001",
       "timeout_seconds": 45
     },
     "features": {
       "enable_offline_mode": false,
       "auto_sync_interval_minutes": 60
     }
   }
   ```

3. **Save and restart QGIS**

### Method 2: Use Environment Variables (Override)

Environment variables take priority over `plugin_config.json`:

```bash
# Windows Command Prompt
set TERAKA_API_URL=https://api.teraka.example.com
set TERAKA_POSTGREST_URL=https://api.teraka.example.com:3001
qgis

# Windows PowerShell
$env:TERAKA_API_URL="https://api.teraka.example.com"
$env:TERAKA_POSTGREST_URL="https://api.teraka.example.com:3001"
qgis

# Linux/Mac
export TERAKA_API_URL=https://api.teraka.example.com
export TERAKA_POSTGREST_URL=https://api.teraka.example.com:3001
qgis
```

### Method 3: Use Dialog (When Implemented)

**Future feature**: Add "Settings" button to plugin dockwidget to edit config interactively without editing JSON.

---

## 🔐 Production Configuration Example

For a production deployment of Teraka with SSL:

```json
{
  "api": {
    "django_url": "https://teraka.example.com",
    "postgrest_url": "https://api.teraka.example.com:3001",
    "timeout_seconds": 60
  },
  "features": {
    "enable_offline_mode": false,
    "auto_sync_interval_minutes": 120
  }
}
```

---

## 🌐 Network Configuration Examples

### Scenario 1: Local Development (Default)
```json
{
  "api": {
    "django_url": "http://localhost:8000",
    "postgrest_url": "http://localhost:3000",
    "timeout_seconds": 30
  }
}
```
**When**: Running backend with `python manage.py runserver` or `docker compose up`

### Scenario 2: Docker on Same Machine
```json
{
  "api": {
    "django_url": "http://127.0.0.1:8000",
    "postgrest_url": "http://127.0.0.1:3000",
    "timeout_seconds": 30
  }
}
```
**When**: Docker Desktop (Mac/Windows) where `localhost` and `127.0.0.1` may differ

### Scenario 3: Remote Server Over Network
```json
{
  "api": {
    "django_url": "http://192.168.1.50:8000",
    "postgrest_url": "http://192.168.1.50:3000",
    "timeout_seconds": 60
  }
}
```
**When**: Backend on network server (LAN)

### Scenario 4: Cloud Production (HTTPS)
```json
{
  "api": {
    "django_url": "https://teraka.example.com",
    "postgrest_url": "https://teraka.example.com:3001",
    "timeout_seconds": 60
  }
}
```
**When**: Production deployment with SSL/TLS certificates

### Scenario 5: Multi-Environment with Env Vars
```bash
# Development
export TERAKA_API_URL=http://localhost:8000

# Staging
export TERAKA_API_URL=https://staging.teraka.example.com

# Production (in system environment)
export TERAKA_API_URL=https://teraka.example.com
```

---

## 🐛 Troubleshooting

### Plugin Can't Connect to API

**Error**: "Connection refused" or "Cannot reach API"

**Checklist**:
1. ✅ Is the backend server running?
   ```bash
   # Django: should be running on :8000
   # PostgREST: should be running on :3000
   ```

2. ✅ Is the URL correct in `plugin_config.json`?
   ```bash
   # Try accessing in browser/curl
   curl http://localhost:8000/api/auth/login/
   curl http://localhost:3000/communes
   ```

3. ✅ Is firewall blocking the port?
   - Windows: Check Windows Defender Firewall
   - Linux: Check `ufw` or `iptables`
   - Network: Check router/VPN

4. ✅ Are you using the right hostname?
   - `localhost` only works on same machine
   - Use IP address (e.g., `192.168.1.50`) for network
   - Use domain name (e.g., `api.teraka.example.com`) for internet

### Plugin Hangs or Times Out

**Error**: Plugin freezes for 30+ seconds when loading data

**Solution**: Increase timeout in `plugin_config.json`:
```json
{
  "api": {
    "timeout_seconds": 60
  }
}
```

**Or use env var**:
```bash
export TERAKA_API_TIMEOUT=60
```

### Can't Find Configuration Directory

**Use QGIS Python Console**:
```python
from mrv_teraka import ConfigManager
import webbrowser
config_dir = ConfigManager.get_config_dir()
print(f"Config dir: {config_dir}")

# Open in file explorer (Windows)
import os
if os.name == 'nt':
    os.startfile(config_dir)
```

### Configuration Not Taking Effect

**Checklist**:
1. ✅ Saved `plugin_config.json` (CTRL+S)
2. ✅ Restarted QGIS (close and reopen)
3. ✅ Check for typos in JSON (use JSON validator)
4. ✅ Environment variables override config file (if set, remove them)

---

## 📋 Configuration Checklist

Before going to production:

- [ ] ✅ Set `django_url` to production domain
- [ ] ✅ Set `postgrest_url` to production domain
- [ ] ✅ Test connection: can reach API from QGIS
- [ ] ✅ Timeout set appropriately (≥30s)
- [ ] ✅ No credentials stored in plain text
- [ ] ✅ Using HTTPS/SSL if on internet
- [ ] ✅ Firewall rules allow connection
- [ ] ✅ Backend server is running and healthy

---

## 🔄 Configuration Priority

When plugin starts, it loads configuration in this order (first wins):

1. **Environment Variables** (highest priority)
   - `TERAKA_API_URL` → overrides django_url
   - `TERAKA_POSTGREST_URL` → overrides postgrest_url
   - `TERAKA_API_TIMEOUT` → overrides timeout_seconds

2. **plugin_config.json** (user config file)
   - If file exists, load JSON values

3. **Built-in Defaults** (lowest priority)
   - `django_url`: `http://localhost:8000`
   - `postgrest_url`: `http://localhost:3000`
   - `timeout_seconds`: `30`

**Example**: If `plugin_config.json` says `localhost:8000` but `TERAKA_API_URL` env var is set, the env var wins.

---

## 💡 Tips

### Backup Your Configuration
```bash
# Windows
copy "%LOCALAPPDATA%\Teraka\config\plugin_config.json" plugin_config.json.backup

# Linux/Mac
cp ~/.config/Teraka/config/plugin_config.json plugin_config.json.backup
```

### Test Configuration
```bash
# In QGIS Python Console
from mrv_teraka import ConfigManager
config = ConfigManager.get_config()
print("Django URL:", ConfigManager.get_api_url())
print("PostgREST URL:", ConfigManager.get_postgrest_url())
```

### Share Configuration
```bash
# Send only plugin_config.json to team (NOT containing secrets)
# Then each user can customize based on their network
```

---

## 📞 Support

If configuration doesn't work:

1. Check `~/.teraka/logs/plugin.log` for error messages
2. Set `LOG_LEVEL=DEBUG` in backend `.env`
3. Check network connectivity: `ping <your-server>`
4. Verify backend is responding: `curl <your-api-url>`
5. Open issue on GitHub with configuration details

---

**Last Updated**: 2026-06-01  
**Version**: 1.0  
**Status**: Documentation for config management system
