from langchain_mcp_adapters.client import MultiServerMCPClient
from claude_project.mcp.mcp_config import load_educosys_mcp_configs
from claude_project.observability.logging import get_logger


logger = get_logger(__name__)


async def get_educosys_mcp_tools() -> list:
  """Connect to all configured MCP servers and return their tools."""
  configs = load_educosys_mcp_configs()
  logger.info(f"Connecting to MCP servers: {list(configs.keys())}")
  client = MultiServerMCPClient(configs)
  tools = await client.get_tools()
  logger.info(f"Loaded {len(tools)} tools from MCP servers")
  return tools
