# G2 Terraform — OFF-1: network foundation (not deployed)

> **Status (2026-11-26): only VPC/subnet/routes/NAT/S3 endpoint source code exists. No EKS cluster, node group, Pod Identity or GPU resources created.** Don't run `terraform apply` yet. Terraform state is not committed.

## Logical network design

![G2 network architecture](../../docs/diagrams/g2/01-network.svg)

[Editable draw.io source](../../docs/diagrams/g2/01-network.drawio)

The diagram is a planned topology, not deployed infrastructure. Worker placement is illustrative.

```text
                         AWS-managed EKS API (future)
                              private endpoint
                                     |
                    G2 VPC: 10.42.0.0/16 (planned)
                      /                          \
           ap-northeast-2a                  ap-northeast-2c
          public 10.42.0.0/24              public 10.42.1.0/24
            [NAT Gateway + EIP]               (no NAT)
                 |                                 |
          private 10.42.10.0/24           private 10.42.11.0/24
          [future CPU/GPU]                 [future GPU]
                 |                                 |
            private RT A                      private RT C
            0.0.0.0/0 ────► same NAT ◄────── 0.0.0.0/0
            S3 prefix route → S3 Gateway ← S3 prefix route
```

- Private nodes will have **no public IPv4**. NAT in public subnet allows public API, ECR and internet egress (but not unsolicited inbound).
- **S3 Gateway Endpoint** is associated with *both* private route tables. AWS installs S3 prefix-list routes; S3 GetObject/PutObject uses endpoint rather than NAT. S3 IAM and bucket policy remain separate.
- The IGW is attached to the VPC. The NAT Gateway has an Elastic IP and lives in public AZ-a subnet; public route table `0.0.0.0/0 → IGW`.
- Single NAT is cheaper in number of gateways, but **not AZ resilient**, and cross-AZ network transfer may cost extra.
- Network code does not create an EKS Cluster, private API endpoint, security groups, IAM roles or nodes. These belong to the next steps.
- The CIDR is a *proposed lab CIDR*; verify there is no overlap with any peering/VPN/on-prem networks before applying.

## Local read-only checks (no AWS resources created)

```bash
cd infra/g2
terraform init -backend=false
terraform fmt -check
terraform validate
```

`terraform init -backend=false` downloads providers but does not create AWS resources; `terraform validate` checks configuration locally. The next stage adds EKS, node groups, IAM and remote administrator access strategy. **Do not run `terraform apply` or create chargeable NAT/EIP until the full G2 ON checklist is complete**.

Once all stages are prepared, inspect `terraform plan` against the target AWS account and region, confirm budget/cleanup and backup, then explicitly proceed to `apply`.

## Design notes

- AWS Region: ap-northeast-2; two subnets each in AZ 2a, 2c, in one VPC.
- Existing G1 S3 bucket is not created or modified by this Terraform root.
- Public EKS API access for WSL `kubectl` is not yet decided; a restricted public endpoint alongside the private endpoint is a possible lab choice.
- G2 Batch 32/64/128/256 capacity tests and actual YOLO Job are **later G2 ON tasks**, not part of this networking stage.
