"""Real-time WebSocket chat streaming and Pub/Sub session broker for TrackFlow Support Agent.

Implements Part 2 of the Real-Time Systems architecture:
- Persistent bidirectional WebSocket channel per chat session (`session_id` / `thread_id`).
- Backoffice JWT authentication via handshake query string (`?token=...`) or initial `auth` frame.
- Session and thread ownership authorization bound to the authenticated user (`owner_id` / `owner_email`).
- Producer/Consumer (Pub/Sub) decoupling between LangGraph agent execution and WebSocket subscribers.
- Token-by-token streaming (`token_chunk`) with genuine mid-stream task cancellation on client interrupt.
- Preservation of partial assistant responses marked as `interrupted` (`generation_interrupted`),
  followed by a new assistant turn when redirected with `new_input`.
- Full thread/checkpoint rehydration (`session_rehydrated`) upon reconnection with the same `session_id`.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt

from services.agent import get_compiled_agent
from services.agent.state import AgentState
from services.agent.tracing import AgentRunTrace, trace_store
from trackflow_api.auth import ALGORITHM, get_secret_key
from trackflow_api.database import get_users_db
from trackflow_api.models import UserRecord
from trackflow_api.repositories import get_user_record_by_id

logger = logging.getLogger("trackflow_api.ws_chat")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def tokenize_for_stream(text: str) -> list[str]:
    """Split generated answer into natural token chunks (words with trailing whitespace/newlines)."""
    if not text:
        return []
    tokens = re.findall(r"\S+\s*|\n+", text)
    return tokens if tokens else [text]


def authenticate_jwt_token(token: Optional[str]) -> Optional[UserRecord]:
    """Validate a Backoffice JWT token using the same secret, algorithm, and user repository as HTTP routes."""
    if not token or not isinstance(token, str):
        return None
    raw_token = token.strip()
    if raw_token.lower().startswith("bearer "):
        raw_token = raw_token[7:].strip()
    if not raw_token:
        return None

    try:
        payload = jwt.decode(raw_token, get_secret_key(), algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not isinstance(user_id, str) or not user_id.strip():
            return None
    except JWTError:
        return None

    db = get_users_db()
    try:
        record = get_user_record_by_id(db, user_id)
    finally:
        db.close()

    if record is None:
        return None

    user = UserRecord.model_validate(record)
    if not user.is_active:
        return None
    return user


@dataclass
class ChatMessageRecord:
    """Represents a single user or assistant turn in a chat session."""

    message_id: str
    turn_id: str
    session_id: str
    thread_id: str
    role: str  # "user" | "assistant"
    content: str
    status: str  # "streaming" | "completed" | "interrupted"
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)
    source_route: Optional[str] = None
    tool_used: Optional[str] = None
    nodes_executed: list[str] = field(default_factory=list)
    run_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.message_id,
            "message_id": self.message_id,
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "thread_id": self.thread_id,
            "role": self.role,
            "content": self.content,
            "status": self.status,
            "interrupted": self.status == "interrupted",
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source_route": self.source_route,
            "tool_used": self.tool_used,
            "nodes_executed": list(self.nodes_executed),
            "run_id": self.run_id,
        }


class ChatSessionChannel:
    """Per-session state and Pub/Sub channel decoupling agent generation from WebSocket connections."""

    def __init__(
        self,
        session_id: str,
        thread_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        owner_email: Optional[str] = None,
    ) -> None:
        self.session_id: str = session_id
        self.thread_id: str = thread_id or session_id
        self.owner_id: Optional[str] = owner_id
        self.owner_email: Optional[str] = owner_email
        self.messages: list[ChatMessageRecord] = []
        self.subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self.active_producer_task: Optional[asyncio.Task[None]] = None
        self.active_cancel_event: Optional[asyncio.Event] = None
        self.active_turn_id: Optional[str] = None
        self.active_message_id: Optional[str] = None
        self.status: str = "idle"
        self.created_at: str = _utc_now_iso()
        self.updated_at: str = self.created_at
        self._lock = asyncio.Lock()

    def is_owned_by(
        self, owner_id: Optional[str] = None, owner_email: Optional[str] = None
    ) -> bool:
        """Return True if the session has no owner yet or matches the given user identity."""
        if self.owner_id is None and self.owner_email is None:
            return True
        if owner_id and self.owner_id and owner_id == self.owner_id:
            return True
        if owner_email and self.owner_email and owner_email == self.owner_email:
            return True
        if owner_id and self.owner_email and owner_id == self.owner_email:
            return True
        if owner_email and self.owner_id and owner_email == self.owner_id:
            return True
        return False

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self.subscribers.discard(queue)

    async def publish(self, event_payload: dict[str, Any]) -> None:
        """Broadcast an event to all currently subscribed WebSocket consumer queues."""
        self.updated_at = _utc_now_iso()
        for queue in list(self.subscribers):
            try:
                queue.put_nowait(event_payload)
            except Exception as exc:
                logger.warning("Failed to publish event to subscriber queue: %s", exc)


class ChatSessionPubSubManager:
    """In-memory Pub/Sub broker managing chat sessions, LangGraph streaming, and mid-stream interruption."""

    def __init__(self, token_delay_seconds: float = 0.025) -> None:
        self._sessions: dict[str, ChatSessionChannel] = {}
        self._thread_owners: dict[str, tuple[Optional[str], Optional[str]]] = {}
        self.token_delay_seconds: float = token_delay_seconds

    def _verify_thread_ownership(
        self,
        thread_id: str,
        owner_id: Optional[str] = None,
        owner_email: Optional[str] = None,
    ) -> None:
        """Ensure `thread_id` is not bound to a different authenticated user."""
        if not owner_id and not owner_email:
            return

        # 1. Check recorded thread owner map
        recorded = self._thread_owners.get(thread_id)
        if recorded is not None:
            rec_id, rec_email = recorded
            temp_channel = ChatSessionChannel(
                session_id=thread_id,
                thread_id=thread_id,
                owner_id=rec_id,
                owner_email=rec_email,
            )
            if not temp_channel.is_owned_by(owner_id=owner_id, owner_email=owner_email):
                raise PermissionError(
                    "No tienes permisos para acceder al hilo de conversación de otro usuario."
                )

        # 2. Check any other active session referencing this thread_id
        for existing_sess in self._sessions.values():
            if existing_sess.thread_id == thread_id:
                if not existing_sess.is_owned_by(
                    owner_id=owner_id, owner_email=owner_email
                ):
                    raise PermissionError(
                        "No tienes permisos para acceder al hilo de conversación de otro usuario."
                    )

        # 3. Check LangGraph checkpoint state if it records a session_user
        try:
            app = get_compiled_agent()
            config = {"configurable": {"thread_id": thread_id}}
            snapshot = app.get_state(config)
            if snapshot and snapshot.values:
                ckpt_user = snapshot.values.get("session_user")
                if (
                    isinstance(ckpt_user, str)
                    and ckpt_user.strip()
                    and ckpt_user.strip() not in {owner_id or "", owner_email or ""}
                ):
                    raise PermissionError(
                        "No tienes permisos para acceder al hilo de conversación de otro usuario."
                    )
        except PermissionError:
            raise
        except Exception as exc:
            logger.debug("Checkpoint ownership check skipped for %s: %s", thread_id, exc)

    def get_or_create_session(
        self,
        session_id: str,
        thread_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        owner_email: Optional[str] = None,
    ) -> ChatSessionChannel:
        canonical_id = session_id.strip()
        session = self._sessions.get(canonical_id)
        effective_thread_id = (
            (thread_id or (session.thread_id if session else None) or canonical_id).strip()
        )

        if session is not None:
            if (owner_id or owner_email) and not session.is_owned_by(
                owner_id=owner_id, owner_email=owner_email
            ):
                raise PermissionError(
                    "No tienes permisos para acceder a la sesión de conversación de otro usuario."
                )
            self._verify_thread_ownership(
                effective_thread_id, owner_id=owner_id, owner_email=owner_email
            )
            if thread_id and thread_id.strip():
                session.thread_id = effective_thread_id
            if owner_id and not session.owner_id:
                session.owner_id = owner_id
            if owner_email and not session.owner_email:
                session.owner_email = owner_email
        else:
            self._verify_thread_ownership(
                effective_thread_id, owner_id=owner_id, owner_email=owner_email
            )
            session = ChatSessionChannel(
                session_id=canonical_id,
                thread_id=effective_thread_id,
                owner_id=owner_id,
                owner_email=owner_email,
            )
            self._sessions[canonical_id] = session

        if session.owner_id or session.owner_email:
            self._thread_owners[session.thread_id] = (
                session.owner_id,
                session.owner_email,
            )

        self._sync_from_langgraph_checkpoint(session)
        return session

    def reset(self) -> None:
        """Cancel any active tasks and clear all sessions (used in automated tests)."""
        for session in list(self._sessions.values()):
            if session.active_cancel_event is not None:
                session.active_cancel_event.set()
            if session.active_producer_task and not session.active_producer_task.done():
                session.active_producer_task.cancel()
        self._sessions.clear()
        self._thread_owners.clear()

    def _sync_from_langgraph_checkpoint(self, session: ChatSessionChannel) -> dict[str, Any]:
        """Inspect LangGraph MemorySaver checkpoint and rehydrate messages if session history is empty."""
        checkpoint_info: dict[str, Any] = {
            "has_checkpoint": False,
            "thread_id": session.thread_id,
            "values": {},
            "next": [],
        }
        try:
            app = get_compiled_agent()
            config = {"configurable": {"thread_id": session.thread_id}}
            snapshot = app.get_state(config)
            if snapshot and snapshot.values:
                values = dict(snapshot.values)
                checkpoint_info["has_checkpoint"] = True
                checkpoint_info["values"] = {
                    "question": values.get("question"),
                    "answer": values.get("answer"),
                    "source_route": values.get("source_route"),
                    "tool_used": values.get("tool_used"),
                    "is_valid": values.get("is_valid"),
                }
                checkpoint_info["next"] = list(snapshot.next) if snapshot.next else []

                # If the session has no messages in memory yet (e.g. created via prior checkpoint),
                # reconstruct the user/assistant messages from the LangGraph checkpoint state.
                if not session.messages and values.get("question"):
                    turn_id = f"turn_ckpt_{uuid.uuid4().hex[:8]}"
                    session.messages.append(
                        ChatMessageRecord(
                            message_id=f"msg_user_{uuid.uuid4().hex[:8]}",
                            turn_id=turn_id,
                            session_id=session.session_id,
                            thread_id=session.thread_id,
                            role="user",
                            content=str(values["question"]),
                            status="completed",
                        )
                    )
                    if values.get("answer"):
                        is_interrupted = bool(values.get("interrupted", False))
                        session.messages.append(
                            ChatMessageRecord(
                                message_id=f"msg_asst_{uuid.uuid4().hex[:8]}",
                                turn_id=turn_id,
                                session_id=session.session_id,
                                thread_id=session.thread_id,
                                role="assistant",
                                content=str(values["answer"]),
                                status="interrupted" if is_interrupted else "completed",
                                source_route=values.get("source_route"),
                                tool_used=values.get("tool_used"),
                            )
                        )
        except Exception as exc:
            logger.debug("Checkpoint inspection skipped for %s: %s", session.thread_id, exc)

        return checkpoint_info

    def build_rehydration_payload(self, session: ChatSessionChannel) -> dict[str, Any]:
        """Build the `session_rehydrated` snapshot payload for connecting/reconnecting clients."""
        checkpoint_info = self._sync_from_langgraph_checkpoint(session)
        return {
            "type": "session_rehydrated",
            "event": "session_rehydrated",
            "session_id": session.session_id,
            "thread_id": session.thread_id,
            "status": session.status,
            "active_turn_id": session.active_turn_id,
            "active_message_id": session.active_message_id,
            "messages": [m.to_dict() for m in session.messages],
            "checkpoint": checkpoint_info,
            "timestamp": _utc_now_iso(),
        }

    async def start_user_turn(
        self,
        session: ChatSessionChannel,
        question: str,
        *,
        session_user: Optional[str] = None,
        authorized_orders: Optional[list[str]] = None,
        token_delay: Optional[float] = None,
    ) -> dict[str, Any]:
        """Start a new user turn on the session.

        If a previous generation is still streaming, it is genuinely aborted first
        (marking its partial message as `interrupted`) before starting the new turn.
        """
        clean_question = question.strip()
        if not clean_question:
            raise ValueError("El mensaje no puede estar vacío.")

        # If a generation is already running on this session, interrupt it first!
        if (
            session.active_producer_task is not None
            and not session.active_producer_task.done()
        ):
            await self.interrupt_active_generation(
                session, new_input=clean_question, trigger_new_turn=False
            )

        turn_id = f"turn_{uuid.uuid4().hex[:10]}"
        user_msg_id = f"msg_user_{uuid.uuid4().hex[:10]}"
        asst_msg_id = f"msg_asst_{uuid.uuid4().hex[:10]}"

        user_record = ChatMessageRecord(
            message_id=user_msg_id,
            turn_id=turn_id,
            session_id=session.session_id,
            thread_id=session.thread_id,
            role="user",
            content=clean_question,
            status="completed",
        )
        asst_record = ChatMessageRecord(
            message_id=asst_msg_id,
            turn_id=turn_id,
            session_id=session.session_id,
            thread_id=session.thread_id,
            role="assistant",
            content="",
            status="streaming",
        )

        cancel_event = asyncio.Event()
        session.messages.append(user_record)
        session.messages.append(asst_record)
        session.active_turn_id = turn_id
        session.active_message_id = asst_msg_id
        session.active_cancel_event = cancel_event
        session.status = "streaming"

        # Publish user_message and generation_started events to subscribers
        await session.publish(
            {
                "type": "user_message",
                "event": "user_message",
                "session_id": session.session_id,
                "thread_id": session.thread_id,
                "turn_id": turn_id,
                "message_id": user_msg_id,
                "role": "user",
                "content": clean_question,
                "status": "completed",
                "timestamp": user_record.created_at,
            }
        )
        await session.publish(
            {
                "type": "generation_started",
                "event": "generation_started",
                "session_id": session.session_id,
                "thread_id": session.thread_id,
                "turn_id": turn_id,
                "message_id": asst_msg_id,
                "role": "assistant",
                "status": "streaming",
                "timestamp": asst_record.created_at,
            }
        )

        effective_delay = (
            token_delay if token_delay is not None else self.token_delay_seconds
        )
        producer_task = asyncio.create_task(
            self._produce_agent_turn(
                session=session,
                question=clean_question,
                turn_id=turn_id,
                asst_record=asst_record,
                cancel_event=cancel_event,
                session_user=session_user,
                authorized_orders=authorized_orders,
                token_delay=effective_delay,
            )
        )
        session.active_producer_task = producer_task
        return {
            "turn_id": turn_id,
            "user_message_id": user_msg_id,
            "assistant_message_id": asst_msg_id,
        }

    async def interrupt_active_generation(
        self,
        session: ChatSessionChannel,
        *,
        new_input: Optional[str] = None,
        session_user: Optional[str] = None,
        authorized_orders: Optional[list[str]] = None,
        token_delay: Optional[float] = None,
        trigger_new_turn: bool = True,
    ) -> dict[str, Any]:
        """Genuinely abort the in-flight producer task for `session`, mark the partial message
        as `interrupted`, emit `generation_interrupted`, and optionally start a new turn with `new_input`.
        """
        task = session.active_producer_task
        cancel_event = session.active_cancel_event
        interrupted_msg: Optional[ChatMessageRecord] = None

        for msg in reversed(session.messages):
            if msg.role == "assistant" and msg.status == "streaming":
                interrupted_msg = msg
                break

        if cancel_event is not None:
            cancel_event.set()

        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                logger.debug("Task finished during cancellation: %s", exc)

        # Ensure partial message is marked interrupted and generation_interrupted was emitted
        if interrupted_msg is not None and interrupted_msg.status == "streaming":
            await self._finalize_interrupted_message(
                session=session,
                asst_record=interrupted_msg,
                new_input=new_input,
            )
        elif interrupted_msg is None:
            # Even if no active streaming task was running when interrupt arrived,
            # check if the last assistant message was just marked interrupted by the task itself
            for msg in reversed(session.messages):
                if msg.role == "assistant" and msg.status == "interrupted":
                    interrupted_msg = msg
                    break

        clean_new_input = (new_input or "").strip()
        new_turn_info: Optional[dict[str, Any]] = None
        if trigger_new_turn and clean_new_input:
            new_turn_info = await self.start_user_turn(
                session=session,
                question=clean_new_input,
                session_user=session_user,
                authorized_orders=authorized_orders,
                token_delay=token_delay,
            )

        return {
            "interrupted_message_id": (
                interrupted_msg.message_id if interrupted_msg else None
            ),
            "partial_content": interrupted_msg.content if interrupted_msg else "",
            "new_turn": new_turn_info,
        }

    async def _finalize_interrupted_message(
        self,
        session: ChatSessionChannel,
        asst_record: ChatMessageRecord,
        new_input: Optional[str] = None,
    ) -> None:
        """Mark the assistant message as `interrupted`, persist checkpoint state, and publish `generation_interrupted`."""
        if asst_record.status == "interrupted":
            return

        asst_record.status = "interrupted"
        asst_record.updated_at = _utc_now_iso()
        session.status = "interrupted"
        session.active_turn_id = None
        session.active_message_id = None

        # Update LangGraph checkpoint with the partial content so rehydration reflects the interrupted state
        try:
            app = get_compiled_agent()
            config = {"configurable": {"thread_id": session.thread_id}}
            app.update_state(
                config,
                {
                    "answer": asst_record.content,
                },
            )
        except Exception as exc:
            logger.debug("Could not update checkpoint on interrupt: %s", exc)

        await session.publish(
            {
                "type": "generation_interrupted",
                "event": "generation_interrupted",
                "session_id": session.session_id,
                "thread_id": session.thread_id,
                "turn_id": asst_record.turn_id,
                "message_id": asst_record.message_id,
                "role": "assistant",
                "status": "interrupted",
                "interrupted": True,
                "content": asst_record.content,
                "partial_content": asst_record.content,
                "new_input": (new_input or "").strip() or None,
                "timestamp": asst_record.updated_at,
            }
        )

    async def _produce_agent_turn(
        self,
        session: ChatSessionChannel,
        question: str,
        turn_id: str,
        asst_record: ChatMessageRecord,
        cancel_event: asyncio.Event,
        session_user: Optional[str],
        authorized_orders: Optional[list[str]],
        token_delay: float,
    ) -> None:
        """Producer coroutine that streams LangGraph execution and emits `token_chunk` events."""
        t_start = time.perf_counter()
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        asst_record.run_id = run_id

        app = get_compiled_agent()
        initial_state: AgentState = {
            "question": question,
            "thread_id": session.thread_id,
            "is_valid": False,
            "context": [],
            "answer": "",
            "error": None,
            "trace": [],
            "source_route": None,
            "tool_used": None,
            "tool_result": None,
            "k": None,
            "min_score": None,
            "collection_name": None,
            "pending_proposal": None,
            "proposal_decision": None,
            "new_proposal": None,
            "relevant_memories": None,
            "session_user": session_user,
            "authorized_orders": authorized_orders,
            "guardrail_action": None,
            "guardrail_failure_type": None,
            "guardrail_reason": None,
            "is_blocked": False,
        }
        config = {"configurable": {"thread_id": session.thread_id}}

        try:
            # 1. Execute LangGraph using `.stream(..., stream_mode="updates")` checking cancellation at each node
            accumulated_state: dict[str, Any] = dict(initial_state)
            nodes_executed: list[str] = []

            def _run_graph_stream() -> list[dict[str, Any]]:
                chunks: list[dict[str, Any]] = []
                for update in app.stream(
                    initial_state, config=config, stream_mode="updates"
                ):
                    if cancel_event.is_set():
                        break
                    if isinstance(update, dict):
                        chunks.append(update)
                return chunks

            stream_updates = await asyncio.to_thread(_run_graph_stream)

            if cancel_event.is_set():
                raise asyncio.CancelledError()

            for update in stream_updates:
                for node_name, node_values in update.items():
                    nodes_executed.append(node_name)
                    if isinstance(node_values, dict):
                        accumulated_state.update(node_values)

            answer_text = str(accumulated_state.get("answer") or "")
            source_route = accumulated_state.get("source_route")
            tool_used = accumulated_state.get("tool_used")
            trace_steps = accumulated_state.get("trace", [])

            asst_record.source_route = source_route
            asst_record.tool_used = tool_used
            asst_record.nodes_executed = nodes_executed

            # 2. Stream the generated answer token by token (`token_chunk`)
            tokens = tokenize_for_stream(answer_text)
            for idx, token_str in enumerate(tokens):
                if cancel_event.is_set():
                    raise asyncio.CancelledError()

                asst_record.content += token_str
                asst_record.updated_at = _utc_now_iso()

                await session.publish(
                    {
                        "type": "token_chunk",
                        "event": "token_chunk",
                        "session_id": session.session_id,
                        "thread_id": session.thread_id,
                        "turn_id": turn_id,
                        "message_id": asst_record.message_id,
                        "role": "assistant",
                        "token": token_str,
                        "chunk": token_str,
                        "delta": token_str,
                        "content": token_str,
                        "accumulated_content": asst_record.content,
                        "index": idx,
                        "status": "streaming",
                        "timestamp": asst_record.updated_at,
                    }
                )

                if token_delay > 0:
                    await asyncio.sleep(token_delay)

            if cancel_event.is_set():
                raise asyncio.CancelledError()

            # 3. Complete the generation normally
            total_duration = (time.perf_counter() - t_start) * 1000.0
            asst_record.status = "completed"
            asst_record.updated_at = _utc_now_iso()
            session.status = "idle"
            session.active_turn_id = None
            session.active_message_id = None

            agent_trace = AgentRunTrace(
                run_id=run_id,
                thread_id=session.thread_id,
                question=question,
                nodes_executed=nodes_executed,
                steps=trace_steps if isinstance(trace_steps, list) else [],
                answer=asst_record.content,
                error=accumulated_state.get("error"),
                source_route=source_route,
                tool_used=tool_used,
                total_duration_ms=round(total_duration, 2),
            )
            trace_store.save_trace(agent_trace)

            await session.publish(
                {
                    "type": "generation_completed",
                    "event": "generation_completed",
                    "session_id": session.session_id,
                    "thread_id": session.thread_id,
                    "turn_id": turn_id,
                    "message_id": asst_record.message_id,
                    "run_id": run_id,
                    "role": "assistant",
                    "status": "completed",
                    "content": asst_record.content,
                    "answer": asst_record.content,
                    "source_route": source_route,
                    "tool_used": tool_used,
                    "nodes_executed": nodes_executed,
                    "duration_ms": round(total_duration, 2),
                    "timestamp": asst_record.updated_at,
                }
            )

        except asyncio.CancelledError:
            await self._finalize_interrupted_message(
                session=session,
                asst_record=asst_record,
            )
            raise
        except Exception as exc:
            logger.error("Error in WebSocket agent producer: %s", exc, exc_info=True)
            asst_record.status = "completed"
            if not asst_record.content:
                asst_record.content = (
                    "Error interno procesando la consulta en el agente de soporte."
                )
            asst_record.updated_at = _utc_now_iso()
            session.status = "idle"
            session.active_turn_id = None
            session.active_message_id = None
            await session.publish(
                {
                    "type": "error",
                    "event": "error",
                    "session_id": session.session_id,
                    "thread_id": session.thread_id,
                    "turn_id": turn_id,
                    "message_id": asst_record.message_id,
                    "detail": "Error interno procesando la consulta en el agente de soporte.",
                    "timestamp": asst_record.updated_at,
                }
            )


# Singleton Pub/Sub manager shared across WebSocket endpoints
chat_pubsub_manager = ChatSessionPubSubManager()


def _extract_handshake_token(websocket: WebSocket) -> Optional[str]:
    """Extract JWT token from WebSocket query string or Authorization header."""
    query_token = (
        websocket.query_params.get("token")
        or websocket.query_params.get("access_token")
        or websocket.query_params.get("jwt")
    )
    if query_token:
        return query_token

    auth_header = websocket.headers.get("authorization")
    if auth_header:
        return auth_header
    return None


def _extract_session_and_thread_id(
    websocket: WebSocket, path_session_id: Optional[str] = None
) -> tuple[Optional[str], Optional[str]]:
    """Extract `session_id` and `thread_id` from URL path or query parameters."""
    q_session = websocket.query_params.get("session_id")
    q_thread = websocket.query_params.get("thread_id")

    session_id = (path_session_id or q_session or q_thread or "").strip() or None
    thread_id = (q_thread or session_id or "").strip() or None
    return session_id, thread_id


async def handle_agent_websocket(
    websocket: WebSocket,
    path_session_id: Optional[str] = None,
) -> None:
    """Core WebSocket handler enforcing JWT auth, `session_id` ownership binding, Pub/Sub streaming, and mid-stream abort."""
    session_id, thread_id = _extract_session_and_thread_id(websocket, path_session_id)
    handshake_token = _extract_handshake_token(websocket)

    # 1. If a handshake token was explicitly provided in query/headers, validate it BEFORE accepting
    authenticated_user: Optional[UserRecord] = None
    if handshake_token is not None:
        authenticated_user = authenticate_jwt_token(handshake_token)
        if authenticated_user is None:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid or expired JWT token",
            )
            return

    # 2. If session_id/thread_id is missing and token was already provided, reject immediately before accept
    if authenticated_user is not None and not session_id:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="session_id or thread_id is required in handshake",
        )
        return

    await websocket.accept()

    # 3. If no token was in the query string, allow a brief window for a first-frame `auth` message
    if authenticated_user is None:
        try:
            first_frame = await asyncio.wait_for(websocket.receive_json(), timeout=0.45)
        except Exception:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Missing authentication token",
            )
            return

        if not isinstance(first_frame, dict):
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="First frame must be a JSON auth payload",
            )
            return

        frame_type = str(
            first_frame.get("type") or first_frame.get("event") or ""
        ).lower()
        frame_token = first_frame.get("token") or first_frame.get("access_token")
        if frame_type != "auth" or not frame_token:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Authentication required before chat events",
            )
            return

        authenticated_user = authenticate_jwt_token(str(frame_token))
        if authenticated_user is None:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid or expired JWT token",
            )
            return

        # Allow session_id/thread_id in the auth frame if not in URL
        if not session_id:
            frame_session = str(
                first_frame.get("session_id") or first_frame.get("thread_id") or ""
            ).strip()
            if frame_session:
                session_id = frame_session
                thread_id = (
                    str(first_frame.get("thread_id") or frame_session).strip()
                    or frame_session
                )

    if not session_id:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="session_id or thread_id is required",
        )
        return

    # 4. Bind socket to the session channel (enforcing user ownership) & subscribe to Pub/Sub events
    try:
        session = chat_pubsub_manager.get_or_create_session(
            session_id=session_id,
            thread_id=thread_id,
            owner_id=authenticated_user.id,
            owner_email=authenticated_user.email,
        )
    except PermissionError as exc:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=str(exc),
        )
        return

    subscriber_queue = session.subscribe()

    # 5. Immediately send `session_rehydrated` snapshot so reconnections restore full history/checkpoint
    rehydration_payload = chat_pubsub_manager.build_rehydration_payload(session)
    await websocket.send_json(rehydration_payload)

    async def _consumer_loop() -> None:
        """Forward events from the session's Pub/Sub queue to this WebSocket client."""
        try:
            while True:
                event = await subscriber_queue.get()
                await websocket.send_json(event)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.debug("WebSocket consumer loop ended for %s: %s", session_id, exc)

    consumer_task = asyncio.create_task(_consumer_loop())

    try:
        while True:
            raw_msg = await websocket.receive_json()
            if not isinstance(raw_msg, dict):
                continue

            msg_type = (
                str(raw_msg.get("type") or raw_msg.get("event") or "user_message")
                .strip()
                .lower()
            )
            token_delay_override = raw_msg.get("token_delay")
            parsed_delay: Optional[float] = (
                float(token_delay_override)
                if isinstance(token_delay_override, (int, float))
                else None
            )

            if msg_type in ("ping", "heartbeat"):
                await websocket.send_json(
                    {
                        "type": "pong",
                        "event": "pong",
                        "session_id": session.session_id,
                        "thread_id": session.thread_id,
                        "timestamp": _utc_now_iso(),
                    }
                )
                continue

            if msg_type in ("rehydrate", "sync", "get_state", "history"):
                await websocket.send_json(
                    chat_pubsub_manager.build_rehydration_payload(session)
                )
                continue

            if msg_type in ("interrupt", "abort", "cancel", "stop"):
                redirect_input = (
                    raw_msg.get("new_input")
                    or raw_msg.get("question")
                    or raw_msg.get("content")
                    or raw_msg.get("message")
                )
                await chat_pubsub_manager.interrupt_active_generation(
                    session=session,
                    new_input=str(redirect_input) if redirect_input else None,
                    session_user=authenticated_user.email,
                    authorized_orders=raw_msg.get("authorized_orders"),
                    token_delay=parsed_delay,
                    trigger_new_turn=True,
                )
                continue

            if msg_type in ("user_message", "message", "chat", "ask", "query"):
                question_text = str(
                    raw_msg.get("content")
                    or raw_msg.get("question")
                    or raw_msg.get("message")
                    or raw_msg.get("text")
                    or raw_msg.get("new_input")
                    or ""
                ).strip()
                if not question_text:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "event": "error",
                            "session_id": session.session_id,
                            "thread_id": session.thread_id,
                            "detail": "El mensaje no puede estar vacío.",
                            "timestamp": _utc_now_iso(),
                        }
                    )
                    continue

                await chat_pubsub_manager.start_user_turn(
                    session=session,
                    question=question_text,
                    session_user=authenticated_user.email,
                    authorized_orders=raw_msg.get("authorized_orders"),
                    token_delay=parsed_delay,
                )
                continue

            await websocket.send_json(
                {
                    "type": "error",
                    "event": "error",
                    "session_id": session.session_id,
                    "thread_id": session.thread_id,
                    "detail": f"Tipo de evento no soportado: {msg_type}",
                    "timestamp": _utc_now_iso(),
                }
            )

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected from session_id=%s", session_id)
    except Exception as exc:
        logger.debug("WebSocket connection closed for %s: %s", session_id, exc)
    finally:
        session.unsubscribe(subscriber_queue)
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
