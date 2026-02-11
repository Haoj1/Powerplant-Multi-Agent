"""Agent Diagnosis - performs root cause analysis."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Agent Diagnosis",
    description="Performs root cause analysis on alerts",
    version="0.1.0",
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "agent-diagnosis"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
