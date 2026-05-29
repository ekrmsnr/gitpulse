import argparse
import sys
from pathlib import Path
from .analyzer import RepoAnalyzer
from .display import Display


def main():
    parser = argparse.ArgumentParser(
        prog="gitpulse",
        description="Analyze a Git repository and generate a visual report.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to the Git repository (default: current directory)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of top files/contributors to show (default: 10)",
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        metavar="DATE",
        help="Analyze commits since this date, e.g. '2024-01-01'",
    )
    parser.add_argument(
        "--html",
        type=str,
        default=None,
        metavar="FILE",
        help="Export an HTML report to FILE, e.g. report.html",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )

    args = parser.parse_args()
    repo_path = Path(args.path).resolve()

    if not repo_path.exists():
        print(f"Error: path '{repo_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    display = Display(no_color=args.no_color)

    try:
        display.print_header(str(repo_path))
        analyzer = RepoAnalyzer(repo_path, since=args.since)

        with display.progress("Loading commits..."):
            analyzer.load()

        display.print_summary(analyzer.summary())
        display.print_contributors(analyzer.top_contributors(args.top))
        display.print_file_churn(analyzer.top_churned_files(args.top))
        display.print_commit_activity(analyzer.commit_activity())
        display.print_languages(analyzer.language_breakdown())

        if args.html:
            from .html_report import build_html
            html_path = Path(args.html)
            build_html(html_path, analyzer)
            display.print_success(f"HTML report saved → {html_path}")

    except ValueError as exc:
        display.print_error(str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
