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
from pulumi_kubernetes import yaml as kubernetes_yaml

import json

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
    opts=pulumi.resource.ResourceOptions(depends_on=[iam.eks_cluster_role, vpc.security_group]),
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
        max_size=10,
        min_size=1,
    ),
    instance_types=["t3.medium"],
    tags={
        "Name": f"{eks_name_prefix}-default",
        "k8s.io/cluster-autoscaler/enabled": "true",
        f"k8s.io/cluster-autoscaler/{eks_cluster.name}": "owned",
    },
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

with open(path.join(path.dirname(__file__), "iam/policies", "aws-load-balancer-controller.json")) as f:
    policy_aws_load_balancer_controller = json.loads(f.read())

# https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.6.0/docs/install/iam_policy.json
eks_policy_aws_load_balancer_controller = aws_iam.Policy(
    f"{eks_name_prefix}-aws-load-balancer-controller",
    policy=pulumi.Output.json_dumps(policy_aws_load_balancer_controller)
)

aws_iam.RolePolicyAttachment(
    f"{eks_name_prefix}-aws-load-balancer-controller",
    policy_arn=eks_policy_aws_load_balancer_controller.arn,
    role=eks_sa_role_aws_load_balancer_controller.name,
)

k8s_provider = kubernetes_provider(
    "k8s-provider",
    kubeconfig=tools.create_kubeconfig(eks_cluster=eks_cluster, region=aws_region),
    opts=pulumi.ResourceOptions(depends_on=[eks_cluster]),
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

with open(path.join(path.dirname(__file__), "iam/policies", "external-dns.json")) as f:
    policy_external_dns = json.loads(f.read())

# https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/aws.md
eks_policy_external_dns = aws_iam.Policy(
    f"{eks_name_prefix}-external-dns",
    policy=pulumi.Output.json_dumps(policy_external_dns)
)

aws_iam.RolePolicyAttachment(
    f"{eks_name_prefix}-external-dns",
    policy_arn=eks_policy_external_dns.arn,
    role=eks_sa_role_external_dns.name,
)

helm_aws_load_balancer_controller_chart = Chart(
    release_name="aws-load-balancer-controller",
    config=ChartOpts(
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
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[eks_cluster, eks_node_group],
        transformations=[tools.ignore_changes],
    ),
)

helm_external_dns_chart = Chart(
    release_name="external-dns",
    config=ChartOpts(
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
            "deploymentStrategy": {
                "type": "Recreate",
            },
            "serviceAccount": {
                "create": True,
                "annotations": {
                    "eks.amazonaws.com/role-arn": eks_sa_role_external_dns.arn,
                },
            }
        },
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[eks_cluster, eks_node_group]),
)

helm_metrics_server_chart = Chart(
    release_name="metrics-server",
    config=ChartOpts(
        chart="metrics-server",
        version="3.11.0",
        fetch_opts=FetchOpts(
        repo="https://kubernetes-sigs.github.io/metrics-server",
        ),
        namespace="kube-system",
        values={
            "resources": {
                "limits": {
                    "cpu": "200m",
                    "memory": "200Mi"
                },
                "requests": {
                    "cpu": "200m",
                    "memory": "200Mi"
                }
            }
        },
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[eks_cluster, eks_node_group,]),
)

eks_sa_role_karpenter = aws_iam.Role(
    f"{eks_name_prefix}-karpenter",
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

with open(path.join(path.dirname(__file__), "iam/policies", "karpenter.json")) as f:
    policy_karpenter = json.loads(f.read())

# https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/aws.md
eks_policy_karpenter = aws_iam.Policy(
    f"{eks_name_prefix}-karpenter",
    policy=pulumi.Output.json_dumps(policy_karpenter)
)

aws_iam.RolePolicyAttachment(
    f"{eks_name_prefix}-karpenter",
    policy_arn=eks_policy_karpenter.arn,
    role=eks_sa_role_karpenter.name,
)

helm_karpenter_chart = Chart(
    release_name="karpenter",
    config=ChartOpts(
        chart="karpenter",
        version="0.16.3",
        fetch_opts=FetchOpts(
            repo="https://charts.karpenter.sh",
        ),
        namespace="kube-system",
        values={
            "serviceAccount": {
                "create": True,
                "annotations": {
                    "eks.amazonaws.com/role-arn": eks_sa_role_karpenter.arn,
                },
            },
            "clusterEndpoint": eks_cluster.endpoint,
            "clusterName": eks_cluster.name,
            "settings": {
                "aws": {
                    "defaultInstanceProfile": f"{eks_cluster.name}-KarpenterNode"
                }
            },
            "extraObjects": []
        },
    ),
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[eks_cluster, eks_node_group, helm_aws_load_balancer_controller_chart],
        transformations=[tools.ignore_changes],
    ),
)

eks_sa_role_cluster_autoscaler = aws_iam.Role(
    f"{eks_name_prefix}-cluster-autoscaler",
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

with open(path.join(path.dirname(__file__), "iam/policies", "cluster-autoscaler.json")) as f:
    policy_cluster_autoscaler = json.loads(f.read())

# https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/aws.md
eks_policy_cluster_autoscaler = aws_iam.Policy(
    f"{eks_name_prefix}-cluster-autoscaler",
    policy=pulumi.Output.json_dumps(policy_cluster_autoscaler)
)

aws_iam.RolePolicyAttachment(
    f"{eks_name_prefix}-cluster-autoscaler",
    policy_arn=eks_policy_cluster_autoscaler.arn,
    role=eks_sa_role_cluster_autoscaler.name,
)

helm_karpenter_chart = Chart(
    release_name="cluster-autoscaler",
    config=ChartOpts(
        chart="cluster-autoscaler",
        version="9.29.2",
        fetch_opts=FetchOpts(
            repo="https://kubernetes.github.io/autoscaler",
        ),
        namespace="kube-system",
        values={
            "cloudProvider": "aws",
            "awsRegion": aws_region,
            "autoDiscovery": {
                "clusterName": eks_cluster.name,
                "tags": [
                    "k8s.io/cluster-autoscaler/enabled"
                ],
                "roles": ["worker"],
            },
            "rbac": {
                "create": True,
                "serviceAccount": {
                    "create": True,
                    "name": "cluster-autoscaler",
                    "automountServiceAccountToken": True,
                    "annotations": {
                        "eks.amazonaws.com/role-arn": eks_sa_role_cluster_autoscaler.arn,
                    }
                }
            },
            "resources": {
                "limits": {
                    "cpu": "200m",
                    "memory": "200Mi"
                },
                "requests": {
                    "cpu": "200m",
                    "memory": "200Mi"
                }
            },
        },
    ),
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[eks_cluster, eks_node_group, helm_aws_load_balancer_controller_chart],
        transformations=[tools.ignore_changes],
    ),
)

pulumi.export("eks_sa_role_aws_load_balancer_controller", eks_sa_role_aws_load_balancer_controller.name)
pulumi.export("eks_sa_role_external_dns", eks_sa_role_external_dns.name)

nginx_deployment = kubernetes_yaml.ConfigFile(
    name='nginx',
    file=path.join(path.dirname(__file__), "k8s/manifests", "deployment.yaml"),
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[eks_cluster, eks_node_group, helm_aws_load_balancer_controller_chart, helm_external_dns_chart]
    ),
)

#nginx_endpoint = nginx_deployment.get_resource('networking.k8s.io/v1/Ingress', 'nginx-ingress')
#pulumi.export('nginx_deployment_endpoint', nginx_endpoint.spec.rules[0].host)
