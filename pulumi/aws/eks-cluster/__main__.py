"""
Simple EKS cluster with a single node group  
"""

# Import components
import vpc
import iam

from pulumi_aws import eks

eks_cluster = eks.Cluster(
  "eks-main",
  role_arn=iam.eks_cluster_role.arn,
  vpc_config=eks.ClusterVpcConfigArgs(
    public_access_cidrs=["0.0.0.0/0"],
    security_group_ids=[vpc.security_group.id],
    subnet_ids=[ s.id for s in vpc.public_subnets ],
  ),
)

