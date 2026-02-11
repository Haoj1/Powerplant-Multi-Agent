"""Agent Review - handles human review and feedback."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Agent Review",
    description="Handles human review and feedback loop",
    version="0.1.0",
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "agent-review"}


@app.post("/review")
async def submit_review():
    """Submit a review (placeholder)."""
    return {"message": "Review endpoint - to be implemented"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
