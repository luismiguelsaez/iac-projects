"""
Simple EKS cluster with a single node group  
"""

# Import components
import vpc
import iam
import tools
import helm

import pulumi
from pulumi_aws import eks, ec2, get_caller_identity
from pulumi_kubernetes import Provider as kubernetes_provider
from pulumi_kubernetes.core.v1 import Namespace, Service
from pulumi_kubernetes.admissionregistration.v1 import MutatingWebhookConfiguration, ValidatingWebhookConfiguration


aws_config = pulumi.Config("aws")
aws_region = aws_config.require("region")

aws_eks_config = pulumi.Config("aws-eks-cluster")
eks_version = aws_eks_config.require("eks_version")
eks_name_prefix = aws_eks_config.require("name_prefix")

ingress_config = pulumi.Config("ingress")
ingress_acm_cert_arn = ingress_config.require("acm_certificate_arn")

aws_config = pulumi.Config("networking")
cilium_enabled = aws_config.require_bool("cilium_enabled")

"""
Create EKS cluster
"""
eks_cluster = eks.Cluster(
    name=eks_name_prefix,
    resource_name=eks_name_prefix,
    version=eks_version,
    role_arn=iam.eks_cluster_role.arn,
    vpc_config=eks.ClusterVpcConfigArgs(
        endpoint_private_access=True,
        endpoint_public_access=True,
        public_access_cidrs=[
            # Allow access to current public IP to the API server
            f"{tools.get_public_ip()}/32",
        ],
        security_group_ids=[vpc.security_group.id],
        subnet_ids=[ s.id for s in vpc.private_subnets ],
    ),
    enabled_cluster_log_types=[
        "api",
        "audit",
    ],
    tags={
        "Name": eks_name_prefix,
    },
    opts=pulumi.resource.ResourceOptions(depends_on=[iam.eks_cluster_role, vpc.security_group]),
)

oidc_provider = iam.create_oidc_provider(
    name=f"{eks_name_prefix}-oidc-provider",
    eks_issuer_url=eks_cluster.identities[0].oidcs[0].issuer,
    aws_region=aws_region,
    depends_on=[eks_cluster]
)

"""
Create default EKS node group
"""
eks_node_group_key_pair = ec2.KeyPair(
    eks_name_prefix,
    public_key=tools.get_ssh_public_key("id_rsa.pub"),
)

eks_node_group = eks.NodeGroup(
    f"{eks_name_prefix}-default",
    cluster_name=eks_cluster.name,
    node_group_name="default",
    node_role_arn=iam.ec2_role.arn,
    subnet_ids=[ s.id for s in vpc.private_subnets ],
    scaling_config=eks.NodeGroupScalingConfigArgs(
        desired_size=3,
        max_size=10,
        min_size=1,
    ),
    instance_types=["t3.medium"],
    capacity_type="ON_DEMAND",
    disk_size=20,
    update_config=eks.NodeGroupUpdateConfigArgs(
        max_unavailable=1,
    ),
    taints=[
        eks.NodeGroupTaintArgs(
            key="node.cilium.io/agent-not-ready",
            value="true",
            effect="NO_EXECUTE",
        )
    ] if cilium_enabled else [],
    labels={
        "role": "default",
    },
    remote_access=eks.NodeGroupRemoteAccessArgs(
        ec2_ssh_key=eks_node_group_key_pair.key_name,
        source_security_group_ids=[],
    ),
    tags={
        "Name": f"{eks_name_prefix}-default",
        "k8s.io/cluster-autoscaler/enabled": "true",
    },
)

pulumi.export("eks_cluster_name", eks_cluster.name)
pulumi.export("eks_cluster_endpoint", eks_cluster.endpoint)
pulumi.export("eks_cluster_oidc_issuer", eks_cluster.identities[0].oidcs[0].issuer)
pulumi.export("kubeconfig", tools.create_kubeconfig(eks_cluster=eks_cluster, region=aws_region))
pulumi.export("eks_node_group_role_instance_profile", iam.ec2_role_instance_profile.name)

aws_account_id = get_caller_identity().account_id

k8s_provider = kubernetes_provider(
    "k8s-provider",
    kubeconfig=tools.create_kubeconfig(eks_cluster=eks_cluster, region=aws_region),
    opts=pulumi.ResourceOptions(depends_on=[eks_cluster]),
)

"""
Create cloud controllers service account roles
"""
eks_sa_role_aws_load_balancer_controller = iam.create_role_oidc(f"{eks_name_prefix}-aws-load-balancer-controller", oidc_provider.arn)
eks_sa_role_cluster_autoscaler = iam.create_role_oidc(f"{eks_name_prefix}-cluster-autoscaler", oidc_provider.arn)
eks_sa_role_external_dns = iam.create_role_oidc(f"{eks_name_prefix}-external-dns", oidc_provider.arn)
eks_sa_role_karpenter = iam.create_role_oidc(f"{eks_name_prefix}-karpenter", oidc_provider.arn)
eks_sa_role_ebs_csi_driver = iam.create_role_oidc(f"{eks_name_prefix}-ebs-csi-driver", oidc_provider.arn)

iam.create_role_policy_attachment(f"{eks_name_prefix}-aws-load-balancer-controller", eks_sa_role_aws_load_balancer_controller.name, iam.eks_policy_aws_load_balancer_controller.arn)
iam.create_role_policy_attachment(f"{eks_name_prefix}-karpenter", eks_sa_role_karpenter.name, iam.eks_policy_karpenter.arn)
iam.create_role_policy_attachment(f"{eks_name_prefix}-cluster-autoscaler", eks_sa_role_cluster_autoscaler.name, iam.eks_policy_cluster_autoscaler.arn)
iam.create_role_policy_attachment(f"{eks_name_prefix}-external-dns", eks_sa_role_external_dns.name, iam.eks_policy_external_dns.arn)
iam.create_role_policy_attachment(f"{eks_name_prefix}-ebs-csi-driver", eks_sa_role_ebs_csi_driver.name, iam.eks_policy_ebs_csi_driver.arn)

"""
Create Kubernetes namespaces
"""
k8s_namespace_controllers = Namespace(
    resource_name="cloud-controllers",
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[eks_cluster, eks_node_group])
)
k8s_namespace_ingress = Namespace(
    resource_name="ingress",
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[eks_cluster, eks_node_group])
)

"""
Create Helm charts    
"""
if cilium_enabled:
    helm_cilium_chart = helm.release(name="cilium",
                chart="cilium",
                version="1.14.1",
                repo="https://helm.cilium.io",
                namespace="kube-system",
                skip_await=False,
                depends_on=[eks_cluster, eks_node_group],
                provider=k8s_provider,
                values={
                    "cluster": {
                        "name": eks_cluster.name,
                        "id": 0,
                    },
                    "eni": {
                        "enabled": True,
                    },
                    "ipam": {
                        "mode": "eni",
                    },
                    "egressMasqueradeInterfaces": "eth0",
                    "routingMode": "native",
                    "hubble": {
                        "enabled": True,
                    }
                },
    )
    helm_cilium_chart_status=helm_cilium_chart.status

helm_aws_load_balancer_controller_chart = helm.release(
    name="aws-load-balancer-controller",
    chart="aws-load-balancer-controller",
    version="1.6.0",
    repo="https://aws.github.io/eks-charts",
    namespace=k8s_namespace_controllers.metadata.name,
    skip_await=False,
    depends_on=[eks_cluster, eks_node_group],
    provider=k8s_provider,
    #transformations=[tools.ignore_changes],
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
)

"""
Ensure that the webhooks are created
"""
helm_aws_load_balancer_controller_chart_status = helm_aws_load_balancer_controller_chart.status
aws_load_balancer_service = Service.get(
    resource_name="aws-load-balancer-webhook-service",
    id=pulumi.Output.concat(helm_aws_load_balancer_controller_chart_status.namespace, "/aws-load-balancer-webhook-service"),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[helm_aws_load_balancer_controller_chart])
)
aws_load_balancer_mutating_webhook = MutatingWebhookConfiguration.get(
    resource_name="aws-load-balancer-webhook",
    id=pulumi.Output.concat(helm_aws_load_balancer_controller_chart_status.namespace, "/aws-load-balancer-webhook"),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[helm_aws_load_balancer_controller_chart])
)
aws_load_balancer_validating_webhook = ValidatingWebhookConfiguration.get(
    resource_name="aws-load-balancer-webhook",
    id=pulumi.Output.concat(helm_aws_load_balancer_controller_chart_status.namespace, "/aws-load-balancer-webhook"),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[helm_aws_load_balancer_controller_chart])
)

helm_external_dns_chart = helm.release(
    name="external-dns",
    chart="external-dns",
    version="1.13.0",
    repo="https://kubernetes-sigs.github.io/external-dns",
    namespace=k8s_namespace_controllers.metadata.name,
    skip_await=False,
    depends_on=[eks_cluster, eks_node_group, helm_aws_load_balancer_controller_chart],
    provider=k8s_provider,
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
)
helm_external_dns_chart_status=helm_external_dns_chart.status

helm_cluster_autoscaler_chart = helm.chart(
    name="cluster-autoscaler",
    chart="cluster-autoscaler",
    version="9.29.2",
    repo="https://kubernetes.github.io/autoscaler",
    namespace=k8s_namespace_controllers.metadata.name,
    skip_await=False,
    depends_on=[eks_cluster, eks_node_group, helm_aws_load_balancer_controller_chart],
    provider=k8s_provider,
    transformations=[tools.ignore_changes],
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
)

helm_karpenter_chart = helm.chart(
    name="karpenter",
    chart="karpenter",
    version="0.16.3",
    repo="https://charts.karpenter.sh",
    namespace=k8s_namespace_controllers.metadata.name,
    skip_await=False,
    depends_on=[eks_cluster, eks_node_group, helm_aws_load_balancer_controller_chart],
    provider=k8s_provider,
    transformations=[tools.ignore_changes],
    values={
        "serviceAccount": {
            "annotations": {
                "eks.amazonaws.com/role-arn": eks_sa_role_karpenter.arn,
            },
        },
        "clusterName": eks_cluster.name,
        "clusterEndpoint": eks_cluster.endpoint,
        "aws": {
            "defaultInstanceProfile": "AmazonSSMManagedInstanceCore",
        },
    },
)

helm_ingress_nginx_chart = helm.release(
    name="ingress-nginx",
    chart="ingress-nginx",
    version="4.2.5",
    repo="https://kubernetes.github.io/ingress-nginx",
    namespace=k8s_namespace_ingress.metadata.name,
    skip_await=False,
    depends_on=[eks_cluster, eks_node_group, helm_aws_load_balancer_controller_chart, helm_external_dns_chart],
    provider=k8s_provider,
    values={
        "admissionWebhooks": {
            "enabled": True
        },
        "controller": {
            "kind": "DaemonSet",
            "healthCheckPath": "/healthz",
            "lifecycle": {
                "preStop": {
                    "exec": {
                        "command": [
                            "/wait-shutdown",
                        ]
                    }
                }
            },
            "priorityClassName": "system-node-critical",
            "ingressClassByName": True,
            "ingressClass": "nginx-internet-facing",
            "ingressClassResource": {
                "name": "nginx-internet-facing",
                "enabled": True,
                "default": False,
                "controllerValue": "k8s.io/ingress-nginx-internet-facing"
            },
            "electionID": "ingress-controller-external-leader",
            "config": {
                "use-forwarded-headers": True,
                "use-proxy-protocol": True,
                "log-format-upstream": '$remote_addr - $host [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent" $request_length $request_time [$proxy_upstream_name] [$proxy_alternative_upstream_name] $upstream_addr $upstream_response_length $upstream_response_time $upstream_status $req_id'
            },
            "service": {
                "enabled": True,
                "type": "LoadBalancer",
                "enableHttp": False,
                "enableHttps": True,
                "ports": {
                    "http": 80,
                    "https": 443
                },
                "targetPorts": {
                    "http": "http",
                    "https": "http"
                },
                "httpPort": {
                    "enable": False,
                    "targetPort": "http"
                },
                "httpsPort": {
                    "enable": True,
                    "targetPort": "http"
                },
                "annotations": {
                    "service.beta.kubernetes.io/aws-load-balancer-name": "k8s-ingress-internet-facing",
                    "service.beta.kubernetes.io/aws-load-balancer-type": "external",
                    "service.beta.kubernetes.io/aws-load-balancer-scheme": "internet-facing",
                    "service.beta.kubernetes.io/aws-load-balancer-nlb-target-type": "instance",
                    "service.beta.kubernetes.io/aws-load-balancer-backend-protocol": "tcp",
                    "service.beta.kubernetes.io/load-balancer-source-ranges": "0.0.0.0/0",
                    "service.beta.kubernetes.io/aws-load-balancer-manage-backend-security-group-rules": True,
                    "service.beta.kubernetes.io/aws-load-balancer-connection-idle-timeout": 300,
                    "service.beta.kubernetes.io/aws-load-balancer-attributes": "load_balancing.cross_zone.enabled=true",
                    # SSL options
                    "service.beta.kubernetes.io/aws-load-balancer-ssl-ports": 443,
                    "service.beta.kubernetes.io/aws-load-balancer-ssl-cert": ingress_acm_cert_arn,
                    "service.beta.kubernetes.io/aws-load-balancer-ssl-negotiation-policy": "ELBSecurityPolicy-TLS13-1-2-2021-06",
                    # Health check options
                    "service.beta.kubernetes.io/aws-load-balancer-healthcheck-protocol": "tcp",
                    "service.beta.kubernetes.io/aws-load-balancer-healthcheck-path": "/nginx-health",
                    "service.beta.kubernetes.io/aws-load-balancer-healthcheck-timeout": 10,
                    # Proxy protocol options
                    "service.beta.kubernetes.io/aws-load-balancer-proxy-protocol": "*",
                }
            },
        },
    }
)
helm_ingress_nginx_chart_status=helm_ingress_nginx_chart.status

helm_metrics_server_chart = helm.release(
    name="metrics-server",
    chart="metrics-server",
    version="3.11.0",
    repo="https://kubernetes-sigs.github.io/metrics-server",
    namespace="kube-system",
    skip_await=False,
    depends_on=[eks_cluster, eks_node_group, helm_aws_load_balancer_controller_chart],
    provider=k8s_provider,
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
)
helm_metrics_server_chart_status=helm_metrics_server_chart.status
