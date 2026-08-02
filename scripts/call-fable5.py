# -*- coding: utf-8 -*-
"""
claude-codex-3tier-team 기획·전략참모 호출 스크립트 (Fable 5, API 건당 과금)

용법:
  python call-fable5.py "자문 요청 프롬프트"
  python call-fable5.py --file 질문.md
  python call-fable5.py --system "역할 지시" "프롬프트"

API 키: 환경변수 ANTHROPIC_API_KEY (하드코딩 금지)
의존성: 표준 라이브러리만 사용 (urllib) — anthropic SDK 불필요
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

MODEL = "claude-fable-5"
API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_SYSTEM = (
    "너는 claude-codex-3tier-team 편제의 기획·전략참모(Fable 5)다. "
    "소대장의 자문 요청에 대해 기획·전략 관점의 판단을 제시한다. "
    "결론 먼저, 근거는 뒤에. 대안이 갈리면 추천 1개와 이유를 명시한다. "
    "너는 부대원이 아니라 호출 대상이다 — 자문 결과만 반환하고 작업을 수행하지 않는다."
)


def main():
    parser = argparse.ArgumentParser(description="Fable 5 전략참모 자문 호출")
    parser.add_argument("prompt", nargs="?", help="자문 요청 프롬프트")
    parser.add_argument("--file", help="프롬프트를 파일에서 읽기")
    parser.add_argument("--system", default=DEFAULT_SYSTEM, help="시스템 프롬프트 재정의")
    parser.add_argument("--max-tokens", type=int, default=4096)
    args = parser.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            prompt = f.read()
    elif args.prompt:
        prompt = args.prompt
    else:
        parser.error("프롬프트 또는 --file 중 하나가 필요합니다")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "[오류] 환경변수 ANTHROPIC_API_KEY가 설정되어 있지 않습니다.\n"
            "설정 후 재실행하세요 (PowerShell): $env:ANTHROPIC_API_KEY = '<키>'\n"
            "참모 호출은 API 건당 과금입니다 — 키가 없으면 참모 없이 진행하십시오.",
            file=sys.stderr,
        )
        sys.exit(2)

    body = json.dumps({
        "model": MODEL,
        "max_tokens": args.max_tokens,
        "system": args.system,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        print(f"[오류] API 호출 실패 (HTTP {e.code}): {detail}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"[오류] 네트워크 오류: {e.reason}", file=sys.stderr)
        sys.exit(1)

    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    print(text)

    usage = data.get("usage", {})
    print(
        f"\n--- [참모 호출 완료] model={data.get('model', MODEL)} "
        f"in={usage.get('input_tokens', '?')}tok out={usage.get('output_tokens', '?')}tok (API 건당 과금) ---",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
