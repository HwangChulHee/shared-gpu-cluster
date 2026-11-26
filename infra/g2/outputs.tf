output "vpc_id" {
  value = aws_vpc.g2.id
}

output "public_subnet_ids" {
  value = { for az, subnet in aws_subnet.public : az => subnet.id }
}

output "private_subnet_ids" {
  value = { for az, subnet in aws_subnet.private : az => subnet.id }
}

output "private_route_table_ids" {
  value = { for az, rt in aws_route_table.private : az => rt.id }
}

output "nat_gateway_id" {
  value = aws_nat_gateway.g2.id
}

output "s3_gateway_endpoint_id" {
  value = aws_vpc_endpoint.s3.id
}

output "eks_cluster_name" {
  value = aws_eks_cluster.g2.name
}

output "eks_cluster_endpoint" {
  value = aws_eks_cluster.g2.endpoint
}

output "eks_cluster_security_group_id" {
  value = aws_eks_cluster.g2.vpc_config[0].cluster_security_group_id
}

output "eks_cluster_role_arn" {
  value = aws_iam_role.eks_cluster.arn
}

output "cpu_node_group_name" {
  value = aws_eks_node_group.cpu.node_group_name
}

output "eks_node_role_arn" {
  value = aws_iam_role.eks_node.arn
}
