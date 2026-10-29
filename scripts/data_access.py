"""List challenge data or fetch one public bucket file into ignored local storage."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path, PurePosixPath


REPO = Path(__file__).resolve().parents[1]
DEFAULT_LOCAL = REPO / "data" / "raw" / "working_data"
BUCKET_ROOT = os.environ.get("CHALLENGE_BUCKET_ROOT", "datasets_challenge/working_data").strip("/")


def relative_path(value: str) -> PurePosixPath:
    if chr(92) in value:
        raise ValueError("Use bucket-relative paths with forward slashes")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError("Path must stay within working_data")
    return path


def local_root() -> Path:
    return Path(os.environ.get("CHALLENGE_DATA_ROOT", DEFAULT_LOCAL)).expanduser().resolve()


def cloud_fs():
    try:
        import gcsfs
    except ImportError as exc:
        raise SystemExit("Install requirements.txt to list or fetch the cloud data") from exc
    return gcsfs.GCSFileSystem(token="anon")


def list_data(source: str, path_value: str) -> None:
    part = relative_path(path_value) if path_value else None
    if source == "local":
        root = local_root()
        folder = root.joinpath(*part.parts) if part else root
        if not folder.is_dir():
            raise SystemExit(f"Local folder missing: {folder}")
        for child in sorted(folder.iterdir()):
            print(f"{child.name}/" if child.is_dir() else child.name)
        return
    fs = cloud_fs()
    folder = BUCKET_ROOT + (f"/{part}" if part else "")
    for item in sorted(fs.ls(folder, detail=False)):
        if item.rstrip("/") == folder:
            continue
        print(item.rsplit("/", 1)[-1])


def fetch_file(path_value: str) -> None:
    part = relative_path(path_value)
    destination = DEFAULT_LOCAL.joinpath(*part.parts)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise SystemExit(f"Already exists; leaving it intact: {destination}")
    fs = cloud_fs()
    remote = f"{BUCKET_ROOT}/{part}"
    if fs.isdir(remote):
        raise SystemExit("Choose one file, not a folder")
    temporary = destination.with_name(destination.name + ".part")
    if temporary.exists():
        raise SystemExit(f"Remove or inspect the interrupted download first: {temporary}")
    try:
        with fs.open(remote, "rb") as source, temporary.open("xb") as target:
            shutil.copyfileobj(source, target, length=8 * 1024 * 1024)
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    print(f"Saved {destination} ({destination.stat().st_size:,} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list", help="List a source folder")
    listing.add_argument("--source", choices=("cloud", "local"), default="cloud")
    listing.add_argument("--path", default="", help="Folder relative to working_data")
    fetching = sub.add_parser("fetch", help="Download one exact cloud file")
    fetching.add_argument("path", help="File path relative to working_data")
    args = parser.parse_args()
    if args.command == "list":
        list_data(args.source, args.path)
    else:
        fetch_file(args.path)


if __name__ == "__main__":
    main()
