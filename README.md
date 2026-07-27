# YouTube Studio+ — n8n 자동 업로드 + 유투봇

휴대폰이나 PC가 꺼져도 **VPS의 Docker 서비스가 계속 실행**되어 정해진 시간에 Shorts를 만들고 YouTube에 예약 게시합니다. 같은 서버에서 GPT형 **유투봇**이 대화·사진·채널/영상 분석과 자동화 설정 수정을 지원합니다.

> [!CAUTION]
> 채팅에 공개한 `GOCSPX-...` 형태의 값은 API 키가 아니라 **Google OAuth Client Secret**입니다. 이미 노출된 secret은 즉시 Google Cloud Console에서 폐기하고 새 OAuth 클라이언트를 만드세요. 이 저장소에는 해당 값을 넣지 않았습니다.

## 동작 구조

```text
[자동 제작]
매일 03:00 KST n8n → 유투봇 설정 조회 → Gemini 기획 → TTS/FFmpeg 렌더
→ YouTube OAuth로 private 업로드 + publishAt → 매일 18:00 자동 공개

[유투봇]
Studio 로그인 → 영구 대화/사진 업로드 → 내 채널 + 벤치마킹 채널 실데이터 수집
→ 각 채널 지정 영상 0~15개(비우면 최신 15개) → Gemini 분석/수정/설정 제안
→ 사용자가 확인한 설정만 저장 → 다음 n8n 실행부터 반영
```

- **n8n 2.31.6 + PostgreSQL 16**: 워크플로와 OAuth 자격 증명 영구 저장
- **유투봇 Studio**: HttpOnly 로그인, 대화방, 사진, 내보내기/삭제, 채널 비교, 자동화 설정 UI
- **Video Worker**: Gemini 멀티모달, YouTube Data API, TTS, Pexels, FFmpeg를 묶은 FastAPI 서비스
- **대화 보존**: 인위적인 메시지 개수·만료 제한 없이 SQLite/볼륨에 저장(모델에 보내는 최근 문맥 수만 제한)
- **중복 방지**: 날짜·채널별 idempotency 키와 업로드 완료 상태를 SQLite에 보존
- **상시 재시작**: 모든 핵심 컨테이너에 `restart: unless-stopped`
- **정확한 게시**: 게시 시간까지 n8n을 기다리게 하지 않고, 영상을 미리 비공개 업로드한 뒤 YouTube `publishAt`으로 예약
- **HTTPS**: production profile의 Caddy가 인증서를 자동 발급·갱신
- **정리 작업**: 렌더 파일은 기본 7일 뒤 자동 삭제, n8n 실행 기록도 7일 뒤 정리

## 1. 서버 준비

GitHub Pages나 휴대폰 브라우저만으로는 백그라운드 작업이 불가능합니다. **항상 켜져 있는 Linux VPS**가 필요합니다.

권장 사양:

- Ubuntu 24.04 또는 동급 Linux
- 최소 2 vCPU / RAM 4 GB, 권장 4 vCPU / RAM 8 GB
- 여유 디스크 30 GB 이상
- Docker Engine + Docker Compose v2
- VPS를 가리키는 DNS A/AAAA 레코드 2개(예: `n8n.example.com`, `studio.example.com`)
- 방화벽 TCP 80/443 허용

```bash
git clone https://github.com/gubin0425a-creator/YouTube-Studio.git
cd YouTube-Studio
./scripts/init-env.sh
nano .env
```

`.env`에서 반드시 설정할 값:

```dotenv
N8N_HOST=n8n.example.com
STUDIO_HOST=studio.example.com
GEMINI_API_KEY=AIza...실제_Gemini_API_키
YOUTUBE_DATA_API_KEY=AIza...YouTube_Data_API_v3_조회키
```

Gemini와 YouTube 조회 키는 API 제한을 서로 다르게 걸 수 있도록 별도 키를 권장합니다. `POSTGRES_PASSWORD`, `N8N_ENCRYPTION_KEY`, `VIDEO_WORKER_TOKEN`, `STUDIO_ACCESS_PASSWORD`, `STUDIO_SESSION_SECRET`은 스크립트가 무작위로 생성합니다. **운영을 시작한 뒤 `N8N_ENCRYPTION_KEY`를 바꾸면 저장된 n8n 자격 증명을 읽을 수 없으므로 변경하지 마세요.**

서버 시작:

```bash
docker compose --profile production up -d --build
docker compose ps
docker compose logs -f n8n video-worker
```

Caddy가 인증서를 발급하면:

- `https://N8N_HOST`: n8n 소유자 계정 생성·워크플로 관리
- `https://STUDIO_HOST`: `.env`의 `STUDIO_ACCESS_PASSWORD`로 유투봇 로그인

n8n 소유자 생성이 끝나면 `n8n-import`가 이를 감지해 `YouTube Shorts - 24x7 Create and Scheduled Upload` 워크플로를 한 번만 자동 import합니다. 안전을 위해 처음에는 unpublished 상태입니다.

```bash
docker compose logs -f n8n-import
```

### 갤럭시 앱으로 설치

1. 갤럭시의 Chrome 또는 Samsung Internet에서 `https://STUDIO_HOST`를 엽니다.
2. 상단 **앱 설치**를 누릅니다.
3. 설치 팝업이 없으면 브라우저 메뉴의 **앱 설치**를 선택합니다. 일반 `홈 화면에 바로가기`가 아니라 앱 설치 항목을 사용합니다.
4. 설치 후 앱 서랍/홈 화면의 `유투봇` 아이콘으로 독립 실행합니다.

이 PWA는 채팅·사진·설정·실행 상태를 관리하는 리모컨입니다. Android 절전 정책과 전원 종료 때문에 휴대폰 자체에서 24시간 렌더를 돌리지는 않습니다. **실제 자동화는 VPS에서 실행되므로 앱을 닫거나 갤럭시 전원을 꺼도 n8n workflow가 Published 상태인 한 계속됩니다.** PWA service worker는 화면 셸만 캐시하며 로그인·대화·사진·설정 API 응답은 캐시하지 않습니다.

## 2. Google 값의 정확한 구분

| 형태 | 정체 | 이 프로젝트에서 쓰는 곳 |
|---|---|---|
| `GOCSPX-...` | OAuth **Client Secret** | n8n YouTube OAuth 자격 증명에만 입력. Git/.env 금지 |
| `숫자-문자.apps.googleusercontent.com` | OAuth **Client ID** | n8n YouTube OAuth 자격 증명에 입력 |
| `AIza...` (보통 39자) | Google **API Key** | `.env`의 `GEMINI_API_KEY` / `YOUTUBE_DATA_API_KEY`; OAuth 업로드를 대신할 수 없음 |
| OAuth Refresh Token | 채널 장기 접근 토큰 | n8n이 암호화 저장. 직접 복사하거나 Git에 저장하지 않음 |

**YouTube 업로드는 API 키로 할 수 없고 OAuth 2.0이 필수**입니다. 반대로 Gemini 대본 생성에는 OAuth Client ID/Secret이 아니라 `AIza...` API 키가 필요합니다.

### 발급 직전 공식 페이지 3종

| 순서 | 용도 | 바로가기 | 저장 위치 |
|---|---|---|---|
| ① | Gemini 대본·사진·유투봇 | [Google AI Studio API Keys](https://aistudio.google.com/app/apikey) | VPS `.env`의 `GEMINI_API_KEY` |
| ② | YouTube 채널·영상 통계 | [YouTube Data API v3 활성화](https://console.cloud.google.com/apis/library/youtube.googleapis.com) → [API 키 생성](https://console.cloud.google.com/apis/credentials) | VPS `.env`의 `YOUTUBE_DATA_API_KEY` |
| ③ | 실제 채널 업로드·예약 공개 | [OAuth 동의 화면](https://console.cloud.google.com/auth/overview) → [OAuth Client 생성](https://console.cloud.google.com/auth/clients/create) | n8n `YouTube OAuth2 API` credential |

③은 한 종류의 업로드 자격 증명이지만 실제로는 `Client ID`와 `Client Secret` 두 값이 발급됩니다. OAuth Application type은 **Web application**을 고르고, Redirect URI는 n8n credential 화면에 표시된 값을 그대로 넣습니다. Google Cloud 링크는 먼저 올바른 프로젝트를 선택해야 합니다.

자세한 재발급 및 연결 절차: [`docs/GOOGLE_OAUTH_KO.md`](./docs/GOOGLE_OAUTH_KO.md)

## 3. n8n에서 최초 1회 연결

### 3-1. 내부 video worker 인증

1. VPS에서 `.env`의 `VIDEO_WORKER_TOKEN` 값을 확인합니다. 화면 공유·채팅·Git에는 복사하지 마세요.
2. n8n **Credentials → Add credential → Header Auth**를 엽니다.
3. Header Name은 정확히 `X-Worker-Token`, Value는 위 token 값으로 저장합니다.
4. 워크플로의 `Load Automation Config`, `Render Video`, `Download MP4`, `Mark Uploaded (Idempotency)` 네 노드에 같은 Header Auth credential을 선택합니다.

n8n에는 worker token을 환경 변수로 노출하지 않고 encrypted credential로만 저장하며, workflow의 임의 환경 변수 접근도 차단했습니다.

### 3-2. YouTube OAuth

1. Google Cloud에서 기존에 노출된 OAuth 클라이언트를 폐기하고 새 **Web application** OAuth 클라이언트를 만듭니다.
2. YouTube Data API v3를 활성화합니다.
3. 승인된 리디렉션 URI에 n8n이 보여 주는 주소를 그대로 추가합니다. 일반적으로:
   `https://n8n.example.com/rest/oauth2-credential/callback`
4. n8n 워크플로에서 `Upload + Schedule on YouTube` 노드를 엽니다.
5. 새 `YouTube OAuth2 API` credential을 만들고 **새 Client ID / 새 Client Secret**을 입력합니다.
6. `Sign in with Google`로 실제 업로드할 YouTube 채널을 승인합니다.
7. 노드에 그 credential을 선택하고 저장합니다.

## 4. 유투봇 사용

`https://STUDIO_HOST`의 **유투봇 AI** 탭에서 다음을 사용할 수 있습니다.

- 대화방을 계속 만들고 서버에 영구 저장, JSON 내보내기 또는 완전 삭제
- JPEG/PNG/WEBP 사진 최대 5장씩 업로드·분석(서버에서 EXIF 제거 후 JPEG로 정규화)
- 내 채널 주소와 벤치마킹 채널 주소 입력
- 양쪽 영상 주소를 각각 **0~15개 선택 입력**; 비우면 각 채널의 최신 15개 자동 수집
- 실제 구독자/조회수/좋아요/댓글/게시일/영상 길이를 근거로 비교
- 제목·설명·대본·콘텐츠 전략·n8n 설정 수정안 요청
- 봇이 제안한 자동화 설정은 사용자가 **검토 후 적용**을 눌러야 저장

대화 전체는 삭제 전까지 저장되지만 Gemini에 매번 전송하는 문맥은 비용·성능을 위해 최근 `CHAT_HISTORY_MESSAGES`개(기본 40개)입니다. 업로드 사진도 대화 삭제 시 같이 삭제됩니다.

## 5. 주제와 지정 시간 변경

유투봇 탭의 **n8n 자동화 설정**에서 바꿉니다. n8n은 매 실행마다 worker에서 최신 설정을 읽습니다.

| 필드 | 기본값 | 의미 |
|---|---:|---|
| `topicPool` | AI/스마트폰/유튜브 등 | 쉼표로 나눈 주제를 날짜별 순환 |
| `timezone` | `Asia/Seoul` | 게시 시간대 |
| `publishHour` | `18` | 공개 시각(0~23시) |
| `publishMinute` | `0` | 공개 분 |
| `minimumLeadMinutes` | `120` | 업로드·처리용 최소 여유 시간 |
| `durationSeconds` | `45` | 목표 영상 길이, 최대값은 `.env`에서 제한 |
| `channelKey` | `main` | 중복 방지용 채널 구분값 |

제작 시작 시각만 n8n의 `Daily 03:00 KST` Schedule Trigger에서 바꿉니다. **제작 시작은 게시 시각보다 최소 2시간 빠르게** 두는 것이 안전합니다.

## 6. 활성화 전 검증

1. 워크플로에서 `Manual Test`로 한 번 실행합니다.
2. 실행 결과가 모든 노드에서 성공인지 확인합니다.
3. YouTube Studio에서 영상이 **비공개·예약 상태**이고 제목/음성/자막/게시 시각이 맞는지 확인합니다.
4. 아동용 여부, 합성 콘텐츠 공개, 저작권·Pexels 라이선스, 채널 정책을 직접 확인합니다.
5. 문제가 없을 때만 n8n 우측 상단에서 **Publish/Active**로 전환합니다.
6. 폰과 PC를 끈 뒤 다음 실행 기록이 서버에서 생성되는지 확인합니다.

## 운영 명령

```bash
# 상태
docker compose ps

# 최근 로그
docker compose logs --tail=200 n8n video-worker postgres caddy

# 재시작
docker compose restart n8n video-worker

# 안전한 업데이트 전 백업
docker compose exec -T postgres pg_dump -U n8n n8n | gzip > n8n-$(date +%F).sql.gz

# 종료(데이터 볼륨은 유지)
docker compose --profile production down
```

운영·복구 상세: [`docs/OPERATIONS_KO.md`](./docs/OPERATIONS_KO.md)

## 중요한 제한

- “무제한·평생”은 서비스 약속으로 보장할 수 없습니다. 앱에는 메시지 횟수/자동 만료 제한을 두지 않았지만 VPS 디스크, 백업, 도메인, Gemini 비용·rate limit, YouTube quota는 계속 필요합니다.
- 채팅 데이터와 사진은 `video_data` Docker volume에 있으므로 그 볼륨을 백업하지 않으면 서버 장애 때 잃을 수 있습니다.
- 기본 YouTube Data API 할당량에서는 조회와 업로드 수가 제한됩니다. 대량 업로드용 구성이 아닙니다.
- 신규/미감사 API 프로젝트의 API 업로드는 YouTube 정책에 따라 **비공개로 잠길 수 있습니다**. 공개 예약 운영 전 YouTube API Services 감사를 확인하세요.
- Google OAuth 동의 화면을 `Testing`으로 두면 외부 앱의 refresh token이 짧게 만료될 수 있습니다. 장기 무인 운영 전에 앱 게시 상태와 검증 요건을 확인하세요.
- AI가 만든 대본도 사실 오류, 반복 콘텐츠, 스팸 또는 저작권 문제가 생길 수 있습니다. 완전 자동 게시를 활성화하는 책임은 채널 소유자에게 있습니다.
- Edge TTS는 간편 기본값입니다. 상업 서비스 수준의 SLA가 필요하면 `.env`에서 `TTS_PROVIDER=google`과 Google Cloud TTS 키를 설정하세요.
- 서버가 완전히 중단되면 n8n Schedule Trigger도 실행되지 않습니다. VPS 모니터링과 백업이 필요합니다.

## 개발 검증

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r worker/requirements-dev.txt
PYTHONPATH=worker pytest -q worker/tests
ruff check worker/app worker/tests

docker compose config
```

보안상 실제 `.env`, OAuth secret, refresh token, 렌더된 MP4는 모두 Git에서 제외됩니다.
