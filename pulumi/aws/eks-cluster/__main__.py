"""
Simple EKS cluster with a single node group  
"""

# Import components
import vpc
import iam
import tools

import pulumi
from pulumi_aws import eks

aws_config = pulumi.Config("aws")
aws_region = aws_config.require("region")
aws_eks_config = pulumi.Config("aws-eks-cluster")
eks_version = aws_eks_config.require("eks_version")
eks_name_prefix = aws_eks_config.require("name_prefix")

eks_cluster = eks.Cluster(
  eks_name_prefix,
  version=eks_version,
  role_arn=iam.eks_cluster_role.arn,
  vpc_config=eks.ClusterVpcConfigArgs(
    public_access_cidrs=["0.0.0.0/0"],
    security_group_ids=[vpc.security_group.id],
    subnet_ids=[ s.id for s in vpc.public_subnets ],
  ),
)

eks_node_group = eks.NodeGroup(
  f"{eks_name_prefix}-default",
  cluster_name=eks_cluster.name,
  node_group_name="default",
  node_role_arn=iam.ec2_role.arn,
  subnet_ids=[ s.id for s in vpc.public_subnets ],
  scaling_config=eks.NodeGroupScalingConfigArgs(
    desired_size=2,
    max_size=2,
    min_size=1,
  ),
  instance_types=["t3.medium"],
)

pulumi.export("eks_cluster_name", eks_cluster.name)
pulumi.export("eks_cluster_endpoint", eks_cluster.endpoint)
pulumi.export("kubeconfig", tools.create_kubeconfig(eks_cluster=eks_cluster, region=aws_region))
