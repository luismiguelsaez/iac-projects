"""
Simple EKS cluster with a single node group  
"""

# Import components
from os import path
import vpc
import iam
import tools

import pulumi
from pulumi_aws import eks, ec2, get_caller_identity
from pulumi_aws import iam as aws_iam
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts
from pulumi_kubernetes import Provider as kubernetes_provider

aws_config = pulumi.Config("aws")
aws_region = aws_config.require("region")
aws_eks_config = pulumi.Config("aws-eks-cluster")
eks_version = aws_eks_config.require("eks_version")
eks_name_prefix = aws_eks_config.require("name_prefix")

eks_cluster = eks.Cluster(
    name=eks_name_prefix,
    resource_name=eks_name_prefix,
    version=eks_version,
    role_arn=iam.eks_cluster_role.arn,
    vpc_config=eks.ClusterVpcConfigArgs(
        public_access_cidrs=["0.0.0.0/0"],
        security_group_ids=[vpc.security_group.id],
        subnet_ids=[ s.id for s in vpc.public_subnets ],
    ),
    tags={
        "Name": eks_name_prefix,
    },
    opts=None,
)

oidc_fingerprint = tools.get_ssl_cert_fingerprint(host=f"oidc.eks.{aws_region}.amazonaws.com")
oidc_provider = aws_iam.OpenIdConnectProvider(
    f"{eks_name_prefix}-oidc-provider",
    client_id_lists=["sts.amazonaws.com"],
    thumbprint_lists=[oidc_fingerprint],
    url=eks_cluster.identities[0].oidcs[0].issuer,
    opts=pulumi.ResourceOptions(depends_on=[eks_cluster]),
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

eks_sa_role_aws_load_balancer_controller = aws_iam.Role(
    f"{eks_name_prefix}-aws-load-balancer-controller",
    assume_role_policy=pulumi.Output.json_dumps(
        {
        "Version": "2012-10-17",
        "Statement": [
            {
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Principal": {
                "Federated": oidc_provider.arn
            },
            "Effect": "Allow",
            "Sid": "",
            },
        ],
        }
    )
)

# https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.6.0/docs/install/iam_policy.json
eks_policy_aws_load_balancer_controller = aws_iam.Policy(
    f"{eks_name_prefix}-aws-load-balancer-controller",
    policy=pulumi.Output.json_dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "iam:CreateServiceLinkedRole"
                ],
                "Resource": "*",
                "Condition": {
                    "StringEquals": {
                        "iam:AWSServiceName": "elasticloadbalancing.amazonaws.com"
                    }
                }
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:DescribeAccountAttributes",
                    "ec2:DescribeAddresses",
                    "ec2:DescribeAvailabilityZones",
                    "ec2:DescribeInternetGateways",
                    "ec2:DescribeVpcs",
                    "ec2:DescribeVpcPeeringConnections",
                    "ec2:DescribeSubnets",
                    "ec2:DescribeSecurityGroups",
                    "ec2:DescribeInstances",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:DescribeTags",
                    "ec2:GetCoipPoolUsage",
                    "ec2:DescribeCoipPools",
                    "elasticloadbalancing:DescribeLoadBalancers",
                    "elasticloadbalancing:DescribeLoadBalancerAttributes",
                    "elasticloadbalancing:DescribeListeners",
                    "elasticloadbalancing:DescribeListenerCertificates",
                    "elasticloadbalancing:DescribeSSLPolicies",
                    "elasticloadbalancing:DescribeRules",
                    "elasticloadbalancing:DescribeTargetGroups",
                    "elasticloadbalancing:DescribeTargetGroupAttributes",
                    "elasticloadbalancing:DescribeTargetHealth",
                    "elasticloadbalancing:DescribeTags"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "cognito-idp:DescribeUserPoolClient",
                    "acm:ListCertificates",
                    "acm:DescribeCertificate",
                    "iam:ListServerCertificates",
                    "iam:GetServerCertificate",
                    "waf-regional:GetWebACL",
                    "waf-regional:GetWebACLForResource",
                    "waf-regional:AssociateWebACL",
                    "waf-regional:DisassociateWebACL",
                    "wafv2:GetWebACL",
                    "wafv2:GetWebACLForResource",
                    "wafv2:AssociateWebACL",
                    "wafv2:DisassociateWebACL",
                    "shield:GetSubscriptionState",
                    "shield:DescribeProtection",
                    "shield:CreateProtection",
                    "shield:DeleteProtection"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:AuthorizeSecurityGroupIngress",
                    "ec2:RevokeSecurityGroupIngress"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:CreateSecurityGroup"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:CreateTags"
                ],
                "Resource": "arn:aws:ec2:*:*:security-group/*",
                "Condition": {
                    "StringEquals": {
                        "ec2:CreateAction": "CreateSecurityGroup"
                    },
                    "Null": {
                        "aws:RequestTag/elbv2.k8s.aws/cluster": "false"
                    }
                }
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:CreateTags",
                    "ec2:DeleteTags"
                ],
                "Resource": "arn:aws:ec2:*:*:security-group/*",
                "Condition": {
                    "Null": {
                        "aws:RequestTag/elbv2.k8s.aws/cluster": "true",
                        "aws:ResourceTag/elbv2.k8s.aws/cluster": "false"
                    }
                }
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:AuthorizeSecurityGroupIngress",
                    "ec2:RevokeSecurityGroupIngress",
                    "ec2:DeleteSecurityGroup"
                ],
                "Resource": "*",
                "Condition": {
                    "Null": {
                        "aws:ResourceTag/elbv2.k8s.aws/cluster": "false"
                    }
                }
            },
            {
                "Effect": "Allow",
                "Action": [
                    "elasticloadbalancing:CreateLoadBalancer",
                    "elasticloadbalancing:CreateTargetGroup"
                ],
                "Resource": "*",
                "Condition": {
                    "Null": {
                        "aws:RequestTag/elbv2.k8s.aws/cluster": "false"
                    }
                }
            },
            {
                "Effect": "Allow",
                "Action": [
                    "elasticloadbalancing:CreateListener",
                    "elasticloadbalancing:DeleteListener",
                    "elasticloadbalancing:CreateRule",
                    "elasticloadbalancing:DeleteRule"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "elasticloadbalancing:AddTags",
                    "elasticloadbalancing:RemoveTags"
                ],
                "Resource": [
                    "arn:aws:elasticloadbalancing:*:*:targetgroup/*/*",
                    "arn:aws:elasticloadbalancing:*:*:loadbalancer/net/*/*",
                    "arn:aws:elasticloadbalancing:*:*:loadbalancer/app/*/*"
                ],
                "Condition": {
                    "Null": {
                        "aws:RequestTag/elbv2.k8s.aws/cluster": "true",
                        "aws:ResourceTag/elbv2.k8s.aws/cluster": "false"
                    }
                }
            },
            {
                "Effect": "Allow",
                "Action": [
                    "elasticloadbalancing:AddTags",
                    "elasticloadbalancing:RemoveTags"
                ],
                "Resource": [
                    "arn:aws:elasticloadbalancing:*:*:listener/net/*/*/*",
                    "arn:aws:elasticloadbalancing:*:*:listener/app/*/*/*",
                    "arn:aws:elasticloadbalancing:*:*:listener-rule/net/*/*/*",
                    "arn:aws:elasticloadbalancing:*:*:listener-rule/app/*/*/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "elasticloadbalancing:ModifyLoadBalancerAttributes",
                    "elasticloadbalancing:SetIpAddressType",
                    "elasticloadbalancing:SetSecurityGroups",
                    "elasticloadbalancing:SetSubnets",
                    "elasticloadbalancing:DeleteLoadBalancer",
                    "elasticloadbalancing:ModifyTargetGroup",
                    "elasticloadbalancing:ModifyTargetGroupAttributes",
                    "elasticloadbalancing:DeleteTargetGroup"
                ],
                "Resource": "*",
                "Condition": {
                    "Null": {
                        "aws:ResourceTag/elbv2.k8s.aws/cluster": "false"
                    }
                }
            },
            {
                "Effect": "Allow",
                "Action": [
                    "elasticloadbalancing:AddTags"
                ],
                "Resource": [
                    "arn:aws:elasticloadbalancing:*:*:targetgroup/*/*",
                    "arn:aws:elasticloadbalancing:*:*:loadbalancer/net/*/*",
                    "arn:aws:elasticloadbalancing:*:*:loadbalancer/app/*/*"
                ],
                "Condition": {
                    "StringEquals": {
                        "elasticloadbalancing:CreateAction": [
                            "CreateTargetGroup",
                            "CreateLoadBalancer"
                        ]
                    },
                    "Null": {
                        "aws:RequestTag/elbv2.k8s.aws/cluster": "false"
                    }
                }
            },
            {
                "Effect": "Allow",
                "Action": [
                    "elasticloadbalancing:RegisterTargets",
                    "elasticloadbalancing:DeregisterTargets"
                ],
                "Resource": "arn:aws:elasticloadbalancing:*:*:targetgroup/*/*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "elasticloadbalancing:SetWebAcl",
                    "elasticloadbalancing:ModifyListener",
                    "elasticloadbalancing:AddListenerCertificates",
                    "elasticloadbalancing:RemoveListenerCertificates",
                    "elasticloadbalancing:ModifyRule"
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

k8s_provider = kubernetes_provider(
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
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Principal": {
                "Federated": oidc_provider.arn
            },
            "Effect": "Allow",
            "Sid": "",
            },
        ],
        }
    )
)

# https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/aws.md
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
                    "route53:ListResourceRecordSets",
                    "route53:ListTagsForResource"
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
        version="1.13.0",
        fetch_opts=FetchOpts(
        repo="https://kubernetes-sigs.github.io/external-dns",
        ),
        namespace="kube-system",
        values={
        "provider": "aws",
        "sources": ["service", "ingress"],
        "policy": "sync",
        "deploymentStrategy":
            "type": "Recreate",
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

pulumi.export("eks_sa_role_aws_load_balancer_controller", eks_sa_role_aws_load_balancer_controller.name)
pulumi.export("eks_sa_role_external_dns", eks_sa_role_external_dns.name)
