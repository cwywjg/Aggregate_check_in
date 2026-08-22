"""Build a deployment archive without copying local runtime credentials/databases."""
from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_DIR = (PROJECT_ROOT / "deploy").resolve()
STAGE = (DEPLOY_DIR / ".package-stage").resolve()
DESTINATION = (PROJECT_ROOT / "deploy.zip").resolve()


def assert_in_project(path: Path) -> None:
    if PROJECT_ROOT.resolve() not in path.resolve().parents:
        raise RuntimeError(f"package path escaped project root: {path}")


def ignore_python_cache(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name == "__pycache__" or name.endswith(".pyc")}


def build() -> str:
    assert_in_project(STAGE)
    if STAGE.exists():
        shutil.rmtree(STAGE)

    try:
        server_stage = STAGE / "server"
        yyb_stage = STAGE / "yyb_go"
        server_stage.mkdir(parents=True)
        yyb_stage.mkdir(parents=True)

        excluded = {"data.db", "tjcu.db", "scratch_dump_q.py"}
        for source in (PROJECT_ROOT / "server").iterdir():
            if source.is_file() and source.name not in excluded and source.suffix != ".pyc":
                shutil.copy2(source, server_stage / source.name)
        for name in ("models", "routers", "services", "tests"):
            shutil.copytree(
                PROJECT_ROOT / "server" / name,
                server_stage / name,
                ignore=ignore_python_cache,
            )

        shutil.copy2(PROJECT_ROOT / "yyb_go" / "yyb-go", yyb_stage / "yyb-go")
        resource_stage = yyb_stage / "resource"
        resource_stage.mkdir()
        for name in ("static", "templates"):
            shutil.copytree(
                PROJECT_ROOT / "yyb_go" / "resource" / name,
                resource_stage / name,
            )
        shutil.copy2(DEPLOY_DIR / "setup_server.sh", STAGE / "setup_server.sh")

        required = [
            server_stage / "main.py",
            server_stage / "services" / "teachermate.py",
            server_stage / "services" / "keepalive.py",
            server_stage / "routers" / "quiz.py",
            yyb_stage / "yyb-go",
            STAGE / "setup_server.sh",
        ]
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise RuntimeError(f"missing staged files: {missing}")

        if DESTINATION.exists():
            DESTINATION.unlink()
        with zipfile.ZipFile(DESTINATION, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(STAGE.rglob("*"), key=lambda item: item.as_posix()):
                if path.is_file():
                    archive.write(path, path.relative_to(STAGE).as_posix())

        digest = hashlib.sha256(DESTINATION.read_bytes()).hexdigest().upper()
        print(f"Created: {DESTINATION}")
        print(f"SHA256: {digest}")
        return digest
    finally:
        if STAGE.exists():
            assert_in_project(STAGE)
            shutil.rmtree(STAGE)


if __name__ == "__main__":
    build()
