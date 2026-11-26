# OFF-1: managed control plane only. Do not apply before the G2 ON gate.
resource "aws_iam_role" "eks_cluster" {
  name = "${var.name}-eks-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "eks.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster" {
  role       = aws_iam_role.eks_cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_eks_cluster" "g2" {
  name     = "${var.name}-eks"
  role_arn = aws_iam_role.eks_cluster.arn
  version  = var.eks_version

  vpc_config {
    subnet_ids              = [for az in var.availability_zones : aws_subnet.private[az].id]
    endpoint_public_access  = true
    endpoint_private_access = true
    public_access_cidrs     = var.admin_access_cidrs
  }

  # Lab bootstrap: the creating IAM principal receives cluster admin access.
  access_config {
    authentication_mode                         = "API"
    bootstrap_cluster_creator_admin_permissions = true
  }

  # Avoid automatic entry into higher-priced extended support.
  upgrade_policy {
    support_type = "STANDARD"
  }

  # Keep the role's permissions available throughout cluster deletion.
  depends_on = [aws_iam_role_policy_attachment.eks_cluster]
}
