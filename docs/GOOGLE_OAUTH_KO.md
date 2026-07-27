# Google OAuth / API 키 설정

## 공식 발급 바로가기

1. **Gemini API 키**: [AI Studio API Keys](https://aistudio.google.com/app/apikey)
2. **YouTube Data API 키**: [API 활성화](https://console.cloud.google.com/apis/library/youtube.googleapis.com) → [Credentials / API key 생성](https://console.cloud.google.com/apis/credentials)
3. **YouTube 업로드 OAuth**: [동의 화면](https://console.cloud.google.com/auth/overview) → [OAuth Client 생성](https://console.cloud.google.com/auth/clients/create)

Google Cloud 링크에서는 먼저 같은 프로젝트를 선택하세요. 3번은 Web application으로 만들고 n8n이 표시하는 OAuth Redirect URL을 Authorized redirect URI에 그대로 등록합니다.

## 0. 노출된 값 먼저 폐기

채팅, 이슈, 커밋, 화면 공유에 한 번이라도 공개된 `GOCSPX-...` Client Secret은 더 이상 안전하지 않습니다.

1. [Google Cloud Console — 사용자 인증 정보](https://console.cloud.google.com/apis/credentials)로 이동합니다.
2. 올바른 프로젝트를 선택합니다.
3. 노출된 OAuth 2.0 클라이언트를 삭제하거나 secret을 재설정합니다.
4. n8n에는 **새로 만든 값만** 연결합니다.
5. 예전 값을 `.env`, workflow JSON, GitHub Actions Secret에 다시 넣지 않습니다.

Client ID는 본질적으로 공개 식별자이지만 Client Secret과 함께 노출됐다면 새 OAuth 클라이언트로 교체하는 편이 안전합니다.

## 1. YouTube API 활성화

1. [API 라이브러리](https://console.cloud.google.com/apis/library)에서 프로젝트를 선택합니다.
2. `YouTube Data API v3`를 검색해 **사용**으로 전환합니다.
3. [OAuth 동의 화면](https://console.cloud.google.com/auth/overview)을 구성합니다.
4. 외부 앱이라면 실제 채널 Google 계정을 테스트 사용자로 먼저 등록합니다.
5. 장기 무인 운영 전 게시 상태, 검증, YouTube API Services 감사를 확인합니다.

공식 자료:

- [n8n Google OAuth2 single service](https://docs.n8n.io/integrations/builtin/credentials/google/oauth-single-service/)
- [YouTube Data API OAuth 2.0](https://developers.google.com/youtube/v3/guides/authentication)
- [YouTube API Services Audit and Quota Extension](https://support.google.com/youtube/contact/yt_api_form)

## 2. 새 OAuth 클라이언트 생성

1. **APIs & Services → Credentials → Create credentials → OAuth client ID**를 선택합니다.
2. Application type은 **Web application**입니다.
3. n8n에서 YouTube OAuth credential 생성 화면을 열어 **OAuth Redirect URL**을 복사합니다.
4. Google의 **Authorized redirect URIs**에 한 글자도 바꾸지 않고 붙여넣습니다.

일반적인 self-hosted 주소:

```text
https://n8n.example.com/rest/oauth2-credential/callback
```

다음은 서로 다른 값입니다.

```text
Client ID:     숫자-무작위문자.apps.googleusercontent.com
Client Secret: GOCSPX-무작위문자
```

이 둘은 Gemini API 키가 아닙니다.

## 3. n8n에 안전하게 저장

1. n8n의 `YouTube Shorts - 24x7 Create and Scheduled Upload` 워크플로를 엽니다.
2. `Upload + Schedule on YouTube` 노드를 엽니다.
3. Credential → **Create New → YouTube OAuth2 API**를 선택합니다.
4. 새 Client ID와 새 Client Secret을 credential 폼에 입력합니다.
5. **Sign in with Google**을 눌러 업로드 대상 채널 계정으로 승인합니다.
6. 저장 후 해당 credential을 YouTube 노드에 선택합니다.

n8n은 OAuth access/refresh token을 PostgreSQL에 저장하며, `N8N_ENCRYPTION_KEY`로 암호화합니다. 따라서:

- `N8N_ENCRYPTION_KEY`를 Git에 올리지 않습니다.
- 운영 시작 뒤 encryption key를 임의로 바꾸지 않습니다.
- DB 백업과 encryption key의 안전한 별도 백업이 모두 필요합니다.
- Google OAuth 값을 workflow의 Set/Code 노드에 직접 적지 않습니다.

## 4. 실제 Gemini API 키 만들기

AI 대본 생성에는 [Google AI Studio](https://aistudio.google.com/apikey)에서 발급한 별도 API 키를 사용합니다.

일반적인 형태:

```text
AIza...................................
```

VPS의 `.env`에만 넣습니다.

```dotenv
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.5-flash
```

운영용 Gemini 키와 YouTube 조회 키는 **서로 다른 키**로 만드는 것을 권장합니다.

```dotenv
GEMINI_API_KEY=AIza...        # 대본·유투봇 멀티모달
YOUTUBE_DATA_API_KEY=AIza...  # 유투봇 채널/영상 통계
```

- Gemini 서버 키: Generative Language API로 API 제한을 걸고 `.env`에만 저장
- 유투봇 YouTube 서버 키: YouTube Data API v3로 제한하고 `.env`에만 저장
- 정적 Pages 조회 키를 따로 쓸 경우: YouTube Data API v3 및 실제 Pages 도메인 HTTP referrer로 제한
- OAuth Client Secret: API 키 제한 화면이 아니라 n8n encrypted credential에만 저장

적용:

```bash
docker compose up -d --build video-worker
docker compose exec video-worker python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"
```

응답의 `geminiConfigured`, `youtubeDataConfigured`가 모두 `true`여야 유투봇의 AI·채널 비교 기능이 완전히 동작합니다.

## 5. 예약 게시 조건

워크플로는 영상 업로드 시 다음 값을 보냅니다.

- `privacyStatus = private`
- `publishAt = 미래 ISO 8601 시각`
- `selfDeclaredMadeForKids = false` (채널 성격에 맞지 않으면 반드시 수정)

YouTube 예약 공개는 비공개 영상에 미래 `publishAt`을 설정하는 방식입니다. API 프로젝트가 감사되지 않은 경우 API 업로드가 private 상태로 잠길 수 있으므로, 첫 테스트에서 반드시 YouTube Studio의 예약 상태를 확인하세요.

## 6. 자주 발생하는 오류

### `redirect_uri_mismatch`

Google Cloud의 Authorized redirect URI와 n8n credential 화면의 Redirect URL이 다릅니다. 프로토콜(`https`), 호스트, 경로, 끝의 slash까지 그대로 맞춥니다. `.env`의 `N8N_HOST`, `N8N_PROTOCOL`, `WEBHOOK_URL`도 확인합니다.

### `access_denied` 또는 테스트 사용자 오류

OAuth 동의 화면이 Testing이면 로그인할 Google 계정을 Test users에 추가합니다.

### 업로드는 됐지만 계속 비공개

`publishAt`이 미래인지, 업로드 당시 privacy가 private인지, YouTube Studio에 예약 표시가 있는지, API 프로젝트 감사가 필요한지 확인합니다.

### 며칠 뒤 OAuth가 풀림

OAuth 동의 화면의 Testing 상태와 refresh token 만료 정책을 확인합니다. 장기 운영 요건을 충족한 뒤 Production으로 게시하고 필요한 검증/감사를 진행합니다.

### `quotaExceeded`

YouTube API 일일 할당량을 소진했습니다. 기본 할당량에서 영상 업로드는 비용이 큰 작업이므로 하루 여러 개를 무제한 업로드할 수 없습니다. 실행 빈도를 줄이거나 정식 quota extension을 신청합니다.
