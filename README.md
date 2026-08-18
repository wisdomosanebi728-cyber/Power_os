# ⚡ POWER OS — Distributed Microgrid Operating System

**POWER OS** is an energy management and real-time telemetry operating system engineered for rural mini-grids, industrial microgrids, and commercial solar-plus-storage distributed energy resources (DERs).

---

## 🏛️ System Architecture

```
                                  ┌───────────────────────────────┐
                                  │      Power_OS Simulator       │
                                  │ (PV, BESS, Genset, Microloads)│
                                  └──────────────┬────────────────┘
                                                 │ (MQTT)
                                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    Infrastructure Tier                                      │
│           TimescaleDB (Hypertable)   •   Eclipse Mosquitto (MQTT)   •   Redis Streams       │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
                                                 ▲
      ┌──────────────────────┬───────────────────┼───────────────────┬──────────────────────┐
      │                      │                   │                   │                      │
┌─────┴──────────────┐ ┌─────┴─────────────┐ ┌───┴─────────────┐ ┌───┴────────────┐ ┌─────┴──────────────┐
│ Ingestion Service  │ │ Auth & Device     │ │ Energy Service  │ │ Forecasting    │ │ Optimization       │
│ (SunSpec, Meters,  │ │ (JWT, Device Keys,│ │ (State Agg,     │ │ (Solar & Load  │ │ (MILP Solver,      │
│ Buffer Writer)     │ │ RBAC, Heartbeat)  │ │ Anomaly Engine) │ │ 24h Predictors)│ │ Physical Guard)    │
└─────┬──────────────┘ └─────┬─────────────┘ └───┬─────────────┘ └───┬────────────┘ └─────┬──────────────┘
      │                      │                   │                   │                    │
      └──────────────────────┴───────────────────┼───────────────────┴────────────────────┘
                                                 ▼
                                ┌───────────────────────────────────┐
                                │      Unified API Gateway & Hub    │
                                │   FastAPI + WebSocket Live Stream │
                                └─────────────────┬─────────────────┘
                                                  │
                                                  ▼
                                ┌───────────────────────────────────┐
                                │  Interactive Operations Dashboard │
                                │     (Real-Time Web Interface)     │
                                └───────────────────────────────────┘
```

---

## 🚀 Quickstart

### 1. Launch with Docker Compose (Recommended)
To boot the full multi-service stack (Database, MQTT Broker, Redis, Microservices, Simulator, and Web Dashboard):

```bash
cd infrastructure/docker
docker compose up --build -d
```

Open your browser to:
- **Operations Dashboard**: [http://localhost:8080](http://localhost:8080)
- **API Swagger Documentation**: [http://localhost:8080/docs](http://localhost:8080/docs)

---

### 2. Local Python Development Mode
Install dependencies in editable mode across services and start the unified gateway:

```bash
pip install -e services/common
pip install -e services/auth-device-service
pip install -e services/energy-service
pip install -e services/forecasting-service
pip install -e services/optimization-service
pip install -e services/ingestion-service
pip install -e services/gateway-service
pip install -r simulator/requirements.txt

# Start the Gateway & Live Dashboard
python run_poweros.py
```

---

## 📦 Microservices Directory

| Service | Port | Description |
| :--- | :---: | :--- |
| **`poweros-gateway`** | `8080` | Unified API entrypoint, WebSocket 1 Hz telemetry broadcaster, and web dashboard static server. |
| **`poweros-auth-device`** | `8000` | RBAC authentication (JWT), device API key issuance, and heartbeat monitor. |
| **`poweros-ingestion`** | `8001` | High-throughput telemetry ingestion with SunSpec, Modbus, and JSON adapters. |
| **`poweros-energy`** | `8002` | Live energy state aggregation, generation mix LCOE calculation, and anomaly detection. |
| **`poweros-forecasting`** | `8003` | Physics-informed 24h solar generation models and multi-tier consumer demand forecasting. |
| **`poweros-optimization`**| `8004` | Mixed-Integer Linear Programming (MILP) dispatch solver with inverter physical safety guards. |
| **`poweros-simulator`** | — | High-fidelity hardware physics simulator (Solar PV, BESS LFP, Diesel Genset, Tiered Loads). |

---

## 🧪 Simulation Scenarios

The simulator supports real-time scenario injection via the dashboard or API:
- `normal`: Standard clear afternoon with high solar self-consumption.
- `cloud_pass`: Sudden 85% drop in irradiance, triggering BESS discharge buffer.
- `grid_blackout`: Utility grid fails, microgrid seamlessly islands onto BESS + Solar.
- `heatwave_surge`: Extreme cooling & AC load demand exceeding inverter peak ratings.
- `generator_failover`: Nighttime zero-solar scenario testing diesel backup start and fuel burn rate.
