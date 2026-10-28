"""Unit and integration tests for Part 2: Real-Time WebSocket Chat Streaming.

Validates:
1. Backoffice JWT authentication on WebSocket handshake (`?token=...` and first `auth` frame)
   and rejection of unauthenticated sockets before any chat event.
2. Mandatory `session_id` / `thread_id` binding and strict per-user session/thread ownership ACL.
3. Event contract (`session_rehydrated`, `user_message`, `token_chunk`, `generation_interrupted`,
   `generation_completed`).
4. Genuine mid-stream interruption (`interrupt` with `new_input`): stops further `token_chunk`
   emissions from the aborted generation, preserves partial response as `interrupted`, and starts
   a new assistant turn for `new_input` without overwriting the interrupted message.
5. Reconnection with the same `session_id` / `thread_id` rehydrating full conversation history
   and LangGraph checkpoint state.
6. Pub/Sub producer-consumer decoupling across multiple WebSocket subscribers on the same session.
"""

from __future__ import annotations

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from trackflow_api.auth import create_access_token, get_password_hash
from trackflow_api.database import get_users_db, init_inventory_db
from trackflow_api.main import app
from trackflow_api.ws_chat import chat_pubsub_manager


@pytest.fixture(autouse=True)
def reset_chat_sessions(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Ensure clean Pub/Sub session state and isolated user DB for each test."""
    monkeypatch.setenv("TRACKFLOW_USERS_DB_PATH", str(tmp_path / "users-ws-test.json"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'ws-test.db'}")
    monkeypatch.setenv("SECRET_KEY", "trackflow-ws-test-secret")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    db = get_users_db()
    db.table("users").insert(
        {
            "id": "usr-ws-001",
            "email": "soporte@trackflow.com",
            "hashed_password": "hashed-test-password",
            "is_active": True,
            "role": "manager",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    )
    db.table("users").insert(
        {
            "id": "usr-ws-002",
            "email": "otro.usuario@trackflow.com",
            "hashed_password": "hashed-test-password",
            "is_active": True,
            "role": "manager",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    )
    db.close()
    chat_pubsub_manager.reset()
    yield
    chat_pubsub_manager.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def valid_jwt() -> str:
    """Create a valid JWT for the seeded backoffice support user (`usr-ws-001`)."""
    return create_access_token(subject="usr-ws-001")


@pytest.fixture
def second_user_jwt() -> str:
    """Create a valid JWT for a different backoffice user (`usr-ws-002`)."""
    return create_access_token(subject="usr-ws-002")


def test_websocket_rejects_unauthenticated_connection(client: TestClient) -> None:
    """WebSocket must reject connections with missing or invalid JWT before any chat event."""
    # 1. Invalid token in query string -> rejected immediately with 1008
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/agent/ws?session_id=sess-unauth-1&token=invalid.jwt.token"
        ) as ws:
            ws.receive_json()
    assert exc_info.value.code == 1008

    # 2. Missing token and client sends a chat message instead of an auth frame -> rejected with 1008
    with pytest.raises(WebSocketDisconnect) as exc_info2:
        with client.websocket_connect("/agent/ws?session_id=sess-unauth-2") as ws:
            ws.send_json({"type": "user_message", "content": "Hola"})
            ws.receive_json()
    assert exc_info2.value.code == 1008


def test_websocket_requires_session_id_or_thread_id(
    client: TestClient, valid_jwt: str
) -> None:
    """WebSocket must require `session_id` or `thread_id` in the handshake."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/agent/ws?token={valid_jwt}") as ws:
            ws.receive_json()
    assert exc_info.value.code == 1008


def test_websocket_accepts_first_frame_auth(
    client: TestClient, valid_jwt: str
) -> None:
    """WebSocket supports authenticating via the first client JSON frame when query token is omitted."""
    with client.websocket_connect("/agent/ws?session_id=sess-frame-auth") as ws:
        ws.send_json({"type": "auth", "token": valid_jwt})
        rehydrated = ws.receive_json()
        assert rehydrated["event"] == "session_rehydrated"
        assert rehydrated["session_id"] == "sess-frame-auth"
        assert rehydrated["thread_id"] == "sess-frame-auth"
        assert rehydrated["messages"] == []


def test_websocket_and_http_reject_cross_user_session_and_thread_access(
    client: TestClient, valid_jwt: str, second_user_jwt: str
) -> None:
    """Another authenticated user must NOT be able to read or subscribe to a session_id or thread_id owned by user 1."""
    session_id = "sess-private-owner-001"
    thread_id = "thread-private-owner-001"

    # User 1 opens and owns the session/thread
    with client.websocket_connect(
        f"/agent/ws/{session_id}?thread_id={thread_id}&token={valid_jwt}"
    ) as ws_owner:
        rehydrated = ws_owner.receive_json()
        assert rehydrated["event"] == "session_rehydrated"
        assert rehydrated["session_id"] == session_id

    # User 1 can fetch their own session state over HTTP
    own_http = client.get(
        f"/agent/sessions/{session_id}?thread_id={thread_id}",
        headers={"Authorization": f"Bearer {valid_jwt}"},
    )
    assert own_http.status_code == 200

    # User 2 attempting HTTP GET on User 1's session -> 403 Forbidden
    other_http = client.get(
        f"/agent/sessions/{session_id}?thread_id={thread_id}",
        headers={"Authorization": f"Bearer {second_user_jwt}"},
    )
    assert other_http.status_code == 403

    # User 2 attempting HTTP GET with a new session_id but User 1's thread_id -> 403 Forbidden
    hijack_thread_http = client.get(
        f"/agent/sessions/sess-attacker-new?thread_id={thread_id}",
        headers={"Authorization": f"Bearer {second_user_jwt}"},
    )
    assert hijack_thread_http.status_code == 403

    # User 2 attempting WebSocket connection on User 1's session_id -> rejected with 1008
    with pytest.raises(WebSocketDisconnect) as exc_ws_session:
        with client.websocket_connect(
            f"/agent/ws/{session_id}?token={second_user_jwt}"
        ) as ws_other:
            ws_other.receive_json()
    assert exc_ws_session.value.code == 1008

    # User 2 attempting WebSocket connection with a different session_id but User 1's thread_id -> rejected with 1008
    with pytest.raises(WebSocketDisconnect) as exc_ws_thread:
        with client.websocket_connect(
            f"/agent/ws/sess-attacker-ws?thread_id={thread_id}&token={second_user_jwt}"
        ) as ws_other_thread:
            ws_other_thread.receive_json()
    assert exc_ws_thread.value.code == 1008


def test_websocket_streams_token_chunks_and_completes(
    client: TestClient, valid_jwt: str
) -> None:
    """Agent response is streamed token-by-token (`token_chunk`) and finalized with `generation_completed`."""
    session_id = "sess-stream-001"
    with client.websocket_connect(
        f"/agent/ws/{session_id}?token={valid_jwt}"
    ) as ws:
        initial = ws.receive_json()
        assert initial["event"] == "session_rehydrated"
        assert initial["session_id"] == session_id

        ws.send_json(
            {
                "type": "user_message",
                "content": "¿Cuáles son los tiempos de entrega estándar y express en España?",
                "token_delay": 0.002,
            }
        )

        token_chunks: list[dict] = []
        completed_event: dict | None = None

        while True:
            event = ws.receive_json()
            ev_type = event.get("event") or event.get("type")
            if ev_type == "token_chunk":
                token_chunks.append(event)
            elif ev_type == "generation_completed":
                completed_event = event
                break
            elif ev_type == "error":
                pytest.fail(f"Unexpected error event: {event}")

        assert len(token_chunks) > 1, "Expected multiple token_chunk events"
        assert completed_event is not None
        assert completed_event["status"] == "completed"
        assert completed_event["session_id"] == session_id
        assert completed_event["thread_id"] == session_id

        assembled = "".join(c["token"] for c in token_chunks)
        assert assembled == completed_event["content"]
        assert len(assembled.strip()) > 10


def test_websocket_interrupt_aborts_stream_and_starts_new_turn_with_new_input(
    client: TestClient, valid_jwt: str
) -> None:
    """Mid-stream interruption must:
    1. Stop further `token_chunk` events from the original generation.
    2. Mark the partial assistant message as `interrupted` preserving emitted tokens.
    3. Accept `new_input` and start a new assistant turn without overwriting the interrupted message.
    """
    session_id = "sess-interrupt-001"
    with client.websocket_connect(
        f"/agent/ws/{session_id}?token={valid_jwt}"
    ) as ws:
        rehydrated = ws.receive_json()
        assert rehydrated["event"] == "session_rehydrated"

        # Start first generation with a slower token delay so we can interrupt mid-stream
        ws.send_json(
            {
                "type": "user_message",
                "content": "¿Cuáles son los tiempos de entrega estándar y express en España y Estados Unidos?",
                "token_delay": 0.04,
            }
        )

        first_turn_chunks: list[dict] = []
        first_turn_id: str | None = None
        first_message_id: str | None = None

        # Collect 3 token chunks from the first turn, then interrupt and redirect
        while len(first_turn_chunks) < 3:
            ev = ws.receive_json()
            if ev.get("event") == "token_chunk":
                first_turn_chunks.append(ev)
                first_turn_id = ev["turn_id"]
                first_message_id = ev["message_id"]

        assert first_turn_id is not None
        assert first_message_id is not None

        # Send interrupt signal with redirected new_input
        redirect_question = "Hola, solo confírmame si estás operativo."
        ws.send_json(
            {
                "type": "interrupt",
                "new_input": redirect_question,
                "token_delay": 0.002,
            }
        )

        interrupted_event: dict | None = None
        chunks_after_interrupt_for_first_turn: list[dict] = []
        second_turn_chunks: list[dict] = []
        second_completed_event: dict | None = None

        while True:
            ev = ws.receive_json()
            ev_type = ev.get("event") or ev.get("type")

            if ev_type == "generation_interrupted":
                interrupted_event = ev
            elif ev_type == "token_chunk":
                if ev.get("turn_id") == first_turn_id:
                    if interrupted_event is not None:
                        chunks_after_interrupt_for_first_turn.append(ev)
                    else:
                        first_turn_chunks.append(ev)
                else:
                    second_turn_chunks.append(ev)
            elif ev_type == "generation_completed":
                if ev.get("turn_id") != first_turn_id:
                    second_completed_event = ev
                    break

        # 1. Verify generation_interrupted event contract
        assert interrupted_event is not None
        assert interrupted_event["turn_id"] == first_turn_id
        assert interrupted_event["message_id"] == first_message_id
        assert interrupted_event["status"] == "interrupted"
        assert interrupted_event["interrupted"] is True
        partial_text = interrupted_event["partial_content"]
        assert partial_text == "".join(c["token"] for c in first_turn_chunks)
        assert len(partial_text) > 0

        # 2. Verify NO further token_chunk events were emitted for the first turn after interruption
        assert chunks_after_interrupt_for_first_turn == []

        # 3. Verify the redirected turn completed as a brand-new message/turn
        assert second_completed_event is not None
        assert second_completed_event["turn_id"] != first_turn_id
        assert second_completed_event["message_id"] != first_message_id
        assert second_completed_event["status"] == "completed"
        assert len(second_turn_chunks) > 0
        assert second_completed_event["content"] == "".join(
            c["token"] for c in second_turn_chunks
        )


def test_websocket_reconnection_rehydrates_conversation_and_checkpoint(
    client: TestClient, valid_jwt: str
) -> None:
    """Reconnecting with the same `session_id` must restore the full message history
    (including interrupted partial messages and completed turns) and LangGraph checkpoint.
    """
    session_id = "sess-reconnect-001"

    # Connection 1: run a turn that gets interrupted and redirected to a second turn
    with client.websocket_connect(
        f"/agent/ws/{session_id}?token={valid_jwt}"
    ) as ws1:
        ws1.receive_json()  # initial empty session_rehydrated
        ws1.send_json(
            {
                "type": "user_message",
                "content": "¿Cuál es la ventana de devolución estándar?",
                "token_delay": 0.03,
            }
        )
        seen_chunks = 0
        while seen_chunks < 2:
            ev = ws1.receive_json()
            if ev.get("event") == "token_chunk":
                seen_chunks += 1

        ws1.send_json(
            {
                "type": "interrupt",
                "new_input": "¿Qué transportista tiene mejor cobertura en zonas rurales de Aragón?",
                "token_delay": 0.002,
            }
        )

        while True:
            ev = ws1.receive_json()
            if ev.get("event") == "generation_completed":
                break

    # Connection 2 (simulate drop & reconnect with same session_id):
    with client.websocket_connect(
        f"/agent/ws/{session_id}?token={valid_jwt}"
    ) as ws2:
        rehydrated = ws2.receive_json()
        assert rehydrated["event"] == "session_rehydrated"
        assert rehydrated["session_id"] == session_id
        assert rehydrated["thread_id"] == session_id

        messages = rehydrated["messages"]
        # Expect 4 messages: user 1, assistant 1 (interrupted), user 2, assistant 2 (completed)
        assert len(messages) == 4
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["status"] == "interrupted"
        assert messages[1]["interrupted"] is True
        assert len(messages[1]["content"]) > 0

        assert messages[2]["role"] == "user"
        assert "Aragón" in messages[2]["content"]
        assert messages[3]["role"] == "assistant"
        assert messages[3]["status"] == "completed"
        assert len(messages[3]["content"]) > 0

        # Verify LangGraph checkpoint metadata is present
        assert rehydrated["checkpoint"]["has_checkpoint"] is True


def test_websocket_pubsub_broadcasts_to_multiple_subscribers(
    client: TestClient, valid_jwt: str
) -> None:
    """Multiple WebSocket subscribers connected to the same `session_id` receive identical
    events from a single decoupled agent producer task.
    """
    session_id = "sess-pubsub-fanout"
    with client.websocket_connect(
        f"/agent/ws/{session_id}?token={valid_jwt}"
    ) as ws_a, client.websocket_connect(
        f"/agent/ws/{session_id}?token={valid_jwt}"
    ) as ws_b:
        assert ws_a.receive_json()["event"] == "session_rehydrated"
        assert ws_b.receive_json()["event"] == "session_rehydrated"

        ws_a.send_json(
            {
                "type": "user_message",
                "content": "Hola",
                "token_delay": 0.002,
            }
        )

        completed_a = None
        completed_b = None
        chunks_a: list[str] = []
        chunks_b: list[str] = []

        while completed_a is None:
            ev = ws_a.receive_json()
            if ev.get("event") == "token_chunk":
                chunks_a.append(ev["token"])
            elif ev.get("event") == "generation_completed":
                completed_a = ev

        while completed_b is None:
            ev = ws_b.receive_json()
            if ev.get("event") == "token_chunk":
                chunks_b.append(ev["token"])
            elif ev.get("event") == "generation_completed":
                completed_b = ev

        assert chunks_a == chunks_b
        assert completed_a["message_id"] == completed_b["message_id"]
        assert completed_a["run_id"] == completed_b["run_id"]
