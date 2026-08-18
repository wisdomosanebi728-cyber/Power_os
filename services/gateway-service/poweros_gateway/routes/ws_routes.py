import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from poweros_energy.state_aggregator import EnergyStateAggregator
from poweros_energy.routes.energy_routes import LATEST_SNAPSHOTS, get_default_seed_readings
from poweros_energy.anomaly_detector import AnomalyDetector
from poweros_optimization.solver import EconomicDispatchSolver
from poweros_optimization.config import OptimizationConfig
from poweros_common.schemas.optimization import OptimizationRequest

logger = logging.getLogger("poweros-gateway-ws")
router = APIRouter(tags=["WebSocket Stream"])

# Store connected clients per community
CONNECTED_CLIENTS: Dict[str, Set[WebSocket]] = {}
solver = EconomicDispatchSolver(OptimizationConfig())


class ConnectionManager:
    @staticmethod
    async def connect(community_id: str, websocket: WebSocket):
        await websocket.accept()
        if community_id not in CONNECTED_CLIENTS:
            CONNECTED_CLIENTS[community_id] = set()
        CONNECTED_CLIENTS[community_id].add(websocket)
        logger.info(f"WebSocket client connected for community: {community_id} (Total: {len(CONNECTED_CLIENTS[community_id])})")

    @staticmethod
    def disconnect(community_id: str, websocket: WebSocket):
        if community_id in CONNECTED_CLIENTS:
            CONNECTED_CLIENTS[community_id].discard(websocket)
            if not CONNECTED_CLIENTS[community_id]:
                del CONNECTED_CLIENTS[community_id]
        logger.info(f"WebSocket client disconnected for community: {community_id}")

    @staticmethod
    async def broadcast(community_id: str, message: dict):
        if community_id in CONNECTED_CLIENTS:
            dead_sockets = set()
            for ws in CONNECTED_CLIENTS[community_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead_sockets.add(ws)
            for ws in dead_sockets:
                CONNECTED_CLIENTS[community_id].discard(ws)


manager = ConnectionManager()


@router.websocket("/ws/live/{community_id}")
async def websocket_live_stream(websocket: WebSocket, community_id: str):
    await manager.connect(community_id, websocket)
    try:
        while True:
            # Generate live combined microgrid frame
            readings = LATEST_SNAPSHOTS.get(community_id) or get_default_seed_readings(community_id)
            energy_state = EnergyStateAggregator.calculate_live_state(readings, community_id)
            alerts = AnomalyDetector.detect_anomalies(energy_state)

            # Generate real-time economic dispatch recommendation
            opt_req = OptimizationRequest(
                community_id=community_id,
                current_demand_kw=energy_state.consumption.total_demand_kw,
                available_solar_kw=energy_state.generation.solar_kw,
                battery_soc_percent=energy_state.storage.state_of_charge_percent,
                battery_capacity_kwh=energy_state.storage.battery_capacity_kwh,
                grid_available=energy_state.grid_status.available,
                grid_tariff_per_kwh=energy_state.grid_status.tariff_per_kwh,
                generator_available=True,
                generator_rated_kw=35.0,
            )
            recommendation = solver.solve(opt_req)

            frame = {
                "type": "live_telemetry_frame",
                "community_id": community_id,
                "timestamp": energy_state.timestamp.isoformat(),
                "energy_state": energy_state.model_dump(),
                "alerts": alerts,
                "optimization": recommendation.model_dump(),
            }

            await websocket.send_json(frame)
            await asyncio.sleep(1.0)  # Stream at 1 Hz update rate

    except WebSocketDisconnect:
        manager.disconnect(community_id, websocket)
    except Exception as e:
        logger.warning(f"Error in live WebSocket stream: {e}")
        manager.disconnect(community_id, websocket)
