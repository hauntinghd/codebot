import zipfile
from pathlib import Path

def zip_project(project_dir: Path) -> Path:
    zip_path = project_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in project_dir.rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(project_dir))
    return zip_path
