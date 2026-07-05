from dotenv import load_dotenv
load_dotenv()
from langchain.agents.middleware import ModelCallLimitMiddleware
from langchain.agents.middleware import ToolCallLimitMiddleware




import asyncio
import os
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent


async def run_agent():
   client = MultiServerMCPClient(
       {
           "playwright": {
               "command": "npx",
               "args": [
                   "-y",
                   "@playwright/mcp@latest"
               ],
               "transport": "stdio"
           }
       }
   )


   tools = await client.get_tools()
   agent = create_agent(
       "openai:gpt-5.5",
       tools,
       middleware=[
               ModelCallLimitMiddleware(run_limit=15, exit_behavior="end"),
               ToolCallLimitMiddleware(tool_name="browser_navigate", run_limit=5, exit_behavior="end"),
               ToolCallLimitMiddleware(tool_name="browser_snapshot", run_limit=5, exit_behavior="end"),
               ToolCallLimitMiddleware(tool_name="browser_click", run_limit=5, exit_behavior="end"),
           ]
       )


   response = await agent.ainvoke({"messages": "Go to https://google.com, search for 'Model Context Protocol', and summarize the top result"})
   print(response["messages"][-1].content)


if __name__ == "__main__":
   asyncio.run(run_agent())
