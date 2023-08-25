"""
Simple EKS cluster with a single node group  
"""

# Import components
import vpc
import iam
import tools

import pulumi
from pulumi_aws import eks, ec2, get_caller_identity
from pulumi_aws import iam as aws_iam

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

eks_node_group_key_pair = ec2.KeyPair(
  eks_name_prefix,
  public_key=tools.get_ssh_public_key("id_rsa.pub"),
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
pulumi.export("eks_cluster_oidc_issuer", eks_cluster.identities[0].oidcs[0].issuer)
pulumi.export("kubeconfig", tools.create_kubeconfig(eks_cluster=eks_cluster, region=aws_region))

aws_account_id = get_caller_identity().account_id
eks_cluster_oidc_provider = pulumi.Output.all(
  eks_cluster.identities[0].oidcs[0].issuer).apply(lambda o: o[0].replace("https://", f"arn:aws:iam::{aws_account_id}:oidc-provider/"))

eks_sa_role_aws_load_balancer_controller = aws_iam.Role(
  f"{eks_name_prefix}-aws-load-balancer-controller",
  assume_role_policy=pulumi.Output.json_dumps(
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Action": "sts:AssumeRole",
          "Principal": {
            "Federated": eks_cluster_oidc_provider
          },
          "Effect": "Allow",
          "Sid": "",
        },
      ],
    }
  )
)

eks_policy_aws_load_balancer_controller = aws_iam.Policy(
  f"{eks_name_prefix}-aws-load-balancer-controller",
  policy=pulumi.Output.json_dumps(
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "acm:DescribeCertificate",
                    "acm:ListCertificates",
                    "acm:GetCertificate"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:AuthorizeSecurityGroupIngress",
                    "ec2:CreateSecurityGroup",
                    "ec2:CreateTags",
                    "ec2:DeleteTags",
                    "ec2:DeleteSecurityGroup",
                    "ec2:DescribeAccountAttributes",
                    "ec2:DescribeAddresses",
                    "ec2:DescribeInstances",
                    "ec2:DescribeInstanceStatus",
                    "ec2:DescribeInternetGateways",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:DescribeSecurityGroups",
                    "ec2:DescribeSubnets",
                    "ec2:DescribeTags",
                    "ec2:DescribeVpcs",
                    "ec2:ModifyInstanceAttribute",
                    "ec2:ModifyNetworkInterfaceAttribute",
                    "ec2:RevokeSecurityGroupIngress"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "elasticloadbalancing:AddListenerCertificates",
                    "elasticloadbalancing:AddTags",
                    "elasticloadbalancing:CreateListener",
                    "elasticloadbalancing:CreateLoadBalancer",
                    "elasticloadbalancing:CreateRule",
                    "elasticloadbalancing:CreateTargetGroup",
                    "elasticloadbalancing:DeleteListener",
                    "elasticloadbalancing:DeleteLoadBalancer",
                    "elasticloadbalancing:DeleteRule",
                    "elasticloadbalancing:DeleteTargetGroup",
                    "elasticloadbalancing:DeregisterTargets",
                    "elasticloadbalancing:DescribeListenerCertificates",
                    "elasticloadbalancing:DescribeListeners",
                    "elasticloadbalancing:DescribeLoadBalancers",
                    "elasticloadbalancing:DescribeLoadBalancerAttributes",
                    "elasticloadbalancing:DescribeRules",
                    "elasticloadbalancing:DescribeSSLPolicies",
                    "elasticloadbalancing:DescribeTags",
                    "elasticloadbalancing:DescribeTargetGroups",
                    "elasticloadbalancing:DescribeTargetGroupAttributes",
                    "elasticloadbalancing:DescribeTargetHealth",
                    "elasticloadbalancing:ModifyListener",
                    "elasticloadbalancing:ModifyLoadBalancerAttributes",
                    "elasticloadbalancing:ModifyRule",
                    "elasticloadbalancing:ModifyTargetGroup",
                    "elasticloadbalancing:ModifyTargetGroupAttributes",
                    "elasticloadbalancing:RegisterTargets",
                    "elasticloadbalancing:RemoveListenerCertificates",
                    "elasticloadbalancing:RemoveTags",
                    "elasticloadbalancing:SetIpAddressType",
                    "elasticloadbalancing:SetSecurityGroups",
                    "elasticloadbalancing:SetSubnets",
                    "elasticloadbalancing:SetWebACL"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "iam:CreateServiceLinkedRole",
                    "iam:GetServerCertificate",
                    "iam:ListServerCertificates"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "cognito-idp:DescribeUserPoolClient"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "waf-regional:GetWebACLForResource",
                    "waf-regional:GetWebACL",
                    "waf-regional:AssociateWebACL",
                    "waf-regional:DisassociateWebACL"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "tag:GetResources",
                    "tag:TagResources"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "waf:GetWebACL"
                ],
                "Resource": "*"
            }
        ]
    }
  )
)

aws_iam.RolePolicyAttachment(
  f"{eks_name_prefix}-aws-load-balancer-controller",
  policy_arn=eks_policy_aws_load_balancer_controller.arn,
  role=eks_sa_role_aws_load_balancer_controller.name,
)

from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts
import pulumi_kubernetes as k8s

# Create kubernetes provider
k8s_provider = k8s.Provider(
  "k8s-provider",
  kubeconfig=tools.create_kubeconfig(eks_cluster=eks_cluster, region=aws_region),
)

helm_aws_load_balancer_controller_chart = Chart(
  "aws-load-balancer-controller",
  ChartOpts(
    chart="aws-load-balancer-controller",
    version="1.6.0",
    fetch_opts=FetchOpts(
      repo="https://aws.github.io/eks-charts",
    ),
    namespace="kube-system",
    values={
      "clusterName": eks_cluster.name,
      "region": aws_region,
      "vpcId": vpc.vpc.id,
      "serviceAccount": {
        "create": True,
        "annotations": {
          "eks.amazonaws.com/role-arn": eks_sa_role_aws_load_balancer_controller.arn,
        },
      }
    },
  ),
  opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[eks_cluster]),
)

eks_sa_role_external_dns = aws_iam.Role(
  f"{eks_name_prefix}-external-dns",
  assume_role_policy=pulumi.Output.json_dumps(
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Action": "sts:AssumeRole",
          "Principal": {
            "Federated": eks_cluster_oidc_provider
          },
          "Effect": "Allow",
          "Sid": "",
        },
      ],
    }
  )
)

eks_policy_external_dns = aws_iam.Policy(
  f"{eks_name_prefix}-external-dns",
  policy=pulumi.Output.json_dumps(
    {
        "Statement": [
            {
                "Action": [
                    "route53:ChangeResourceRecordSets"
                ],
                "Effect": "Allow",
                "Resource": [
                    "arn:aws:route53:::hostedzone/*"
                ]
            },
            {
                "Action": [
                    "route53:ListHostedZones",
                    "route53:ListResourceRecordSets"
                ],
                "Effect": "Allow",
                "Resource": [
                    "*"
                ]
            }
        ],
        "Version": "2012-10-17"
    }
  )
)

aws_iam.RolePolicyAttachment(
  f"{eks_name_prefix}-external-dns",
  policy_arn=eks_policy_external_dns.arn,
  role=eks_sa_role_external_dns.name,
)

helm_external_dns_chart = Chart(
  "external-dns",
  ChartOpts(
    chart="external-dns",
    version="1.10.1",
    fetch_opts=FetchOpts(
      repo="https://kubernetes-sigs.github.io/external-dns",
    ),
    namespace="kube-system",
    values={
      "provider": "aws",
      "sources": ["service", "ingress"],
      "policy": "sync",
      "deploymentStrategy": "Recreate",
      "serviceAccount": {
        "create": True,
        "annotations": {
          "eks.amazonaws.com/role-arn": eks_sa_role_external_dns.arn,
        },
      }
    },
  ),
  opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[eks_cluster]),
)
