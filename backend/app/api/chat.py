from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agent.orchestrator import run_agent
from app.core.deps import get_current_user
from app.database import get_db
from app.models import ChatHistory, User
from app.schemas.chat import ChatHistoryItem, ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    previous = (
        db.query(ChatHistory)
        .filter(ChatHistory.session_id == payload.session_id)
        .order_by(ChatHistory.created_at)
        .all()
    )
    history = [{"role": h.role, "content": h.message} for h in previous if h.role in ("user", "assistant")]

    result = run_agent(payload.message, chat_history=history)

    db.add(ChatHistory(session_id=payload.session_id, user_id=current_user.id, role="user", message=payload.message))
    db.add(
        ChatHistory(
            session_id=payload.session_id, user_id=current_user.id, role="assistant", message=result["answer"]
        )
    )
    db.commit()

    return ChatResponse(answer=result["answer"], tool_used=result["tool_used"], sources=result["sources"])


@router.get("/chat/history", response_model=list[ChatHistoryItem])
def chat_history(
    session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    rows = (
        db.query(ChatHistory)
        .filter(ChatHistory.session_id == session_id)
        .order_by(ChatHistory.created_at)
        .all()
    )
    return rows
