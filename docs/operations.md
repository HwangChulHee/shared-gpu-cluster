# 실습 운영·비용·안전 원칙

## 비용 통제

- 로컬에서 설명·설계·컨테이너 빌드·GPU가 불필요한 K8s 시험을 먼저 수행
- AWS GPU 테스트 전에 **계정 GPU 인스턴스 쿼터 / 지역·AZ 가용성 / 온디맨드 단가 / 가동 시간**을 확인
- GPU 실험을 한 세션으로 묶어 가동하고, 충분한 로그·메트릭을 저장한 뒤 제거
- EKS Control Plane, CPU 노드, EBS, EFS, NAT Gateway, Load Balancer, Public IPv4, 데이터 전송 등 GPU 정지 이후에도 발생할 수 있는 비용 확인
- Terraform `destroy` 이후 EC2, EKS, ENI, EBS, EFS, NAT, LB, IP, CloudWatch 및 기타 잔여 과금 자원 점검
- 가격은 프로젝트 초기부터 고정 수치로 기재하지 않고 각 세션의 리전·가격·시간·사용량을 기록
- 체크포인트/모델 파일 등 보존이 필요한 결과물은 별도 비용과 삭제 정책 결정

## GPU 실행 환경

- 클라우드 GPU VM에서 OS/드라이버/Toolkit/Device Plugin 버전·구성 기록
- NVIDIA GPU Operator 사용 여부는 EKS AMI의 기설치 컴포넌트와 중복 가능성을 먼저 판단
- GPU Operator와 Device Plugin을 함께 중복 관리하는 구성을 무비판적으로 적용하지 않음
- 이미지·모델·데이터셋 버전 및 라이선스 확인
- 온디맨드 GPU를 이용하더라도 해당 AZ의 일시적 용량 부족은 가능하므로 사전 확인

## 보안 및 사용자 시연

- UI에서 Gemma 질의, YOLO 데이터셋/epoch, XGBoost 데이터셋 등 **제한된 입력만** 허용
- FastAPI 백엔드는 사용자·팀별 허용된 작업 및 파라미터를 서버 측 검증
- Kubernetes API 접근은 전용 ServiceAccount + 최소 RBAC
- 임의 이미지/커맨드 실행, 무제한 업로드, 공개 비밀키/토큰 커밋 금지
- 시연용 사용자·부서 선택은 실 사용자 인증/인가와 구분하여 문서화
- 테스트 데이터는 공개·합성 데이터셋 사용, 개인정보/비밀 데이터 제외

## 장애 실험 원칙

- 사용자 트래픽이 없는 격리된 실습 환경에서 수행
- 실제 클라우드 하드웨어 고장, Xid 오류를 강제로 유도하거나 드라이버를 파괴하지 않음
- 장애 전/후 정상 기준선과 영향 범위 확인
- 노드 교체, Pod/Job 재실행, 체크포인트 복구, 서비스 가용성을 분리 검증
- 모든 조치는 로그와 스크립트로 기록하고 인프라 비용과 리소스 누수 확인

## 단계별 산출물

- **Lab Notes**: 목적, 핵심 개념, 내부 흐름, 서술형 질문, 명령어, 실습 관측
- **Infrastructure**: Terraform, K8s 매니페스트, 설정 및 버전
- **Workloads**: Gemma 4, YOLO, XGBoost 실행 코드/이미지/테스트 입력
- **Experiments**: 반복 가능한 테스트 시나리오와 실측 결과
- **Operations**: Incident Report, RCA, Runbook, 사후 개선
- **Summary**: 실제 구현·미구현·제약을 구분한 README

완료된 시험 증거가 확보되기 전에는 설계상 기대 동작을 결과처럼 표시하지 않습니다.
