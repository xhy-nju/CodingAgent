from __future__ import annotations

import tomllib
from pathlib import Path

from starlette.testclient import TestClient

from coding_agent.api import create_app


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_runtime_distribution_includes_pytest() -> None:
    with (ROOT / "pyproject.toml").open("rb") as project_file:
        data = tomllib.load(project_file)

    assert "pytest>=8.2.0" in data["project"]["dependencies"]


def test_distribution_files_define_safe_docker_runtime() -> None:
    dockerfile = read("Dockerfile")
    assert "CMD [\"uvicorn\", \"coding_agent.api:app\"" in dockerfile
    assert "COPY --from=frontend-build /app/frontend/dist ./frontend/dist" in dockerfile
    assert "COPY frontend/package-lock.json ./package-lock.json" in dockerfile
    assert "RUN npm ci" in dockerfile
    assert "USER codingagent" in dockerfile
    assert (ROOT / "frontend/package-lock.json").exists()
    assert "ADMIN_PASSWORD: ${ADMIN_PASSWORD:-change-this-before-deploying}" in read(
        "docker-compose.yml"
    )
    assert "CODING_AGENT_DATA_DIR: /data" in read("docker-compose.yml")
    assert "OPENAI_API_KEY=" in read(".env.example")
    assert "ENABLE_REAL_LLM=false" in read(".env.example")
    assert ".env" in read(".dockerignore")
    assert ".coding-agent-data/" in read(".dockerignore")


def test_ci_files_cover_backend_frontend_and_docker() -> None:
    github_ci = read(".github/workflows/ci.yml")
    gitlab_ci = read(".gitlab-ci.yml")

    assert "pytest -q" in github_ci
    assert "npm ci" in github_ci
    assert "npm test" in github_ci
    assert "npm run build" in github_ci
    assert "docker build -t coding-agent:ci ." in github_ci
    assert "unit-test:" in gitlab_ci
    assert "pytest -q" in gitlab_ci


def test_readme_documents_local_and_docker_demo_commands() -> None:
    readme = read("README.md")

    for command in [
        "python -m coding_agent demo bugfix",
        "python -m coding_agent demo dangerous-action",
        "uvicorn coding_agent.api:app --reload",
        "cp .env.example .env",
        "docker compose up --build",
        "docker compose logs -f coding-agent",
    ]:
        assert command in readme
    assert "阿里云" in readme


def test_api_serves_built_frontend_when_dist_exists(tmp_path: Path, monkeypatch) -> None:
    dist_dir = tmp_path / "frontend-dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<main>CodingAgent WebUI</main>", encoding="utf-8")
    monkeypatch.setenv("CODING_AGENT_FRONTEND_DIST", str(dist_dir))

    client = TestClient(create_app(data_dir=tmp_path / "data"))

    response = client.get("/")

    assert response.status_code == 200
    assert "CodingAgent WebUI" in response.text
