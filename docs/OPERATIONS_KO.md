# 24시간 운영·복구 가이드

## 실제로 폰이 꺼져도 되는 조건

자동화는 폰이 아니라 VPS에서 실행됩니다. 아래 네 조건이 모두 충족돼야 합니다.

1. VPS가 켜져 있음
2. Docker daemon이 부팅 시 자동 시작됨
3. `n8n`, `postgres`, `video-worker`가 healthy/running 상태
4. n8n workflow가 **Published/Active** 상태

Ubuntu에서 Docker 자동 시작:

```bash
sudo systemctl enable --now docker
systemctl is-enabled docker
```

## 일일 확인

```bash
docker compose ps
docker compose logs --since=24h n8n video-worker | tail -300
```

정상 기준:

- `postgres`, `video-worker`, `n8n`, `caddy`가 Up/healthy
- `https://STUDIO_HOST/health`가 `status: ok`이고 유투봇 로그인 가능
- n8n Executions에 매일 03:00 실행이 Success
- YouTube Studio에 해당 날짜 영상이 비공개 예약으로 표시
- 게시 시각과 workflow timezone이 일치

외부 모니터링 서비스에서는 `https://N8N_HOST/healthz/readiness`를 5분 간격으로 확인하는 것을 권장합니다. n8n 편집기 자체는 인터넷에 공개되므로 강한 소유자 비밀번호와 최신 보안 업데이트를 유지하세요.

## 중복 방지 방식

worker는 다음 키를 영구 저장합니다.

```text
channelKey + 게시 날짜 기반 idempotencyKey
```

같은 날짜 작업이 다시 실행되면:

- 렌더 완료 전: 409로 동시 실행 차단
- 렌더 완료 후 업로드 전: 기존 MP4 재사용
- 업로드 완료 표시 후: `alreadyUploaded=true`를 반환해 YouTube 노드를 건너뜀

단, YouTube 업로드 성공 직후 `Mark Uploaded` 노드가 실행되기 전에 서버가 정확히 중단되면 드물게 중복 가능성이 있습니다. 실패 실행을 재시도하기 전 YouTube Studio에서 같은 제목·예약 시각 영상이 이미 있는지 확인하세요.

## 지정 시간을 놓쳤을 때

Schedule Trigger 시각에 n8n이 완전히 꺼져 있었다면 그 실행은 소급 실행되지 않습니다.

- 게시 시각까지 `minimumLeadMinutes` 이상 남음: Manual Test 실행 시 오늘 게시로 예약
- 남은 시간이 더 짧음: 안전을 위해 다음 날로 자동 예약
- 반드시 오늘 올려야 함: CONFIG의 게시 시각과 lead를 임시 조정하고 Manual Test 후 원래 값으로 복구

매일 작업을 놓치지 않으려면 VPS/컨테이너 외부 uptime 알림을 설정해야 합니다.

## 백업

### PostgreSQL

```bash
mkdir -p backups
docker compose exec -T postgres pg_dump -U n8n -Fc n8n \
  > backups/n8n-$(date -u +%Y%m%dT%H%M%SZ).dump
chmod 600 backups/*.dump
```

### 유투봇 대화·사진

대화 DB와 업로드 사진은 `video_data` volume의 `/data/studio.sqlite3`, `/data/chat-images`에 있습니다. 일관된 백업을 위해 worker를 잠시 멈춥니다.

```bash
mkdir -p backups/youtubot
docker compose stop video-worker
docker compose cp video-worker:/data/studio.sqlite3 backups/youtubot/studio.sqlite3
docker compose cp video-worker:/data/chat-images backups/youtubot/chat-images
docker compose start video-worker
tar -C backups -czf backups/youtubot-$(date -u +%Y%m%dT%H%M%SZ).tar.gz youtubot
rm -rf backups/youtubot
```

### 반드시 별도 보관할 값

- PostgreSQL dump
- 유투봇 `studio.sqlite3`와 `chat-images` 백업
- `.env`의 `N8N_ENCRYPTION_KEY`, `STUDIO_SESSION_SECRET`, 기타 secret
- 현재 `compose.yaml`과 workflow JSON 버전

DB만 있고 encryption key가 없으면 OAuth credential을 복호화할 수 없습니다. `.env` 전체에는 다른 secret도 있으므로 암호화된 비밀 저장소에 백업하고 일반 클라우드 드라이브나 Git에 올리지 마세요.

렌더된 MP4는 재생성 가능하므로 기본 백업 대상이 아닙니다.

## 복원

빈 서버에서 저장소와 원래 `.env`를 준비한 뒤:

```bash
docker compose up -d postgres
cat backups/n8n-TIMESTAMP.dump | \
  docker compose exec -T postgres pg_restore -U n8n -d n8n --clean --if-exists
docker compose --profile production up -d --build
```

유투봇 백업도 복원하려면 worker를 한 번 생성한 뒤 멈추고 파일을 되돌립니다.

```bash
docker compose up -d video-worker
docker compose stop video-worker
docker compose cp backups/youtubot/studio.sqlite3 video-worker:/data/studio.sqlite3
docker compose cp backups/youtubot/chat-images video-worker:/data/chat-images
docker compose run --rm --user root --entrypoint chown video-worker -R worker:worker /data
docker compose start video-worker
```

복원 후 유투봇 대화 목록, OAuth credential 연결 상태, workflow Published 상태를 확인하고 Manual Test를 수행합니다.

## 업데이트

n8n과 Caddy 이미지는 재현 가능한 버전으로 고정돼 있습니다. 무인 자동 업데이트 대신 다음 절차를 사용합니다.

1. DB와 `.env`를 백업합니다.
2. release note와 breaking changes를 확인합니다.
3. 별도 테스트 서버 또는 비게시 Manual Test로 검증합니다.
4. 이미지 태그를 명시적으로 변경합니다.
5. 다음을 실행합니다.

```bash
docker compose pull
docker compose --profile production up -d --build
docker compose ps
docker compose logs --since=10m n8n video-worker
```

## 디스크 정리

- worker MP4/MP3/자막: `VIDEO_RETENTION_DAYS`(기본 7일)
- 유투봇 대화/사진: 자동 만료 없음. UI에서 대화 삭제 시 함께 삭제
- n8n execution data: 168시간(7일)
- PostgreSQL과 Docker 로그: 호스트 정책에 따라 별도 관리

사용량 확인:

```bash
docker system df
docker compose exec postgres du -sh /var/lib/postgresql/data
docker compose exec video-worker du -sh /data
```

데이터 볼륨까지 삭제하는 `docker compose down -v`는 운영 중 사용하지 마세요.

## 장애별 점검

### worker가 unhealthy

```bash
docker compose logs --tail=300 video-worker
docker compose exec video-worker ffmpeg -version
docker compose exec video-worker fc-list | grep -i noto | head
```

Gemini key, TTS voice, API quota, 네트워크, 디스크 여유를 확인합니다.

### n8n이 unhealthy

```bash
docker compose logs --tail=300 n8n postgres
docker compose exec postgres pg_isready -U n8n -d n8n
```

`N8N_ENCRYPTION_KEY`를 예전 값과 다르게 바꾸지 않았는지 확인합니다.

### OAuth 오류

- Google Cloud의 redirect URI
- YouTube Data API v3 활성화
- OAuth 동의 화면 테스트 사용자/게시 상태
- n8n credential의 Connected 상태
- 새 secret으로 교체했는지 확인

### 영상 생성은 성공하지만 YouTube 업로드 실패

- YouTube 노드 Input Binary Field가 `data`인지 확인
- 다운로드 노드 binary MIME이 `video/mp4`인지 확인
- 채널 인증 계정과 quota 확인
- YouTube Studio에서 이미 업로드된 영상이 없는지 먼저 확인
- n8n execution 상세 오류를 확인
