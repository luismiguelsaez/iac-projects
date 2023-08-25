from pulumi_aws import iam
import pulumi

aws_config = pulumi.Config("aws-eks-cluster")
eks_name_prefix = aws_config.require("name_prefix")

eks_cluster_role = iam.Role(
  eks_name_prefix,
  assume_role_policy="""{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": "sts:AssumeRole",
        "Principal": {
          "Service": "eks.amazonaws.com"
        },
        "Effect": "Allow",
        "Sid": ""
      }
    ]
  }""",
  tags={
    "Name": eks_name_prefix,
  },
)

iam.RolePolicyAttachment(
  f"{eks_name_prefix}-AmazonEKSClusterPolicy",
  policy_arn="arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
  role=eks_cluster_role.name,
)

iam.RolePolicyAttachment(
  f"{eks_name_prefix}-AmazonEKSServicePolicy",
  policy_arn="arn:aws:iam::aws:policy/AmazonEKSServicePolicy",
  role=eks_cluster_role.name,
)

ec2_role = iam.Role(
  f"{eks_name_prefix}-nodegroup",
  assume_role_policy="""{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": "sts:AssumeRole",
        "Principal": {
          "Service": "ec2.amazonaws.com"
        },
        "Effect": "Allow",
        "Sid": ""
      }
    ]
  }""",
  tags={
    "Name": f"{eks_name_prefix}-nodegroup",
  },
)

iam.RolePolicyAttachment(
  f"{eks_name_prefix}-nodegroup-AmazonEKSWorkerNodePolicy",
  policy_arn="arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
  role=ec2_role.name,
)

iam.RolePolicyAttachment(
  f"{eks_name_prefix}-nodegroup-AmazonEKS_CNI_Policy",
  policy_arn="arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
  role=ec2_role.name,
)

iam.RolePolicyAttachment(
  f"{eks_name_prefix}-nodegroup-AmazonEC2ContainerRegistryReadOnly",
  policy_arn="arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
  role=ec2_role.name,
)
