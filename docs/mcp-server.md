# Aider MCP Server

Aider can run as a Model Context Protocol (MCP) server, allowing MCP hosts like Cline or Claude Desktop to access your codebase through Aider.

## What is the Model Context Protocol?

The Model Context Protocol (MCP) is a protocol that allows AI assistants to access and modify files in your codebase. It provides a standardized way for AI tools to interact with your local development environment.

## Installation

To use Aider as an MCP server, you need to install Aider with the MCP dependencies:

```bash
pip install "aider-chat[mcp]"
```

This will install the required dependencies for the MCP server, including FastAPI and Uvicorn.

## Running the MCP Server

To run Aider as an MCP server, use the `--mcp-server` flag:

```bash
# Change directory into your codebase
cd /to/your/project

# Run Aider as an MCP server
aider --mcp-server --mcp-host 0.0.0.0 --mcp-port 12000
```

### Command-line Options

- `--mcp-server`: Run Aider as an MCP server instead of interactive mode
- `--mcp-host`: Host address for the MCP server (default: 0.0.0.0)
- `--mcp-port`: Port for the MCP server (default: 12000)

You can also use other Aider options like `--model`, `--api-key`, etc. to configure the server.

## Connecting to the MCP Server

Once the MCP server is running, you can connect to it from an MCP host like Cline or Claude Desktop. The exact steps depend on the MCP host you're using.

### Example: Connecting from Cline

In Cline, you can connect to the MCP server by setting the MCP server URL in the settings:

1. Open Cline
2. Go to Settings
3. Set the MCP server URL to `http://localhost:12000/mcp`
4. Start a new conversation

### Example: Connecting from Claude Desktop

In Claude Desktop, you can connect to the MCP server by setting the MCP server URL in the settings:

1. Open Claude Desktop
2. Go to Settings
3. Set the MCP server URL to `http://localhost:12000/mcp`
4. Start a new conversation

## MCP Server API

The MCP server implements the following JSON-RPC methods:

### getContext

Retrieves the content of one or more files.

**Request:**

```json
{
  "jsonrpc": "2.0",
  "method": "getContext",
  "params": {
    "file_paths": ["/path/to/file1.py", "/path/to/file2.py"]
  },
  "id": 1
}
```

**Response:**

```json
{
  "jsonrpc": "2.0",
  "result": {
    "files": {
      "/path/to/file1.py": "def hello():\n    print('Hello, world!')\n",
      "/path/to/file2.py": "def goodbye():\n    print('Goodbye, world!')\n"
    }
  },
  "id": 1
}
```

### applyChanges

Applies changes to a file.

**Request:**

```json
{
  "jsonrpc": "2.0",
  "method": "applyChanges",
  "params": {
    "file_path": "/path/to/file1.py",
    "content": "def hello():\n    print('Hello, Aider!')\n"
  },
  "id": 2
}
```

**Response:**

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "message": "Changes applied and committed to /path/to/file1.py"
  },
  "id": 2
}
```

## Troubleshooting

If you encounter issues with the MCP server, check the following:

- Make sure you have installed Aider with the MCP dependencies: `pip install "aider-chat[mcp]"`
- Check that the port you're using is not already in use by another application
- Ensure that your MCP host is configured to connect to the correct URL
- Check the Aider logs for any error messages

## Limitations

- The MCP server currently only supports the `getContext` and `applyChanges` methods
- The server does not support authentication, so it should only be used on trusted networks
- The server does not support HTTPS, so it should not be used over the internet