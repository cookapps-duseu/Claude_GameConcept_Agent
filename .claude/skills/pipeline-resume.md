---
description: 중단된 파이프라인을 output/session.json에서 읽어 이어서 실행한다.
---

# pipeline-resume 스킬

중단된 게임 컨셉 파이프라인을 재개한다.

## 실행 방법

1. `output/session.json`을 Read 툴로 읽는다.
   없으면 오류 메시지 출력 후 종료:
   ```
   output/session.json이 없습니다. 재개할 파이프라인이 없습니다.
   pipeline 스킬을 처음부터 실행하세요.
   ```

2. session.json에서 `completed_steps` 목록을 확인한다.

3. 현재 상태 요약 출력:
   ```
   [파이프라인 재개]
   완료된 단계: {completed_steps}
   
   이어서 실행할까요? (y/n)
   ```

4. y이면 → `pipeline` 스킬을 실행한다 (session.json의 completed_steps를 활용해 완료된 단계는 건너뜀)
5. n이면 → 종료
