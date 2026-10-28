"""Service-level test suite for Part 2 WebSocket chat streaming (`services/api/tests/`)."""

from tests.test_websocket_chat import (  # noqa: F401
    client,
    reset_chat_sessions,
    test_websocket_accepts_first_frame_auth,
    test_websocket_interrupt_aborts_stream_and_starts_new_turn_with_new_input,
    test_websocket_pubsub_broadcasts_to_multiple_subscribers,
    test_websocket_reconnection_rehydrates_conversation_and_checkpoint,
    test_websocket_rejects_unauthenticated_connection,
    test_websocket_requires_session_id_or_thread_id,
    test_websocket_streams_token_chunks_and_completes,
    valid_jwt,
)
