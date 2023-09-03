from pulumi_aws import iam
import pulumi
import json
from os import path
import tools

aws_config = pulumi.Config("aws-eks-cluster")
eks_name_prefix = aws_config.require("name_prefix")

def create_oidc_provider(name: str, eks_issuer_url: str, aws_region: str, depends_on: list = [])->iam.OpenIdConnectProvider:

  oidc_fingerprint = tools.get_ssl_cert_fingerprint(host=f"oidc.eks.{aws_region}.amazonaws.com")
  oidc_provider = iam.OpenIdConnectProvider(
      name,
      client_id_lists=["sts.amazonaws.com"],
      thumbprint_lists=[oidc_fingerprint],
      url=eks_issuer_url,
      opts=pulumi.ResourceOptions(depends_on=depends_on),
  )
  
  return oidc_provider

def create_policy_from_file(name: str, policy_file: str)->iam.Policy:
  
  with open(path.join(path.dirname(__file__), policy_file)) as f:
    policy_json = json.loads(f.read())

  policy = iam.Policy(
      name,
      policy=pulumi.Output.json_dumps(policy_json)
  )
  
  return policy
  
def create_role_oidc(name, oidc_provider_arn: str)->iam.Role:
  
  role = iam.Role(
      name,
      assume_role_policy=pulumi.Output.json_dumps(
          {
          "Version": "2012-10-17",
          "Statement": [
              {
              "Action": "sts:AssumeRoleWithWebIdentity",
              "Principal": {
                  "Federated": oidc_provider_arn
              },
              "Effect": "Allow",
              "Sid": "",
              },
          ],
          }
      )
  )

  return role

def create_role_policy_attachment(name: str, role_name: str, policy_arn: str)->iam.RolePolicyAttachment:

  attachment = iam.RolePolicyAttachment(
      name,
      role=role_name,
      policy_arn=policy_arn,
  )
  
  return attachment

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
  resource_name=f"{eks_name_prefix}-nodegroup",
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

ec2_role_instance_profile = iam.InstanceProfile(
  f"{eks_name_prefix}-nodegroup",
  role=ec2_role.name,
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
# https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.6.0/docs/install/iam_policy.json
eks_policy_aws_load_balancer_controller = create_policy_from_file(f"{eks_name_prefix}-aws-load-balancer-controller", "iam/policies/aws-load-balancer-controller.json")
# https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/aws.md
eks_policy_external_dns = create_policy_from_file(f"{eks_name_prefix}-external-dns", "iam/policies/external-dns.json")
eks_policy_karpenter = create_policy_from_file(f"{eks_name_prefix}-karpenter", "iam/policies/karpenter.json")
eks_policy_cluster_autoscaler = create_policy_from_file(f"{eks_name_prefix}-cluster-autoscaler", "iam/policies/cluster-autoscaler.json")
eks_policy_ebs_csi_driver = create_policy_from_file(f"{eks_name_prefix}-ebs-csi-driver", "iam/policies/ebs-csi-driver.json")
