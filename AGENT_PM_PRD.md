# Product Requirements Document (PRD)
# agentFlow - AI Agent Project Management System

**Version:** 1.0  
**Date:** 2025-12-29  
**Author:** fellowork  
**Status:** Ready for Implementation

---

## 🎯 Executive Summary

**agentFlow** is a lightweight, local-first project management system designed specifically for AI agent teams. It enables Product Owners and Developer Agents to collaboratively break down PRDs into Stories and Tasks, track progress, and coordinate work across multiple agents.

### Key Value Proposition
- **Structured Collaboration**: Clear hierarchy (PRD → Stories → Tasks)
- **Agent-Native**: Designed for AI agents, exposed via MCP
- **Local-First**: 100% local SQLite, no external dependencies
- **Workflow Management**: States, assignments, comments
- **Zero Boilerplate**: Run directly from git with `uvx`

---

## 🔍 Problem Statement

Current challenges for AI agent teams:
1. **No structured task breakdown** - PRDs remain monolithic
2. **Poor coordination** - Agents don't know what others are working on
3. **No state tracking** - Can't track progress across Stories/Tasks
4. **Generic memory insufficient** - Semantic search can't replace structured queries
5. **Manual tracking** - Humans must manually track agent work

---

## 👥 Target Users

### Primary Users (AI Agents)
- **Product Owner Agent**: Creates PRDs, breaks into Stories, reviews progress
- **Developer Agents**: Pick up Tasks, update status, add comments
- **QA Agent**: Reviews Tasks, adds test results
- **DevOps Agent**: Handles deployment Tasks

### Secondary Users (Humans)
- **Human PO**: May oversee or initialize PRDs
- **Developers**: Can view/interact with agent work

---

## ✨ Core Features

### 1. Hierarchical Structure
```
Project
└── PRD (Product Requirement Document)
    └── Story (User Story / Epic)
        └── Task (Concrete work item)
            └── Comment (Discussion thread)
```

### 2. Entity Types

#### **PRD**
- Title, Description
- Status: Draft → Active → Completed → Archived
- Created by (agent_id)
- Created/Updated timestamps
- Metadata (tags, priority)

#### **Story**
- Title, Description
- Belongs to PRD (parent)
- Status: Todo → In Progress → Review → Done → Archived
- Assigned to agent_id (optional)
- Story points / Estimate
- Acceptance criteria
- Created/Updated timestamps
- Metadata

#### **Task**
- Title, Description
- Belongs to Story (parent)
- Status: Todo → In Progress → Blocked → Review → Done → Archived
- Assigned to agent_id
- Depends on (other task IDs)
- Created/Updated timestamps
- Metadata

#### **Comment**
- Content
- Author (agent_id)
- Belongs to (PRD/Story/Task)
- Created timestamp
- Type: comment, question, decision, blocker

### 3. Workflow Management
- State transitions with validation
- Agent assignment and reassignment
- Dependency tracking (Task depends on Task)
- Progress calculation (% completion)

### 4. Query & Filter
- List by status
- List by assigned agent
- List by parent (all Stories in PRD, all Tasks in Story)
- Filter by metadata
- Get agent workload

---

## 🛠️ Technical Requirements

### Architecture
Following **memAlpha best practices**:

#### Technology Stack
- **Language**: Python 3.10+
- **Database**: SQLite (local, persistent)
- **Package Manager**: `uv` (fast, zero-config)
- **MCP Server**: Python `mcp` library, stdio transport
- **Data Validation**: Pydantic v2
- **Testing**: pytest, pytest-cov, pytest-bdd
- **Coverage Target**: 90%+ on core modules

#### Design Principles
1. **Local-First**: All data stored locally in SQLite
2. **Agent Isolation**: Each project isolated by project_id
3. **No External Dependencies**: Works completely offline
4. **Simple Deployment**: `uvx --from git+https://... agentflow`
5. **TDD Approach**: Tests written before implementation
6. **Minimal Dependencies**: Only essential packages

### Data Storage

**Location**: `~/.local/share/agentflow/`
```
~/.local/share/agentflow/
├── agentflow.db          # SQLite database
└── attachments/          # Optional: file attachments
```

**Database Schema**:

```sql
-- Projects (container for PRDs)
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

-- PRDs (Product Requirement Documents)
CREATE TABLE prds (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'draft',  -- draft, active, completed, archived
    created_by TEXT NOT NULL,     -- agent_id
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Stories (User Stories / Epics)
CREATE TABLE stories (
    id TEXT PRIMARY KEY,
    prd_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'todo',  -- todo, in_progress, review, done, archived
    assigned_to TEXT,            -- agent_id (optional)
    story_points INTEGER,
    acceptance_criteria TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON,
    FOREIGN KEY (prd_id) REFERENCES prds(id) ON DELETE CASCADE
);

-- Tasks (Concrete work items)
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    story_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'todo',  -- todo, in_progress, blocked, review, done, archived
    assigned_to TEXT NOT NULL,   -- agent_id (required)
    depends_on TEXT,             -- comma-separated task IDs or JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON,
    FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
);

-- Comments (Discussion threads)
CREATE TABLE comments (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,   -- prd, story, task
    entity_id TEXT NOT NULL,     -- ID of parent entity
    author TEXT NOT NULL,        -- agent_id
    content TEXT NOT NULL,
    comment_type TEXT DEFAULT 'comment',  -- comment, question, decision, blocker
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

-- Indexes for performance
CREATE INDEX idx_stories_prd_id ON stories(prd_id);
CREATE INDEX idx_stories_assigned_to ON stories(assigned_to);
CREATE INDEX idx_tasks_story_id ON tasks(story_id);
CREATE INDEX idx_tasks_assigned_to ON tasks(assigned_to);
CREATE INDEX idx_comments_entity ON comments(entity_type, entity_id);
```

---

## 🔧 MCP Tools Specification

### Project Management Tools

#### 1. `create_project`
```json
{
  "name": "create_project",
  "description": "Create a new project container",
  "parameters": {
    "name": "string (required)",
    "description": "string (optional)",
    "metadata": "object (optional)"
  },
  "returns": "Project object with ID"
}
```

#### 2. `list_projects`
```json
{
  "name": "list_projects",
  "description": "List all projects",
  "parameters": {
    "limit": "integer (default: 50)",
    "offset": "integer (default: 0)"
  },
  "returns": "List of Project objects"
}
```

#### 3. `get_project`
```json
{
  "name": "get_project",
  "description": "Get project by ID with summary statistics",
  "parameters": {
    "project_id": "string (required)"
  },
  "returns": "Project object with stats (PRD count, Story count, etc.)"
}
```

### PRD Tools

#### 4. `create_prd`
```json
{
  "name": "create_prd",
  "description": "Create a Product Requirement Document",
  "parameters": {
    "project_id": "string (required)",
    "agent_id": "string (required) - creator",
    "title": "string (required)",
    "description": "string (required)",
    "metadata": "object (optional - tags, priority, etc.)"
  },
  "returns": "PRD object with ID"
}
```

#### 5. `get_prd`
```json
{
  "name": "get_prd",
  "description": "Get PRD by ID with all Stories",
  "parameters": {
    "prd_id": "string (required)"
  },
  "returns": "PRD object with nested Stories"
}
```

#### 6. `update_prd`
```json
{
  "name": "update_prd",
  "description": "Update PRD title, description, status or metadata",
  "parameters": {
    "prd_id": "string (required)",
    "title": "string (optional)",
    "description": "string (optional)",
    "status": "string (optional - draft, active, completed, archived)",
    "metadata": "object (optional)"
  },
  "returns": "Updated PRD object"
}
```

#### 7. `list_prds`
```json
{
  "name": "list_prds",
  "description": "List PRDs in a project with optional filters",
  "parameters": {
    "project_id": "string (required)",
    "status": "string (optional - filter by status)",
    "created_by": "string (optional - filter by creator agent)",
    "limit": "integer (default: 50)",
    "offset": "integer (default: 0)"
  },
  "returns": "List of PRD objects with summary stats"
}
```

### Story Tools

#### 8. `create_story`
```json
{
  "name": "create_story",
  "description": "Create a User Story under a PRD",
  "parameters": {
    "prd_id": "string (required)",
    "agent_id": "string (required) - creator",
    "title": "string (required)",
    "description": "string (required)",
    "acceptance_criteria": "string (optional)",
    "story_points": "integer (optional)",
    "assigned_to": "string (optional - agent_id)",
    "metadata": "object (optional)"
  },
  "returns": "Story object with ID"
}
```

#### 9. `get_story`
```json
{
  "name": "get_story",
  "description": "Get Story by ID with all Tasks",
  "parameters": {
    "story_id": "string (required)"
  },
  "returns": "Story object with nested Tasks"
}
```

#### 10. `update_story`
```json
{
  "name": "update_story",
  "description": "Update Story fields",
  "parameters": {
    "story_id": "string (required)",
    "title": "string (optional)",
    "description": "string (optional)",
    "status": "string (optional - todo, in_progress, review, done, archived)",
    "assigned_to": "string (optional - agent_id)",
    "story_points": "integer (optional)",
    "acceptance_criteria": "string (optional)",
    "metadata": "object (optional)"
  },
  "returns": "Updated Story object"
}
```

#### 11. `list_stories`
```json
{
  "name": "list_stories",
  "description": "List Stories with optional filters",
  "parameters": {
    "prd_id": "string (optional - filter by PRD)",
    "status": "string (optional - filter by status)",
    "assigned_to": "string (optional - filter by assigned agent)",
    "limit": "integer (default: 50)",
    "offset": "integer (default: 0)"
  },
  "returns": "List of Story objects with Task counts"
}
```

### Task Tools

#### 12. `create_task`
```json
{
  "name": "create_task",
  "description": "Create a Task under a Story",
  "parameters": {
    "story_id": "string (required)",
    "agent_id": "string (required) - creator",
    "title": "string (required)",
    "description": "string (required)",
    "assigned_to": "string (required - agent_id who will work on it)",
    "depends_on": "array[string] (optional - task IDs)",
    "metadata": "object (optional)"
  },
  "returns": "Task object with ID"
}
```

#### 13. `get_task`
```json
{
  "name": "get_task",
  "description": "Get Task by ID with comments",
  "parameters": {
    "task_id": "string (required)"
  },
  "returns": "Task object with Comments"
}
```

#### 14. `update_task`
```json
{
  "name": "update_task",
  "description": "Update Task fields",
  "parameters": {
    "task_id": "string (required)",
    "title": "string (optional)",
    "description": "string (optional)",
    "status": "string (optional - todo, in_progress, blocked, review, done, archived)",
    "assigned_to": "string (optional - reassign to different agent)",
    "depends_on": "array[string] (optional)",
    "metadata": "object (optional)"
  },
  "returns": "Updated Task object"
}
```

#### 15. `list_tasks`
```json
{
  "name": "list_tasks",
  "description": "List Tasks with optional filters",
  "parameters": {
    "story_id": "string (optional - filter by Story)",
    "status": "string (optional - filter by status)",
    "assigned_to": "string (optional - filter by assigned agent)",
    "limit": "integer (default: 50)",
    "offset": "integer (default: 0)"
  },
  "returns": "List of Task objects"
}
```

#### 16. `get_agent_workload`
```json
{
  "name": "get_agent_workload",
  "description": "Get all Tasks assigned to a specific agent",
  "parameters": {
    "agent_id": "string (required)",
    "status": "string (optional - filter by status, e.g., 'in_progress')",
    "project_id": "string (optional - filter by project)"
  },
  "returns": "List of Tasks with Story/PRD context"
}
```

### Comment Tools

#### 17. `add_comment`
```json
{
  "name": "add_comment",
  "description": "Add a comment to PRD, Story, or Task",
  "parameters": {
    "entity_type": "string (required - prd, story, task)",
    "entity_id": "string (required - ID of the entity)",
    "agent_id": "string (required - comment author)",
    "content": "string (required)",
    "comment_type": "string (optional - comment, question, decision, blocker)",
    "metadata": "object (optional)"
  },
  "returns": "Comment object with ID"
}
```

#### 18. `get_comments`
```json
{
  "name": "get_comments",
  "description": "Get all comments for an entity",
  "parameters": {
    "entity_type": "string (required - prd, story, task)",
    "entity_id": "string (required)",
    "limit": "integer (default: 50)",
    "offset": "integer (default: 0)"
  },
  "returns": "List of Comment objects"
}
```

### Progress & Analytics Tools

#### 19. `get_project_progress`
```json
{
  "name": "get_project_progress",
  "description": "Get overall project progress statistics",
  "parameters": {
    "project_id": "string (required)"
  },
  "returns": {
    "total_prds": "integer",
    "total_stories": "integer",
    "total_tasks": "integer",
    "stories_by_status": "object {todo: X, in_progress: Y, ...}",
    "tasks_by_status": "object",
    "tasks_by_agent": "object {agent_id: count}",
    "completion_percentage": "float"
  }
}
```

#### 20. `get_story_progress`
```json
{
  "name": "get_story_progress",
  "description": "Get Story completion progress",
  "parameters": {
    "story_id": "string (required)"
  },
  "returns": {
    "story": "Story object",
    "total_tasks": "integer",
    "completed_tasks": "integer",
    "in_progress_tasks": "integer",
    "blocked_tasks": "integer",
    "completion_percentage": "float"
  }
}
```

---

## 📋 Use Cases & User Stories

### Use Case 1: PRD Creation & Breakdown
```
PO Agent:
1. create_project(name="E-commerce Platform")
2. create_prd(project_id=X, title="User Authentication", description="...")
3. create_story(prd_id=Y, title="Login with Email", description="...")
4. create_story(prd_id=Y, title="Social Login", description="...")
5. create_task(story_id=Z, title="Design API endpoints", assigned_to="backend-agent")
```

### Use Case 2: Developer Agent Picks Up Work
```
Backend Dev Agent:
1. get_agent_workload(agent_id="backend-agent", status="todo")
   # Returns: [Task: "Design API endpoints"]
2. update_task(task_id=T, status="in_progress")
3. add_comment(entity_type="task", entity_id=T, content="Started working on this")
4. [... works on task ...]
5. update_task(task_id=T, status="review")
6. add_comment(entity_type="task", entity_id=T, content="Ready for review, implemented JWT")
```

### Use Case 3: QA Agent Reviews
```
QA Agent:
1. list_tasks(status="review")
   # Returns: Tasks ready for review
2. get_task(task_id=T)
3. add_comment(entity_type="task", entity_id=T, comment_type="question", 
   content="What about token refresh?")
4. update_task(task_id=T, status="in_progress")  # Send back
```

### Use Case 4: Progress Tracking
```
PO Agent:
1. get_project_progress(project_id=X)
   # Returns: 65% complete, 12 tasks in progress, 3 blocked
2. list_tasks(status="blocked")
   # Returns: Blocked tasks to unblock
3. get_story_progress(story_id=Y)
   # Returns: 3/5 tasks done (60% complete)
```

---

## 🧪 Testing Requirements

### Test Strategy
Following **memAlpha TDD approach**:

1. **Unit Tests** (pytest)
   - Test all data models (Pydantic validation)
   - Test all database operations (CRUD)
   - Test state transitions
   - Test dependency validation
   - **Target**: 95%+ coverage

2. **Integration Tests**
   - Test MCP tool calls end-to-end
   - Test complete workflows (PRD → Story → Task → Done)
   - Test multi-agent scenarios

3. **BDD Tests** (pytest-bdd)
   - Feature: PO creates PRD and breaks into Stories
   - Feature: Dev agents pick up and complete Tasks
   - Feature: Progress tracking across agents
   - Feature: Comment-based collaboration

### Test Data
Use realistic AI agent team scenarios:
- Backend Developer Agent
- Frontend Developer Agent
- QA Agent
- DevOps Agent
- Product Owner Agent

---

## 🚀 Deployment & Distribution

### Installation
Following **memAlpha deployment model**:

```bash
# Run directly from GitHub (no checkout needed)
uvx --from git+https://github.com/fellowork/agentFlow agentflow
```

### MCP Configuration
```json
{
  "mcpServers": {
    "agentFlow": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/fellowork/agentFlow", "agentflow"]
    }
  }
}
```

### Environment Variables (All Optional)
```bash
# Data directory (default: ~/.local/share/agentflow)
AGENTFLOW_DATA_DIR=/custom/path

# Database path (default: $DATA_DIR/agentflow.db)
AGENTFLOW_DB_PATH=/custom/db.sqlite
```

---

## 📦 Project Structure

```
agentflow/
├── src/
│   ├── __init__.py
│   ├── models.py              # Pydantic models
│   ├── database.py            # SQLite operations
│   ├── store.py               # High-level CRUD operations
│   ├── workflows.py           # State transitions, validations
│   └── server.py              # MCP server entry point
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_database.py
│   ├── test_store.py
│   ├── test_workflows.py
│   ├── test_server.py
│   └── features/              # BDD scenarios
│       ├── prd_management.feature
│       ├── story_breakdown.feature
│       ├── task_lifecycle.feature
│       └── agent_collaboration.feature
├── .github/
│   └── workflows/
│       ├── test-and-merge.yml # CI/CD (same as memAlpha)
│       └── test-main.yml
├── .gitignore
├── .python-version            # 3.10
├── pyproject.toml
├── README.md
├── LICENSE                    # MIT
└── llm.txt                    # AI-optimized docs
```

---

## 🔒 Non-Functional Requirements

### Performance
- Create/update operations: < 50ms
- List queries: < 100ms for 1000 items
- Database size: ~1MB per 1000 tasks
- Startup time: < 500ms

### Scalability
- Support 100+ PRDs per project
- Support 1000+ Stories per PRD
- Support 10,000+ Tasks per project
- Support 10+ concurrent agent operations

### Reliability
- SQLite ACID transactions
- Automatic schema migrations
- Data integrity constraints (foreign keys)
- Graceful error handling

### Security
- Local-only (no network exposure)
- File system permissions
- No authentication needed (local use)

---

## 📝 Data Models (Pydantic)

### Core Models

```python
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4
from pydantic import BaseModel, Field

class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PRDCreate(BaseModel):
    project_id: str
    agent_id: str  # creator
    title: str = Field(..., min_length=1)
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PRD(PRDCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    status: str = "draft"  # draft, active, completed, archived
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class StoryCreate(BaseModel):
    prd_id: str
    agent_id: str  # creator
    title: str = Field(..., min_length=1)
    description: str
    acceptance_criteria: Optional[str] = None
    story_points: Optional[int] = None
    assigned_to: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Story(StoryCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    status: str = "todo"  # todo, in_progress, review, done, archived
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class TaskCreate(BaseModel):
    story_id: str
    agent_id: str  # creator
    title: str = Field(..., min_length=1)
    description: str
    assigned_to: str  # required for tasks
    depends_on: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Task(TaskCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    status: str = "todo"  # todo, in_progress, blocked, review, done, archived
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CommentCreate(BaseModel):
    entity_type: str  # prd, story, task
    entity_id: str
    agent_id: str  # author
    content: str = Field(..., min_length=1)
    comment_type: str = "comment"  # comment, question, decision, blocker
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Comment(CommentCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## 🎨 State Transition Rules

### PRD States
```
draft → active → completed → archived
  ↓       ↓         ↓
  └───────┴─────────┴─→ archived (anytime)
```

### Story States
```
todo → in_progress → review → done → archived
  ↓         ↓          ↓       ↓
  └─────────┴──────────┴───────┴─→ archived (anytime)
```

### Task States
```
todo → in_progress → review → done → archived
  ↓         ↓                   ↓
  └─────────┴───────→ blocked ──┴─→ archived (anytime)
```

**Validation Rules:**
- Task can only be "done" if not blocking other tasks
- Story automatically moves to "review" when all Tasks are "done"
- PRD automatically moves to "completed" when all Stories are "done"

---

## 🔄 Migration from memAlpha Patterns

### What to Keep from memAlpha
✅ Local-first architecture  
✅ `uv` for package management  
✅ MCP server with stdio transport  
✅ Pydantic for data validation  
✅ TDD approach with pytest  
✅ 90%+ test coverage  
✅ Direct git deployment  
✅ Minimal dependencies  
✅ MIT License  

### What to Change
❌ Replace ChromaDB → SQLite (structured data)  
❌ Remove embedding provider (not needed)  
❌ Add relational schema (hierarchy)  
❌ Add workflow state machines  
❌ More complex query patterns  

---

## 📚 Dependencies

**pyproject.toml** (minimal, like memAlpha):

```toml
[project]
name = "agentflow"
version = "0.1.0"
description = "AI Agent Project Management System"
authors = [{ name = "fellowork GmbH" }]
requires-python = ">=3.10"
dependencies = [
    "mcp>=1.0.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-bdd>=6.0.0",
]

[project.scripts]
agentflow = "src.server:run"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --strict-markers"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src"]
```

---

## 🎯 Success Metrics

### Development Phase
- ✅ All 20 MCP tools implemented
- ✅ 90%+ test coverage
- ✅ All BDD scenarios passing
- ✅ Zero external dependencies (except dev)
- ✅ < 500ms startup time

### Usage Phase
- ✅ Agents can create/manage PRDs without human intervention
- ✅ Task assignment and tracking works smoothly
- ✅ Progress tracking provides accurate insights
- ✅ Comment-based collaboration enables coordination
- ✅ State transitions prevent invalid workflows

---

## 🚧 Out of Scope (v1.0)

- ❌ Web UI / Dashboard (CLI/MCP only)
- ❌ Real-time notifications
- ❌ File attachments
- ❌ Time tracking
- ❌ Burndown charts
- ❌ Git integration
- ❌ Multi-user auth (local-only)
- ❌ Cloud sync
- ❌ API webhooks

These may be added in future versions based on user feedback.

---

## 📖 Documentation Requirements

### README.md
- Quick start guide
- MCP configuration
- All tool descriptions
- Usage examples
- Workflow examples (PO → Dev → QA)

### llm.txt
- AI-optimized documentation
- Tool reference
- Example queries
- Best practices

### .github/SETUP.md
- CI/CD setup (same as memAlpha)
- Development workflow
- Testing instructions

---

## 🏁 Implementation Plan

### Phase 1: Foundation (Week 1)
1. Setup project structure
2. Implement data models (Pydantic)
3. Setup SQLite database
4. Write unit tests for models
5. Implement CRUD operations

### Phase 2: Core Features (Week 2)
6. Implement all MCP tools
7. Add state transitions & validations
8. Write integration tests
9. Implement progress calculations

### Phase 3: Testing & Polish (Week 3)
10. Write BDD scenarios
11. Achieve 90%+ coverage
12. Add documentation
13. Setup CI/CD (GitHub Actions)
14. Create llm.txt

### Phase 4: Release (Week 4)
15. Final testing
16. Performance optimization
17. Documentation review
18. v1.0 release

---

## ✅ Definition of Done

This PRD is considered complete when:
- ✅ All 20 MCP tools are implemented and tested
- ✅ Test coverage is 90%+
- ✅ All BDD scenarios pass
- ✅ Documentation is complete (README, llm.txt, SETUP)
- ✅ CI/CD pipeline is working
- ✅ Can be run directly from git via `uvx`
- ✅ Example workflows are documented
- ✅ Ready for real AI agent teams to use

---

## 📞 Contact & Support

- **Repository**: https://github.com/fellowork/agentFlow (TBD)
- **Issues**: https://github.com/fellowork/agentFlow/issues
- **Related**: memAlpha (https://github.com/fellowork/memAlpha)

---

**Ready to build!** 🚀

This PRD is ready to be used as input for a new Cursor project. Copy this entire document and use it to guide implementation.

