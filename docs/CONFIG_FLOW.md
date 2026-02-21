# Spark Configuration Flow Diagram

## Complete Configuration Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     WEB BROWSER (React)                              │
│                    index_knox.html                                   │
│                                                                       │
│  sparkConfig State (14 fields):                                      │
│  ├─ driverMemory: "8g"                                               │
│  ├─ driverCores: 4                                                   │
│  ├─ executorMemory: "8g"                                             │
│  ├─ executorCores: 4                                                 │
│  ├─ numExecutors: 8                                                  │
│  ├─ queue: "root.datalake"                                           │
│  ├─ proxyUser: "sddesigner"                                          │
│  ├─ heartbeatTimeoutInSecond: 60                                     │
│  ├─ conf: {}                                                         │
│  ├─ archives: []                                                     │
│  ├─ files: []                                                        │
│  ├─ jars: []                                                         │
│  └─ pyFiles: []                                                      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ POST /api/v1/analyze
                           │ with spark_config
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│              FastAPI Server (server.py)                              │
│                                                                       │
│  @app.post("/api/v1/analyze")                                        │
│  async def analyze_v1(request: TrendAnalysisV1Request):              │
│      request.spark_config = {...}  ◄─── Received from UI            │
│      job_id = create_job(...)                                        │
│      thread.start(execute_analysis_async(                            │
│          job_id, prompt, request.spark_config))  ◄─── Passed!        │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│          Trend Analyzer (trend_analyzer.py)                          │
│                                                                       │
│  def analyze_trend(user_prompt, spark_config={})                     │
│      spark_config = {                                                │
│          'driverMemory': '8g',                                       │
│          'driverCores': 4,                                           │
│          ...                                                         │
│      }                                                               │
│                                                                       │
│      livy_config = {                                                 │
│          'knox_host': Config.KNOX_HOST,                              │
│          'driver_memory': spark_config.get('driverMemory',           │
│                           Config.DRIVER_MEMORY),                     │
│          'driver_cores': spark_config.get('driverCores', ..),        │
│          ...  ◄─── Merge user config + defaults                     │
│      }                                                               │
│                                                                       │
│      livy = KnoxLivyClient(**livy_config)  ◄─── Pass config          │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│          Livy Client (livy_client.py)                                │
│                                                                       │
│  class KnoxLivyClient:                                               │
│      def __init__(self,                                              │
│          ...                                                         │
│          driver_memory="4g",     ◄─── Receives from trend_analyzer  │
│          driver_cores=2,                                             │
│          executor_memory="4g",                                       │
│          executor_cores=2,                                           │
│          num_executors=4,                                            │
│          queue="root.datalake",                                      │
│          proxy_user=None,                                            │
│          heartbeat_timeout_in_second=0,                              │
│          conf=None,                                                  │
│          archives=None,                                              │
│          files=None,                                                 │
│          jars=None,                                                  │
│          py_files=None):                                             │
│                                                                       │
│          self.driver_memory = driver_memory  ◄─── Store in self     │
│          ... (store all 14 params)                                   │
│                                                                       │
│      def create_session(self):                                       │
│          payload = {                                                 │
│              "kind": "spark",                                        │
│              "driverMemory": self.driver_memory,  ◄─── Use stored    │
│              "driverCores": self.driver_cores,                       │
│              "executorMemory": self.executor_memory,                 │
│              "executorCores": self.executor_cores,                   │
│              "numExecutors": self.num_executors,                     │
│              "queue": self.queue,                                    │
│              "proxyUser": self.proxy_user,                           │
│              "heartbeatTimeoutInSecond": self.heartbeat...,          │
│              "conf": self.conf,  ◄─── Add optional params if set    │
│              "archives": self.archives,                              │
│              "files": self.files,                                    │
│              "jars": self.jars,                                      │
│              "pyFiles": self.py_files                                │
│          }                                                           │
│          POST /gateway/.../livy/v1/sessions  ◄─── Send to Livy       │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│             Apache Livy (Knox Gateway)                               │
│                                                                       │
│  Creates Spark Session with:                                         │
│  ├─ driverMemory: 8g     (instead of default 4g)                     │
│  ├─ driverCores: 4       (instead of default 2)                      │
│  ├─ executorMemory: 8g   (instead of default 4g)                     │
│  ├─ executorCores: 4     (instead of default 2)                      │
│  ├─ numExecutors: 8      (instead of default 4)                      │
│  ├─ queue: root.datalake (same as default)                           │
│  ├─ proxyUser: sddesigner                                            │
│  ├─ heartbeatTimeoutInSecond: 60                                     │
│  └─ ... (other advanced params if provided)                          │
│                                                                       │
│  ✓ Session ID 123 Created Successfully!                              │
└────────────────────────────────────────────────────────────────────┘
```

## Key Transformation Points

### 1️⃣ Frontend → API
```javascript
// React state
sparkConfig = {
  driverMemory: "8g",
  driverCores: 4,
  executorMemory: "8g",
  executorCores: 4,
  numExecutors: 8,
  queue: "root.datalake"
}

// POST to /api/v1/analyze
fetch('/api/v1/analyze', {
  method: 'POST',
  body: JSON.stringify({
    prompt: "...",
    spark_config: sparkConfig  // ✓ Passed here!
  })
})
```

### 2️⃣ API → Analyzer
```python
# In server.py
thread = Thread(target=JobManager.execute_analysis_async, 
                args=(job_id, prompt, request.spark_config))
                              
# In execute_analysis_async()
result = analyze_trend(prompt, spark_config=spark_config or {})
```

### 3️⃣ Analyzer → Livy Client
```python
# In trend_analyzer.py
livy_config = {
    'knox_host': Config.KNOX_HOST,
    'ad_user': Config.AD_USER,
    'ad_password': Config.AD_PASSWORD,
    'driver_memory': spark_config.get('driverMemory', Config.DRIVER_MEMORY),
    'driver_cores': spark_config.get('driverCores', Config.DRIVER_CORES),
    # ... merge user config with defaults
}

# Remove None values
livy_config = {k: v for k, v in livy_config.items() if v is not None}

# Create client with merged config
livy = KnoxLivyClient(**livy_config)
```

### 4️⃣ Livy Client → Livy Server
```python
# In livy_client.py create_session()
payload = {
    "kind": "spark",
    "driverMemory": self.driver_memory,      # "8g"
    "driverCores": self.driver_cores,        # 4
    "executorMemory": self.executor_memory,  # "8g"
    "executorCores": self.executor_cores,    # 4
    "numExecutors": self.num_executors,      # 8
    "queue": self.queue,                     # "root.datalake"
    "proxyUser": self.proxy_user,            # "sddesigner"
    "heartbeatTimeoutInSecond": self.heartbeat_timeout_in_second
}

# Add optional params only if they have values
if self.conf:
    payload["conf"] = self.conf
if self.archives:
    payload["archives"] = self.archives
# ... etc

requests.post(f"{self.base_url}/sessions", json=payload)
```

## Configuration Precedence Order

When a parameter is requested:

```
1. USER INPUT (Highest Priority)
   ├─ Values from sparkConfig in UI
   │
2. ENVIRONMENT DEFAULTS (If user didn't specify)
   ├─ Values from Config class
   │ (src/models/config.py)
   │
3. LIVY DEFAULTS (Lowest Priority)
   └─ Built-in Livy defaults
```

Example with Driver Memory:

```
User specifies: spark_config.driverMemory = "8g"
   │
   ├─ USE: "8g" ✓
   
User specifies: null or undefined
   │
   ├─ Check Config.DRIVER_MEMORY = "4g"
   ├─ USE: "4g" ✓
   
Neither specified
   │
   ├─ Use Livy default (not sent in payload)
   └─ Livy uses: typically "1g"
```

## Logging for Debugging

All key transformation points are logged:

```bash
# 1. API receives config
2026-02-21 14:20:40 - src.api.server - INFO - ⚙️  Config Spark: {'driverMemory': '8g'...}

# 2. Analyzer processes config  
2026-02-21 14:20:41 - src.agents.trend_analyzer - INFO - Config Spark: {'driverMemory': '8g'...}

# 3. Livy client creates payload (see spark_server.log for details)
```

To view real-time logs during execution:
```bash
tail -f /tmp/spark_server.log | grep -i "config\|payload"
```

## Testing the Configuration Flow

### Test 1: Verify Config is Passed Through
```bash
# Send custom config
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Analyse table=splio.active date=20260121",
    "spark_config": {
      "driverMemory": "16g",
      "driverCores": 8,
      "numExecutors": 16
    }
  }'

# Check logs
grep "Config Spark" /tmp/spark_server.log | tail -2
# Should see: driverMemory: 16g, driverCores: 8, numExecutors: 16
```

### Test 2: Verify Defaults Fallback
```bash
# Send empty config
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Analyse table=splio.active date=20260121",
    "spark_config": {}
  }'

# Check logs
grep "Config Spark" /tmp/spark_server.log | tail -1
# Should show fallback to Config defaults
```

### Test 3: Verify UI Sends Config
In browser console:
```javascript
// Before submitting, check what will be sent
console.log('Spark Config:', sparkConfig)
// Should show all 14 fields with user values
```
