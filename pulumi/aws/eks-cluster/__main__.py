"""
Simple EKS cluster with a single node group  
"""

# Import components
import vpc
import iam
import tools

import pulumi
from pulumi_aws import eks

aws_config = pulumi.Config("aws-eks-cluster")
eks_version = aws_config.require("eks_version")

eks_cluster = eks.Cluster(
  "eks-main",
  version=eks_version,
  role_arn=iam.eks_cluster_role.arn,
  vpc_config=eks.ClusterVpcConfigArgs(
    public_access_cidrs=["0.0.0.0/0"],
    security_group_ids=[vpc.security_group.id],
    subnet_ids=[ s.id for s in vpc.public_subnets ],
  ),
)

pulumi.export("eks_cluster_name", eks_cluster.name)
pulumi.export("eks_cluster_endpoint", eks_cluster.endpoint)
pulumi.export("kubeconfig", tools.create_kubeconfig(eks_cluster))
