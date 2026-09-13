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
- 첫 호출의 임무명세서에는 대상 파일 경로·범위·기준·산출 형식·종료 마커를 전부 담는다. 단, 내부 분해 방식은 지시하지 않는다.
- `codex exec` 는 프로세스가 매 호출마다 끝난다. 하지만 **세션과 맥락은 남는다.** 아래 §7 참조 — 상주하지 않는 것과 맥락이 사라지는 것은 다르다.

## 7. 세션을 이어 쓰는 두 경로

**기본은 `exec resume` 이다.** 창을 띄울 필요가 없고, 호출하면 그 자리에서 실행된다.

```
codex exec --skip-git-repo-check "<첫 임무명세서>"           # 이 호출이 세션을 만든다
codex exec --skip-git-repo-check resume --last "<이어질 지시>"
codex exec --skip-git-repo-check resume <세션 id> "<이어질 지시>"
```

실측: 첫 `exec` 호출로 rollout 이 생성되고, `resume --last` 가 직전 지시를 그대로 복창했다.
**맥락이 이어진다.** 분대장이 여럿이면 `--last` 는 의도한 세션이 아닐 수 있으므로 세션 id 를 명시한다.

`exec resume` 의 장점: 창 불필요 · 즉시 실행 · 세션 탐색 부담 적음.
**반려 수정, 추가 자료 전달, 범위 조정은 전부 이 경로로 한다.** 임무명세서를 매번 새로 쓰는 것은
맥락을 버리고 토큰을 두 번 내는 짓이고, 분대장이 자기 산출물을 모르는 채 수정에 들어간다.

### 7.1 대화형 TUI + `codex queue` — 지휘관이 화면을 봐야 할 때만

대화형으로 띄운 세션에는 살아 있는 상태로 메시지를 넣을 수 있다.

```
codex queue --thread <세션 UUID> --message "<메시지>"
```

성공하면 `Queued message <id> for thread <uuid>` 가 나온다. 이 줄이 없으면 실패다.

- **큐는 즉시 실행이 아니다.** 현재 턴이 끝난 뒤 소비된다. 반영 확인은 산출물 파일 변경으로 한다.
- **빈 세션에는 큐를 넣을 수 없다.** `no rollout found for thread id` 가 난다. rollout 은 첫 턴이
  돌아야 생기므로, 띄울 때 첫 프롬프트를 같이 줘야 한다.

**세션을 띄우는 절차** — 런처는 반드시 `.ps1` 파일로 만들고 `-File` 로 넘긴다.

```powershell
# launch_codex.ps1  — ★ UTF-8 BOM 으로 저장할 것
Set-Location '<작업 디렉터리>'
codex '대기 상태다. 준비됐다고 한 줄로만 답해라.'
```

```powershell
Start-Process -FilePath 'powershell.exe' `
  -ArgumentList '-NoExit','-NoProfile','-ExecutionPolicy','Bypass','-File','<위 경로>' `
  -PassThru -WindowStyle Normal
```

- **`-Command` 에 한글 프롬프트를 중첩 따옴표로 직접 넣으면 런처가 조용히 죽는다.** 창이 뜬 것처럼
  보이는데 프로세스가 없고 rollout 도 안 생긴다. 이걸 "rollout 생성 고장" 으로 오판하기 쉽다.
- **`.ps1` 을 BOM 없이 저장하면 한글이 깨진 채 들어간다.** Windows PowerShell 5.1 은 BOM 이 없으면
  ANSI 로 읽는다(§2 와 같은 함정). 실측에서 `대기 상태다…` 가 `?湲??곹깭??…` 로 들어갔다.
  시드 프롬프트를 영문으로 쓰면 이 문제를 피한다.

### 7.2 세션 UUID·작업 디렉터리 얻기

`history.jsonl` 은 **사람이 친 입력만** 기록한다. 소대장이 띄운 세션은 거기 안 잡힌다.
**rollout 파일명에서 뽑는 것이 정석이다.**

```
rollout-<시작시각>-<thread UUID>.jsonl
```

작업 디렉터리는 그 파일 **첫 줄 메타의 `cwd`** 에 있다. UUID 와 cwd 를 한 번에 얻으므로
아래 오배송 방지 판정까지 이 파일 하나로 끝난다.

```bash
# 최신 세션의 UUID 와 cwd
f=$(ls -t ~/.codex/sessions/*/*/*/rollout-*.jsonl | head -1)
echo "uuid: $(basename "$f" .jsonl | sed 's/^rollout-[0-9T-]*-//')"
python -c "import json,sys;m=json.loads(open(sys.argv[1],encoding='utf-8').readline());print('cwd:',(m.get('payload') or m).get('cwd'))" "$f"
```

### 7.3 대상 오배송 방지 — 보내기 전 게이트 (필수)

Codex 세션은 여러 개가 **서로 다른 프로젝트를 동시에** 판다. "가장 최근 세션" 만 보고 고르면
지휘관이 다른 창에 한 줄 치는 순간 대상이 넘어가 **남의 분대에 지시가 꽂힌다.**
`exec resume --last` 도 같은 위험을 갖는다.

보내기 전 셋을 확인한다.

1. **작업 디렉터리** — rollout 첫 줄 메타의 `cwd` 가 현재 임무의 저장소 아래인가
2. **생존** — `~/.codex/logs_2.sqlite` 에 그 `thread_id` 의 로그가 최근 N분(권장 30분) 안에 있는가
3. **후보 수** — 정확히 1개인가. **0개거나 2개 이상이면 보내지 말고 지휘관에게 보고한다**

```python
# 후보 판정 (Python). PROJECT_ROOT 를 현재 임무의 저장소 루트로 바꾼다.
import json, pathlib, sqlite3, os, tempfile, shutil, time, datetime
PROJECT_ROOT = r"<현재 임무 저장소 루트>"
LIVE_MIN = 30
home = pathlib.Path.home() / ".codex"

tmp = os.path.join(tempfile.gettempdir(), "codex_gate.sqlite")
for ext in ("", "-wal", "-shm"):
    s = home / ("logs_2.sqlite" + ext)
    if s.exists(): shutil.copy2(s, tmp + ext)
cur = sqlite3.connect(tmp).cursor()
now = int(time.time())

ok = []
for p in sorted(home.glob("sessions/*/*/*/rollout-*.jsonl"), key=lambda x: x.stat().st_size)[-40:]:
    tid = p.name[:-6][-36:]
    try:
        meta = json.loads(p.read_text(encoding="utf-8", errors="replace").splitlines()[0])
        cwd = (meta.get("payload") or meta).get("cwd", "")
    except Exception:
        continue
    in_proj = bool(cwd) and os.path.normcase(cwd).startswith(os.path.normcase(PROJECT_ROOT))
    r = cur.execute("SELECT MAX(ts) FROM logs WHERE feedback_log_body LIKE ?", (f"%{tid}%",)).fetchone()[0]
    live = bool(r) and (now - r) / 60 <= LIVE_MIN
    if in_proj and live:
        ok.append(tid)
    print(("OK " if (in_proj and live) else "-- "), tid[:13], cwd)

print("후보:", ok if ok else "없음")
assert len(ok) == 1, "후보가 1개가 아니다 — 보내지 말고 지휘관에게 보고한다"
```

**보고에는 대상의 작업 디렉터리를 반드시 적는다.** 세션 id 만 적으면 지휘관이 대상이 맞는지
확인할 방법이 없다.

## 8. 세션 상태 진단

세션이 멈춘 것처럼 보일 때 **파일 타임스탬프로 판정하지 마라.**

| 신호 | 신뢰도 | 비고 |
|---|---|---|
| `~/.codex/logs_2.sqlite` 의 `logs` 테이블 | **높음** | 턴·에러가 실시간 기록. `feedback_log_body` 에 `thread_id` 포함 |
| `~/.codex/history.jsonl` 의 `ts` | 높음 | 사용자 입력 시각 |
| rollout `*.jsonl` **크기** | 높음 | 두 번 재서 늘면 살아 있다 |
| `thread_history_1.sqlite` 의 `thread_items` | 높음 | `created_at_ms` 최신값이 마지막 기록 시각 |
| 프로세스 CPU | 낮음 | 모델 응답 대기는 네트워크 대기라 CPU 가 안 오른다. 정체 ≠ 멈춤 |
| rollout `*.jsonl` **mtime** | **쓰지 마라** | 아래 ★ |
| `session_index.jsonl` 의 `updated_at` | **쓰지 마라** | 갱신이 멎는다 |

### ★ mtime 함정 — 실제로 오진했다

**Windows 는 열린 핸들로 계속 append 되는 파일의 mtime 을 갱신하지 않는다.** 핸들이 닫힐 때까지
디렉터리 항목의 타임스탬프가 멈춰 있다(NTFS 지연 메타데이터 갱신).

실측: rollout 의 mtime 이 **이틀 전**에 멈춰 있는데 같은 파일 크기를 70초 간격으로 두 번 재니
`31,410,231` → `31,430,007` 바이트로 **19.8KB 늘어 있었다.** 세션은 완전히 정상이었다.

이 mtime 을 근거로 "기록이 죽었다 → `--resume` 불가 → 맥락이 프로세스 메모리에만 있다" 는 결론을
냈다가 전부 철회했다. **세션 생존은 크기 증가나 `logs_2.sqlite` 로 판정하라.**

### 저장 구조 (오해 방지)

rollout `*.jsonl` 이 **선행 기록 로그**이고, `~/.codex/thread_history_1.sqlite` 가 그것을 읽어 만든
**페이지 단위 투영본**이다. 둘은 경쟁 관계가 아니다.

- `thread_history_projection_state.next_rollout_byte_offset` — 그 스레드의 rollout 을 어디까지 읽었는지
- `thread_items` / `thread_turns` — 투영된 대화 항목·턴
- `codex migrate-rollouts` (플래그 없이 실행하면 **보고만**) 로 이관 상태를 볼 수 있다.
  실측 시점 5,961건 중 5,957건 투영 완료, 오프셋 이상 **0건**.

투영 오프셋이 파일 크기보다 커 보이면 **낡은 크기와 비교한 것**이다. 다시 재라.

### 관측된 고장

- **`after_agent` 훅 실패** — 매 턴 `hook_name=legacy_notify error=파일 이름이나 확장명이 너무 깁니다. (os error 206)`.
  Windows `ERROR_FILENAME_EXCED_RANGE`. 턴은 "continuing" 으로 진행된다. rollout 과는 **무관하다**
  (rollout 은 정상 기록 중임이 확인됐다). 원인 미확인.
- **로그 폭주 발신자 추적** — `logs` 테이블의 `process_uuid` 로 어느 프로세스가 로그를 쏟는지 가른다.
  실측 사례에서 이 방법으로 401 재시도 폭주(분당 20~24건)의 발신자가 작업 중인 Codex 가 아니라
  별개 프로세스임을 특정해, 작업을 건드리지 않고 그것만 종료시켰다.
