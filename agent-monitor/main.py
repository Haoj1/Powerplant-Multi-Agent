"""Agent Monitor - detects anomalies in telemetry data."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Agent Monitor",
    description="Monitors telemetry and detects anomalies",
    version="0.1.0",
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "agent-monitor"}


@app.get("/metrics")
async def metrics():
    """Get monitoring metrics."""
    return {
        "messages_processed": 0,
        "alerts_generated": 0,
        "assets_monitored": [],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
