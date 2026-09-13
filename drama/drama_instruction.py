# -*- coding: utf-8 -*-
"""워드프레스 드라마 지시글 파서."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any
from bs4 import BeautifulSoup


@dataclass
class DramaInstruction:
    post_id: int
    source_title: str
    drama_title: str
    thumbnail_url: str | None = None
    youtube_url: str | None = None
    broadcast_link: str | None = None
    reference_url: str | None = None
    reference_content: str | None = None
    raw_text: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.drama_title or self.drama_title == "미상":
            errors.append("드라마 제목을 찾지 못했습니다.")
        return errors

    def to_prompt_payload(self) -> str:
        return "\n".join(
            [
                f"지시글 원본 제목: {self.source_title}",
                f"드라마 제목: {self.drama_title}",
                f"대표 썸네일 URL: {self.thumbnail_url or '없음'}",
                f"유튜브 영상 링크: {self.youtube_url or '없음'}",
                f"실시간 방송 바로가기 링크 (내부링크): {self.broadcast_link or '없음'}",
                f"참고 사이트 URL (최신 정보 확인용): {self.reference_url or '없음'}",
                f"참고 추가 내용: {self.reference_content or '없음'}",
                "",
                "--- [사용자 입력 상세 정보 (최우선 반영)] ---",
                self.raw_text,
                "------------------------------------------",
                "",
                "중요 지침:",
                "1. 위 '[사용자 입력 상세 정보]'에 포함된 방송 기간, 시간, 회차, 출연진 등의 데이터를 절대 누락하지 말고 100% 반영하여 작성하세요.",
                "2. '참고 사이트 URL'과 '참고 추가 내용'이 제공된 경우, 해당 정보를 함께 반영하세요.",
                "3. 드라마의 방영 연도, 상태(방영 중/예정) 등 최신 정보를 정확하게 작성하세요. (현재 시점: 2026년 6월)",
            ]
        )


def _html_to_text_and_images(html_content: str) -> tuple[str, list[str]]:
    soup = BeautifulSoup(html_content or "", "html.parser")
    image_urls: list[str] = []
    for image in soup.find_all("img"):
        src = image.get("src")
        if src:
            image_urls.append(src.strip())
    
    # 텍스트 추출 시 줄바꿈 보존
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for block in soup.find_all(["p", "div", "li", "tr", "h1", "h2", "h3", "h4"]):
        block.append("\n")
        
    text = soup.get_text("\n")
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip(), image_urls


def _find_field(text: str, names: list[str]) -> str | None:
    joined = "|".join(re.escape(name) for name in names)
    pattern = rf"(?:^|\n)\s*(?:{joined})\s*[:：=]\s*(.+?)(?=\n\s*[가-힣A-Za-z ]{{1,20}}\s*[:：=]|\Z)"
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return match.group(1).strip()


def parse_drama_instruction(post: dict[str, Any]) -> DramaInstruction:
    post_id = int(post.get("id"))
    source_title = post.get("title", {}).get("rendered") or post.get("title", {}).get("raw") or ""
    content_html = post.get("content", {}).get("rendered") or post.get("content", {}).get("raw") or ""
    text, image_urls = _html_to_text_and_images(content_html)

    # 필드 추출
    drama_title = _find_field(text, ["드라마 제목", "드라마", "제목", "title"]) or source_title
    # HTML 태그 제거 및 정제
    drama_title = re.sub(r"\[.*?\]", "", drama_title).strip()
    
    # '대표 썸네일 URL' 등 다양한 양식을 인식하도록 키워드 추가
    thumbnail_url = _find_field(text, ["대표 썸네일 URL", "대표 썸네일", "썸네일", "이미지", "thumbnail", "image"])
    if not thumbnail_url and image_urls:
        thumbnail_url = image_urls[0]
        
    youtube_url = _find_field(text, ["유튜브", "youtube", "영상"])
    broadcast_link = _find_field(text, ["실시간 방송 링크", "방송 링크", "broadcast", "link"])
    reference_url = _find_field(text, ["참고 사이트", "참고", "reference", "정보"])
    reference_content = _find_field(text, ["참고 내용", "추가 내용", "note", "content"])

    # 자동 URL 매칭 보완
    all_links = re.findall(r"https?://[^\s]+", text)
    for link in all_links:
        link = link.strip()
        if not youtube_url and ("youtube" in link or "youtu.be" in link):
            youtube_url = link
        elif not broadcast_link and ("live" in link or "onair" in link):
            broadcast_link = link
        elif not reference_url and link != thumbnail_url and link != youtube_url and link != broadcast_link:
            reference_url = link

    return DramaInstruction(
        post_id=post_id,
        source_title=source_title,
        drama_title=drama_title,
        thumbnail_url=thumbnail_url,
        youtube_url=youtube_url,
        broadcast_link=broadcast_link,
        reference_url=reference_url,
        reference_content=reference_content,
        raw_text=text,
    )
