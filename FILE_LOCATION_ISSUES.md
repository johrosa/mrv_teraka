# File Location & Accessibility Issues & Solutions

**Date**: June 1, 2026  
**Branch**: `fix/file-location-accessibility`

## 📍 Problems Identified

### 1. Plugin Files in Hidden AppData Folder ❌

**Location**: `C:\Users\<user>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\mrv_teraka`

**Issues**:
- AppData is hidden by default (not accessible via file explorer without "Show hidden files")
- Relative paths within plugin_dir scatter files:
  - `layer_table_mapping.json` — API/table mappings
  - `Q_v17_7_7_ITASY2026_WP.qgz` — default project file
  - `mergin_workflows/` — workflow scripts
  - `i18n/` — translations
  - `synthetic_data_generator.py` creates in-memory data (OK)

**Impact**:
- Users cannot easily access config files to edit them
- Cannot backup/share config files easily
- Hard to debug without exploring hidden folders

---

### 2. API URLs Hardcoded ❌

**Locations**:
- `mrv_teraka.py` line 52: `self.api_base_url = 'http://localhost:8000'`
- `auth_dialog.py` line 63-64: Default URL hardcoded in UI
- Multiple files assume PostgREST on `:3000`

**Issues**:
- Cannot switch between dev/prod/staging without code change
- Cannot run plugin if server on different machine/port
- No environment variable override

**Impact**:
- Plugin tied to local development setup
- Cannot deploy to production without code modification

---

### 3. Backend Paths on D: Drive ❌

**Locations**:
- `docker-compose.prod.yml` — references D:\ paths
- `run_servers.py` — hardcoded directory paths
- Backend assumes specific folder layout

**Issues**:
- Not portable to other machines (might have different drives)
- Docker paths don't work on Linux/Mac
- Hardcoded paths break in CI/CD

**Impact**:
- Cannot clone/use backend on different machines
- Docker builds fail cross-platform

---

### 4. No Project Data Directory ❌

**Current state**:
- Layer mappings in plugin_dir
- Default projects hardcoded as file path
- No central location for user projects/exports

**Impact**:
- Users cannot organize their projects
- Backups scattered everywhere
- Export functionality impossible to implement

---

## ✅ Solutions

### Solution 1: Create Standard Config Directory Structure

**Windows Plugin Config Path**:
```
%USERPROFILE%\Documents\Teraka\  (or %LOCALAPPDATA%\Teraka\)
├── config/
│   ├── plugin_config.json     (← NEW: API URLs, paths)
│   └── layer_table_mapping.json
├── projects/
│   └── *.qgz (user projects)
├── exports/
│   └── (CSV, Shapefile exports)
└── logs/
    └── plugin.log
```

**Linux/Mac**:
```
~/.teraka/
├── config/...
├── projects/...
├── exports/...
└── logs/...
```

### Solution 2: Create Configuration File

**File**: `plugin_config.json` (new, user-editable)

```json
{
  "api": {
    "django_url": "http://localhost:8000",
    "postgrest_url": "http://localhost:3000",
    "timeout_seconds": 30
  },
  "paths": {
    "projects_dir": "~/Documents/Teraka/projects",
    "exports_dir": "~/Documents/Teraka/exports",
    "cache_dir": "~/.teraka/cache"
  },
  "features": {
    "enable_offline_mode": false,
    "auto_sync_interval_minutes": 60
  }
}
```

### Solution 3: Create Config Manager Class

**File**: `config_manager.py` (new)

```python
class ConfigManager:
    @staticmethod
    def get_config_dir():
        """Returns writable config dir (cross-platform)."""
        if sys.platform == 'win32':
            base = os.path.expandvars('$LOCALAPPDATA')
        else:
            base = os.path.expanduser('~/.config')
        config_dir = os.path.join(base, 'Teraka')
        os.makedirs(config_dir, exist_ok=True)
        return config_dir
    
    @staticmethod
    def get_api_url():
        """Returns Django API URL from config or env."""
        return os.getenv('TERAKA_API_URL', 'http://localhost:8000')
    
    @staticmethod
    def load_plugin_config():
        """Load user config from JSON file."""
        config_file = os.path.join(ConfigManager.get_config_dir(), 'plugin_config.json')
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
        return {}  # Return defaults if not exists
```

### Solution 4: Use Environment Variables

Allow override via env vars:

```bash
# Development
set TERAKA_API_URL=http://localhost:8000
set TERAKA_POSTGREST_URL=http://localhost:3000
set TERAKA_CONFIG_DIR=C:\dev\teraka_config

# Production
set TERAKA_API_URL=https://api.teraka.example.com
set TERAKA_POSTGREST_URL=https://api.teraka.example.com:3001
```

### Solution 5: Docker Path Portability

**Update**: `docker-compose.prod.yml`

```yaml
volumes:
  - ./:/app                    # Relative path (portable)
  - ./logs:/app/logs          # Relative to compose file
  - ./config:/app/config      # Relative config mount
```

**Update**: Use relative paths + environment variable override

```python
# Before (bad)
project_dir = "D:\\asa\\Teraka\\teraka_plateform_project"

# After (good)
project_dir = os.getenv('TERAKA_PROJECT_DIR', os.path.dirname(os.path.abspath(__file__)))
```

---

## 📋 Implementation Checklist

### Phase 1: Config Infrastructure (Priority 1)
- [ ] Create `config_manager.py` in plugin
- [ ] Create `plugin_config.json` template
- [ ] Add ConfigManager tests
- [ ] Update `mrv_teraka.py` to use ConfigManager for API URLs

### Phase 2: Plugin Path Refactoring (Priority 1)
- [ ] Create `~/.teraka/config/` directory structure
- [ ] Move `layer_table_mapping.json` to config dir (with fallback)
- [ ] Move project defaults to `~/.teraka/projects/`
- [ ] Update all file path references to use config dir

### Phase 3: Backend Docker Portability (Priority 2)
- [ ] Update `docker-compose.prod.yml` to use relative paths
- [ ] Update `run_servers.py` to use `os.path.dirname(__file__)`
- [ ] Add `TERAKA_PROJECT_DIR` env var support
- [ ] Create `.env.example` with all required vars

### Phase 4: Documentation (Priority 2)
- [ ] Create `CONFIGURATION.md` — user config guide
- [ ] Create `ENVIRONMENT_VARIABLES.md` — all env vars
- [ ] Update README.md with new paths
- [ ] Create setup script to create directory structure

### Phase 5: Migration (Priority 3)
- [ ] Add migration script for existing users
- [ ] Script to copy old configs to new location
- [ ] Backward compatibility mode (check old paths if config missing)

---

## 🎯 Expected Outcomes

### Before
```
C:\Users\john\AppData\Roaming\QGIS\...mrv_teraka\
├── layer_table_mapping.json (inaccessible)
├── Q_v17_7_7_ITASY2026_WP.qgz (buried)
└── mergin_workflows/ (hidden)

D:\asa\Teraka\teraka_plateform_project\ (D: drive only)
├── docker-compose.prod.yml (hardcoded D: paths)
└── run_servers.py (not portable)
```

### After
```
C:\Users\john\AppData\Local\Teraka\  ← Accessible!
├── config/
│   ├── plugin_config.json (← User-editable!)
│   └── layer_table_mapping.json
├── projects/  ← Can organize here
│   └── project1.qgz
├── exports/   ← Backups/exports
└── logs/

D:\asa\Teraka\... (or any path via env var!)
├── docker-compose.prod.yml (uses relative paths)
└── run_servers.py (uses $PWD)

Environment overrides:
export TERAKA_API_URL=https://...  ← Production
export TERAKA_CONFIG_DIR=/etc/teraka/  ← Server deployment
```

---

## 🔧 Files to Create/Modify

**Plugin Repo**:
- [x] NEW: `config_manager.py` — config loading logic
- [ ] MODIFY: `mrv_teraka.py` — use ConfigManager instead of hardcoded URLs
- [ ] MODIFY: `auth_dialog.py` — load default URL from config
- [ ] MODIFY: `config_postgrest.py` — look in config dir first
- [ ] NEW: `plugin_config.json.template` — example config
- [ ] NEW: `CONFIGURATION.md` — user guide

**Backend Repo**:
- [ ] MODIFY: `docker-compose.prod.yml` — relative paths
- [ ] MODIFY: `run_servers.py` — use `os.path` instead of hardcoded
- [ ] NEW: `.env.example` — env var reference
- [ ] MODIFY: `README.md` — add env vars section

---

## Status

**Branch**: `fix/file-location-accessibility`  
**Created**: 2026-06-01 16:30  
**Next**: Implement Phase 1 (ConfigManager)
