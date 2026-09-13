# 달러 스위칭 백테스터

원화와 달러 사이를 오가는 분할 매수/분할 매도 전략을 환율 데이터로 테스트하는 Streamlit 앱입니다.

## 로컬 실행

```powershell
& "C:\Users\Jason\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pip install -r requirements.txt
& "C:\Users\Jason\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m streamlit run app.py
```

현재 PC의 기본 `python`이 32비트 Anaconda일 수 있어 Streamlit 의존성 설치가 실패할 수 있습니다. 위처럼 Codex 번들 Python 3.12 64비트 경로를 명시하면 로컬 테스트가 안정적입니다.

## CSV 형식

업로드 CSV에는 날짜 열과 환율 열이 필요합니다.

- 날짜 열: `date` 또는 `날짜`
- 환율 열: `rate`, `close`, `usdkrw`, `exchange_rate`, `환율`

예시:

```csv
date,rate
2024-01-02,1304.5
2024-01-03,1310.2
```

## 현재 전략 로직

- 기준 환율 이하에서 1차 매수합니다.
- 환율이 `추가 매수 간격`만큼 더 내려가면 다음 회차를 매수합니다.
- 각 매수 회차는 독립 포지션으로 관리합니다.
- 매수 환율 대비 목표 수익률과 수수료를 반영한 목표 환율에 도달하면 해당 회차만 매도합니다.
- 최종 평가금액은 원화 현금과 미청산 달러 평가액을 합산합니다.
