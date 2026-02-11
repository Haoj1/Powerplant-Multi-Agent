"""Agent Ticket - creates tickets/cases from diagnoses."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Agent Ticket",
    description="Creates tickets from diagnosis reports",
    version="0.1.0",
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "agent-ticket"}


@app.get("/tickets")
async def list_tickets():
    """List recent tickets (placeholder)."""
    return {"tickets": []}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
