"""MCP server for noGojira."""

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .models import (
    CommentCreate,
    EntityType,
    PRDCreate,
    PRDUpdate,
    ProjectCreate,
    StoryCreate,
    StoryUpdate,
    TaskCreate,
    TaskUpdate,
)
from .store import Store

# Initialize store
store = Store()


# Tool definitions
TOOLS: list[Tool] = [
    # Project Management Tools
    Tool(
        name="create_project",
        description="Create a new project container",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Project name (required)"},
                "description": {"type": "string", "description": "Project description (optional)"},
                "metadata": {"type": "object", "description": "Additional metadata (optional)"},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="list_projects",
        description="List all projects",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Maximum number of results (default: 50)"},
                "offset": {"type": "integer", "description": "Pagination offset (default: 0)"},
            },
        },
    ),
    Tool(
        name="get_project",
        description="Get project by ID with summary statistics",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project ID (required)"},
            },
            "required": ["project_id"],
        },
    ),
    # PRD Tools
    Tool(
        name="create_prd",
        description="Create a Product Requirement Document",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Parent project ID (required)"},
                "agent_id": {"type": "string", "description": "Creator agent ID (required)"},
                "title": {"type": "string", "description": "PRD title (required)"},
                "description": {"type": "string", "description": "PRD description (required)"},
                "metadata": {"type": "object", "description": "Additional metadata (optional)"},
            },
            "required": ["project_id", "agent_id", "title", "description"],
        },
    ),
    Tool(
        name="get_prd",
        description="Get PRD by ID with all Stories",
        inputSchema={
            "type": "object",
            "properties": {
                "prd_id": {"type": "string", "description": "PRD ID (required)"},
            },
            "required": ["prd_id"],
        },
    ),
    Tool(
        name="update_prd",
        description="Update PRD title, description, status or metadata",
        inputSchema={
            "type": "object",
            "properties": {
                "prd_id": {"type": "string", "description": "PRD ID (required)"},
                "title": {"type": "string", "description": "Updated title (optional)"},
                "description": {"type": "string", "description": "Updated description (optional)"},
                "status": {
                    "type": "string",
                    "description": "Status: draft, active, completed, archived (optional)",
                    "enum": ["draft", "active", "completed", "archived"],
                },
                "metadata": {"type": "object", "description": "Updated metadata (optional)"},
            },
            "required": ["prd_id"],
        },
    ),
    Tool(
        name="list_prds",
        description="List PRDs in a project with optional filters",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Filter by project ID (optional)"},
                "status": {"type": "string", "description": "Filter by status (optional)"},
                "created_by": {"type": "string", "description": "Filter by creator agent (optional)"},
                "limit": {"type": "integer", "description": "Maximum results (default: 50)"},
                "offset": {"type": "integer", "description": "Pagination offset (default: 0)"},
            },
        },
    ),
    # Story Tools
    Tool(
        name="create_story",
        description="Create a User Story under a PRD",
        inputSchema={
            "type": "object",
            "properties": {
                "prd_id": {"type": "string", "description": "Parent PRD ID (required)"},
                "agent_id": {"type": "string", "description": "Creator agent ID (required)"},
                "title": {"type": "string", "description": "Story title (required)"},
                "description": {"type": "string", "description": "Story description (required)"},
                "acceptance_criteria": {"type": "string", "description": "Acceptance criteria (optional)"},
                "story_points": {"type": "integer", "description": "Story points estimate (optional)"},
                "assigned_to": {"type": "string", "description": "Assigned agent ID (optional)"},
                "metadata": {"type": "object", "description": "Additional metadata (optional)"},
            },
            "required": ["prd_id", "agent_id", "title", "description"],
        },
    ),
    Tool(
        name="get_story",
        description="Get Story by ID with all Tasks",
        inputSchema={
            "type": "object",
            "properties": {
                "story_id": {"type": "string", "description": "Story ID (required)"},
            },
            "required": ["story_id"],
        },
    ),
    Tool(
        name="update_story",
        description="Update Story fields",
        inputSchema={
            "type": "object",
            "properties": {
                "story_id": {"type": "string", "description": "Story ID (required)"},
                "title": {"type": "string", "description": "Updated title (optional)"},
                "description": {"type": "string", "description": "Updated description (optional)"},
                "status": {
                    "type": "string",
                    "description": "Status: todo, in_progress, review, done, archived (optional)",
                    "enum": ["todo", "in_progress", "review", "done", "archived"],
                },
                "assigned_to": {"type": "string", "description": "Reassign to agent (optional)"},
                "story_points": {"type": "integer", "description": "Updated story points (optional)"},
                "acceptance_criteria": {"type": "string", "description": "Updated criteria (optional)"},
                "metadata": {"type": "object", "description": "Updated metadata (optional)"},
            },
            "required": ["story_id"],
        },
    ),
    Tool(
        name="list_stories",
        description="List Stories with optional filters",
        inputSchema={
            "type": "object",
            "properties": {
                "prd_id": {"type": "string", "description": "Filter by PRD ID (optional)"},
                "status": {"type": "string", "description": "Filter by status (optional)"},
                "assigned_to": {"type": "string", "description": "Filter by assigned agent (optional)"},
                "limit": {"type": "integer", "description": "Maximum results (default: 50)"},
                "offset": {"type": "integer", "description": "Pagination offset (default: 0)"},
            },
        },
    ),
    # Task Tools
    Tool(
        name="create_task",
        description="Create a Task under a Story",
        inputSchema={
            "type": "object",
            "properties": {
                "story_id": {"type": "string", "description": "Parent story ID (required)"},
                "agent_id": {"type": "string", "description": "Creator agent ID (required)"},
                "title": {"type": "string", "description": "Task title (required)"},
                "description": {"type": "string", "description": "Task description (required)"},
                "assigned_to": {"type": "string", "description": "Assigned agent ID (required)"},
                "depends_on": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Task IDs this depends on (optional)",
                },
                "metadata": {"type": "object", "description": "Additional metadata (optional)"},
            },
            "required": ["story_id", "agent_id", "title", "description", "assigned_to"],
        },
    ),
    Tool(
        name="get_task",
        description="Get Task by ID with comments",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID (required)"},
            },
            "required": ["task_id"],
        },
    ),
    Tool(
        name="update_task",
        description="Update Task fields",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID (required)"},
                "title": {"type": "string", "description": "Updated title (optional)"},
                "description": {"type": "string", "description": "Updated description (optional)"},
                "status": {
                    "type": "string",
                    "description": "Status: todo, in_progress, blocked, review, done, archived (optional)",
                    "enum": ["todo", "in_progress", "blocked", "review", "done", "archived"],
                },
                "assigned_to": {"type": "string", "description": "Reassign to agent (optional)"},
                "depends_on": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Updated dependencies (optional)",
                },
                "metadata": {"type": "object", "description": "Updated metadata (optional)"},
            },
            "required": ["task_id"],
        },
    ),
    Tool(
        name="list_tasks",
        description="List Tasks with optional filters",
        inputSchema={
            "type": "object",
            "properties": {
                "story_id": {"type": "string", "description": "Filter by story ID (optional)"},
                "status": {"type": "string", "description": "Filter by status (optional)"},
                "assigned_to": {"type": "string", "description": "Filter by assigned agent (optional)"},
                "limit": {"type": "integer", "description": "Maximum results (default: 50)"},
                "offset": {"type": "integer", "description": "Pagination offset (default: 0)"},
            },
        },
    ),
    Tool(
        name="get_agent_workload",
        description="Get all Tasks assigned to a specific agent",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID (required)"},
                "status": {"type": "string", "description": "Filter by status (optional)"},
                "project_id": {"type": "string", "description": "Filter by project (optional)"},
            },
            "required": ["agent_id"],
        },
    ),
    # Comment Tools
    Tool(
        name="add_comment",
        description="Add a comment to PRD, Story, or Task",
        inputSchema={
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "description": "Entity type: prd, story, task (required)",
                    "enum": ["prd", "story", "task"],
                },
                "entity_id": {"type": "string", "description": "Entity ID (required)"},
                "agent_id": {"type": "string", "description": "Comment author agent ID (required)"},
                "content": {"type": "string", "description": "Comment content (required)"},
                "comment_type": {
                    "type": "string",
                    "description": "Type: comment, question, decision, blocker (optional)",
                    "enum": ["comment", "question", "decision", "blocker"],
                },
                "metadata": {"type": "object", "description": "Additional metadata (optional)"},
            },
            "required": ["entity_type", "entity_id", "agent_id", "content"],
        },
    ),
    Tool(
        name="get_comments",
        description="Get all comments for an entity",
        inputSchema={
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "description": "Entity type: prd, story, task (required)",
                    "enum": ["prd", "story", "task"],
                },
                "entity_id": {"type": "string", "description": "Entity ID (required)"},
                "limit": {"type": "integer", "description": "Maximum results (default: 50)"},
                "offset": {"type": "integer", "description": "Pagination offset (default: 0)"},
            },
            "required": ["entity_type", "entity_id"],
        },
    ),
    # Progress & Analytics Tools
    Tool(
        name="get_project_progress",
        description="Get overall project progress statistics",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project ID (required)"},
            },
            "required": ["project_id"],
        },
    ),
    Tool(
        name="get_story_progress",
        description="Get Story completion progress",
        inputSchema={
            "type": "object",
            "properties": {
                "story_id": {"type": "string", "description": "Story ID (required)"},
            },
            "required": ["story_id"],
        },
    ),
]


def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("nogojira")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List all available tools."""
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle tool calls."""
        try:
            result = None

            # Project Tools
            if name == "create_project":
                project_create = ProjectCreate(**arguments)
                project = store.create_project(project_create)
                result = project.model_dump_json(indent=2)

            elif name == "list_projects":
                limit = arguments.get("limit", 50)
                offset = arguments.get("offset", 0)
                projects = store.list_projects(limit=limit, offset=offset)
                result = f"Found {len(projects)} projects:\n\n"
                for p in projects:
                    result += f"- {p.name} (ID: {p.id})\n"
                    if p.description:
                        result += f"  Description: {p.description}\n"

            elif name == "get_project":
                project = store.get_project(arguments["project_id"])
                if not project:
                    result = f"Project {arguments['project_id']} not found"
                else:
                    result = project.model_dump_json(indent=2)

            # PRD Tools
            elif name == "create_prd":
                prd_create = PRDCreate(**arguments)
                prd = store.create_prd(prd_create)
                result = prd.model_dump_json(indent=2)

            elif name == "get_prd":
                prd = store.get_prd_with_stats(arguments["prd_id"])
                if not prd:
                    result = f"PRD {arguments['prd_id']} not found"
                else:
                    result = prd.model_dump_json(indent=2)

            elif name == "update_prd":
                prd_id = arguments.pop("prd_id")
                prd_update = PRDUpdate(**arguments)
                prd = store.update_prd(prd_id, prd_update)
                if not prd:
                    result = f"PRD {prd_id} not found"
                else:
                    result = prd.model_dump_json(indent=2)

            elif name == "list_prds":
                prds = store.list_prds(**arguments)
                result = f"Found {len(prds)} PRDs:\n\n"
                for prd in prds:
                    result += f"- {prd.title} (ID: {prd.id}, Status: {prd.status.value})\n"
                    result += f"  Created by: {prd.created_by}\n"

            # Story Tools
            elif name == "create_story":
                story_create = StoryCreate(**arguments)
                story = store.create_story(story_create)
                result = story.model_dump_json(indent=2)

            elif name == "get_story":
                story = store.get_story_with_stats(arguments["story_id"])
                if not story:
                    result = f"Story {arguments['story_id']} not found"
                else:
                    result = story.model_dump_json(indent=2)

            elif name == "update_story":
                story_id = arguments.pop("story_id")
                story_update = StoryUpdate(**arguments)
                story = store.update_story(story_id, story_update)
                if not story:
                    result = f"Story {story_id} not found"
                else:
                    result = story.model_dump_json(indent=2)

            elif name == "list_stories":
                stories = store.list_stories(**arguments)
                result = f"Found {len(stories)} stories:\n\n"
                for story in stories:
                    result += f"- {story.title} (ID: {story.id}, Status: {story.status.value})\n"
                    if story.assigned_to:
                        result += f"  Assigned to: {story.assigned_to}\n"
                    if story.story_points:
                        result += f"  Story points: {story.story_points}\n"

            # Task Tools
            elif name == "create_task":
                task_create = TaskCreate(**arguments)
                task = store.create_task(task_create)
                result = task.model_dump_json(indent=2)

            elif name == "get_task":
                task = store.get_task(arguments["task_id"])
                if not task:
                    result = f"Task {arguments['task_id']} not found"
                else:
                    result = task.model_dump_json(indent=2)

            elif name == "update_task":
                task_id = arguments.pop("task_id")
                task_update = TaskUpdate(**arguments)
                task = store.update_task(task_id, task_update)
                if not task:
                    result = f"Task {task_id} not found"
                else:
                    result = task.model_dump_json(indent=2)

            elif name == "list_tasks":
                tasks = store.list_tasks(**arguments)
                result = f"Found {len(tasks)} tasks:\n\n"
                for task in tasks:
                    result += f"- {task.title} (ID: {task.id}, Status: {task.status.value})\n"
                    result += f"  Assigned to: {task.assigned_to}\n"
                    if task.depends_on:
                        result += f"  Depends on: {', '.join(task.depends_on)}\n"

            elif name == "get_agent_workload":
                tasks = store.get_agent_workload(**arguments)
                result = f"Agent {arguments['agent_id']} has {len(tasks)} tasks:\n\n"
                for task in tasks:
                    result += f"- {task.title} (Status: {task.status.value})\n"
                    result += f"  Story: {task.story_title}\n"
                    result += f"  PRD: {task.prd_title}\n"
                    result += f"  Project: {task.project_id}\n\n"

            # Comment Tools
            elif name == "add_comment":
                comment_create = CommentCreate(**arguments)
                comment = store.add_comment(comment_create)
                result = comment.model_dump_json(indent=2)

            elif name == "get_comments":
                entity_type = EntityType(arguments["entity_type"])
                entity_id = arguments["entity_id"]
                limit = arguments.get("limit", 50)
                offset = arguments.get("offset", 0)
                comments = store.get_comments(entity_type, entity_id, limit=limit, offset=offset)
                result = f"Found {len(comments)} comments:\n\n"
                for comment in comments:
                    result += f"- {comment.author} ({comment.comment_type.value}): {comment.content}\n"
                    result += f"  Created: {comment.created_at}\n\n"

            # Progress Tools
            elif name == "get_project_progress":
                progress = store.get_project_progress(arguments["project_id"])
                if not progress:
                    result = f"Project {arguments['project_id']} not found"
                else:
                    result = progress.model_dump_json(indent=2)

            elif name == "get_story_progress":
                progress = store.get_story_progress(arguments["story_id"])
                if not progress:
                    result = f"Story {arguments['story_id']} not found"
                else:
                    result = progress.model_dump_json(indent=2)

            else:
                result = f"Unknown tool: {name}"

            return [TextContent(type="text", text=result)]

        except Exception as e:
            error_msg = f"Error executing {name}: {str(e)}"
            return [TextContent(type="text", text=error_msg)]

    return server


async def main():
    """Run the MCP server."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def run():
    """Entry point for the server."""
    asyncio.run(main())


if __name__ == "__main__":
    run()

