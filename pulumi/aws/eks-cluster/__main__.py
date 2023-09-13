import pulumi
from pulumi_aws import eks, ec2, get_caller_identity
from pulumi_kubernetes import Provider as kubernetes_provider
from pulumi_kubernetes.core.v1 import Namespace, Service
from pulumi_kubernetes.admissionregistration.v1 import MutatingWebhookConfiguration, ValidatingWebhookConfiguration
import pulumi_random

import vpc, iam, s3, tools, k8s

#from helm import releases
from python_pulumi_helm import releases

"""
Get Pulumi config values
"""
aws_config = pulumi.Config("aws")
aws_region = aws_config.require("region")

aws_eks_config = pulumi.Config("aws-eks-cluster")
eks_version = aws_eks_config.require("eks_version")
eks_name_prefix = aws_eks_config.require("name_prefix")

ingress_config = pulumi.Config("ingress")
ingress_acm_cert_arn = ingress_config.require("acm_certificate_arn")
ingress_domain_name = ingress_config.require("domain_name")

github_config = pulumi.Config("github")
github_user = github_config.require("user")

# Charts configuration
prometheus_config = pulumi.Config("prometheus")
helm_config = pulumi.Config("helm")
argocd_config = pulumi.Config("argocd")
opensearch_config = pulumi.Config("opensearch")

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
        subnet_ids=[ s.id for s in vpc.private_subnets ],
    ),
    enabled_cluster_log_types=[
        "api",
        "audit",
    ],
    tags={
        "Name": eks_name_prefix,
    },
    opts=pulumi.resource.ResourceOptions(depends_on=[iam.eks_cluster_role]),
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
    public_key=tools.get_ssh_public_key_from_gh(github_user),
)

eks_node_group = eks.NodeGroup(
    f"{eks_name_prefix}-system",
    cluster_name=eks_cluster.name,
    node_group_name="system",
    node_role_arn=iam.ec2_role.arn,
    subnet_ids=[ s.id for s in vpc.private_subnets ],
    scaling_config=eks.NodeGroupScalingConfigArgs(
        desired_size=3,
        max_size=10,
        min_size=1,
    ),
    instance_types=["t4g.medium"],
    capacity_type="ON_DEMAND",
    ami_type="BOTTLEROCKET_ARM_64",
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
    ] if helm_config.require_bool("cilium") else [],
    labels={
        "role": "system",
    },
    remote_access=eks.NodeGroupRemoteAccessArgs(
        ec2_ssh_key=eks_node_group_key_pair.key_name,
        source_security_group_ids=[],
    ),
    tags={
        "Name": f"{eks_name_prefix}-system",
        "k8s.io/cluster-autoscaler/enabled": "true",
    },
)

pulumi.export("eks_cluster_name", eks_cluster.name)
pulumi.export("eks_cluster_endpoint", eks_cluster.endpoint)
pulumi.export("eks_cluster_oidc_issuer", eks_cluster.identities[0].oidcs[0].issuer)
pulumi.export("kubeconfig", tools.create_kubeconfig(eks_cluster=eks_cluster, region=aws_region))
pulumi.export("eks_node_group_role_instance_profile", iam.ec2_role_instance_profile.name)

aws_account_id = get_caller_identity().account_id

"""
Create Kubernetes provider from EKS cluster Kubernetes config
"""
k8s_provider = kubernetes_provider(
    "k8s-provider",
    kubeconfig=tools.create_kubeconfig(eks_cluster=eks_cluster, region=aws_region),
    opts=pulumi.ResourceOptions(depends_on=[eks_cluster]),
)

"""
Create cloud controllers service account roles
"""
# Try: https://www.pulumi.com/registry/packages/aws-iam/api-docs/roleforserviceaccountseks
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
    metadata={
        "name": "cloud-controllers",
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[eks_cluster, eks_node_group])
)

"""
Create Helm charts    
"""
require_cilium = []
if helm_config.require_bool("cilium"):
    helm_cilium_chart = releases.cilium(
        provider=k8s_provider,
        eks_cluster_name=eks_cluster.name,
        depends_on=[eks_cluster, eks_node_group],
    )
    helm_cilium_chart_status=helm_cilium_chart.status
    require_cilium = [helm_cilium_chart]
"""
Install AWS Load Balancer Controller
"""
helm_aws_load_balancer_controller_chart = releases.aws_load_balancer_controller(
    provider=k8s_provider,
    aws_region=aws_region,
    aws_vpc_id=vpc.vpc.id,
    eks_sa_role_arn=eks_sa_role_aws_load_balancer_controller.arn,
    eks_cluster_name=eks_cluster.name,
    namespace=k8s_namespace_controllers.metadata.name,
    depends_on=[eks_cluster, eks_node_group] + require_cilium,
)

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

"""
Install External DNS
"""
helm_external_dns_chart = releases.external_dns(
    provider=k8s_provider,
    eks_sa_role_arn=eks_sa_role_external_dns.arn,
    namespace=k8s_namespace_controllers.metadata.name,
    depends_on=[eks_cluster, eks_node_group],
)
helm_external_dns_chart_status=helm_external_dns_chart.status

"""
Install Cluster Autoscaler
"""
helm_cluster_autoscaler_chart = releases.cluster_autoscaler(
    provider=k8s_provider,
    aws_region=aws_region,
    eks_sa_role_arn=eks_sa_role_cluster_autoscaler.arn,
    eks_cluster_name=eks_cluster.name,
    namespace=k8s_namespace_controllers.metadata.name,
    depends_on=[eks_cluster, eks_node_group, helm_aws_load_balancer_controller_chart],
)

"""
Install AWS CSI Driver
"""
if helm_config.require_bool("aws_csi_driver"):
    helm_ebs_csi_driver_chart = releases.aws_ebs_csi_driver(
        provider=k8s_provider,
        eks_sa_role_arn=eks_sa_role_ebs_csi_driver.arn,
        default_storage_class_name="ebs",
        namespace=k8s_namespace_controllers.metadata.name,
        depends_on=[eks_cluster, eks_node_group]
    )
    helm_ebs_csi_driver_chart_status=helm_ebs_csi_driver_chart.status


"""
Install Metrics Server
"""
if helm_config.require_bool("metrics_server"):
    helm_metrics_server_chart = releases.metrics_server(
        provider=k8s_provider,
        depends_on=[eks_cluster, eks_node_group],
    )
    helm_metrics_server_chart_status=helm_metrics_server_chart.status

"""
Install Karpenter
"""
if helm_config.require_bool("karpenter"):
    helm_karpenter_chart = releases.karpenter(
        namespace=k8s_namespace_controllers.metadata.name,
        provider=k8s_provider,
        eks_sa_role_arn=eks_sa_role_karpenter.arn,
        eks_cluster_name=eks_cluster.name,
        eks_cluster_endpoint=eks_cluster.endpoint,
        default_instance_profile_name=iam.ec2_role_instance_profile.name,
        depends_on=[eks_cluster, eks_node_group, helm_aws_load_balancer_controller_chart],
    )

    helm_karpenter_chart_status = helm_karpenter_chart.status
    karpenter_validating_webhook_config = ValidatingWebhookConfiguration.get(
        resource_name="validation.webhook.config.karpenter.sh",
        id=pulumi.Output.concat(helm_karpenter_chart_status.namespace, "/validation.webhook.config.karpenter.sh"),
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[helm_karpenter_chart])
    )
    karpenter_validating_webhook_provisioners = ValidatingWebhookConfiguration.get(
        resource_name="validation.webhook.provisioners.karpenter.sh",
        id=pulumi.Output.concat(helm_karpenter_chart_status.namespace, "/validation.webhook.provisioners.karpenter.sh"),
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[helm_karpenter_chart])
    )
    karpenter_mutating_webhook_provisioners = MutatingWebhookConfiguration.get(
        resource_name="defaulting.webhook.provisioners.karpenter.sh",
        id=pulumi.Output.concat(helm_karpenter_chart_status.namespace, "/defaulting.webhook.provisioners.karpenter.sh"),
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[helm_karpenter_chart])
    )

    """
    Create cluster-wide AWSNodeTemplates
    """
    karpenter_template_default = k8s.karpenter_templates(
        name="karpenter-awsnodetemplate",
        manifests_path="k8s/manifests/karpenter/awsnodetemplate",
        eks_cluster_name=eks_name_prefix,
        provider=k8s_provider,
        depends_on=[eks_cluster, eks_node_group, helm_karpenter_chart],
    )

"""
Install Prometheus Stack
"""
if helm_config.require_bool("prometheus_stack"):
    k8s_namespace_prometheus = Namespace(
        resource_name="prometheus",
        metadata={
            "name": "prometheus",
        },
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[eks_cluster, eks_node_group])
    )

    thanos_s3_bucket_random_string = "0n9f3ofow90m"
    #thanos_s3_bucket_random_string = pulumi_random.RandomString(
    #    resource_name="thanos-s3-bucket-random-string",
    #    length=10,
    #    special=False,
    #    upper=False,
    #    number=False,
    #    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[eks_cluster, eks_node_group])
    #).result
    thanos_s3_bucket_name = ""
    thanos_iam_role_arn = ""

    if helm_config.require_bool("thanos"):
        thanos_s3_bucket_name = f"{pulumi.get_stack()}-thanos-{thanos_s3_bucket_random_string}"
        #thanos_s3_bucket_name = pulumi.Output.concat(pulumi.get_stack(), "-thanos-", thanos_s3_bucket_random_string)
        eks_sa_role_thanos_storage = iam.create_role_oidc("thanos-storage", oidc_provider.arn)
        thanos_iam_role_arn = eks_sa_role_thanos_storage.arn
        thanos_s3_bucket = s3.bucket_with_allowed_roles(name=thanos_s3_bucket_name, acl="private", force_destroy=True, roles=[eks_sa_role_thanos_storage.arn])

    helm_prometheus_stack_chart = releases.prometheus_stack(
        ingress_domain=ingress_domain_name,
        ingress_class_name="nginx-external",
        storage_class_name="ebs",
        prometheus_external_label_env = pulumi.get_stack(),
        prometheus_tsdb_retention=prometheus_config.require("tsdb_retention"),
        eks_sa_role_arn=thanos_iam_role_arn,
        thanos_enabled=helm_config.require_bool("thanos"),
        name_override="prom-stack",
        obj_storage_bucket=thanos_s3_bucket_name,
        provider=k8s_provider,
        namespace=k8s_namespace_prometheus.metadata.name,
        depends_on=[eks_cluster, eks_node_group, helm_aws_load_balancer_controller_chart, helm_external_dns_chart],  
    )
    helm_prometheus_stack_chart_status = helm_prometheus_stack_chart.status
    # Service name is based on the fullnameOverride of the Prometheus chart ( `name_override="prom-stack"` )
    prometheus_service = Service.get(
        resource_name="prom-stack-prometheus-service",
        id=pulumi.Output.concat(helm_prometheus_stack_chart_status.namespace, "/prom-stack-prometheus"),
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[helm_prometheus_stack_chart])
    )

    if helm_config.require_bool("thanos"):
        # Service name is based on the fullnameOverride of the Prometheus chart ( `name_override="prom-stack"` )
        prometheus_thanos_service = Service.get(
            resource_name="prom-stack-prometheus-thanos-service",
            id=pulumi.Output.concat(helm_prometheus_stack_chart_status.namespace, "/prom-stack-thanos-discovery"),
            opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[helm_prometheus_stack_chart])
        )
        releases.thanos_stack(
            aws_region=aws_region,
            ingress_domain=ingress_domain_name,
            ingress_class_name="nginx-external",
            storage_class_name="ebs",
            name_override="thanos-stack",
            eks_sa_role_arn=thanos_iam_role_arn,
            obj_storage_bucket=thanos_s3_bucket_name,
            provider=k8s_provider,
            namespace=k8s_namespace_prometheus.metadata.name,
            depends_on=[eks_cluster, eks_node_group, helm_aws_load_balancer_controller_chart, helm_external_dns_chart],  
        )

"""
Install ingress controllers
"""
if helm_config.require_bool("ingress_nginx"):
    k8s_namespace_ingress = Namespace(
        resource_name="ingress",
        metadata={
            "name": "ingress",
        },
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[eks_cluster, eks_node_group])
    )
    helm_ingress_nginx_chart = releases.ingress_nginx(
        provider=k8s_provider,
        name="ingress-nginx-internet-facing",
        name_suffix="external",
        public=True,
        ssl_enabled=True,
        acm_cert_arns=[ingress_acm_cert_arn],
        metrics_enabled=helm_config.require_bool("prometheus_stack"),
        namespace=k8s_namespace_ingress.metadata.name,
        depends_on=[eks_cluster, eks_node_group, helm_aws_load_balancer_controller_chart, helm_external_dns_chart],
    )
    helm_ingress_nginx_chart_status=helm_ingress_nginx_chart.status

    helm_ingress_nginx_internal_chart = releases.ingress_nginx(
        provider=k8s_provider,
        name="ingress-nginx-internal",
        name_suffix="internal",
        public=False,
        ssl_enabled=True,
        acm_cert_arns=[ingress_acm_cert_arn],
        metrics_enabled=helm_config.require_bool("prometheus_stack"),
        namespace=k8s_namespace_ingress.metadata.name,
        depends_on=[eks_cluster, eks_node_group, helm_aws_load_balancer_controller_chart, helm_external_dns_chart],
    )
    helm_ingress_nginx_internal_chart_status=helm_ingress_nginx_internal_chart.status

"""
Install Opensearch cluster
"""
if helm_config.require_bool("opensearch"):
    k8s_namespace_prometheus = Namespace(
        resource_name="opensearch",
        metadata={
            "name": "opensearch",
        },
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[eks_cluster, eks_node_group])
    )
    releases.opensearch(
        ingress_domain=ingress_domain_name,
        ingress_class_name="nginx-internal",
        storage_class_name="ebs",
        storage_size=opensearch_config.require("storage_size"),
        replicas=opensearch_config.require_int("replicas"),
        karpenter_node_enabled=helm_config.require_bool("karpenter"),
        karpenter_node_provider_name="default",
        resources_memory_mb=opensearch_config.require("memory_mb"),
        resources_cpu=opensearch_config.require("cpu"),
        provider=k8s_provider,
        namespace=k8s_namespace_prometheus.metadata.name,
        depends_on=[eks_cluster, eks_node_group, helm_aws_load_balancer_controller_chart, helm_external_dns_chart],  
    )

"""
Install ArgoCD
"""
if helm_config.require_bool("argocd"):
    k8s_namespace_argocd = Namespace(
        resource_name="argocd",
        metadata={
            "name": "argocd",
        },
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[eks_cluster, eks_node_group])
    )
    releases.argocd(
        ingress_hostname=f"argocd.{ingress_domain_name}",
        ingress_protocol="https",
        ingress_class_name="nginx-external",
        argocd_redis_ha_enabled=argocd_config.require_bool("ha_enabled"),
        argocd_redis_ha_haproxy_enabled=True,
        argocd_application_controller_replicas=argocd_config.require_int("application_controller_replicas"),
        argocd_applicationset_controller_replicas=argocd_config.require_int("applicationset_controller_replicas"),
        provider=k8s_provider,
        namespace=k8s_namespace_argocd.metadata.name,
        depends_on=[eks_cluster, eks_node_group, helm_aws_load_balancer_controller_chart, helm_external_dns_chart],  
    )
