# Resolve compatible default add-on versions for the selected Kubernetes version.
data "aws_eks_addon_version" "g2" {
  for_each = toset(["vpc-cni", "eks-pod-identity-agent", "kube-proxy", "coredns"])

  addon_name         = each.value
  kubernetes_version = var.eks_version
}

# Install host-network bootstrap add-ons before compute.
resource "aws_eks_addon" "pod_identity" {
  cluster_name                = aws_eks_cluster.g2.name
  addon_name                  = "eks-pod-identity-agent"
  addon_version               = data.aws_eks_addon_version.g2["eks-pod-identity-agent"].version
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"
}

resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = aws_eks_cluster.g2.name
  addon_name                  = "vpc-cni"
  addon_version               = data.aws_eks_addon_version.g2["vpc-cni"].version
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  pod_identity_association {
    service_account = "aws-node"
    role_arn        = aws_iam_role.cni.arn
  }

  depends_on = [
    aws_iam_role_policy_attachment.cni,
    aws_eks_addon.pod_identity
  ]
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name                = aws_eks_cluster.g2.name
  addon_name                  = "kube-proxy"
  addon_version               = data.aws_eks_addon_version.g2["kube-proxy"].version
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"
}

# CoreDNS requires schedulable compute; avoid waiting for it before nodes exist.
resource "aws_eks_addon" "coredns" {
  cluster_name                = aws_eks_cluster.g2.name
  addon_name                  = "coredns"
  addon_version               = data.aws_eks_addon_version.g2["coredns"].version
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  configuration_values = jsonencode({
    nodeSelector = {
      workload = "system"
    }
  })

  depends_on = [aws_eks_node_group.cpu]
}
