locals {
  pod_identity_trust = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "pods.eks.amazonaws.com"
      }
      Action = ["sts:AssumeRole", "sts:TagSession"]
    }]
  })
}

resource "aws_iam_role" "cni" {
  name               = "${var.name}-cni-role"
  assume_role_policy = local.pod_identity_trust
}

resource "aws_iam_role_policy_attachment" "cni" {
  role       = aws_iam_role.cni.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

resource "aws_iam_role" "yolo" {
  name               = "${var.name}-yolo-role"
  assume_role_policy = local.pod_identity_trust
}

resource "aws_iam_role_policy" "yolo_s3" {
  name = "g2-s3-access"
  role = aws_iam_role.yolo.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "arn:aws:s3:::${var.data_bucket_name}/datasets/*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:AbortMultipartUpload"]
        Resource = "arn:aws:s3:::${var.data_bucket_name}/results/g2/*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = "arn:aws:s3:::${var.data_bucket_name}"
        Condition = {
          StringLike = {
            "s3:prefix" = ["datasets", "datasets/*", "results/g2", "results/g2/*"]
          }
        }
      }
    ]
  })
}

resource "aws_eks_pod_identity_association" "yolo" {
  cluster_name    = aws_eks_cluster.g2.name
  namespace       = "gpu-training"
  service_account = "yolo"
  role_arn        = aws_iam_role.yolo.arn

  depends_on = [
    aws_iam_role_policy.yolo_s3,
    aws_eks_addon.pod_identity
  ]
}
