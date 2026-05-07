# RepoAnalyzer

Analyze GitHub repositories and local Git workspaces directly from your terminal —
with themed tables, sparklines, block bars, and exportable reports.

```text
╔═══════════════════════════════ v1.0.0 ═══════════════════════════════════╗
║   ____                  ___                __                            ║
║  / __ \___  ____  ____ /   |  ____  ____ _/ /_  _______  _____           ║
║ / /_/ / _ \/ __ \/ __ \ /| | / __ \/ __ `/ / / / /_  / / / / ___/        ║
║/ _, _/  __/ /_/ / /_/ / ___ |/ / / / /_/ / / /_/ / /_/ / /               ║
║/_/ |_|\___/ .___/\____/_/  |_/_/ /_/\__,_/_/\__, / /___/\___/_/          ║
║          /_/                               /____/                        ║
╚══════════════════════ GitHub & Git Analytics ════════════════════════════╝
```

## Features

- **Two data sources, one interface** — analyze a GitHub repository by URL or
  `owner/name` slug, or any local Git working copy on disk.
- **Repository stats** — stars, forks, issues, watchers, license, dates,
  commit and contributor totals.
- **Commit analytics** — totals, average per day, active days, most active
  month, average commit size (local), plus monthly activity sparklines.
- **Contributor rankings** — top authors with commit counts and share.
- **Language breakdown** — via the GitHub languages API, or locally by file
  extension, rendered as block bars (`Python [██████████░░] 73%`).
- **File analysis** — biggest files, type counts, and lines of code for local
  scans (noise directories like `.git` and `node_modules` are skipped).
- **Export** — full reports as `json`, `csv`, `md`, or styled `html`.
- **Resilient UX** — graceful error messages, rate-limit warnings, UTF-8-safe
  output on Windows.

## Installation

Requires Python 3.12+ and Git.

```bash
git clone <this-repo> repo-analyzer
cd repo-analyzer
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
repo-analyzer --help
```

Alternatively, run from the project root without installing:

```bash
pip install -r requirements.txt
python main.py --help
```

## Quick start

```bash
# Clone a repository with a live progress bar
repo-analyzer clone https://github.com/octocat/Spoon-Knife.git

# Repository snapshot (works for local paths too)
repo-analyzer stats octocat/Spoon-Knife
repo-analyzer stats ./repos/Spoon-Knife

# Commit analytics with a 6-month activity sparkline
repo-analyzer commits octocat/Spoon-Knife --months 6

# Top contributors
repo-analyzer contributors octocat/Spoon-Knife --top 5

# Language breakdown (GitHub API or local extension scan)
repo-analyzer languages ./src

# Export a report — format inferred from the extension
repo-analyzer export report.html octocat/Spoon-Knife
repo-analyzer export report.json ./repos/Spoon-Knife
repo-analyzer export report.csv octocat/Spoon-Knife --format csv
```

## Configuration

A GitHub token raises the API rate limit from 60 to 5,000 requests/hour.
Provide one in any of the following ways (highest priority first):

| Priority | Method | Example |
| --- | --- | --- |
| 1 | Environment variable | `GITHUB_TOKEN=ghp_xxx` |
| 2 | `.env` file (project or `~/.config/repo-analyzer/`) | `GITHUB_TOKEN=ghp_xxx` |
| 3 | `config.toml` | see below |

`config.toml` (project root or `~/.config/repo-analyzer/config.toml`):

```toml
[github]
token = "ghp_your_token_here"

[paths]
clone_base_dir = "~/repos"   # default: ./repos
```

Tokens are never printed; they appear masked in log output.

## Example output

`repo-analyzer stats` renders a snapshot panel, health score, detail grid,
and contributor table:

```text
╔════════════════════════════════ Repository Snapshot ════════════════════════════════╗
║ Stars 13,989  ·  Forks 158,834  ·  Issues 21,100  ·  Watchers 877  ·  Commits 3     ║
╚══════════════════════════ octocat/Spoon-Knife ═══════════════════════════╝
╔═════════════════════════════ Repository Health ═══════════════════════════╗
║ Grade C   Score 58/100                                                    ║
║                                                                           ║
║ Recency    ████████████████████░░░░  16/30                                 ║
║ Activity   ██████░░░░░░░░░░░░░░░░░░   6/25                                 ║
║ Community  ██████████░░░░░░░░░░░░░░   5/20                                 ║
║ Governance ████████████░░░░░░░░░░░░  12/15                                 ║
║ Engagement ██████████████████████    10/10                                 ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

`repo-analyzer commits` adds a monthly activity sparkline:

```text
Activity  ▁▁▁▁▂▃▅▇▆▄▂█   last 12 months
```

## Export formats

| Format | Contents |
| --- | --- |
| `json` | Full typed report (repository, commits, statistics, contributors, languages) |
| `csv` | Sections: REPOSITORY summary, COMMITS, CONTRIBUTORS, LANGUAGES |
| `md` | Readable Markdown report with snapshot table and language bars |
| `html` | Themed HTML rendering of the terminal output |

## Development

```bash
pip install -r requirements.txt
pytest
```

Set `REPO_ANALYZER_DEBUG=1` for debug logging.

## Project layout

```text
analyzer/    Business logic: github, git, commits, contributors,
             language, files, statistics
commands/    CLI layer (Typer): clone, stats, commits,
             contributors, languages, export
models/      Pydantic domain models
utils/       formatter (console/theme), tables, exporters,
             config, helpers, theme
tests/       pytest suite (offline; real temp Git fixtures)
main.py      Typer application wiring
```

## License

MIT
