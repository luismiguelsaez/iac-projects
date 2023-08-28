from pulumi_aws import iam
import pulumi
import json
from os import path

aws_config = pulumi.Config("aws-eks-cluster")
eks_name_prefix = aws_config.require("name_prefix")

"""
EKS cluster IAM role
"""
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

"""
Node IAM role
"""
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

"""
Controller IAM policies
"""
with open(path.join(path.dirname(__file__), "iam/policies", "aws-load-balancer-controller.json")) as f:
    policy_aws_load_balancer_controller = json.loads(f.read())

# https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.6.0/docs/install/iam_policy.json
eks_policy_aws_load_balancer_controller = iam.Policy(
    f"{eks_name_prefix}-aws-load-balancer-controller",
    policy=pulumi.Output.json_dumps(policy_aws_load_balancer_controller)
)

with open(path.join(path.dirname(__file__), "iam/policies", "external-dns.json")) as f:
    policy_external_dns = json.loads(f.read())

# https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/aws.md
eks_policy_external_dns = iam.Policy(
    f"{eks_name_prefix}-external-dns",
    policy=pulumi.Output.json_dumps(policy_external_dns)
)

with open(path.join(path.dirname(__file__), "iam/policies", "karpenter.json")) as f:
    policy_karpenter = json.loads(f.read())

# https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/aws.md
eks_policy_karpenter = iam.Policy(
    f"{eks_name_prefix}-karpenter",
    policy=pulumi.Output.json_dumps(policy_karpenter)
)

with open(path.join(path.dirname(__file__), "iam/policies", "cluster-autoscaler.json")) as f:
    policy_cluster_autoscaler = json.loads(f.read())

# https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/aws.md
eks_policy_cluster_autoscaler = iam.Policy(
    f"{eks_name_prefix}-cluster-autoscaler",
    policy=pulumi.Output.json_dumps(policy_cluster_autoscaler)
)
