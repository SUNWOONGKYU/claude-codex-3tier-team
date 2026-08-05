# Codex CLI 호출 — Windows 환경 규격

> 이 문서는 Windows에서 Codex CLI를 호출할 때만 읽는다. 이 PC의 실측 기록이며 편제 운용 규칙이 아니다.
> 편제 규칙은 `../SKILL.md` 가 단일 출처다.

## 1. 호출 규격 (위반하면 실패)

- **`--skip-git-repo-check` 를 붙인다.** git 저장소가 아닌 폴더(`C:\Temp\...` 등)에서 플래그 없이 실행하면 `Not inside a trusted directory and --skip-git-repo-check was not specified.` 로 즉시 exit 1. (2026-07-30 실측)
- **프롬프트는 영문으로 쓴다.** 한글을 stdin·인자로 직접 전달하면 mojibake. 한글 지시는 파일로 써서 경로만 참조시킨다. 인코딩 규격은 §2 참고.
- **ASCII 경로에서 실행한다.** 한글 경로에서 실행하면 codex·빌드 오류. 작업물은 `C:\Temp\...` 로 복사해 넘긴다.
- **stdin을 종료시킨다.** 파이프(`|`) + `-` 인자로 EOF를 준다. 없으면 `Reading additional input from stdin...` 무한 대기.
- **종료 마커를 강제한다.** 프롬프트 말미에 `TASK_DONE:` / `TASK_BLOCKED:` 형식을 지정하지 않으면 성공·실패를 판별할 수 없다.

`C:\Temp\...` 는 ASCII 경로 제약 때문에 거치는 경유지일 뿐이다. 회수한 산출물은 소대장 작업 폴더에 저장하고, Codex 전용 폴더를 남기지 않는다.

## 2. 임무명세서 인코딩 — 두 경로가 정반대다

2026-08-02 실사고로 확정된 규격이다.

- **경로 A — stdin 파이프** (`$p | codex exec ... -`): 임무명세서는 **UTF-8 BOM 없이** 작성한다. 이 경로는 BOM이 있으면 오히려 문제가 된다.
- **경로 B — Codex가 파일을 직접 읽음** (호출문에 "○○.md 를 읽고 그 지시대로 하라"고 지시하는 방식): 임무명세서는 **UTF-8 BOM 필수**다. Codex가 내부적으로 PowerShell(`Get-Content`)로 읽는데, PowerShell 5.1은 BOM 없는 UTF-8을 시스템 ANSI 코드페이지로 오독해 한글이 통째로 깨진다.

```powershell
# 경로 B 전용 — BOM 있는 UTF-8로 저장
[System.IO.File]::WriteAllText($path, $txt, (New-Object System.Text.UTF8Encoding $true))
```

- `Out-File -Encoding utf8` 은 이 환경에서 BOM을 안 붙일 수 있으니 신뢰하지 않는다. 저장 후 **첫 3바이트가 `239 187 191`** 인지 확인한다.
- 호출문에 보험 한 줄을 넣는다 — *"파일을 읽을 때 한글이 깨지면 `-Encoding UTF8` 을 지정해 다시 읽어라"*.
- ⚠️ **깨짐은 조용하다.** 소스 파일(코드·HTML 등)은 멀쩡히 읽히고 **지시서만** 깨질 수 있다. Codex는 깨진 지시로도 그럴듯하게 작업을 진행한다. 호출 직후 출력 앞부분에서 지시서 원문이 제대로 인용되는지 눈으로 확인한다.
- **실사고 (2026-08-02)** — 통합검증 브리핑 파일이 BOM 없이 저장돼 한글이 통째로 깨졌고(`# V??理쒖쥌 ...`), 소스 파일은 정상 읽혀 증상이 드러나지 않았다. 판정 기준·조치필요 목록을 하나도 받지 못한 채 331KB를 검증하고서야 발견해 중단했다. 그대로 뒀으면 근거 없는 판정이 통과 도장으로 올라갈 뻔했다.

## 3. 호출 예시 (경로 A)

```powershell
# 임무명세서(한글 가능)를 UTF-8 BOM 없이 파일로
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText("C:\Temp\codex_task.txt", $임무명세서, $utf8NoBom)

# 호출 — 영문 프롬프트 + stdin 파이프 + '-' 인자 + 종료 마커 강제 + git 체크 우회
Set-Location "C:\Temp"
$p = "Read the UTF-8 text file at C:\Temp\codex_task.txt and carry out its instructions fully. Finish with a final line exactly 'TASK_DONE: <summary>' on success, or 'TASK_BLOCKED: <reason>' if blocked."
$p | codex exec --skip-git-repo-check - *> "C:\Temp\codex_log.txt"

# 결과 회수
Select-String -Path "C:\Temp\codex_log.txt" -Pattern "TASK_DONE:|TASK_BLOCKED:" | ForEach-Object { $_.Line } | Select-Object -Last 1
```

승인·샌드박스를 건너뛰어야 하는 임무(파일 쓰기·배포 등)에만 `--dangerously-bypass-approvals-and-sandbox` 를 추가한다. 읽기·분석 임무에는 붙이지 않는다 — 기본 모드로도 파일 읽기와 PowerShell 조회는 된다(실측).

**실측 (2026-07-30)** — 위 규격대로 디버깅 임무 1건(off-by-one 버그 탐색)을 태운 결과: 한글 임무명세서 정상 판독, 범위 준수, 보고 형식 준수, `TASK_DONE:` 마커 출력, exit 0. 34,438토큰 소모. 첫 시도는 `--skip-git-repo-check` 누락으로 exit 1.

## 4. 모델·추론강도 지정

- 모델과 추론강도는 **호출문에 `-c` 로 지정한다.** `config.toml` 전역을 고치면 이 PC의 모든 Codex 작업에 걸린다.
  ```powershell
  codex exec --skip-git-repo-check -c model_reasoning_effort="medium" - ...
  ```
- 추론강도 값 집합: `low` / `medium` / `high` / `xhigh`.
- 호출 전 설치·로그인 상태를 `Get-Command codex` 로 확인한다. 없으면 편제에서 빼고 Claude Code Teammate 분대장으로 대체한다.
- Codex는 모델 목록 조회 명령이 없다. 사용 가능한 모델은 릴리스 노트·`codex update` 로 확인한다.

## 5. Windows 샌드박스 설정

★ **`elevated_windows_sandbox = false` 여야 한다** (2026-08-02 실측).

`~/.codex/config.toml` 의 `[features] elevated_windows_sandbox` 가 `true` 면 샌드박스 헬퍼가 아예 뜨지 않는다 — Store 앱(`OpenAI.Codex`) 쪽 승격 헬퍼를 찾는데 그 경로가 막혀 있고, payload가 Windows 명령줄 한계(32,767자)를 넘겨 `os error 206` 으로 죽는다. **읽기조차 안 된다.** `false` 로 내리면 읽기 전용 샌드박스가 정상 동작한다(이미지 판독 포함).

```powershell
Get-Content "$env:USERPROFILE\.codex\config.toml" | Select-String "elevated_windows_sandbox"
```

- **읽기 전용 검증 호출은 이 설정만으로 충분하다.** bypass 플래그 없이 샌드박스 안에서 돌므로 검증자의 수정 금지가 기계적으로 보장된다.
- **쓰기 임무는 범위 제한이 안 된다** — `-s workspace-write` + `approval_policy="never"` 를 줘도 `read-only sandbox policy rejected` 로 거부된다. Windows에서 승격 헬퍼 없이는 쓰기 권한을 못 준다. 따라서 파일 쓰기·배포 임무는 `--dangerously-bypass-approvals-and-sandbox` + **절차적 격리**(전용 cwd, 명세서에 손댈 파일 명시, 회수 시 폴더 밖 변경 확인)로 간다.

## 6. 알려진 이슈

- `You've hit your usage limit ... try again at HH:MM` — ChatGPT 구독의 별도 사용량 한도다. Claude 한도와 무관하게 따로 걸린다. 안내 시각까지 대기하거나 해당 구역을 Claude Code Teammate 분대장으로 되돌린다.
- hang 발생 시 멈춘 `codex` / 자식 `node` PID만 골라 `Stop-Process`.
- Codex는 세션 맥락을 전혀 공유하지 않는다. 대상 파일 경로·범위·기준·산출 형식·종료 마커를 임무명세서에 전부 담는다. 단, 내부 분해 방식은 지시하지 않는다.
- Codex는 상주하지 않아 반려분을 스스로 고치지 못한다. 소대장이 반려 사유를 임무명세서에 담아 다시 호출한다.
