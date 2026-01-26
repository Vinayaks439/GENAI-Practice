"""
A2A Security Agent - Main Agent Server
Implements the A2A protocol server for the Security Agent.
"""
import asyncio
import json
import uuid
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from .agent_card import get_agent_card, SECURITY_AGENT_CARD
from .agent_executor import handle_task, executor


# FastAPI app
app = FastAPI(
    title="A2A Security Agent",
    description="AI Security Analyst Agent implementing A2A protocol",
    version="1.0.0"
)

# CORS middleware for A2A protocol
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for A2A protocol
class TaskRequest(BaseModel):
    """Request to create a new task."""
    skill_id: str
    input: dict
    metadata: Optional[dict] = None


class TaskResponse(BaseModel):
    """Response containing task information."""
    task_id: str
    state: str
    result: Optional[dict] = None
    error: Optional[str] = None
    messages: list[dict] = []


class MessageRequest(BaseModel):
    """Request to send a message to an existing task."""
    content: str
    metadata: Optional[dict] = None


# Authentication dependency
async def verify_auth(authorization: Optional[str] = Header(None)):
    """Verify authentication for A2A requests."""
    # In production, implement proper JWT/OAuth validation
    # For now, we'll accept any bearer token or allow unauthenticated for testing
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        # Validate token here
        return {"authenticated": True, "token": token}
    return {"authenticated": False, "token": None}


# A2A Protocol Endpoints

@app.get("/.well-known/agent.json")
async def get_agent_info():
    """
    A2A Protocol: Agent Discovery
    Returns the agent card with capabilities and skills.
    """
    return get_agent_card()


@app.post("/tasks")
async def create_task(
    request: TaskRequest,
    auth: dict = Depends(verify_auth)
) -> TaskResponse:
    """
    A2A Protocol: Create a new task
    Creates a task to execute a specific skill.
    """
    # Validate skill exists
    valid_skills = [s.id for s in SECURITY_AGENT_CARD.skills]
    if request.skill_id not in valid_skills:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid skill_id. Valid skills: {valid_skills}"
        )
    
    try:
        result = await handle_task(request.skill_id, request.input)
        
        return TaskResponse(
            task_id=result["task_id"],
            state=result["state"],
            result=result["result"],
            error=result["error"],
            messages=result["messages"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    auth: dict = Depends(verify_auth)
) -> TaskResponse:
    """
    A2A Protocol: Get task status
    Returns the current state and result of a task.
    """
    task = executor.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResponse(
        task_id=task.id,
        state=task.state.value,
        result=task.result,
        error=task.error,
        messages=[
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp
            }
            for msg in task.messages
        ]
    )


@app.post("/tasks/{task_id}/messages")
async def send_message(
    task_id: str,
    request: MessageRequest,
    auth: dict = Depends(verify_auth)
) -> TaskResponse:
    """
    A2A Protocol: Send message to task
    Sends a follow-up message to an existing task.
    """
    task = executor.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # For now, we don't support follow-up messages
    # In a full implementation, this would trigger additional processing
    raise HTTPException(
        status_code=501,
        detail="Follow-up messages not yet implemented"
    )


@app.delete("/tasks/{task_id}")
async def cancel_task(
    task_id: str,
    auth: dict = Depends(verify_auth)
):
    """
    A2A Protocol: Cancel a task
    Cancels a pending or in-progress task.
    """
    task = executor.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Cancel logic would go here
    return {"status": "cancelled", "task_id": task_id}


# Additional endpoints for security-specific features

@app.get("/audit-log")
async def get_audit_log(
    auth: dict = Depends(verify_auth)
):
    """Get the agent's audit log."""
    return {
        "audit_log": executor.get_audit_log(),
        "total_entries": len(executor.get_audit_log())
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent": SECURITY_AGENT_CARD.name,
        "version": SECURITY_AGENT_CARD.version,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/skills")
async def list_skills():
    """List available skills with details."""
    return {
        "skills": [
            {
                "id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "tags": skill.tags
            }
            for skill in SECURITY_AGENT_CARD.skills
        ]
    }


# Quick test endpoint
@app.post("/quick-analyze")
async def quick_analyze(
    text: str,
    auth: dict = Depends(verify_auth)
):
    """
    Quick security analysis without full task creation.
    Useful for simple integrations.
    """
    result = await handle_task("analyze_security", {"text": text, "strict_mode": True})
    return result["result"]


def main():
    """Run the A2A Security Agent server."""
    print("🛡️  A2A Security Agent starting...")
    print(f"   Agent: {SECURITY_AGENT_CARD.name}")
    print(f"   Version: {SECURITY_AGENT_CARD.version}")
    print(f"   Skills: {[s.id for s in SECURITY_AGENT_CARD.skills]}")
    print()
    print("   Endpoints:")
    print("   - GET  /.well-known/agent.json  - Agent discovery")
    print("   - POST /tasks                    - Create task")
    print("   - GET  /tasks/{task_id}         - Get task status")
    print("   - GET  /health                   - Health check")
    print()
    
    uvicorn.run(
        "a2a_agents.security_agent.agent:app",
        host="0.0.0.0",
        port=8081,
        reload=True
    )


if __name__ == "__main__":
    main()
