# Azure OpenAI Agent with MCP Server Integration

This project provides an Azure OpenAI agent that can connect to a remote Fabric GraphQL MCP server to access additional tools and capabilities using Azure AD authentication.

## Features

- **Azure OpenAI Integration**: Uses Azure OpenAI GPT models for conversation with Azure AD authentication
- **MCP Server Support**: Connects to remote MCP servers to access tools with Bearer token authentication
- **Function Calling**: Automatically calls MCP tools when needed
- **Async Architecture**: Built with async/await for better performance
- **Azure AD Authentication**: Secure authentication using Azure credentials
- **Error Handling**: Robust error handling and logging
- **Streaming Support**: Support for streaming responses

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example configuration:
```bash
copy .env.example .env
```

Edit `.env` with your actual values:

Sample:
```bash
# Azure OpenAI Configuration
AZURE_ENDPOINT=https://your-azure-openai-resource.openai.azure.com/
API_VERSION=2024-12-01-preview
DEPLOYMENT_NAME=your-gpt-deployment-name

# MCP Server Configuration
MCP_SERVER_URL=https://your-mcp-server-url

SCOPE=https://analysis.windows-int.net/powerbi/api/user_impersonation
```

### 3. Azure OpenAI Setup

1. Create an Azure OpenAI resource in the Azure Portal
2. Deploy a GPT model (e.g., GPT-4)
3. Get your endpoint URL
4. Note your deployment name
5. Ensure your Azure identity has access to the OpenAI resource

## Usage

### Running the Test Agent

```bash
python test_agent.py
```

