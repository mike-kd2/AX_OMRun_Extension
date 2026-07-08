"""Auffinden von TestObject/.env/.rtl innerhalb einer Config-Wurzel.

Config-Wurzel = eine OMrun-Suite (enthaelt Environment/ und darunter die
Objekt-Ordner mit .tob + RunTimeList/)."""

from __future__ import annotations

from pathlib import Path

from .errors import ConfigNotFoundError


def _environment_dir(config_root: Path) -> Path:
    # Environment/ liegt direkt in der Suite; robust auch tiefer suchen.
    direct = config_root / "Environment"
    if direct.is_dir():
        return direct
    for cand in config_root.rglob("Environment"):
        if cand.is_dir():
            return cand
    raise ConfigNotFoundError(f"kein Environment/-Ordner unter {config_root}")


def find_tob(config_root: Path, name_or_path: str) -> Path:
    p = Path(name_or_path)
    if p.is_file():
        return p
    candidates = list(config_root.rglob("*.tob"))
    name = Path(name_or_path).name
    stem = name[:-4] if name.lower().endswith(".tob") else name

    def matches(tob: Path) -> bool:
        s = tob.stem
        return (
            s == stem
            or s == f"Data_{stem}"
            or s == f"GUI_{stem}"
            or tob.parent.name == stem
        )

    hits = [t for t in candidates if matches(t)]
    if not hits:
        raise ConfigNotFoundError(
            f"kein TestObject '{name_or_path}' unter {config_root} gefunden"
        )
    if len(hits) > 1:
        rels = ", ".join(str(h.relative_to(config_root)) for h in hits)
        raise ConfigNotFoundError(
            f"TestObject '{name_or_path}' mehrdeutig: {rels}"
        )
    return hits[0]


def find_env(config_root: Path, name: str) -> Path:
    env_dir = _environment_dir(config_root)
    stem = name[:-4] if name.lower().endswith(".env") else name
    cand = env_dir / f"{stem}.env"
    if cand.is_file():
        return cand
    for f in env_dir.glob("*.env"):
        if f.stem.lower() == stem.lower():
            return f
    avail = ", ".join(sorted(f.stem for f in env_dir.glob("*.env")))
    raise ConfigNotFoundError(
        f"kein Environment '{name}' in {env_dir} (verfuegbar: {avail})"
    )


def find_global_env(config_root: Path) -> Path | None:
    env_dir = _environment_dir(config_root)
    cand = env_dir / "Global.env"
    return cand if cand.is_file() else None


def find_rtl(tob_path: Path, name: str) -> Path:
    rtl_dir = tob_path.parent / "RunTimeList"
    stem = name[:-4] if name.lower().endswith(".rtl") else name
    cand = rtl_dir / f"{stem}.rtl"
    if cand.is_file():
        return cand
    if rtl_dir.is_dir():
        for f in rtl_dir.glob("*.rtl"):
            if f.stem.lower() == stem.lower():
                return f
        avail = ", ".join(sorted(f.stem for f in rtl_dir.glob("*.rtl")))
        raise ConfigNotFoundError(
            f"keine RunTimeList '{name}' in {rtl_dir} (verfuegbar: {avail})"
        )
    raise ConfigNotFoundError(f"kein RunTimeList/-Ordner neben {tob_path.name}")


def list_objects(config_root: Path) -> list[Path]:
    return sorted(config_root.rglob("*.tob"))


def list_envs(config_root: Path) -> list[Path]:
    try:
        env_dir = _environment_dir(config_root)
    except ConfigNotFoundError:
        return []
    return sorted(env_dir.glob("*.env"))


def list_rtls(tob_path: Path) -> list[Path]:
    rtl_dir = tob_path.parent / "RunTimeList"
    if not rtl_dir.is_dir():
        return []
    return sorted(rtl_dir.glob("*.rtl"))
