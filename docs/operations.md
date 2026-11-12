# GPU 실습 운영·비용·안전 원칙

## 실행 전 비용 게이트

- [ ] AWS 리전·GPU vCPU 쿼터 승인 및 실제 AZ 용량·인스턴스 가격 확인
- [ ] YOLO/데이터셋·컨테이너/AMI·Driver 버전과 라이선스 확인
- [ ] G1/G2에 필요한 GPU, EKS Control Plane, CPU 노드, EBS, S3, NAT/VPC Endpoint, LB, IPv4, 데이터 전송, CloudWatch 예상 비용 계산
- [ ] Terraform plan, 생성 자원, 삭제 경로, 실습 예상 가동 시간 확인
- [ ] 실험 명령/검증 체크리스트/결과 보존 경로 준비
- [ ] 실험 종료: 결과 저장 → 리소스 제거 → EC2/EKS/EBS/NAT/LB/ENI/IP/CloudWatch/S3 잔여 비용 확인

GPU 계열 증액 요청은 제출되었으나 **승인되었다고 기록하지 않는다**. 실측한 값만 결과로 사용한다. 비용 줄이기 위해 L 이론·코드 준비를 먼저 끝낸 다음 G1 세션, G2 세션을 묶어 실행한다.

## GPU 구성

- G1은 **호스트 Driver → Docker/Container Toolkit → CUDA 컨테이너 → YOLO** 순서로 확인; 이때 Device Plugin은 필요하지 않음.
- G2는 실제 GPU Worker에서 Driver/Toolkit과 Kubernetes Device Plugin의 책임을 나누어 검증.
- GPU EKS 최적화 AMI 또는 Operator 사용 시 이미 탑재된 드라이버·런타임 구성요소 중복 설치 금지.
- `Node Ready`, GPU Capacity, 컨테이너 CUDA 성공, YOLO 학습 성공은 서로 다른 단계의 증거.
- 리전/AMI/패키지 호환성은 실습 직전 공식 자료와 실제 환경으로 확인한다.

## YOLO 및 데이터

- 공개 또는 합성 이미지 데이터 사용; 사람·개인정보/민감 데이터 배제 또는 적법한 라이선스 확인.
- 데이터 버전, 모델 버전, seed, Batch, Epoch, CPU worker 수, GPU 메모리, 캐시(콜드/웜) 상태 고정.
- Checkpoint 생성·복원은 YOLO 작업의 책임. 플랫폼은 적절한 종료/재실행 정책과 외부 저장소 접근을 제공할 뿐 자동 저장을 보장하지 않음.
- S3/EBS/로컬 캐시 차이를 주장할 때 접근 방식이 실제로 가능한지 먼저 검증한다. 이미지 개별 객체 S3 요청과 로컬 파일 읽기는 동일 조건이 아님.

## 장애 주입 안전

- 격리된 테스트 환경에서 사전 동의된 리소스에만 장애 주입; 기존 자원 손상 최소화.
- 실제 GPU 하드웨어, Xid, Driver를 무리하게 고장 내지 않음. Device Plugin 미등록/설정 이슈는 안전하게 관측·원복.
- Node 중단 시 남은 GPU 용량이 부족하면 Job은 계속 Pending일 수 있음.
- 자연 발생 사고, 기술 문서의 잠재 문제, **우리가 만든 통제 실험**을 구분.
- 매 실험은 정상 기준선 → 입력/조건 변경 → 실제 로그·메트릭 → 복원 → RCA/한계 기록.

## 산출물

Terraform / 버전 고정된 YOLO 실행 환경 / GPU·노드·Job 메트릭 / 실험 비교표 / 운영 Runbook·RCA / 비용·삭제 기록. **UI·FastAPI·Gemma·XGBoost·Slurm·MIG는 필수 범위 제외**.
