# Bible RAG

시맨틱 검색 기반 다국어 성경 공부 플랫폼. 한국어/영어를 모두 지원하며, 원어(히브리어·헬라어·아람어) 분석을 통합합니다.

[English README](README.md)

---

## 개요

Bible RAG는 **검색 증강 생성(RAG, Retrieval-Augmented Generation)** 을 활용하여 성경 공부를 혁신하는 시스템입니다. 한국어나 영어로 자연어 질문을 입력하면 관련 성경 구절, 번역 비교, 원어 분석, AI 해석을 스트리밍으로 제공합니다.

---

## 주요 기능

### 채팅 인터페이스
멀티턴 대화 + AI 스트리밍 응답

```
"What does Jesus say about forgiveness?"
"용서에 대한 예수님의 말씀"
"요한복음에서 love에 대한 구절"   ← 코드 스위칭도 지원
```

### 10개 이상 번역본 지원
| 언어 | 번역본 |
|------|--------|
| 영어 | NIV, ESV, NASB, KJV, NKJV, NLT, WEB |
| 한국어 | 개역한글(KRV), 새번역(RNKSV), 개역개정(NKRV) |
| 원어 | 히브리어(구약), 헬라어(신약), 아람어 |

> API 키 불필요 — 모두 무료 API 사용

### 하이브리드 검색 파이프라인

```
쿼리
  → LLM 쿼리 확장 (동의어·관련어 생성)
  → 임베딩 생성 (multilingual-e5-large, 1024차원)
  → 벡터 검색 (pgvector 코사인 유사도)
    + 전문 검색 (PostgreSQL tsvector)
  → RRF 결합 (Reciprocal Rank Fusion)
  → 크로스 인코더 리랭킹 (BAAI/bge-reranker-v2-m3, top-30)
  → LLM 응답 생성 (Gemini 2.5 Flash → Groq Llama 3.3 70B 폴백)
```

### 원어 통합 (442,413 단어 수록)

| 언어 | 수록 단어 | 구절 수 | Strong's 커버리지 | 출처 |
|------|----------|--------|----------------|------|
| 헬라어(신약) | 137,500 | 7,957 | 99.9% | OpenGNT |
| 히브리어(구약) | 299,487 | ~23,145 | 98.1% | OSHB/WLC |
| 아람어 | 4,913 | ~68 | 98.0% | OSHB/WLC |
| **합계** | **442,413** | **~31,170** | **98.3%** | — |

- Strong's 번호(G1–G5624 헬라어, H1–H8674 히브리어/아람어)
- 형태소 분석 (시제·태·서법·격·성·수)
- 음역(transliteration) 및 발음 가이드
- 단어별 인터리니어(interlinear) 분석
- Strong's 번호 → Blue Letter Bible 링크

### 한국어 특화 기능
- **한자(漢字) 표시**: 신학 용어 한자 병기
- **로마자 표기**: `aromanize` 라이브러리 활용
- **최적화 폰트**: Noto Sans KR
- **경어 처리**: 존댓말 자연어 처리

```
속죄 (sokjoe) = Atonement = כָּפַר (kaphar, H3722)
구원 (guwon) = Salvation = σωτηρία (soteria, G4991)
은혜 (eunhye) = Grace = χάρις (charis, G5485)
```

### 그 외 기능
- **번역 비교**: 여러 번역본 나란히 보기
- **교차 참조**: 관련 구절 자동 연결 (인용·평행·암시·주제별)
- **문맥 확장**: 검색 결과 ±2절 인라인 확장
- **인라인 인용**: AI 응답 내 구절 참조(예: "요한복음 3:16")를 클릭 가능한 카드로 자동 변환
- **사용자 API 키**: Gemini/Groq 키 직접 등록 (서버에 저장되지 않음)
- **다크 모드**: 시스템 테마 자동 연동

---

## 기술 스택

### 백엔드
| 항목 | 기술 |
|------|------|
| 웹 프레임워크 | FastAPI (Python 3.12+), 비동기 스트리밍 NDJSON |
| 데이터베이스 | PostgreSQL 16 + pgvector (ivfflat 인덱스) |
| 캐싱 | Redis 7 (24시간 TTL, MD5 정규화 키) |
| 임베딩 모델 | multilingual-e5-large (1024차원, 자체 호스팅) |
| 리랭커 | BAAI/bge-reranker-v2-m3 (크로스 인코더) |
| 주 LLM | Google Gemini 2.5 Flash |
| 폴백 LLM | Groq Llama 3.3 70B |
| ORM | SQLAlchemy 2.0 (비동기) |

### 프론트엔드
| 항목 | 기술 |
|------|------|
| 프레임워크 | Next.js 15 (App Router) |
| UI 라이브러리 | React 19 |
| 타입 | TypeScript 5.7 |
| 스타일링 | Tailwind CSS 3 |
| 한국어 폰트 | Noto Sans KR |
| 로마자 표기 | aromanize |

### 인프라
| 환경 | 구성 |
|------|------|
| 로컬 개발 | Docker Compose (PostgreSQL + Redis) |
| 프론트엔드 | Vercel |
| 백엔드/DB | Railway / Supabase |
| CI/CD | GitHub Actions |

---

## 빠른 시작

### 사전 요구사항
- Python 3.12+
- Node.js 22 LTS (또는 20 LTS)
- Docker & Docker Compose
- RAM 8GB 이상 (임베딩 모델 + 리랭커 실행을 위해 16GB 권장)

### 로컬 개발 환경 설정

**1. 저장소 클론**
```bash
git clone https://github.com/calebyhan/bible-rag.git
cd bible-rag
```

**2. 로컬 인프라 시작**
```bash
docker-compose up -d   # PostgreSQL + Redis 실행
```

**3. 백엔드 설정**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # 환경 변수 설정

# 성경 데이터 수집 (9개 번역본 자동 다운로드, 약 90분)
python scripts/data_ingestion.py

# 원어 데이터 수집 (히브리어·헬라어·아람어, 약 1분)
python scripts/original_ingestion.py

# 임베딩 생성 (최초 1회, 약 15~30분)
python scripts/embeddings.py

# API 서버 실행
uvicorn main:app --reload        # http://localhost:8000
```

**4. 프론트엔드 설정**
```bash
cd ../frontend
npm install
cp .env.example .env.local       # 환경 변수 설정
npm run dev                      # http://localhost:3000
```

**5. 앱 접속**  
브라우저에서 [http://localhost:3000](http://localhost:3000) 열기

---

## 검색 예시

### 한국어 시맨틱 검색
```
"사랑에 대한 예수님의 가르침"
"믿음에 관한 성경 구절"
"바울이 은혜에 대해 말한 것"
```

### 영어 시맨틱 검색
```
"Jesus teaching about love"
"Where does the Bible talk about faith?"
"What did Paul say about grace?"
```

### 혼합 언어 검색 (코드 스위칭)
```
"요한복음에서 love에 대한 구절"
"Genesis의 creation story"
```

---

## 성능

| 항목 | 수치 |
|------|------|
| 검색 응답 시간 | < 2초 (초기), < 500ms (캐시 히트) |
| 리랭킹 추가 지연 | 50~200ms (top-30 후보 대상) |
| 임베딩 생성 | 약 15~30분 (전체 성경 ~31,000절, 최초 1회) |
| 캐시 구현 | Redis + MD5 정규화 키 (번역본 정렬, 소문자 정규화) |
| 벡터 검색 | pgvector ivfflat 인덱스 (코사인 유사도) |

---

## 프로젝트 구조

```
bible-rag/
├── backend/                       # FastAPI 백엔드
│   ├── main.py                    # API 진입점, CORS, 라우터 등록
│   ├── config.py                  # Pydantic 설정 (환경 변수 50+)
│   ├── database.py                # SQLAlchemy 비동기 모델 + 연결
│   ├── search.py                  # 하이브리드 검색: 벡터 + FTS → RRF → 리랭킹
│   ├── embeddings.py              # multilingual-e5-large 임베딩 래퍼
│   ├── reranker.py                # BAAI/bge-reranker-v2-m3 크로스 인코더
│   ├── llm.py                     # Gemini(주) / Groq(폴백) LLM 핸들러
│   ├── llm_batcher.py             # LLM 배치 요청 누산기
│   ├── cache.py                   # Redis 캐싱 레이어
│   ├── original_language.py       # Strong's 사전 통합
│   ├── cross_references.py        # 구절 교차 참조 연결
│   ├── schemas.py                 # Pydantic 요청/응답 모델
│   ├── routers/
│   │   ├── search.py              # POST /api/search (스트리밍 NDJSON)
│   │   ├── verses.py              # GET /api/verse, /api/chapter, /api/strongs
│   │   ├── themes.py              # POST /api/themes
│   │   ├── metadata.py            # GET /api/translations, /api/books
│   │   └── health.py              # GET /health
│   ├── scripts/
│   │   ├── data_ingestion.py      # 성경 텍스트 수집 (9개 번역본)
│   │   ├── embeddings.py          # 임베딩 생성
│   │   ├── original_ingestion.py  # 원어 데이터 수집
│   │   └── fetch_nkrv.py          # 개역개정 크롤러
│   └── tests/                     # 테스트 스위트 (54개, 커버리지 90%+)
│
├── frontend/                      # Next.js 15 프론트엔드
│   └── src/
│       ├── app/                   # App Router 페이지
│       │   ├── page.tsx           # 홈/채팅 (메인 검색 인터페이스)
│       │   ├── browse/            # 성경 탐색
│       │   ├── compare/           # 번역본 비교
│       │   ├── themes/            # 주제별 검색
│       │   └── verse/[...]/       # 구절 상세
│       ├── components/            # React 컴포넌트
│       └── lib/
│           ├── api.ts             # 타입 지정 API 클라이언트 (스트리밍 포함)
│           └── verseParser.tsx    # 인라인 구절 인용 파서
│
├── docs/                          # 상세 문서
│   ├── ARCHITECTURE.md            # 시스템 설계
│   ├── DATABASE.md                # DB 스키마 및 인덱싱
│   ├── API.md                     # API 레퍼런스
│   ├── SETUP.md                   # 상세 설정 가이드
│   ├── DEPLOYMENT.md              # 프로덕션 배포 가이드
│   ├── FEATURES.md                # 기능 문서
│   ├── KOREAN.md                  # 한국어 구현 상세
│   └── DATA_SOURCES.md            # 데이터 출처 및 라이선스
│
├── docker-compose.yml             # 로컬 개발 환경 (PostgreSQL + Redis)
└── README.md                      # 영문 README
```

---

## 라이선스

MIT License — 자세한 내용은 [LICENSE](LICENSE) 파일 참조

## 감사의 말

**성경 번역본**
- [Bolls.life API](https://bolls.life) — NIV, ESV, NASB, KRV 등 100개 이상 번역본 무료 제공
- [GetBible API](https://get.bible) — 퍼블릭 도메인 번역본 (KJV, WEB, RKV)
- [SIR.kr 커뮤니티](https://sir.kr) — 개역개정(NKRV) MySQL DB
- 대한성서공회 — 한국어 번역본 저작권자

**원어 데이터**
- [OpenGNT](https://github.com/eliranwong/OpenGNT) — Strong's 번호 포함 헬라어 신약 (CC BY 4.0)
- [OSHB](https://github.com/openscriptures/morphhb) — 오픈 스크립처스 히브리어 성경 (CC BY 4.0)
- [OpenScriptures Strong's](https://github.com/openscriptures/strongs) — Strong's 사전 (Public Domain)

**기타**
- [OpenBible.info](https://openbible.info) — 63,779개 이상 구절 교차 참조 (CC BY 4.0)
- [intfloat/multilingual-e5-large](https://huggingface.co/intfloat/multilingual-e5-large) — 임베딩 모델
- [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) — 리랭킹 모델
- Google Gemini 2.5 Flash (주 LLM), Groq Llama 3.3 70B (폴백 LLM)
