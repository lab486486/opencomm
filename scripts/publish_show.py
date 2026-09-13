#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""대기 지시(queue) → DeepSeek HTML → src/content/shows."""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[1]
QUEUE_DIR = REPO / "src" / "content" / "queue"
SHOWS_DIR = REPO / "src" / "content" / "shows"
DRAMA_DIR = REPO / "drama"
sys.path.insert(0, str(DRAMA_DIR))

from drama_deepseek import DeepSeekDramaGenerator  # noqa: E402
from drama_instruction import DramaInstruction  # noqa: E402

CATEGORIES = {"drama", "entertainment", "sport", "movie", "channel", "archive"}
logger = logging.getLogger("publish_show")


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def yaml_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if value is None:
        return '""'
    text = str(value)
    if text == "":
        return '""'
    if any(ch in text for ch in ":#{}[]&*!|>'\"%@`\n"):
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return text


def dump_frontmatter(data: dict, body: str = "") -> str:
    lines = ["---"]
    for key, value in data.items():
        if value is None:
            lines.append(f"{key}:")
            continue
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {yaml_scalar(item)}")
            continue
        lines.append(f"{key}: {yaml_scalar(value)}")
    lines.append("---")
    if body:
        lines.append("")
        lines.append(body.rstrip() + "\n")
    else:
        lines.append("")
    return "\n".join(lines)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    stripped = text.lstrip("\ufeff")
    if not stripped.startswith("---"):
        return {}, stripped
    parts = stripped.split("---", 2)
    if len(parts) < 3:
        return {}, stripped
    raw, body = parts[1], parts[2].lstrip("\n")
    data: dict = {}
    current_list: str | None = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if current_list and line.startswith("  - "):
            if not isinstance(data.get(current_list), list):
                data[current_list] = []
            data[current_list].append(line[4:].strip().strip('"').strip("'"))
            continue
        current_list = None
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value == "":
            data[key] = ""
            current_list = key
            continue
        if value in ("true", "false"):
            data[key] = value == "true"
            continue
        data[key] = value.strip('"').strip("'")
    return data, body


def write_markdown(path: Path, data: dict, body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_frontmatter(data, body), encoding="utf-8")


def iter_queue_files() -> list[Path]:
    if not QUEUE_DIR.exists():
        return []
    files = []
    for path in sorted(QUEUE_DIR.glob("*.md")):
        if path.name.startswith("_") or path.name.lower() == "readme.md":
            continue
        files.append(path)
    return files


def file_stem(name: str) -> str:
    cleaned = re.sub(r"[^\w가-힣.-]+", "-", name.strip())
    return cleaned.strip("-") or "show"


def existing_slugs() -> set[str]:
    slugs: set[str] = set()
    if not SHOWS_DIR.exists():
        return slugs
    for path in SHOWS_DIR.glob("*.md"):
        meta, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        slug = str(meta.get("entrySlug") or "").strip()
        if slug:
            slugs.add(slug)
    return slugs


def queue_to_instruction(meta: dict) -> DramaInstruction:
    name = str(meta.get("name") or "").strip()
    raw = "\n".join(
        [
            f"드라마 제목: {name}",
            f"방송국: {meta.get('channel') or ''}",
            f"대표 썸네일 URL: {meta.get('thumbnail') or ''}",
            f"방송 기간: {meta.get('period') or ''}",
            f"방송 시간: {meta.get('time') or ''}",
            f"방송 회차: {meta.get('episodes') or ''}",
            f"주요 출연진: {meta.get('cast') or ''}",
            f"연출 및 작가: {meta.get('staff') or ''}",
            f"시놉시스 및 줄거리: {meta.get('synopsis') or ''}",
            f"유튜브 영상 주소: {meta.get('youtubeUrl') or ''}",
            f"실시간 방송 주소: {meta.get('watchUrl') or ''}",
            f"참고 내용: {meta.get('note') or ''}",
        ]
    )
    return DramaInstruction(
        post_id=0,
        source_title=name,
        drama_title=name,
        thumbnail_url=str(meta.get("thumbnail") or "") or None,
        youtube_url=str(meta.get("youtubeUrl") or "") or None,
        broadcast_link=str(meta.get("watchUrl") or "") or None,
        raw_text=raw,
    )


def unique_slug(preferred: str, used: set[str]) -> str:
    slug = re.sub(r"[^\w가-힣-]+", "-", preferred.strip().lower()).strip("-") or "show"
    if slug not in used:
        return slug
    index = 2
    while f"{slug}-{index}" in used:
        index += 1
    return f"{slug}-{index}"


def process_item(
    path: Path,
    llm: DeepSeekDramaGenerator,
    dry_run: bool,
    used_slugs: set[str],
) -> bool:
    raw = path.read_text(encoding="utf-8")
    meta, _body = parse_frontmatter(raw)
    status = str(meta.get("status") or "").strip().lower()
    if status != "pending":
        logger.info("건너뜀 (%s): status=%s", path.name, status or "없음")
        return False

    name = str(meta.get("name") or "").strip()
    category = str(meta.get("category") or "").strip()
    if not name:
        raise ValueError("프로그램 제목이 없습니다.")
    if category not in CATEGORIES:
        raise ValueError(f"카테고리가 올바르지 않습니다: {category}")

    instruction = queue_to_instruction(meta)
    generated = llm.generate(instruction)
    slug = unique_slug(generated.slug, used_slugs)
    dest = SHOWS_DIR / f"{file_stem(name)}.md"
    if dest.exists():
        raise FileExistsError(f"이미 발행된 글이 있습니다: {dest.name}")

    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    post_meta = {
        "title": generated.title,
        "name": name,
        "category": category,
        "channel": str(meta.get("channel") or "").strip(),
        "watchUrl": str(meta.get("watchUrl") or "").strip(),
        "youtubeUrl": str(meta.get("youtubeUrl") or "").strip(),
        "thumbnail": str(meta.get("thumbnail") or "").strip(),
        "period": str(meta.get("period") or "").strip(),
        "time": str(meta.get("time") or "").strip(),
        "episodes": str(meta.get("episodes") or "").strip(),
        "cast": str(meta.get("cast") or "").strip(),
        "excerpt": generated.excerpt,
        "featured": bool(meta.get("featured")),
        "date": now,
        "updated": now,
        "tags": generated.tags,
        "entrySlug": slug,
        "legacyPath": f"/{slug}/",
        "showKey": re.sub(r"[^\w가-힣]+", "", name.lower()) or "show",
        "hiddenFromList": False,
    }

    if dry_run:
        logger.info("[DRY-RUN] 발행 건너뜀: %s (%s자)", generated.title, len(generated.html_content))
        return True

    write_markdown(dest, post_meta, generated.html_content)
    meta["status"] = "done"
    meta["note"] = f"발행됨: /{slug}/"
    write_markdown(path, meta, "")
    used_slugs.add(slug)
    logger.info("발행 완료: %s → %s", generated.title, dest.relative_to(REPO))
    return True


def mark_error(path: Path, message: str, dry_run: bool) -> None:
    if dry_run:
        logger.error("[DRY-RUN] %s 오류: %s", path.name, message)
        return
    raw = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(raw)
    meta["status"] = "error"
    meta["note"] = message
    write_markdown(path, meta, body)
    logger.error("%s 오류로 표시: %s", path.name, message)


def main() -> int:
    parser = argparse.ArgumentParser(description="방송 글 지시를 HTML로 발행합니다.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-posts", type=int, default=1)
    parser.add_argument("--model", type=str, default=None)
    args = parser.parse_args()

    load_dotenv(REPO / ".env")
    load_dotenv(DRAMA_DIR / ".env")
    setup_logging()
    logger.info("온에어 Live Git 발행기 시작")

    pending = []
    for path in iter_queue_files():
        meta, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        if str(meta.get("status") or "").strip().lower() == "pending":
            pending.append(path)

    if not pending:
        logger.info("대기 중인 지시가 없습니다.")
        return 0

    try:
        llm = DeepSeekDramaGenerator(
            api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
            model_name=args.model or os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
    except ValueError as exc:
        logger.error("DeepSeek 초기화 실패: %s", exc)
        return 1

    selected = pending[: max(1, args.max_posts)]
    logger.info("대기 %s건 중 %s건 처리", len(pending), len(selected))
    used_slugs = existing_slugs()

    ok = 0
    fail = 0
    for path in selected:
        try:
            if process_item(path, llm, dry_run=args.dry_run, used_slugs=used_slugs):
                ok += 1
        except Exception as exc:
            fail += 1
            logger.exception("처리 실패: %s", path.name)
            mark_error(path, str(exc), dry_run=args.dry_run)
        if path != selected[-1]:
            time.sleep(3)

    logger.info("완료: 성공 %s / 실패 %s", ok, fail)
    return 1 if fail and not ok else 0


if __name__ == "__main__":
    sys.exit(main())
