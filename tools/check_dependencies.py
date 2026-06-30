from __future__ import annotations

from app.utils.dependency_check import check_dependencies, format_dependency_report


def main() -> int:
    statuses = check_dependencies()
    print(format_dependency_report(statuses), end="")
    missing_required = [item for item in statuses if item.required and not item.available]
    if missing_required:
        print("\nERROR: Brakuje wymaganych zaleznosci.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

