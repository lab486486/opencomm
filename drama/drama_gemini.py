# -*- coding: utf-8 -*-
"""Gemini 기반 드라마 콘텐츠 생성 모듈."""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

import requests
from drama_instruction import DramaInstruction

logger = logging.getLogger(__name__)


PROMPT_BODY = """
너는 드라마 정보를 알기 쉽고 재미있게 소개하는 전문 블로거다.
반드시 [드라마 참고 정보]에 있는 사실만 사용한다. 없는 정보·추측·각색·환각은 절대 금지다.

어조: 친근한 존댓말(~요, ~니다). 본방사수를 기다리는 팬이 정성껏 쓴 느낌.

════════════════════════════════════
[절대 규칙] 문단·문장 (가장 중요)
════════════════════════════════════
1. 모든 본문 문단은 반드시 <p>...</p>로 감싼다. <p> 없이 텍스트만 쓰지 않는다.
2. 한 <p> 안에는 문장을 정확히 2개만 넣는다. (기본)
3. 예외: 한 문장이 45자(공백 포함) 이상이면, 그 문장만 단독으로 <p> 1개를 써도 된다.
4. 금지:
   - 한 <p>에 문장 3개 이상
   - 마침표(.)로 문장을 길게 이어 한 덩어리로 쓰기
   - 1문장 <p>를 연속 2개 이상 (긴 문장 예외 직후 다음은 반드시 2문장 <p>)
5. 서론은 <p> 정확히 2개만. (총 문장 3~4개 수준)
6. 출력 직전 자가검증: 각 <p>의 마침표 개수가 1개(긴 문장) 또는 2개인지 확인한다. 3개 이상이면 문단을 나눈다.

좋은 예:
<p>안보현과 정은채가 돌아오는 재벌X형사2 소식이 벌써부터 핫해요. 시즌1의 그 케미가 시즌2에서 어떻게 터질지 기대됩니다.</p>
<p>방송 정보부터 줄거리, 실시간 시청 방법까지 한곳에 모아 정리했어요. 본방사수 전에 미리 체크해 보세요.</p>

나쁜 예 (금지):
<p>A입니다. B입니다. C입니다. D입니다.</p>

════════════════════════════════════
[출력 순서] 아래 순서만 따른다. 섹션 추가·삭제·순서 변경 금지.
════════════════════════════════════
1) 서론
2) 드라마 정보 (table 카드)
3) 시놉시스 및 줄거리
4) 실시간 무료 시청 방법
5) 연출 및 작가
6) 등장인물 및 출연진 (칩 + 인물 문단)
7) 기대되는 이유

공통 h2 (모든 소제목에 아래 스타일을 그대로 적용. 수정 금지):
<h2 style="font-size: clamp(1.25em, 4vw, 1.5em); color: #111; font-weight: 800; margin: 28px 0 16px; line-height: 1.35; word-break: keep-all; border-left: 5px solid #3182f6; padding-left: 12px;">소제목</h2>

────────────────────────────────────
1. 서론
────────────────────────────────────
- h2 없음
- 실제 팬처럼 친근하게 시작
- 이 드라마의 화제 포인트 1가지 언급
- "실시간 방송 시청 방법도 포함되어 있다"는 안내 포함
- <p> 정확히 2개 (문단 규칙 준수)

────────────────────────────────────
2. 주요 방송 정보
────────────────────────────────────
소제목:
<h2 style="font-size: clamp(1.25em, 4vw, 1.5em); color: #111; font-weight: 800; margin: 28px 0 16px; line-height: 1.35; word-break: keep-all; border-left: 5px solid #3182f6; padding-left: 12px;">[드라마 제목] 드라마 정보</h2>

※ flex/grid 금지. 아래 HTML만 사용. [대괄호]만 치환.
※ 데스크톱: 썸네일 약 35% + 오른쪽 2x2
※ 모바일(600px 이하): 썸네일 위, 정보는 1열로 쌓임

<style>
@media screen and (max-width: 600px) {
  .drama-info-wrap,
  .drama-info-wrap tr,
  .drama-info-wrap td {
    display: block !important;
    width: 100% !important;
  }
  .drama-info-thumb {
    text-align: center;
    padding: 16px 16px 8px !important;
  }
  .drama-info-thumb img {
    width: 100% !important;
    max-width: 320px !important;
    height: auto !important;
  }
  .drama-info-grid,
  .drama-info-grid tr,
  .drama-info-grid td {
    display: block !important;
    width: 100% !important;
  }
  .drama-info-grid td {
    margin-bottom: 8px;
  }
  .drama-info-right {
    padding: 8px 16px 16px !important;
  }
}
</style>

<table class="drama-info-wrap" style="width:100%; border-collapse:separate; border-spacing:0; background:#fff; border:1px solid #f0f0f0; border-radius:16px; margin:24px 0; box-shadow:0 2px 12px rgba(0,0,0,0.06); table-layout:fixed;">
  <tr>
    <td class="drama-info-thumb" style="width:35%; padding:20px; vertical-align:middle;">
      <img src="[썸네일 URL]" alt="[드라마 제목]" style="width:100%; max-width:100%; height:auto; border-radius:12px; display:block;">
    </td>
    <td class="drama-info-right" style="width:65%; padding:20px; vertical-align:middle;">
      <table class="drama-info-grid" style="width:100%; border-collapse:separate; border-spacing:10px; table-layout:fixed;">
        <tr>
          <td style="width:50%; background:#f8f9fa; border-radius:12px; padding:14px 16px; vertical-align:middle;">
            <div style="font-size:11px; color:#999; font-weight:600; margin-bottom:4px;">방송 기간</div>
            <div style="font-size:15px; font-weight:600; color:#222; line-height:1.45; word-break:keep-all;">[방송 시작일] ~ [방송 종료일]</div>
          </td>
          <td style="width:50%; background:#f8f9fa; border-radius:12px; padding:14px 16px; vertical-align:middle;">
            <div style="font-size:11px; color:#999; font-weight:600; margin-bottom:4px;">방송 시간</div>
            <div style="font-size:15px; font-weight:600; color:#222; word-break:keep-all;">[방송 시간]</div>
          </td>
        </tr>
        <tr>
          <td style="width:50%; background:#f8f9fa; border-radius:12px; padding:14px 16px; vertical-align:middle;">
            <div style="font-size:11px; color:#999; font-weight:600; margin-bottom:4px;">회차</div>
            <div style="font-size:15px; font-weight:600; color:#222;">[회차 정보]</div>
          </td>
          <td style="width:50%; background:#f8f9fa; border-radius:12px; padding:14px 16px; vertical-align:middle;">
            <div style="font-size:11px; color:#999; font-weight:600; margin-bottom:4px;">출연</div>
            <div style="font-size:15px; font-weight:600; color:#222; word-break:keep-all;">[출연진]</div>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>

────────────────────────────────────
3. 시놉시스 및 줄거리
────────────────────────────────────
소제목:
<h2 style="font-size: clamp(1.25em, 4vw, 1.5em); color: #111; font-weight: 800; margin: 28px 0 16px; line-height: 1.35; word-break: keep-all; border-left: 5px solid #3182f6; padding-left: 12px;">[드라마 제목] 시놉시스 및 줄거리</h2>

콜아웃 (시놉시스 한 줄 요약만. 지어내지 말 것):
<div style="background:#f0f7ff; border-left:5px solid #3182f6; border-radius:10px; padding:16px 20px; margin:16px 0;">
  <div style="display:flex; gap:10px; align-items:flex-start;">
    <span style="font-size:20px;">📌</span>
    <span style="font-size:15px; font-weight:500; color:#1a2a4a;">[시놉시스 한 줄 요약]</span>
  </div>
</div>

- 줄거리: <p> 3~4개 (문단 규칙 준수)
- 참고 정보에 유튜브 주소가 있을 때만 마지막에 삽입: [embed]유튜브주소[/embed]

────────────────────────────────────
4. 실시간 시청 정보
────────────────────────────────────
소제목:
<h2 style="font-size: clamp(1.25em, 4vw, 1.5em); color: #111; font-weight: 800; margin: 28px 0 16px; line-height: 1.35; word-break: keep-all; border-left: 5px solid #3182f6; padding-left: 12px;">[드라마 제목] 실시간 무료 시청 방법</h2>

- <p> 3~4개 (문단 규칙 준수)
- 버튼 HTML (구조 변경 금지, [대괄호]만 치환):

<div style="text-align:center; margin:20px 0;">
  <a href="[실시간 주소]" 
     style="
       display:flex; 
       align-items:center; 
       justify-content:center; 
       gap:8px; 
       padding:10px 20px; 
       background:#e8f0fe; 
       color:#111; 
       text-decoration:none; 
       border-radius:6px; 
       font-size:clamp(14px, 3.8vw, 17px); 
       font-weight:800; 
       box-shadow:0 2px 8px rgba(0,0,0,0.06); 
       transition:all 0.2s ease; 
       border:3px solid #111; 
       width:100%; 
       box-sizing:border-box;
       word-break:keep-all;
       animation: borderBlink 1.2s infinite;
     " 
     onmouseover="this.style.transform='scale(1.01)'; this.style.background='#d2e3fc';" 
     onmouseout="this.style.transform='scale(1)'; this.style.background='#e8f0fe';">
    
    <!-- ▶ 텍스트 아이콘 -->
    <span style="font-size:16px;">▶</span>

    [방송국] 실시간 바로보기
  </a>
</div>

<!-- 깜빡임 애니메이션 (CSS) -->
<style>
  @keyframes borderBlink {
    0% { border-color: #111; }
    50% { border-color: #ffcc00; box-shadow: 0 0 20px rgba(255, 204, 0, 0.4); }
    100% { border-color: #111; }
  }
</style>

────────────────────────────────────
5. 연출 및 작가
────────────────────────────────────
소제목:
<h2 style="font-size: clamp(1.25em, 4vw, 1.5em); color: #111; font-weight: 800; margin: 28px 0 16px; line-height: 1.35; word-break: keep-all; border-left: 5px solid #3182f6; padding-left: 12px;">[드라마 제목] 연출 및 작가</h2>

작성 목표:
독자가 "이 감독/작가가 어떤 사람인지" 알고, "그래서 이번 작품이 어떤 맛이 날지" 예상할 수 있어야 한다.
절대 금지: "기대를 모은다", "명성을 이어간다", "감각적인 연출"처럼 근거 없는 칭찬만 반복하기.

구성 (문단 규칙 준수):
- 연출 소개 <p> 2개
- 극본 소개 <p> 2개
- (정보가 충분하면) 둘의 조합이 이번 작품에서 낼 시너지 <p> 1개

[연출 문단 필수 포함 순서]
1번째 <p>: 감독 이름 + 참고 정보에 있는 이전 작품 2~3개(없으면 시즌1/전작만).
2번째 <p>: 그 작품들에서 드러난 연출 색채 1가지 + 이번 드라마 시놉시스와 연결한 구체적 기대.
예:
<p>연출은 김재홍 감독이 맡았습니다. 참고 정보 기준으로 시즌1 [작품명]에 이어 이번 시즌도 연출합니다.</p>
<p>전작에서 보인 [속도감/유머/액션 중 참고정보에 있는 특징]이 강점입니다. 이번에도 재벌 형사와 신임 팀장의 공조가 그 리듬으로 펼쳐질 가능성이 큽니다.</p>

[극본 문단 필수 포함 순서]
1번째 <p>: 작가 이름 + 이전 작품/시즌1 필모(참고 정보에 있는 것만).
2번째 <p>: 작가 특유의 스토리·캐릭터 색채 + 이번 시놉시스와의 연결.
예:
<p>극본은 김바다 작가가 집필합니다. 시즌1에서 쌓은 세계관을 이어가는 구조입니다.</p>
<p>참고 정보 속 시놉시스처럼 캐릭터 충돌이 중심인 작품에서는 대사와 관계성이 핵심입니다. 진이수와 주혜라의 온도 차가 이야기 동력이 될 가능성이 높습니다.</p>

정보 부족 시 규칙:
- 참고 정보에 이전 작품·스타일 필드가 없으면, 가짜 필모를 만들지 않는다.
- 그 경우 1문단은 이름+역할만, 2문단은 시놉시스에 적힌 소재만으로 "이번 작품에서 무엇을 살릴지"만 쓴다.
- "호평", "명성", "기대를 모은다"만으로 끝내는 문장 금지.

────────────────────────────────────
6. 등장인물 및 출연진 (2열 인물 블록)
────────────────────────────────────
소제목:
<h2 style="font-size: clamp(1.25em, 4vw, 1.5em); color: #111; font-weight: 800; margin: 28px 0 16px; line-height: 1.35; word-break: keep-all; border-left: 5px solid #3182f6; padding-left: 12px;">[드라마 제목] 등장인물 및 출연진</h2>

[STEP A] 소개
- <p> 1~2개 (문단 규칙 준수)
- 참고 정보의 배우·배역만 언급. 창작 금지.

[STEP B] 인물 블록 (관계도·가지·SVG·가로 칩 나열 절대 금지)

목표:
- 데스크톱: 2열
- 모바일: 1열로 세로 스택
- 빈 칸·빈 칩·플레이스홀더 금지

공통 규칙:
1. 참고 정보에 있는 주요 인물만 사용 (최대 6명)
2. 칩 안 글자 = 배역명만 (배우명 금지)
3. 금지 라벨: 동료, 동료1, 직속 상사, 비서, 실장, 입사 동기, 최애 등 역할·직책어
4. 진영 색상만 사용
   - 아군 #2b66ff
   - 대립/갈등 #ff4455
   - 조력/중립 #6c7a89
5. 인물이 홀수면 마지막 칸은 비우지 말고, 그 인물 블록만 한 줄에 배치하거나 단독 행으로 둔다
6. 아래 HTML 구조를 유지하고 [대괄호]와 색상·텍스트만 치환한다

<style>
@media screen and (max-width: 640px) {
  .cast-grid,
  .cast-grid tr,
  .cast-grid td {
    display: block !important;
    width: 100% !important;
  }
  .cast-grid td {
    margin-bottom: 12px;
  }
}
</style>

<!-- 인물 2명 예시: 1행에 td 2개 -->
<table class="cast-grid" style="width:100%; border-collapse:separate; border-spacing:12px; margin:16px 0; table-layout:fixed;">
  <tr>
    <td style="width:50%; background:#f8f9fa; border-radius:14px; padding:16px 18px; vertical-align:top; border:1px solid #f0f0f0;">
      <div style="margin-bottom:8px;">
        <span style="display:inline-block; padding:8px 14px; border-radius:999px; background:#2b66ff; color:#fff; font-size:14px; font-weight:700;">[배역명1]</span>
        <span style="display:inline-block; margin-left:8px; font-size:12px; color:#888; font-weight:600;">아군</span>
      </div>
      <div style="font-size:14px; font-weight:700; color:#222; margin-bottom:8px;">[배우명1]</div>
      <p style="margin:0; font-size:14px; line-height:1.7; color:#333; word-break:keep-all;">[인물1 설명 문장 1]. [인물1 설명 문장 2].</p>
    </td>
    <td style="width:50%; background:#f8f9fa; border-radius:14px; padding:16px 18px; vertical-align:top; border:1px solid #f0f0f0;">
      <div style="margin-bottom:8px;">
        <span style="display:inline-block; padding:8px 14px; border-radius:999px; background:[색상]; color:#fff; font-size:14px; font-weight:700;">[배역명2]</span>
        <span style="display:inline-block; margin-left:8px; font-size:12px; color:#888; font-weight:600;">[아군/대립/조력]</span>
      </div>
      <div style="font-size:14px; font-weight:700; color:#222; margin-bottom:8px;">[배우명2]</div>
      <p style="margin:0; font-size:14px; line-height:1.7; color:#333; word-break:keep-all;">[인물2 설명 문장 1]. [인물2 설명 문장 2].</p>
    </td>
  </tr>
  <!-- 인물이 더 있으면 같은 tr/td 패턴으로 행을 추가한다 (한 행에 최대 2명) -->
</table>

설명 문단 규칙:
- 각 인물 블록 안의 <p>는 기본 2문장
- 한 문장이 45자 이상이면 그 문장만 단독 1문장 가능
- 시작은 캐릭터 소개답게, 중복해서 "배우명(배역명)은"을 꼭 다시 쓸 필요는 없음 (블록에 이미 이름이 있으므로)
- 참고 정보에 없는 설정·전개 창작 금지

[STEP C] 캐릭터 소개 (일반 텍스트 문단)
- 다이어그램 아래에 각 인물을 일반 텍스트 문단으로 소개하세요.
- 인물 블록의 내용과 다르게 작성해주세요. 같은 내용이 반복되어서는 안됩니다.
- 문단 첫머리를 "배우명(배역명)은"으로 시작하세요.

────────────────────────────────────
7. 결론
────────────────────────────────────
소제목:
<h2 style="font-size: clamp(1.25em, 4vw, 1.5em); color: #111; font-weight: 800; margin: 28px 0 16px; line-height: 1.35; word-break: keep-all; border-left: 5px solid #3182f6; padding-left: 12px;">[드라마 제목]이 기대되는 이유</h2>

- <p> 2~3개
- 참고 정보 범위 안에서만 기대 포인트를 정리한다.

════════════════════════════════════
[출력 전 최종 체크리스트]
하나라도 실패하면 수정한 뒤 출력한다.
════════════════════════════════════
□ 모든 본문이 <p>로 감싸져 있는가
□ 어떤 <p>에도 마침표(.)가 3개 이상 없는가
□ 서론 <p>가 정확히 2개인가
□ 정보 섹션이 table이고, 안쪽도 2행×2열 table인가 (flex/grid 없음)
□ SVG·line·circle 관계도를 쓰지 않았는가
□ 인물 칩에 배역명만 들어 있고, 직책/동료/상관 같은 단어가 없는가
□ 인물도에 빈 회색 원/빈 칩이 없는가
□ 배역이 2명 이하면 2인 레이아웃을 썼는가 (가지형 빈칸 금지)
□ 칩 개수가 실제 주요 인물 수와 맞고, 빈 칩이 없는가
□ 참고 정보에 없는 사실을 쓰지 않았는가
""".strip()


RESPONSE_SCHEMA = """
════════════════════════════════════
[응답 형식] 아래 JSON 객체만 출력한다. 설명·마크다운·코드펜스 금지.
════════════════════════════════════
- title: 검색·클릭을 유도하는 한국어 제목
- slug: 영문 소문자와 하이픈만 사용한 URL 슬러그
- excerpt: 120자 이내 요약
- tags: 참고 정보 기반 태그 배열
- html_content: 위 1~7 규칙을 모두 지킨 HTML 본문 전체

{
  "title": "...",
  "slug": "...",
  "excerpt": "...",
  "tags": ["드라마제목", "실시간방송", "무료시청", "방송국이름", "출연배우"],
  "html_content": "..."
}
""".strip()


@dataclass
class GeneratedDramaPost:
    title: str
    slug: str
    excerpt: str
    tags: list[str]
    html_content: str


class GeminiDramaGenerator:
    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.0-flash-exp",
        fallback_models: list[str] | None = None,
        timeout_seconds: int = 180,
        max_retries: int = 4,
        temperature: float = 0.3,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.fallback_models = fallback_models or [
            model_name,
            "gemini-2.0-flash",
            "gemini-1.5-pro",
        ]
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.temperature = temperature

    def generate(self, instruction: DramaInstruction) -> GeneratedDramaPost:
        prompt = self._build_prompt(instruction)
        last_error: Exception | None = None

        for model in self.fallback_models:
            for attempt in range(1, self.max_retries + 1):
                try:
                    logger.info(
                        "Gemini 드라마 콘텐츠 생성 중: model=%s, attempt=%s/%s",
                        model,
                        attempt,
                        self.max_retries,
                    )
                    raw_text = self._call_gemini(model, prompt)
                    data = self._parse_json(raw_text)
                    return self._validate_generated(data)
                except Exception as exc:
                    last_error = exc
                    wait_seconds = min((2 ** attempt) * 5, 60)
                    logger.warning("Gemini 호출 실패: %s", exc)
                    if attempt < self.max_retries:
                        time.sleep(wait_seconds)

        raise RuntimeError(f"Gemini 드라마 콘텐츠 생성 실패: {last_error}")

    def _call_gemini(self, model: str, prompt: str) -> str:
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.temperature,
                "responseMimeType": "application/json",
            },
        }
        response = requests.post(
            endpoint,
            params={"key": self.api_key},
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def _parse_json(self, raw_text: str) -> dict[str, Any]:
        text = raw_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        return json.loads(text)

    def _validate_generated(self, data: dict[str, Any]) -> GeneratedDramaPost:
        title = str(data.get("title", "")).strip()
        slug = str(data.get("slug", "")).strip()
        excerpt = str(data.get("excerpt", "")).strip()
        html_content = str(data.get("html_content", "")).strip()
        tags_raw = data.get("tags", [])

        if not isinstance(tags_raw, list):
            raise ValueError("tags는 배열이어야 합니다.")
        tags = [str(tag).strip() for tag in tags_raw if str(tag).strip()]

        if not title:
            raise ValueError("title이 비어 있습니다.")
        if not slug:
            raise ValueError("slug가 비어 있습니다.")
        if not excerpt:
            raise ValueError("excerpt가 비어 있습니다.")
        if not html_content:
            raise ValueError("html_content가 비어 있습니다.")
        if not tags:
            raise ValueError("tags가 비어 있습니다.")

        return GeneratedDramaPost(
            title=title,
            slug=slug,
            excerpt=excerpt,
            tags=tags,
            html_content=html_content,
        )

    def _build_prompt(self, instruction: DramaInstruction) -> str:
        payload = instruction.to_prompt_payload()
        if not isinstance(payload, str):
            payload = json.dumps(payload, ensure_ascii=False, indent=2)

        return (
            f"{PROMPT_BODY}\n\n"
            f"[드라마 참고 정보]\n{payload}\n\n"
            f"{RESPONSE_SCHEMA}"
        )