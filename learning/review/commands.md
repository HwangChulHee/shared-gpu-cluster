# 운영 명령어 반복학습 — 명령어 사전

> 목적: 명령어 문법 암기보다 **언제 쓰는지 → 무엇을 측정하는지 → 한계 → 다음 확인**을 인출한다. GPU 없는 Linux/WSL에서 먼저 연습한다.
>
> [복습 기록·문제](review-log.md) · [전체 학습 진도](../progress.md)

## 복습 방식

1. 아래 '호출 상황'만 보고 명령어를 떠올린다.
2. 명령어를 직접 실행하거나 명령어와 주요 지표·한계를 말한다.
3. 정답을 확인하고 [복습 기록](review-log.md)에 **맞음/부분/틀림**, 다음 복습일을 남긴다.
4. 틀린 항목은 다음날, 맞힌 항목은 **1일 → 3일 → 7일 → 14일 → 30일** 간격으로 확인한다. 틀리면 간격을 다시 1일로 설정한다.
5. 각 Lab에서 새 명령어가 나오면 이 표에 누적하되 **핵심 명령어와 참고용 명령어**를 구별한다.

## A. Linux CPU 진단 — 우선 숙지 (Lab 02-01 / 03-01 복습)

| 우선 | 호출 상황 | 명령어 | 핵심 측정·관측 | 한계와 주의 |
|---|---|---|---|---|
| 필수 | 서버가 느리다. 먼저 전체 상태를 본다 | `top` | CPU user/system/idle/iowait, 프로세스 상태·CPU 사용 | 높은 CPU% ≠ 최대 연산 성능; 순간·구간 값 해석 |
| 필수 | 논리 CPU별 부하 편중을 확인한다 | `mpstat -P ALL 1` | CPU별 시간 비율·idle·iowait 등 | 실행 효율·IPC를 측정하지 못함 |
| 필수 | 누가 CPU를 쓰는지 찾는다 | `ps -eo pid,stat,pcpu,comm --sort=-pcpu | head` | 프로세스별 CPU 사용 추정, 상태 | `ps %CPU`는 일반적으로 프로세스 생존기간 평균이며 순간 사용률 아님 |
| 필수 | 프로세스별 CPU 사용을 연속 관측한다 | `pidstat -u 1` | 프로세스/태스크 CPU 시간·사용률 추이 | 캐시 미스·연산 효율의 원인은 알 수 없음 |
| 필수 | CPU를 기다리는 작업이 밀리는지 확인한다 | `vmstat 1` | `r` 실행 가능 작업, `b` 인터럽트 불가 대기, CPU 상태·전환 | `r`은 샘플 시점의 작업 수; 첫 줄은 부팅 이후 평균일 수 있음 |
| 필수 | 서버 부하가 지속되는지 확인한다 | `uptime` | Load Average 1/5/15분 | CPU%가 아니며 R·D 태스크 포함, 코어 수 고려 필요 |
| 필수 | 디스크 I/O 병목과 CPU 대기를 구별한다 | `iostat -xz 1` | 디스크 처리량·IOPS·`await`·`%util` | `%util`은 장치가 I/O 요청을 처리한 시간 비율에 가까움; SSD 최대 성능 사용률 아님 |
| 참고 | 인터랙티브하게 코어와 프로세스를 본다 | `htop` | 코어·프로세스 상태 시각화 | 내부 연산 효율은 모름; 설치 필요 |
| 참고 | CPU 추이를 과거 기록에서 본다 | `sar -u 1 5` | CPU 시간 비율의 시계열 | 과거 기록 조회는 별도 sysstat 수집 설정 필요 |
| 참고 | 특정 스레드의 CPU 사용을 본다 | `top -H -p <PID>` | 스레드별 CPU 사용 | 스레드별 CPU%도 처리량/IPC 아님 |
| 심화 | 실제 하드웨어 명령어 수행을 분석한다 | `perf stat -e cycles,instructions,cache-misses -- <프로그램>` | cycles/instructions, IPC 및 캐시 미스 이벤트 | 이벤트 정의·지원/권한·WSL/VM 제약; IPC만으로 유용 작업량 판단 불가 |
| 심화 | 어디에 CPU 시간을 소비하는지 찾는다 | `perf record -g -- <프로그램>` 후 `perf report` | 샘플 기반 hot path·호출 경로 | 샘플링 편향·심볼/권한 제한, 모든 실행의 완전한 추적 아님 |

### 반드시 구분할 개념

- **CPU Busy %**: 커널에 기록된 실행 상태의 시간 비율. CPU 내부에서 캐시 미스로 파이프라인이 정체되는 시간도 실행 시간에 포함될 수 있다.
- **iowait**: CPU가 유휴인 동안 I/O를 기다린 시간의 통계. 프로세스의 전체 I/O 소요 시간이나 디스크 `%util`과 같지 않다. `100 - idle`은 iowait 등을 포함할 수 있어 도구별 CPU 바쁨 정의에 주의한다.
- **Load Average**: 실행 가능(R) 및 일부 중단 불가 대기(D) 태스크를 반영한 평균 부하. 코어 수를 무시한 CPU% 환산은 금지.
- **IPC = instructions / cycles**: 클럭당 완료된 명령어 수. 최대 FLOPS 달성률 또는 애플리케이션 처리량과 같지 않다.
- **프로그램 처리량(예: images/s, req/s)** 은 CPU/GPU 활동 지표와 별도로 측정한다.

## B. 메모리·프로세스·스토리지 — 우선 숙지 (Lab 02-01)

| 우선 | 호출 상황 | 명령어 | 관측 항목 / 한계 |
|---|---|---|---|
| 필수 | 메모리가 부족한지 본다 | `free -h` | `available` 중심 확인. `free`가 낮아도 회수 가능한 캐시가 존재할 수 있음 |
| 필수 | 문제 프로세스 상태·트리를 본다 | `ps -eo pid,ppid,stat,%cpu,%mem,etime,comm,args` | 상태/프로세스 관계. 순간 CPU 연산 효율은 모름 |
| 필수 | 디스크 공간 부족을 확인한다 | `df -h` | 파일시스템 공간/사용률. 디스크 I/O 속도나 inode 문제는 별개 |
| 필수 | 디스크 inode를 본다 | `df -i` | inode 고갈 여부. 바이트 용량과 구분 |
| 필수 | 커널 OOM·장애 로그를 찾는다 | `dmesg -T | tail -n 60` | 접근 권한·로그 보존 범위에 제약; OOM 로그 없다는 사실만으로 모든 SIGKILL 원인 배제 불가 |
| 참고 | 파일·폴더 용량을 본다 | `du -sh <경로>` | 파일시스템 전체 사용률과 다를 수 있음 |
| 참고 | 서비스 로그를 확인한다 | `journalctl -u <서비스명> -n 100 --no-pager` | systemd 서비스에 한정, 환경별 로그 접근/보존 제약 |

## C. NVIDIA GPU 관측 — 다음 Lab에서 채울 자리 (Lab 03-01)

| 숙지 명령어 | 관측 목적 | 검증 상태 |
|---|---|---|
| `nvidia-smi` | GPU·VRAM·드라이버·프로세스 기본 상태 | GPU ON 예정, 아직 실제 GPU 출력 없음 |
| `nvidia-smi --query-gpu=timestamp,name,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv` | GPU Util·VRAM·온도 필드 | GPU ON 예정, 실제 필드 지원 확인 필요 |
| DCGM 관련 명령·exporter | SM Active·Tensor Active·전력 등 운영 메트릭 | GPU ON 예정, 버전/필드 지원 검증 전 |

**참고:** GPU Util/SM Active/Tensor Active는 GPU의 *최대 연산 처리량 달성률*이 아니다. 실제 처리량과 함께 비교한다.

## D. 추후 확장용 자리

- **네트워크:** `ip`, `ss`, `ping`, `curl`, `dig`, `tcpdump` — 별도 Lab에서 의미·한계 정리
- **AWS/S3/IAM:** `aws sts get-caller-identity`, `aws s3 ls/cp/rm`, `sha256sum` — Lab 02-02과 연동
- **Docker/Kubernetes:** `docker ps/logs/stats`, `kubectl get/describe/logs` — 후속 Lab에서 확장
- **GPU/PyTorch:** `nvidia-smi`, CUDA/PyTorch 진단, DCGM — G1 실측 후 검증 근거 추가

## 암기 목표

- **기본:** 상황을 듣고 올바른 명령어를 고른다.
- **이해:** 출력의 주요 필드와 **알 수 없는 것**을 말한다.
- **운영:** 한 지표만으로 원인을 단정하지 않고, 다음 진단 명령어를 선택한다.

복습 기록은 [review-log.md](review-log.md)에 남긴다.
