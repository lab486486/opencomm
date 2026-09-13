# -*- coding: utf-8 -*-
"""DeepSeek V4 API 기반 드라마 콘텐츠 생성 모듈 (OpenAI 호환)."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from openai import OpenAI

from drama_gemini import GeneratedDramaPost, GeminiDramaGenerator
from drama_instruction import DramaInstruction

logger = logging.getLogger(__name__)


class DeepSeekDramaGenerator:
    """DeepSeek V4로 드라마 소개 JSON/HTML을 생성합니다."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "deepseek-v4-pro",
        base_url: str = "https://api.deepseek.com",
        thinking: bool = False,
        timeout_seconds: int = 240,
        max_retries: int = 4,
        max_tokens: int = 16000,
        temperature: float = 0.7,
        fallback_models: list[str] | None = None,
    ):
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY 가 비어 있습니다.")

        self.api_key = api_key
        self.model_name = (model_name or "deepseek-v4-pro").strip()
        self.base_url = base_url.rstrip("/")
        self.thinking = thinking
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.fallback_models = fallback_models or [
            self.model_name,
            "deepseek-v4-flash",
        ]
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout_seconds,
        )
        logger.info(
            "DeepSeek 드라마 생성기 초기화: model=%s thinking=%s",
            self.model_name,
            self.thinking,
        )

    def generate(self, instruction: DramaInstruction) -> GeneratedDramaPost:
        prompt = GeminiDramaGenerator._build_prompt(self, instruction)
        prompt = (
            prompt
            + "\n\n중요: 반드시 JSON 객체로만 응답하세요. "
            "코드펜스(```) 없이 title, slug, excerpt, tags, html_content 키를 포함하세요."
        )
        last_error: Exception | None = None

        for model in self.fallback_models:
            for attempt in range(1, self.max_retries + 1):
                try:
                    logger.info(
                        "DeepSeek 드라마 콘텐츠 생성 중: model=%s, attempt=%s/%s",
                        model,
                        attempt,
                        self.max_retries,
                    )
                    raw_text = self._call_deepseek(model, prompt)
                    data = self._parse_json(raw_text)
                    generated = self._validate_generated(data)
                    return generated
                except Exception as exc:
                    last_error = exc
                    wait_seconds = min((2 ** attempt) * 5, 60)
                    logger.warning("DeepSeek 호출 실패: %s", exc)
                    if attempt < self.max_retries:
                        time.sleep(wait_seconds)
        raise RuntimeError(f"DeepSeek 드라마 콘텐츠 생성 실패: {last_error}")

    def _call_deepseek(self, model: str, prompt: str) -> str:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "당신은 드라마 정보를 알기 쉽게 소개하는 전문 블로거입니다. "
                        "요청한 JSON 스키마만 출력하고, html_content는 순수 HTML만 담으세요. "
                        "제공된 참고 정보에 없는 내용은 지어내지 마세요."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
            "extra_body": {
                "thinking": {"type": "enabled" if self.thinking else "disabled"},
            },
        }
        if not self.thinking:
            kwargs["temperature"] = self.temperature

        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        if not content or not str(content).strip():
            raise ValueError("DeepSeek 응답이 비어 있습니다.")
        return str(content).strip()

    def _parse_json(self, raw_text: str) -> dict[str, Any]:
        text = raw_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        return json.loads(text)

    def _validate_generated(self, data: dict[str, Any]) -> GeneratedDramaPost:
        html = self._clean_html(str(data.get("html_content", "")).strip())
        if not html:
            raise ValueError("html_content 가 비어 있습니다.")

        tags = data.get("tags", [])
        if not isinstance(tags, list):
            tags = []

        return GeneratedDramaPost(
            title=str(data.get("title", "")).strip(),
            slug=str(data.get("slug", "")).strip(),
            excerpt=str(data.get("excerpt", "")).strip(),
            tags=[str(t).strip() for t in tags if str(t).strip()],
            html_content=html,
        )

    SECTION_H2_STYLE = (
        "font-size: clamp(1.25em, 4vw, 1.5em); color: #111; font-weight: 800; "
        "margin: 28px 0 16px; line-height: 1.35; word-break: keep-all; "
        "border-left: 5px solid #3182f6; padding-left: 12px;"
    )

    @classmethod
    def _clean_html(cls, html: str) -> str:
        text = (html or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:html|HTML)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        text = text.replace("```", "")
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
        # 잘못된 h3/h2 짝 보정
        text = re.sub(r"<h3(\b[^>]*)>", r"<h2\1>", text, flags=re.I)
        text = re.sub(r"</h3>", "</h2>", text, flags=re.I)
        text = cls._ensure_section_heading_styles(text)
        return text.strip()

    @classmethod
    def _ensure_section_heading_styles(cls, html: str) -> str:
        """본문 소제목(h2)에 파란 왼쪽 바 스타일을 강제 적용."""

        def repl(match: re.Match[str]) -> str:
            attrs = match.group(1) or ""
            inner = match.group(2)
            if "border-left" in attrs:
                attrs = re.sub(
                    r"border-left\s*:\s*[^;]+",
                    "border-left: 5px solid #3182f6",
                    attrs,
                    flags=re.I,
                )
                return f"<h2{attrs}>{inner}</h2>"
            if re.search(r'style\s*=\s*"', attrs, flags=re.I):
                attrs = re.sub(
                    r'style\s*=\s*"([^"]*)"',
                    lambda m: f'style="{m.group(1).rstrip("; ")}; {cls.SECTION_H2_STYLE}"',
                    attrs,
                    count=1,
                    flags=re.I,
                )
            else:
                attrs = f' style="{cls.SECTION_H2_STYLE}"'
            return f"<h2{attrs}>{inner}</h2>"

        return re.sub(
            r"<h2([^>]*)>(.*?)</h2>",
            repl,
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
