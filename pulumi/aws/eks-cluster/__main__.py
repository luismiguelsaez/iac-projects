"""
Simple EKS cluster with a single node group  
"""

# Import components
import vpc
import iam
import tools

import pulumi
from pulumi_aws import eks


eks_cluster = eks.Cluster(
  "eks-main",
  version="1.27",
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
