"""Pruebas unitarias del servidor MCP de DaVinci Flow."""

import json
import unittest

from davinci_flow.errors import DaVinciFlowError
from davinci_flow.mcp_server import (
    PROTOCOL_VERSION,
    TOOLS,
    DaVinciFlowMCPServer,
    ToolSpec,
)


class _FakeTool(ToolSpec):
    pass


class MCPServerProtocolTests(unittest.TestCase):
    """Verifica el protocolo JSON-RPC del servidor."""

    def setUp(self) -> None:
        self.server = DaVinciFlowMCPServer()

    def test_initialize_reports_server_info(self) -> None:
        response = self.server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        result = response["result"]
        self.assertEqual(result["protocolVersion"], PROTOCOL_VERSION)
        self.assertEqual(result["serverInfo"]["name"], "davinci-flow")
        self.assertIn("tools", result["capabilities"])

    def test_initialize_negotiates_client_protocol(self) -> None:
        response = self.server.handle(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}}
        )
        self.assertEqual(response["result"]["protocolVersion"], "2024-11-05")

    def test_notifications_return_nothing(self) -> None:
        self.assertIsNone(self.server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_tools_list_publishes_every_tool(self) -> None:
        response = self.server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = response["result"]["tools"]
        self.assertEqual(len(tools), len(TOOLS))
        names = {tool["name"] for tool in tools}
        self.assertIn("davinciflow_status", names)
        self.assertIn("davinciflow_create_fusion_effect", names)
        self.assertIn("davinciflow_synthesize_speech", names)
        self.assertIn("davinciflow_autocorrect", names)
        self.assertIn("davinciflow_write_subtitles", names)
        for tool in tools:
            self.assertIn("description", tool)
            self.assertEqual(tool["inputSchema"]["type"], "object")

    def test_unknown_tool_is_reported(self) -> None:
        response = self.server.handle(
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "inexistente", "arguments": {}}}
        )
        self.assertIn("error", response)

    def test_unknown_method_is_reported(self) -> None:
        response = self.server.handle({"jsonrpc": "2.0", "id": 4, "method": "otro/metodo"})
        self.assertEqual(response["error"]["code"], -32601)

    def test_ping(self) -> None:
        response = self.server.handle({"jsonrpc": "2.0", "id": 5, "method": "ping"})
        self.assertEqual(response["result"], {})


class MCPToolDispatchTests(unittest.TestCase):
    """Verifica el despacho de herramientas con dobles."""

    def test_successful_call_returns_structured_content(self) -> None:
        tool = ToolSpec(
            name="davinciflow_demo",
            description="Demostración",
            input_schema={"type": "object", "properties": {}},
            handler=lambda arguments: {"ok": True, "dato": arguments.get("valor")},
        )
        server = DaVinciFlowMCPServer((tool,))
        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "davinciflow_demo", "arguments": {"valor": 7}},
            }
        )
        result = response["result"]
        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"], {"ok": True, "dato": 7})
        self.assertEqual(json.loads(result["content"][0]["text"])["dato"], 7)

    def test_domain_error_is_returned_as_tool_error(self) -> None:
        def _handler(arguments):
            raise DaVinciFlowError("Resolve no está abierto.")

        tool = ToolSpec(
            name="davinciflow_falla",
            description="Falla controlada",
            input_schema={"type": "object", "properties": {}},
            handler=_handler,
        )
        server = DaVinciFlowMCPServer((tool,))
        response = server.handle(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "davinciflow_falla", "arguments": {}}}
        )
        result = response["result"]
        self.assertTrue(result["isError"])
        self.assertIn("Resolve no está abierto.", result["content"][0]["text"])

    def test_unexpected_error_is_contained(self) -> None:
        def _handler(arguments):
            raise RuntimeError("fallo inesperado")

        tool = ToolSpec(
            name="davinciflow_falla",
            description="Falla inesperada",
            input_schema={"type": "object", "properties": {}},
            handler=_handler,
        )
        server = DaVinciFlowMCPServer((tool,))
        response = server.handle(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "davinciflow_falla", "arguments": {}}}
        )
        self.assertTrue(response["result"]["isError"])


class MCPToolCatalogueTests(unittest.TestCase):
    """Verifica que el catálogo publicado sea coherente."""

    def test_names_are_unique_and_prefixed(self) -> None:
        names = [tool.name for tool in TOOLS]
        self.assertEqual(len(names), len(set(names)))
        for name in names:
            self.assertTrue(name.startswith("davinciflow_"))

    def test_required_fields_are_declared(self) -> None:
        for tool in TOOLS:
            for field in tool.input_schema.get("required", []):
                self.assertIn(field, tool.input_schema.get("properties", {}))


if __name__ == "__main__":
    unittest.main()
