# 달러 환율 나침반

원/달러 환율과 달러지수를 이용해 달러 투자 환경을 점검하고, 원화/달러 스위칭 전략을 백테스트하는 Streamlit 앱입니다.

## 로컬 실행

```powershell
& "C:\Users\Jason\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pip install -r requirements.txt
& "C:\Users\Jason\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m streamlit run app.py
```

현재 PC의 기본 `python`이 32비트 Anaconda일 수 있어 Streamlit 의존성 설치가 실패할 수 있습니다. 위처럼 Codex 번들 Python 3.12 64비트 경로를 명시하면 로컬 테스트가 안정적입니다.

## CSV 형식

현재 버전은 Yahoo Finance의 `KRW=X`, `DX-Y.NYB` 데이터를 사용합니다. 네트워크가 막힌 로컬 환경에서는 샘플 데이터로 자동 대체됩니다.

## 주요 기능

- 첫 화면에서 개요와 계산 화면을 버튼으로 선택합니다.
- 개요 화면은 최신 거래일 기준 4가지 조건을 판정합니다.
- 계산 화면은 거치식과 월 적립식 백테스트를 지원합니다.
- 일별 4조건 판정표와 원화/달러 스위칭 지점을 그래프로 확인할 수 있습니다.
