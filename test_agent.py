import asyncio
import logging
import os
from typing import Optional
from dotenv import load_dotenv
from agents import Agent, OpenAIChatCompletionsModel, Runner
from agents.mcp import MCPServerStreamableHttp
from openai import AsyncAzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider, InteractiveBrowserCredential
import aiohttp
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("openai.agents").setLevel(logging.ERROR)
logging.getLogger("azure").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

class MyTestAgent:
    
    def __init__(
        self,
        azure_endpoint: str,
        api_version: str,
        deployment_name: str,
        mcp_server_url: Optional[str]
    ):
        self.azure_endpoint = azure_endpoint
        self.api_version = api_version
        self.deployment_name = deployment_name
        self.mcp_server_url = mcp_server_url
        self.agent = None
        self.azure_client = None
        self.mcp_server = None
        
    async def initialize(self):
        # Create Azure OpenAI client based on authentication method
        logger.info("Using Azure AD authentication for OpenAI client")
        # Get the same credential used for MWC token
        token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
        
        self.azure_client = AsyncAzureOpenAI(
            azure_endpoint=self.azure_endpoint,
            azure_ad_token_provider=token_provider,
            api_version=self.api_version
        )
        
        # Create MCP server with Bearer token authentication
        headers = {}
        access_token = await self.generate_mcp_access_token()
        headers["Authorization"] = f"Bearer {access_token}"
        
        self.mcp_server = MCPServerStreamableHttp(
            params={
                "url": self.mcp_server_url,
                "headers": headers
            },
            client_session_timeout_seconds=30  # Increase timeout to 30 seconds
        )
        
        try:
            # Connect to the MCP server
            logger.info("connect to MCP server...")
            await self.mcp_server.connect()
            logger.info("Successfully connected to MCP server")
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            logger.error(f"MCP Server URL: {self.mcp_server_url}")
            raise ValueError("failed to connect to MCP server")
        
        self.agent = Agent(
                name="GraphQL MCP test agent",
                instructions = "Use the tools to answer the questions. Maintain context from previous messages in the conversation.",
                model = OpenAIChatCompletionsModel(
                    model = self.deployment_name,
                    openai_client = self.azure_client,
                ),
                mcp_servers=[self.mcp_server]
            )
        
            
    async def generate_mcp_access_token(self):
        private_authority = os.getenv('PRIVATE_AUTHORITY')
        scp = os.getenv('SCOPE')
        if private_authority:
            app = InteractiveBrowserCredential(authority=private_authority)
        else:
            app = DefaultAzureCredential()

        bearer_token = app.get_token(scp).token
        return bearer_token
    
    
    async def chat(self, user_message: str, system_message: Optional[str] = None) -> str:
        """Have a conversation with the Azure OpenAI model"""
        try:
            # Prepare messages
            messages = []
            
            if system_message:
                messages.append({"role": "system", "content": system_message})
            
            messages.append({"role": "user", "content": user_message})
            
            # Use the openai-agents Agent to handle the conversation
            # The Agent automatically handles MCP tool discovery and execution
            response = await Runner.run(
                starting_agent=self.agent,
                input=messages
            )
            
            return response.final_output
            
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return f"Error: {str(e)}"
    
    async def close(self):
        """Clean up resources"""
        logger.info("Cleaning up resources...")
        
        # Close the agent first
        if self.agent and hasattr(self.agent, 'close'):
            try:
                await self.agent.close()
                logger.info("Agent closed successfully")
            except Exception as e:
                logger.warning(f"Error closing agent: {e}")
        
        # Close Azure OpenAI client
        if self.azure_client:
            try:
                await self.azure_client.close()
                logger.info("Azure OpenAI client closed successfully")
            except Exception as e:
                logger.warning(f"Error closing Azure OpenAI client: {e}")
        
        # Small delay to allow tasks to complete
        await asyncio.sleep(0.1)
    

async def main():
    """Example usage of the MyTestAgent with MCP integration"""
    # Load environment variables from .env file
    load_dotenv()
    
    agent = None
    try:
        # Validate required environment variables
        if not os.getenv('MCP_SERVER_URL'):
            logger.error("MCP_SERVER_URL environment variable is required")
            return
        
        if not os.getenv('AZURE_ENDPOINT') or not os.getenv('DEPLOYMENT_NAME'):
            logger.error("Azure OpenAI configuration variables are required: AZURE_ENDPOINT, DEPLOYMENT_NAME")
            return
        
        # Create and initialize the agent
        agent = MyTestAgent(
            azure_endpoint=os.getenv('AZURE_ENDPOINT'),
            api_version=os.getenv('API_VERSION', '2024-02-15-preview'),
            deployment_name=os.getenv('DEPLOYMENT_NAME'),
            mcp_server_url=os.getenv('MCP_SERVER_URL'),
        )
        
        logger.info(f"Using MCP Server URL: {os.getenv('MCP_SERVER_URL')}")
        
        await agent.initialize()
        
        # System message to set context
        system_message = """You are a helpful AI assistant with access to various tools through an MCP server. 
        Use the available tools when they can help answer the user's questions or complete their tasks."""
        
        while True:
            user_input = input("\nYou: ")
            if user_input.lower() in ['quit', 'exit', 'bye']:
                logger.info("Goodbye!")
                break
            
            if user_input.strip():
                response = await agent.chat(user_input, system_message)
                logger.info(f"Assistant: {response}")

    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        # Clean up the agent
        if agent:
            try:
                await agent.close()
            except Exception:
                pass  # Suppress cleanup errors


if __name__ == "__main__":
    try:
        # Suppress all asyncio related warnings and errors during shutdown
        import warnings
        warnings.filterwarnings("ignore", category=RuntimeWarning, module="asyncio")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        # Only log actual application errors, not shutdown issues
        if not isinstance(e, (asyncio.CancelledError, RuntimeError)):
            logger.error(f"Unexpected error: {e}")