import re
import subprocess
import tempfile
from pathlib import Path

_PAGE_NUM_RE = re.compile(r"page-(\d+)\.png$")


def rasterize_pdf(
    pdf_path: Path, start_page: int, end_page: int, dpi: int = 300, out_dir: Path | None = None
) -> list[tuple[int, Path]]:
    """Render pdf pages [start_page, end_page] (1-indexed, inclusive) to PNGs.
    Returns (page_number, path) tuples sorted by page number."""
    out_dir = out_dir or Path(tempfile.mkdtemp(prefix="quizdr_raster_"))
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = out_dir / "page"
    subprocess.run(
        [
            "pdftoppm",
            "-f", str(start_page),
            "-l", str(end_page),
            "-r", str(dpi),
            "-png",
            str(pdf_path),
            str(prefix),
        ],
        check=True,
    )
    results = []
    for path in out_dir.glob("page-*.png"):
        m = _PAGE_NUM_RE.search(path.name)
        if m:
            results.append((int(m.group(1)), path))
    return sorted(results)
