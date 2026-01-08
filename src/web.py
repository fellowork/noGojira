"""Reflex Web UI for noGojira - Modern dashboard."""

import reflex as rx

from .events import get_event_queue
from .store import Store

# Initialize
store = Store()
events = get_event_queue()


class State(rx.State):
    """The app state."""

    # Current page
    current_page: str = "projects"
    
    # Stats
    total_projects: int = 0
    total_prds: int = 0
    total_stories: int = 0
    total_tasks: int = 0
    
    # Projects data
    projects: list[dict] = []
    
    # Recent activity
    recent_events: list[dict] = []

    def on_load(self):
        """Load initial data."""
        self.refresh_all()

    def refresh_all(self):
        """Refresh all dashboard data."""
        self.refresh_stats()
        self.refresh_projects()
        self.refresh_activity()

    def refresh_stats(self):
        """Refresh dashboard statistics."""
        projects = store.list_projects(limit=1000)
        self.total_projects = len(projects)

        prd_count = 0
        story_count = 0
        task_count = 0

        for project in projects:
            prds = store.list_prds(project_id=project.id, limit=1000)
            prd_count += len(prds)

            for prd in prds:
                stories = store.list_stories(prd_id=prd.id, limit=1000)
                story_count += len(stories)

                for story in stories:
                    tasks = store.list_tasks(story_id=story.id, limit=1000)
                    task_count += len(tasks)

        self.total_prds = prd_count
        self.total_stories = story_count
        self.total_tasks = task_count

    def refresh_projects(self):
        """Refresh projects list."""
        projects = store.list_projects(limit=100)
        self.projects = [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description or "No description",
                "created_at": p.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for p in projects
        ]

    def refresh_activity(self):
        """Refresh activity stream."""
        recent = events.get_recent(limit=20)
        self.recent_events = [
            {
                "id": e.id,
                "display": e.to_display_string(),
                "timestamp": e.timestamp.strftime("%H:%M:%S"),
                "agent": e.agent_id,
                "type": e.event_type.value,
            }
            for e in recent
        ]

    def set_page(self, page: str):
        """Change current page."""
        self.current_page = page


def navbar() -> rx.Component:
    """Top navigation bar."""
    return rx.box(
        rx.flex(
            # Left side: Logo & Brand
            rx.hstack(
                rx.heading(
                    "NoGojira",
                    size="6",
                    weight="bold",
                    color=rx.color("grass", 11),
                ),
                rx.text(
                    "AI Builds. No Tickets",
                    size="2",
                    color=rx.color("gray", 11),
                    weight="medium",
                    margin_left="12px",
                ),
                spacing="0",
                align="center",
            ),
            # Center: Navigation
            rx.hstack(
                rx.button(
                    "Projekte",
                    on_click=lambda: State.set_page("projects"),
                    variant=rx.cond(State.current_page == "projects", "soft", "ghost"),
                    color_scheme=rx.cond(State.current_page == "projects", "grass", "gray"),
                ),
                rx.button(
                    "Agent Monitor",
                    on_click=lambda: State.set_page("agents"),
                    variant=rx.cond(State.current_page == "agents", "soft", "ghost"),
                    color_scheme=rx.cond(State.current_page == "agents", "grass", "gray"),
                ),
                rx.button(
                    "Statistics",
                    on_click=lambda: State.set_page("statistics"),
                    variant=rx.cond(State.current_page == "statistics", "soft", "ghost"),
                    color_scheme=rx.cond(State.current_page == "statistics", "grass", "gray"),
                ),
                spacing="4",
                align="center",
                margin_left="48px",
            ),
            rx.spacer(),
            # Right side: Status indicator
            rx.badge(
                "Live",
                color_scheme="green",
                variant="soft",
            ),
            direction="row",
            justify="start",
            align="center",
            width="100%",
            padding_x="24px",
            padding_y="16px",
        ),
        width="100%",
        border_bottom=f"1px solid {rx.color('gray', 6)}",
        background=rx.color("gray", 2),
    )


def empty_projects() -> rx.Component:
    """Empty state for projects page."""
    return rx.center(
        rx.vstack(
            rx.icon(
                "folder_x",
                size=64,
                color=rx.color("gray", 8),
                stroke_width=1.5,
            ),
            rx.heading(
                "Noch keine Projekte",
                size="7",
                weight="bold",
                text_align="center",
                margin_top="20px",
            ),
            rx.text(
                "Verbinde einen AI-Agenten über MCP, um dein erstes Projekt zu starten.",
                size="3",
                color=rx.color("gray", 10),
                text_align="center",
                max_width="500px",
                line_height="1.6",
            ),
            rx.card(
                rx.vstack(
                    rx.text(
                        "Beispiel MCP Konfiguration:",
                        size="2",
                        weight="bold",
                        color=rx.color("gray", 11),
                        margin_bottom="12px",
                    ),
                    rx.box(
                        rx.code(
                            "uvx --from git+https://github.com/fellowork/noGojira nogojira",
                            font_size="14px",
                            color=rx.color("grass", 11),
                        ),
                        padding="16px",
                        border_radius="8px",
                        background=rx.color("gray", 3),
                        border=f"1px solid {rx.color('gray', 6)}",
                        width="100%",
                    ),
                    spacing="2",
                    align="stretch",
                    width="100%",
                ),
                width="100%",
                max_width="600px",
                padding="20px",
            ),
            spacing="5",
            align="center",
            max_width="700px",
        ),
        height="calc(100vh - 120px)",
        width="100%",
    )


def project_card(project: dict) -> rx.Component:
    """Single project card."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("folder", size=24, color=rx.color("grass", 9)),
                rx.heading(
                    project["name"],
                    size="4",
                    weight="bold",
                ),
                rx.spacer(),
                rx.badge("Active", color_scheme="green", variant="soft"),
                width="100%",
                align="center",
            ),
            rx.text(
                project["description"],
                size="2",
                color=rx.color("gray", 10),
            ),
            rx.divider(),
            rx.hstack(
                rx.text(
                    f"Erstellt: {project['created_at']}",
                    size="1",
                    color=rx.color("gray", 9),
                ),
                rx.spacer(),
                rx.button(
                    "Details",
                    size="1",
                    variant="soft",
                    color_scheme="grass",
                ),
                width="100%",
                align="center",
            ),
            spacing="3",
            align="start",
            width="100%",
        ),
        width="100%",
        style={
            ":hover": {
                "border_color": rx.color("grass", 8),
                "transform": "translateY(-2px)",
                "transition": "all 0.2s ease",
            },
        },
    )


def projects_grid() -> rx.Component:
    """Grid of project cards."""
    return rx.box(
        rx.cond(
            State.projects.length() > 0,
            rx.vstack(
                rx.flex(
                    rx.heading("Projekte", size="6", weight="bold"),
                    rx.spacer(),
                    rx.button(
                        rx.icon("refresh_cw", size=16),
                        "Aktualisieren",
                        on_click=State.refresh_all,
                        size="2",
                        variant="soft",
                        color_scheme="grass",
                    ),
                    direction="row",
                    justify="between",
                    align="center",
                    width="100%",
                    margin_bottom="20px",
                ),
                rx.grid(
                    rx.foreach(
                        State.projects,
                        project_card,
                    ),
                    columns="3",
                    spacing="4",
                    width="100%",
                ),
                spacing="0",
                width="100%",
                padding="24px",
            ),
            empty_projects(),
        ),
        width="100%",
        height="100%",
    )


def agent_monitor_page() -> rx.Component:
    """Agent monitor page."""
    return rx.center(
        rx.vstack(
            rx.icon("bot", size=64, color=rx.color("grass", 9), stroke_width=1.5),
            rx.heading("Agent Monitor", size="7", weight="bold", margin_top="20px"),
            rx.text(
                "Agent Activity wird hier angezeigt",
                size="3",
                color=rx.color("gray", 10),
                text_align="center",
            ),
            spacing="5",
            align="center",
        ),
        height="calc(100vh - 120px)",
        width="100%",
    )


def statistics_page() -> rx.Component:
    """Statistics page."""
    return rx.box(
        rx.vstack(
            rx.heading("Statistics", size="6", weight="bold", margin_bottom="20px"),
            rx.grid(
                rx.card(
                    rx.vstack(
                        rx.icon("folder", size=40, color=rx.color("blue", 9), stroke_width=1.5),
                        rx.heading(State.total_projects.to_string(), size="8", weight="bold", margin_top="12px"),
                        rx.text("Projects", size="2", color=rx.color("gray", 10)),
                        spacing="2",
                        align="center",
                        padding="20px",
                    ),
                    width="100%",
                ),
                rx.card(
                    rx.vstack(
                        rx.icon("file_text", size=40, color=rx.color("purple", 9), stroke_width=1.5),
                        rx.heading(State.total_prds.to_string(), size="8", weight="bold", margin_top="12px"),
                        rx.text("PRDs", size="2", color=rx.color("gray", 10)),
                        spacing="2",
                        align="center",
                        padding="20px",
                    ),
                    width="100%",
                ),
                rx.card(
                    rx.vstack(
                        rx.icon("book_open", size=40, color=rx.color("grass", 9), stroke_width=1.5),
                        rx.heading(State.total_stories.to_string(), size="8", weight="bold", margin_top="12px"),
                        rx.text("Stories", size="2", color=rx.color("gray", 10)),
                        spacing="2",
                        align="center",
                        padding="20px",
                    ),
                    width="100%",
                ),
                rx.card(
                    rx.vstack(
                        rx.icon("check_check", size=40, color=rx.color("orange", 9), stroke_width=1.5),
                        rx.heading(State.total_tasks.to_string(), size="8", weight="bold", margin_top="12px"),
                        rx.text("Tasks", size="2", color=rx.color("gray", 10)),
                        spacing="2",
                        align="center",
                        padding="20px",
                    ),
                    width="100%",
                ),
                columns="4",
                spacing="4",
                width="100%",
            ),
            spacing="0",
            width="100%",
        ),
        padding="24px",
        width="100%",
    )


def content_area() -> rx.Component:
    """Main content area with page routing."""
    return rx.box(
        rx.match(
            State.current_page,
            ("projects", projects_grid()),
            ("agents", agent_monitor_page()),
            ("statistics", statistics_page()),
            projects_grid(),  # default
        ),
        width="100%",
        flex="1",
        overflow="auto",
    )


def index() -> rx.Component:
    """The main page."""
    return rx.vstack(
        navbar(),
        content_area(),
        spacing="0",
        width="100%",
        height="100vh",
        on_mount=State.on_load,
    )


# Create the app
app = rx.App(
    theme=rx.theme(
        appearance="dark",
        accent_color="grass",
        gray_color="slate",
        radius="large",
    ),
)

app.add_page(
    index,
    title="noGojira - AI Builds. No Tickets",
    description="AI Agent Project Management System",
)
