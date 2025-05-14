# 🚀 Project “그랬구나"

## 📌 프로젝트 개요

본 서비스 "**여봐라**"는 신기술인 MCP의 사용 설정의 어려움을 파악하고 이를 해결하여 일반 사용자도 사용할 수 있도록 허들을 낮추고 다양한 기능을 한 페이지에서 해결 할 수 있는 편의성 제공을 제공하는  **종합 MCP 플랫폼**입니다.
---

## 🛠 기술 스택

| 기술 | 설명 |
|------|------|
| ![React](https://img.shields.io/badge/React-19.0-blue?logo=react) | Vite 기반의 React 19.0 |
| ![TypeScript](https://img.shields.io/badge/TypeScript-✔-blue?logo=typescript) | 정적 타입 언어 |
| ![Redux](https://img.shields.io/badge/Redux-✔-purple?logo=redux) | 상태 관리 |
| ![TailwindCSS](https://img.shields.io/badge/TailwindCSS-✔-teal?logo=tailwindcss) | 스타일링 |
| ![ESLint](https://img.shields.io/badge/ESLint-✔-yellow?logo=eslint) | 코드 품질 관리 |
| ![Node.js ](https://img.shields.io/badge/Node.js-22.13.1-green?logo=node.js) | 런타임 환경 |
| ![npm](https://img.shields.io/badge/npm-10.9.2-red?logo=npm) | 패키지 매니저 |

---

## 📂 프로젝트 구조

```
📦 프로젝트 루트
├── 📂 src
│   ├── 📂 assets         # 🎨 정적 파일 (이미지, 폰트 등)
│   ├── 📂 components     # 🧩 재사용 가능한 UI 컴포넌트
│   ├── 📂 pages          # 📄 주요 페이지 컴포넌트
│   ├── 📂 store          # 📂 Redux 상태 관리 관련 파일
│   ├── 📂 hooks          # 🔗 커스텀 훅
│   ├── 📂 utils          # 🛠 유틸리티 함수 모음
│   ├── 📂 styles         # 🎨 Tailwind 관련 스타일 파일
│   ├── 📂 api            # 🔗 백엔드 API 요청 관련 함수
│   ├── 📂 router         # 🚦 React Router 관련 파일
│   ├── 📜 main.tsx       # 🚀 애플리케이션 진입점
│   ├── 📜 App.tsx        # 🏠 루트 컴포넌트
├── 📜 index.html         # 📝 기본 HTML 파일
├── 📜 package.json       # 📆 패키지 정보 및 스크립트
├── 📜 tsconfig.json      # ⚙ TypeScript 설정 파일
├── 📜 vite.config.ts     # ⚡ Vite 설정 파일
├── 📜 eslint.config.js   # 🛠 ESLint 설정 파일
└── ... 기타 설정 파일
```

---

## 🚀 설치 및 실행 방법

### 1️⃣ 프로젝트 클론
```sh
# git clone ""
# cd FE
# Git Lab 오픈 후 작성 될 예정
```

### 2️⃣ 패키지 설치
```sh
npm install
```

> 📌 `.npmrc`에서 `legacy-peer-deps=true`가 설정되어 있어 peer dependency 충돌을 자동으로 무시합니다.
> 이 설정은 다음과 같은 이유로 추가되었습니다:
>
> - `react-day-picker@8.x`가 `react@19`를 공식적으로 지원하지 않아 충돌 발생
> - `react-day-picker@8.x`가 `date-fns@4`를 지원하지 않아 충돌 발생
>
> 추후 라이브러리들이 React 19 및 date-fns 4를 공식적으로 지원하게 되면 `.npmrc`의 해당 옵션은 제거하는 것이 좋습니다.

### 3️⃣ 개발 서버 실행
```sh
npm run dev
```

---

## 🔧 ESLint 설정 확장

typescript 타입 체크를 활성화하려면 `eslint.config.js` 파일을 아래와 같이 설정합니다:

```js
import react from 'eslint-plugin-react';
export default tseslint.config({
  languageOptions: {
    parserOptions: {
      project: ['./tsconfig.node.json', './tsconfig.app.json'],
      tsconfigRootDir: import.meta.dirname,
    },
  },
  settings: { react: { version: '18.3' } },
  plugins: { react },
  rules: {
    ...react.configs.recommended.rules,
    ...react.configs['jsx-runtime'].rules,
  },
});
```

---

## 🎁 ShadCN UI 컴포넌트 추가 방법

이 프로젝트는 [shadcn/ui](https://ui.shadcn.dev/) 컴포넌트를 기반으로 UI를 구성할 수 있습니다.

### 📦 컴포넌트 추가 예시

버튼 컴포넌트를 추가하려면 아래 명령어를 실행합니다:
```sh
npx shadcn@latest add button
```

---

## ✅ TODO
- [ ] 🎤 소켓 소통 기능 구현
- [ ] 🔗 백엔드 API 연동
- [ ] 🎨 UI 디자인 및 스타일링
- [ ] 🧪 프로토타입 목업 고정
- [ ] 🧩 프로토타입 페이지 분리
- [ ] 🆕 프로토타입 페이지 생성

---

> 이 문서는 프로젝트 진행에 따라 계속 업데이트될 예정입니다! 🚀