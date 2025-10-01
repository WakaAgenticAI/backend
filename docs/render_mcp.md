Render MCP Server
Manage your Render resources from AI apps like Cursor and Claude Code.
Render's Model Context Protocol (MCP) server enables you to manage your Render infrastructure directly from compatible AI apps, such as Cursor and Claude Code:

Using natural language prompts, you can:

Spin up new services
Query your databases
Analyze metrics and logs
...and more! For inspiration, see some example prompts.

How it works
The Render MCP server is hosted at the following URL:

https://mcp.render.com/mcp
You can configure compatible AI apps (such as Cursor and Claude Code) to communicate with this server. When you provide a relevant prompt, your tool intelligently calls the MCP server to execute supported platform actions:

Diagram of using the hosted Render MCP server with Cursor

In the example diagram above:

A user prompts Cursor to "List my Render services".
Cursor intelligently detects that the Render MCP server supports actions relevant to the prompt.
Cursor directs the MCP server to execute the list_services "tool", which calls the Render API to fetch the corresponding data.
To explore the implementation of the MCP server itself, see the open-source project:

View source on GitHub

Setup
1. Create an API key
The MCP server uses an API key to authenticate with the Render platform. Create an API key from your Account Settings page:

Creating an API key in the Render Dashboard

Render API keys are broadly scoped. They grant access to all workspaces and services your account can access.

Before proceeding, make sure you're comfortable granting these permissions to your AI app. The Render MCP server currently supports only one potentially destructive operation: modifying an existing service's environment variables.

2. Configure your tool
Next, we'll configure your AI app to use Render's hosted MCP server. Most compatible apps define their MCP configuration in a JSON file (such as ~/.cursor/mcp.json for Cursor).

Select the tab for your app:

Cursor
Claude Code
Claude Desktop
Windsurf
Other tools
Windsurf setup
Add the following configuration to ~/.codeium/windsurf/mcp_config.json:

{
  "mcpServers": {
    "render": {
      "url": "https://mcp.render.com/mcp",
      "headers": {
        "Authorization": "Bearer <YOUR_API_KEY>"
      }
    }
  }
}
Replace <YOUR_API_KEY> with your API key.

For more details, see the Windsurf MCP documentation.

3. Set your workspace
To start using the Render MCP server, you first tell your AI app which Render workspace to operate in. This determines which resources the MCP server can access.

You can set your workspace with a prompt like Set my Render workspace to [WORKSPACE_NAME].

Selecting an active Render workspace in Cursor

If you don't set your workspace, your app usually directs you to specify one if you submit a prompt that uses the MCP server (such as List my Render services):

Selecting an active Render workspace in Cursor

With your workspace set, you're ready to start prompting! Get started with some example prompts.

Example prompts
Your AI app can use the Render MCP server to perform a wide variety of platform actions. Here are some basic example prompts to get you started:

Service creation
Create a new database named user-db with 5 GB storage
Deploy an example Flask web service on Render using https://github.com/render-examples/flask-hello-world
Data analysis
Using my Render database, tell me which items were the most frequently bought together
Query my read replica for daily signup counts for the last 30 days
Service metrics
What was the busiest traffic day for my service this month?
What did my service's autoscaling behavior look like yesterday?
Troubleshooting
Pull the most recent error-level logs for my API service
Why isn't my site at example.onrender.com working?
Supported actions
The Render MCP server provides a "tool" for each platform action listed below (organized by resource type). Your AI app (the "MCP host") can combine these tools however it needs to perform the tasks you describe.

For more details on all available tools, see the project README.

Resource Type	Supported Actions
Workspaces

List all workspaces you have access to
Set the current workspace
Fetch details of the currently selected workspace
Services

Create a new web service or static site
Other service types are not yet supported.
List all services in the current workspace
Retrieve details about a specific service
Update all environment variables for a service
Deploys

List the deploy history for a service
Get details about a specific deploy
Logs

List logs matching provided filters
List all values for a given log label
Metrics

Fetch performance metrics for services and datastores, including:
CPU / memory usage
Instance count
Datastore connection counts
Web service response counts, segmentable by status code
Web service response times (requires a Professional workspace or higher)
Render Postgres

Create a new database
List all databases in the current workspace
Get details about a specific database
Run a read-only SQL query against a specific database
Render Key Value

List all Key Value instances in your Render account
Get details about a specific Key Value instance
Create a new Key Value instance
Running locally
We strongly recommend using Render's hosted MCP server instead of running it locally.

The hosted MCP server automatically updates with new capabilities as they're added. Run locally only if required for your use case.

You can install and run the Render MCP server on your local machine as a Docker container, or by running the executable directly:

Docker image
Executable
Docker setup
This method requires docker.

With this configuration, your AI app pulls and runs the Render MCP server as a Docker container.

Add JSON with the format below to your tool's MCP configuration (substitute <YOUR_API_KEY> with your API key):

{
  "mcpServers": {
    "render": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "RENDER_API_KEY",
        "-v",
        "render-mcp-server-config:/config",
        "ghcr.io/render-oss/render-mcp-server"
      ],
      "env": {
        "RENDER_API_KEY": "<YOUR_API_KEY>"
      }
    }
  }
}
The mcpServers key above might differ for specific tools. For example, Zed uses context_servers and GitHub Copilot uses servers. Consult your tool's documentation for details.

Local installation
Follow these instructions only if you're running the MCP server locally and without Docker.

We strongly recommend instead using Render's hosted MCP server, because it automatically updates as new capabilities are added.

Limitations
The Render MCP server attempts to minimize exposing sensitive information (like connection strings) to your AI app's context. However, Render does not guarantee that sensitive information will not be exposed. Exercise caution when interacting with secrets in your AI app.

Note the following additional limitations:

The MCP server supports creation of the following resources:

Web services
Static sites
Render Postgres databases
Render Key Value instances
Other service types (private services, background workers, and cron jobs) are not yet supported.

The MCP server does not support creating free instances.

The MCP server does not support all configuration options when creating services.

For example, you cannot create image-backed services or set up IP allowlists. If there are options you'd like to see supported, please submit an issue on the MCP server's GitHub repository.
The MCP server does not support modifying or deleting existing Render resources, with one exception:

You can modify an existing service's environment variables.
To perform other modifications or deletions, use the Render Dashboard or REST API.
The MCP server does not support triggering deploys, modifying scaling settings, or other operational service controls.