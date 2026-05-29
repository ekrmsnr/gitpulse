from __future__ import annotations

import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from git import Repo, InvalidGitRepositoryError


# Extensions → language name mapping
LANG_MAP: dict[str, str] = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".jsx": "JavaScript", ".tsx": "TypeScript", ".c": "C", ".h": "C",
    ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++",
    ".java": "Java", ".go": "Go", ".rs": "Rust", ".rb": "Ruby",
    ".php": "PHP", ".cs": "C#", ".swift": "Swift", ".kt": "Kotlin",
    ".r": "R", ".m": "MATLAB", ".jl": "Julia", ".scala": "Scala",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
    ".html": "HTML", ".htm": "HTML", ".css": "CSS", ".scss": "CSS",
    ".json": "JSON", ".yaml": "YAML", ".yml": "YAML", ".toml": "TOML",
    ".md": "Markdown", ".ipynb": "Jupyter Notebook",
    ".sql": "SQL", ".tf": "Terraform", ".dockerfile": "Docker",
}


class RepoAnalyzer:
    """Analyzes a Git repository and exposes statistics."""

    def __init__(self, path: Path, since: Optional[str] = None) -> None:
        try:
            self.repo = Repo(str(path), search_parent_directories=True)
        except InvalidGitRepositoryError:
            raise ValueError(f"'{path}' is not a Git repository.")

        self.path = Path(self.repo.working_dir)
        self.since: Optional[datetime] = None
        if since:
            try:
                self.since = datetime.fromisoformat(since).replace(tzinfo=timezone.utc)
            except ValueError:
                raise ValueError(f"Invalid date format '{since}'. Use ISO format, e.g. 2024-01-01")

        self._commits: list = []
        self._loaded = False

    # ------------------------------------------------------------------ #
    #  Loading                                                             #
    # ------------------------------------------------------------------ #

    def load(self) -> None:
        kwargs: dict = {"all": True}
        if self.since:
            kwargs["after"] = self.since.isoformat()
        try:
            self._commits = list(self.repo.iter_commits(**kwargs))
        except Exception:
            # Fallback to HEAD only
            self._commits = list(self.repo.iter_commits())
        self._loaded = True

    def _check_loaded(self) -> None:
        if not self._loaded:
            raise RuntimeError("Call load() before accessing statistics.")

    # ------------------------------------------------------------------ #
    #  Summary                                                             #
    # ------------------------------------------------------------------ #

    def summary(self) -> dict:
        self._check_loaded()
        commits = self._commits
        if not commits:
            return {"total_commits": 0, "repo_name": self.path.name}

        dates = [_commit_dt(c) for c in commits]
        first, last = min(dates), max(dates)
        authors = {c.author.email for c in commits}
        branches = [b.name for b in self.repo.branches]

        try:
            active_branch = self.repo.active_branch.name
        except TypeError:
            active_branch = "detached HEAD"

        return {
            "repo_name": self.path.name,
            "total_commits": len(commits),
            "unique_authors": len(authors),
            "branches": len(branches),
            "active_branch": active_branch,
            "first_commit": first,
            "last_commit": last,
            "age_days": (last - first).days,
        }

    # ------------------------------------------------------------------ #
    #  Contributors                                                        #
    # ------------------------------------------------------------------ #

    def top_contributors(self, n: int = 10) -> list[dict]:
        self._check_loaded()
        counter: Counter = Counter()
        additions: Counter = Counter()
        deletions: Counter = Counter()

        for commit in self._commits:
            key = f"{commit.author.name} <{commit.author.email}>"
            counter[key] += 1
            try:
                stats = commit.stats.total
                additions[key] += stats.get("insertions", 0)
                deletions[key] += stats.get("deletions", 0)
            except Exception:
                pass

        return [
            {
                "author": author,
                "commits": count,
                "additions": additions[author],
                "deletions": deletions[author],
            }
            for author, count in counter.most_common(n)
        ]

    # ------------------------------------------------------------------ #
    #  File churn                                                          #
    # ------------------------------------------------------------------ #

    def top_churned_files(self, n: int = 10) -> list[dict]:
        self._check_loaded()
        churn: Counter = Counter()

        for commit in self._commits:
            try:
                for path, stats in commit.stats.files.items():
                    churn[path] += stats.get("lines", 0)
            except Exception:
                pass

        return [
            {"file": file, "lines_changed": count}
            for file, count in churn.most_common(n)
        ]

    # ------------------------------------------------------------------ #
    #  Commit activity (by weekday & by hour)                             #
    # ------------------------------------------------------------------ #

    def commit_activity(self) -> dict:
        self._check_loaded()
        weekday_counts: Counter = Counter()
        hour_counts: Counter = Counter()
        monthly_counts: Counter = Counter()

        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        for commit in self._commits:
            dt = _commit_dt(commit)
            weekday_counts[day_names[dt.weekday()]] += 1
            hour_counts[dt.hour] += 1
            monthly_counts[dt.strftime("%Y-%m")] += 1

        return {
            "by_weekday": {d: weekday_counts[d] for d in day_names},
            "by_hour": dict(sorted(hour_counts.items())),
            "by_month": dict(sorted(monthly_counts.items())),
        }

    # ------------------------------------------------------------------ #
    #  Language breakdown (from current working tree)                     #
    # ------------------------------------------------------------------ #

    def language_breakdown(self) -> list[dict]:
        lang_counter: Counter = Counter()

        for root, dirs, files in os.walk(self.path):
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".") and d not in ("node_modules", "__pycache__", ".git", "venv", ".venv", "dist", "build")
            ]
            for fname in files:
                ext = Path(fname).suffix.lower()
                lang = LANG_MAP.get(ext)
                if lang:
                    lang_counter[lang] += 1

        total = sum(lang_counter.values()) or 1
        return [
            {"language": lang, "files": count, "pct": round(count / total * 100, 1)}
            for lang, count in lang_counter.most_common()
        ]


# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #

def _commit_dt(commit) -> datetime:
    """Return a timezone-aware datetime from a GitPython commit."""
    ts = commit.committed_date
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt
