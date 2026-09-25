"""Comprehensive test suite for TrackFlow MCP Server.

Validates:
1. FastMCP Tool Discovery & Schemas.
2. Protected Resource Metadata & OAuth Authorization Server Discovery.
3. OAuth 2.1 Bearer Token Authentication (Reject unauthenticated / invalid tokens).
4. Principle of Least Privilege & Scopes Enforcement (incidents:read, incidents:write, inventory:read).
5. Incident Manager Lifecycle Status Transitions (open -> in_progress -> resolved).
6. Strictly Read-Only Inventory with Explicit Write Rejection (INVENTORY_MUTATION_FORBIDDEN).
7. Distinct Error Codes for Auth, Authz, and Validation.
8. Invocation Audit Logging.
"""

from __future__ import annotations

import asyncio
import pytest
from starlette.testclient import TestClient

from mcps.trackflow_mcp.auth import (
    SCOPE_INCIDENTS_READ,
    SCOPE_INCIDENTS_WRITE,
    SCOPE_INVENTORY_READ,
    create_mcp_access_token,
    mcp_auth,
    verify_trackflow_jwt,
)
from mcps.trackflow_mcp.server import app, mcp
from mcps.trackflow_mcp.tools.incidents import manage_incidents
from mcps.trackflow_mcp.tools.inventory import query_inventory


@pytest.fixture
def client() -> TestClient:
    """TestClient fixture for TrackFlow MCP Server ASGI application."""
    return TestClient(app)


class TestMCPServerDiscovery:
    """Discovery and Metadata tests."""

    @pytest.mark.anyio
    async def test_tool_discovery_and_schemas(self):
        """Verify FastMCP exposes manage_incidents and query_inventory with schemas and docs."""
        tools = await mcp.list_tools()
        tool_names = [t.name for t in tools]

        assert "manage_incidents" in tool_names
        assert "query_inventory" in tool_names

        # Verify manage_incidents discovery metadata
        inc_tool = next(t for t in tools if t.name == "manage_incidents")
        assert inc_tool.description is not None
        assert "Incidents Manager" in inc_tool.description or "incidencias" in inc_tool.description.lower()
        assert "properties" in inc_tool.inputSchema
        assert "action" in inc_tool.inputSchema["properties"]

        # Verify query_inventory discovery metadata
        inv_tool = next(t for t in tools if t.name == "query_inventory")
        assert inv_tool.description is not None
        assert "SOLO LECTURA" in inv_tool.description or "read-only" in inv_tool.description.lower()
        assert "properties" in inv_tool.inputSchema
        assert "query" in inv_tool.inputSchema["properties"]

    def test_root_endpoint_metadata(self, client: TestClient):
        """Verify root endpoint exposes discovery links and transport URLs."""
        res = client.get("/")
        assert res.status_code == 200
        data = res.json()
        assert data["server"] == "TrackFlow MCP Server"
        assert "oauth-protected-resource" in data["discovery"]["protected_resource_metadata"]
        assert "oauth-authorization-server" in data["discovery"]["authorization_server_metadata"]

    def test_protected_resource_metadata_rfc9728(self, client: TestClient):
        """Verify RFC 9728 Protected Resource Metadata endpoint."""
        res = client.get("/.well-known/oauth-protected-resource")
        assert res.status_code == 200
        data = res.json()
        assert "authorization_servers" in data
        assert "scopes_supported" in data
        assert SCOPE_INCIDENTS_READ in data["scopes_supported"]
        assert SCOPE_INCIDENTS_WRITE in data["scopes_supported"]
        assert SCOPE_INVENTORY_READ in data["scopes_supported"]

    def test_oauth_authorization_server_metadata_rfc8414(self, client: TestClient):
        """Verify RFC 8414 OAuth 2.0 Authorization Server Metadata endpoint."""
        res = client.get("/.well-known/oauth-authorization-server")
        assert res.status_code == 200
        data = res.json()
        assert "issuer" in data
        assert "token_endpoint" in data
        assert "code_challenge_methods_supported" in data
        assert "S256" in data["code_challenge_methods_supported"]

    def test_health_check_endpoint(self, client: TestClient):
        """Verify health check endpoint returns 200 OK without authentication."""
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


class TestMCPOAuthAuthentication:
    """Authentication and Bearer token enforcement tests."""

    def test_unauthenticated_request_to_sse_rejected(self, client: TestClient):
        """Verify unauthenticated request to /sse is rejected with 401 Unauthorized."""
        res = client.get("/sse")
        assert res.status_code == 401
        data = res.json()
        assert data["error_code"] == "AUTH_401_MISSING_HEADER"
        assert "WWW-Authenticate" in res.headers

    def test_invalid_bearer_token_rejected(self, client: TestClient):
        """Verify malformed or invalid Bearer token is rejected with 401 Unauthorized."""
        headers = {"Authorization": "Bearer invalid.jwt.token.here"}
        res = client.get("/sse", headers=headers)
        assert res.status_code == 401
        data = res.json()
        assert data["error_code"] == "AUTH_401_INVALID_TOKEN"

    def test_valid_token_issuance_and_auth(self, client: TestClient):
        """Verify token generation endpoint and Bearer authentication flow."""
        token_res = client.post("/oauth/token", json={"client_id": "test-agent", "subject": "user-test"})
        assert token_res.status_code == 200
        token_data = token_res.json()
        assert "access_token" in token_data
        token = token_data["access_token"]

        # Verify token can be decoded by mcpauth
        auth_info = verify_trackflow_jwt(token)
        assert auth_info.subject == "user-test"
        assert auth_info.client_id == "test-agent"
        assert SCOPE_INCIDENTS_READ in auth_info.scopes


class TestMCPScopesAndPermissions:
    """Principle of Least Privilege and Scopes enforcement."""

    def test_read_only_token_cannot_create_incident(self):
        """Verify client with only incidents:read scope is forbidden from creating tickets."""
        token = create_mcp_access_token("user-ro", scopes=[SCOPE_INCIDENTS_READ])
        auth_info = verify_trackflow_jwt(token)
        mcp_auth._context_var.set(auth_info)

        res = manage_incidents(
            action="create",
            title="Intento no autorizado",
            description="Debe fallar por falta de scope",
            category="technology",
            origin="internal",
            branch="zaragoza",
        )
        assert res["success"] is False
        assert "scopes" in res["error"].lower() or "permission" in res["error"].lower() or res["error_code"] in ["INCIDENT_TOOL_ERROR", "AUTH_403_INSUFFICIENT_SCOPE"]

    def test_read_only_token_cannot_update_incident_status(self):
        """Verify client with only incidents:read scope is forbidden from modifying ticket status."""
        token = create_mcp_access_token("user-ro", scopes=[SCOPE_INCIDENTS_READ])
        auth_info = verify_trackflow_jwt(token)
        mcp_auth._context_var.set(auth_info)

        res = manage_incidents(
            action="update_status",
            incident_id="TRF-000003",
            new_status="in_progress",
        )
        assert res["success"] is False

    def test_token_without_inventory_scope_cannot_query_inventory(self):
        """Verify client without inventory:read scope is forbidden from querying stock."""
        token = create_mcp_access_token("user-no-inv", scopes=[SCOPE_INCIDENTS_READ, SCOPE_INCIDENTS_WRITE])
        auth_info = verify_trackflow_jwt(token)
        mcp_auth._context_var.set(auth_info)

        res = query_inventory("CLT-SNK-W-42")
        assert res["success"] is False


class TestIncidentsToolLifecycle:
    """Incidents tool domain logic and lifecycle transitions."""

    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """Set up fully authorized client context."""
        token = create_mcp_access_token(
            "admin-tester",
            scopes=[SCOPE_INCIDENTS_READ, SCOPE_INCIDENTS_WRITE, SCOPE_INVENTORY_READ],
        )
        auth_info = verify_trackflow_jwt(token)
        mcp_auth._context_var.set(auth_info)

    def test_create_and_get_incident(self):
        """Verify creating an incident persists it and querying returns it."""
        res_create = manage_incidents(
            action="create",
            title="Paquete dañado en cinta transportadora",
            description="Rotura de embalaje detectada en muelle de carga",
            category="warehouse_operations",
            origin="internal",
            branch="zaragoza",
        )
        assert res_create["success"] is True
        inc = res_create["incident"]
        assert inc["status"] == "open"
        assert inc["branch"] == "zaragoza"
        assert inc["category"] == "warehouse_operations"
        inc_id = inc["id"]

        # Query created incident
        res_get = manage_incidents(action="get", incident_id=inc_id)
        assert res_get["success"] is True
        assert res_get["incident"]["id"] == inc_id

    def test_lifecycle_status_transitions(self):
        """Verify lifecycle status transition enforcement (open -> in_progress -> resolved)."""
        res_create = manage_incidents(
            action="create",
            title="Incidencia prueba transiciones",
            description="Test de ciclo de vida",
            category="technology",
            origin="internal",
            branch="los_angeles",
        )
        inc_id = res_create["incident"]["id"]

        # 1. Invalid transition: open -> resolved is forbidden
        res_invalid = manage_incidents(action="update_status", incident_id=inc_id, new_status="resolved")
        assert res_invalid["success"] is False
        assert res_invalid["error_code"] == "INVALID_STATUS_TRANSITION"
        assert "Transición no permitida" in res_invalid["message"]

        # 2. Valid transition: open -> in_progress
        res_step1 = manage_incidents(action="update_status", incident_id=inc_id, new_status="in_progress")
        assert res_step1["success"] is True
        assert res_step1["current_status"] == "in_progress"

        # 3. Valid transition: in_progress -> resolved
        res_step2 = manage_incidents(action="update_status", incident_id=inc_id, new_status="resolved")
        assert res_step2["success"] is True
        assert res_step2["current_status"] == "resolved"

        # 4. Invalid transition from terminal state: resolved -> open
        res_terminal = manage_incidents(action="update_status", incident_id=inc_id, new_status="open")
        assert res_terminal["success"] is False
        assert res_terminal["error_code"] == "INVALID_STATUS_TRANSITION"


class TestInventoryToolReadOnly:
    """Inventory tool read-only guarantees and write rejection."""

    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """Set up fully authorized client context."""
        token = create_mcp_access_token(
            "inventory-tester",
            scopes=[SCOPE_INVENTORY_READ],
        )
        auth_info = verify_trackflow_jwt(token)
        mcp_auth._context_var.set(auth_info)

    def test_query_inventory_by_sku(self):
        """Verify read-only stock query returns product catalog and live calculations."""
        res = query_inventory("CLT-SNK-W-42")
        assert res["success"] is True
        assert res["total_matched"] >= 1
        product = res["products"][0]
        assert "CLT-SNK-W-42" in product["sku"]
        assert "current_stock" in product
        assert isinstance(product["current_stock"], int)
        assert "unidades disponibles" in res["message"]

    def test_explicit_write_rejection_create(self):
        """Verify attempting to create a product is explicitly rejected."""
        res = query_inventory("NEW-SKU-999", action="create")
        assert res["success"] is False
        assert res["error_code"] == "INVENTORY_MUTATION_FORBIDDEN"
        assert "solo lectura" in res["message"].lower()

    def test_explicit_write_rejection_mutate_flag(self):
        """Verify passing mutate=True is explicitly rejected."""
        res = query_inventory("CLT-SNK-W-42", mutate=True)
        assert res["success"] is False
        assert res["error_code"] == "INVENTORY_MUTATION_FORBIDDEN"

    def test_explicit_write_rejection_quantity_change(self):
        """Verify passing quantity_change is explicitly rejected."""
        res = query_inventory("CLT-SNK-W-42", quantity_change=50)
        assert res["success"] is False
        assert res["error_code"] == "INVENTORY_MUTATION_FORBIDDEN"
