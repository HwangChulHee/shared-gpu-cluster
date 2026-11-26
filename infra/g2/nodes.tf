# OFF-1: CPU system node group. CNI identity is configured in a later step.
resource "aws_iam_role" "eks_node" {
  name = "${var.name}-eks-node-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_node" {
  for_each = toset([
    "AmazonEKSWorkerNodePolicy",
    "AmazonEC2ContainerRegistryPullOnly"
  ])

  role       = aws_iam_role.eks_node.name
  policy_arn = "arn:aws:iam::aws:policy/${each.value}"
}

resource "aws_launch_template" "cpu" {
  name_prefix = "${var.name}-cpu-"

  block_device_mappings {
    device_name = "/dev/xvda"

    ebs {
      volume_size           = 50
      volume_type           = "gp3"
      encrypted             = true
      delete_on_termination = true
    }
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }
}

resource "aws_eks_node_group" "cpu" {
  cluster_name    = aws_eks_cluster.g2.name
  node_group_name = "${var.name}-cpu"
  node_role_arn   = aws_iam_role.eks_node.arn
  subnet_ids      = [for az in var.availability_zones : aws_subnet.private[az].id]

  version        = var.eks_version
  ami_type       = "AL2023_x86_64_STANDARD"
  instance_types = ["m6i.large"]
  capacity_type  = "ON_DEMAND"

  launch_template {
    id      = aws_launch_template.cpu.id
    version = tostring(aws_launch_template.cpu.latest_version)
  }

  scaling_config {
    min_size     = 1
    desired_size = 1
    max_size     = 2
  }

  labels = {
    workload = "system"
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_node,
    aws_route.private_default,
    aws_route.public_default,
    aws_route_table_association.private,
    aws_route_table_association.public,
    aws_vpc_endpoint.s3
  ]
}
