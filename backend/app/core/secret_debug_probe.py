import json
import subprocess
import time
from pathlib import Path

LOG_PATH = Path("/home/aminu-iliyasu/Documents/Real-Time-Cloud-Cost-Optimization-Engine/.cursor/debug-2f3eb8.log")
SESSION_ID = "2f3eb8"
RUN_ID = "pre-fix-secret-scan"


def _log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    payload = {
        "sessionId": SESSION_ID,
        "runId": RUN_ID,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")


def _run(cmd: str) -> str:
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
    return (proc.stdout or "") + (proc.stderr or "")


def main() -> None:
    tracked_files = _run("git ls-files")
    history = _run("git log --name-only --pretty=format:'COMMIT %h %s'")
    compose = Path("docker-compose.yml").read_text(encoding="utf-8") if Path("docker-compose.yml").exists() else ""
    alembic_ini = Path("backend/alembic.ini").read_text(encoding="utf-8") if Path("backend/alembic.ini").exists() else ""

    # region agent log
    _log(
        "H1",
        "backend/app/core/secret_debug_probe.py:34",
        "Check if .env is tracked now",
        {"env_tracked": ".env" in tracked_files.splitlines()},
    )
    # endregion

    # region agent log
    _log(
        "H2",
        "backend/app/core/secret_debug_probe.py:44",
        "Check if .env appeared in commit history",
        {"env_in_history": ".env" in history},
    )
    # endregion

    # region agent log
    _log(
        "H3",
        "backend/app/core/secret_debug_probe.py:54",
        "Check docker-compose hardcoded password token",
        {"compose_has_postgres_password": "POSTGRES_PASSWORD" in compose, "compose_has_literal_postgres_password": "POSTGRES_PASSWORD: postgres" in compose},
    )
    # endregion

    # region agent log
    _log(
        "H4",
        "backend/app/core/secret_debug_probe.py:64",
        "Check alembic URL for embedded credentials",
        {"alembic_has_embedded_password": "postgresql+psycopg2://postgres:postgres@" in alembic_ini},
    )
    # endregion

    # region agent log
    _log(
        "H6",
        "backend/app/core/secret_debug_probe.py:73",
        "Check alembic URL for any literal postgres password pattern",
        {
            "alembic_has_literal_postgres_password": "postgres://postgres:postgres@" in alembic_ini
            or "postgresql://postgres:postgres@" in alembic_ini
            or "postgresql+psycopg2://postgres:postgres@" in alembic_ini
        },
    )
    # endregion

    # region agent log
    _log(
        "H5",
        "backend/app/core/secret_debug_probe.py:86",
        "Persist recent commit subjects for incident correlation",
        {"recent_commits": _run("git log --oneline -n 5").splitlines()},
    )
    # endregion

    # region agent log
    historical_scan = _run(
        "git log -p --all -- docker-compose.yml backend/alembic.ini | "
        "python -c \"import sys; d=sys.stdin.read(); print('FOUND' if ('POSTGRES_PASSWORD: postgres' in d or 'postgresql://postgres:postgres@' in d or 'postgresql+psycopg2://postgres:postgres@' in d) else 'NOT_FOUND')\""
    ).strip()
    _log(
        "H7",
        "backend/app/core/secret_debug_probe.py:98",
        "Check whether historical commits still contain literal password patterns",
        {"historical_secret_pattern_present": historical_scan == "FOUND", "historical_scan_result": historical_scan},
    )
    # endregion


if __name__ == "__main__":
    main()
