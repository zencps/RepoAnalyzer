"""Central Rich color theme for RepoAnalyzer."""

from rich.theme import Theme

REPO_ANALYZER_THEME: Theme = Theme(
    {
        "primary": "deep_sky_blue1",
        "metric": "bold deep_sky_blue1",
        "secondary": "grey74",
        "muted": "grey50",
        "accent": "light_steel_blue1",
        "success": "bold green",
        "warning": "bold dark_orange",
        "error": "bold bright_red",
        "border": "grey50",
        "table.header": "bold deep_sky_blue1",
        "table.border": "grey50",
    }
)
