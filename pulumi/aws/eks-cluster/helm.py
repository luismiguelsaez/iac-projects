from pulumi import ResourceOptions
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts, Release, ReleaseArgs, RepositoryOptsArgs
from pulumi_kubernetes import Provider

def release(
  provider,
  name: str,
  chart: str,
  version: str,
  repo: str,
  namespace: str = "default",
  skip_await: bool = False,
  values: dict = {},
  depends_on: list = []
  )->Release:
  
  repo_opts_args = RepositoryOptsArgs(
    repo=repo
  )

  release_args = ReleaseArgs(
    chart=chart,
    version=version,
    repository_opts=repo_opts_args,
    namespace=namespace,
    skip_await=skip_await,
    values=values
  )
  
  resource_options = ResourceOptions(provider=provider, depends_on=depends_on)

  release = Release(
    name,
    args=release_args,
    opts=resource_options
  )
  
  return release

def chart(
  provider: Provider,
  name: str,
  chart: str,
  version: str,
  repo: str,
  namespace: str = "default",
  skip_await: bool = False,
  values: dict = {},
  depends_on: list = [],
  transformations: list = []
  )->Chart:
  
  fetch_opts = FetchOpts(
    repo=repo
  )

  chart_opts = ChartOpts(
    chart=chart,
    version=version,
    fetch_opts=fetch_opts,
    namespace=namespace,
    skip_await=skip_await,
    values=values
  )

  resource_options = ResourceOptions(provider=provider, depends_on=depends_on, transformations=transformations)

  helm_chart = Chart(
    release_name=name,
    config=chart_opts,
    opts=resource_options
  )
  
  return helm_chart

def release_cilium(
    provider,
    eks_cluster_name: str = "",
    name: str = "cilium",
    chart: str = "cilium",
    version: str = "1.14.1",
    repo: str = "https://helm.cilium.io",
    namespace: str = "kube-system",
    skip_await: bool = False,
    depends_on: list = [],
  )->Release:

  cilium_release = release(
    name=name,
    chart=chart,
    version=version,
    repo=repo,
    namespace=namespace,
    skip_await=skip_await,
    depends_on=depends_on,
    provider=provider,
    values={
        "cluster": {
            "name": eks_cluster_name,
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

  return cilium_release

def release_metrics_server(
    provider,
    name: str = "metrics-server",
    chart: str = "metrics-server",
    version: str = "3.11.0",
    repo: str = "https://kubernetes-sigs.github.io/metrics-server",
    namespace: str = "kube-system",
    skip_await: bool = False,
    depends_on: list = [],
  )->Release:

  metrics_server_release = release(
    name=name,
    chart=chart,
    version=version,
    repo=repo,
    namespace=namespace,
    skip_await=skip_await,
    depends_on=depends_on,
    provider=provider,
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

  return metrics_server_release

def release_cluster_autoscaler(
    provider,
    aws_region,
    eks_sa_role_arn,
    eks_cluster_name,
    name: str = "cluster-autoscaler",
    chart: str = "cluster-autoscaler",
    version: str = "9.29.3",
    repo: str = "https://kubernetes.github.io/autoscaler",
    namespace: str = "default",
    skip_await: bool = False,
    depends_on: list = [],
  )->Release:

  cluster_autoscaler_release = release(
      name=name,
      chart=chart,
      version=version,
      repo=repo,
      namespace=namespace,
      skip_await=skip_await,
      depends_on=depends_on,
      provider=provider,
      values={
          "cloudProvider": "aws",
          "awsRegion": aws_region,
          "autoDiscovery": {
              "clusterName": eks_cluster_name,
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
                      "eks.amazonaws.com/role-arn": eks_sa_role_arn,
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
  
  return cluster_autoscaler_release

def release_aws_load_balancer_controller(
    provider,
    aws_region,
    aws_vpc_id,
    eks_sa_role_arn,
    eks_cluster_name,
    name: str = "aws-load-balancer-controller",
    chart: str = "aws-load-balancer-controller",
    version: str = "1.6.0",
    repo: str = "https://aws.github.io/eks-charts",
    namespace: str = "default",
    skip_await: bool = False,
    depends_on: list = [],
  )->Release:

  aws_load_balancer_controller_release = release(
    name=name,
    chart=chart,
    version=version,
    repo=repo,
    namespace=namespace,
    skip_await=skip_await,
    depends_on=depends_on,
    provider=provider,
    #transformations=[tools.ignore_changes],
    values={
        "clusterName": eks_cluster_name,
        "region": aws_region,
        "vpcId": aws_vpc_id,
        "serviceAccount": {
            "create": True,
            "annotations": {
                "eks.amazonaws.com/role-arn": eks_sa_role_arn,
            },
        }
    },
  )

  return aws_load_balancer_controller_release

def release_external_dns(
    provider,
    eks_sa_role_arn,
    name: str = "external-dns",
    chart: str = "external-dns",
    version: str = "1.13.0",
    repo: str = "https://kubernetes-sigs.github.io/external-dns",
    namespace: str = "default",
    skip_await: bool = False,
    depends_on: list = [],
  )->Release:

  external_dns_release = release(
    name=name,
    chart=chart,
    version=version,
    repo=repo,
    namespace=namespace,
    skip_await=skip_await,
    depends_on=depends_on,
    provider=provider,
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
                "eks.amazonaws.com/role-arn": eks_sa_role_arn,
            },
        }
    },
  )

  return external_dns_release

def release_aws_csi_driver(
    provider,
    eks_sa_role_arn,
    name: str = "aws-ebs-csi-driver",
    chart: str = "aws-ebs-csi-driver",
    version: str = "2.9.0",
    repo: str = "https://kubernetes-sigs.github.io/aws-ebs-csi-driver",
    namespace: str = "default",
    skip_await: bool = False,
    depends_on: list = [],
  )->Release:

  aws_ebs_csi_driver_release = release(
      name=name,
      chart=chart,
      version=version,
      repo=repo,
      namespace=namespace,
      skip_await=skip_await,
      depends_on=depends_on,
      provider=provider,
      values={
          "storageClasses": [
              {
                  "name": "ebs",
                  "annotations": {
                      "storageclass.kubernetes.io/is-default-class": "true",
                  },
                  "labels": {},
                  "volumeBindingMode": "WaitForFirstConsumer",
                  "reclaimPolicy": "Retain",
                  "allowVolumeExpansion": True,
                  "parameters": {
                      "encrypted": "true",
                  },
              }
          ],
          "controller": {
              "serviceAccount": {
                  "create": True,
                  "annotations": {
                      "eks.amazonaws.com/role-arn": eks_sa_role_arn,
                  },
              }
          },
          "node": {
              "serviceAccount": {
                  "create": True,
                  "annotations": {
                      "eks.amazonaws.com/role-arn": eks_sa_role_arn,
                  },
              }
          },
      },
  )

  return aws_ebs_csi_driver_release

def release_karpenter(
    provider,
    eks_sa_role_arn,
    eks_cluster_name,
    eks_cluster_endpoint,
    default_instance_profile_name,
    name: str = "karpenter",
    chart: str = "karpenter",
    version: str = "0.16.3",
    repo: str = "https://charts.karpenter.sh",
    namespace: str = "default",
    skip_await: bool = False,
    depends_on: list = [],
  )->Release:

  karpenter_release = release(
      name=name,
      chart=chart,
      version=version,
      repo=repo,
      namespace=namespace,
      skip_await=skip_await,
      depends_on=depends_on,
      provider=provider,
      #transformations=[tools.ignore_changes],
      values={
          "serviceAccount": {
              "annotations": {
                  "eks.amazonaws.com/role-arn": eks_sa_role_arn,
              },
          },
          "clusterName": eks_cluster_name,
          "clusterEndpoint": eks_cluster_endpoint,
          "aws": {
              "defaultInstanceProfile": default_instance_profile_name,
          },
      },
  )

  return karpenter_release

def release_ingress_nginx(
    provider,
    name_suffix: str = "default",
    ssl_enabled: bool = False,
    acm_cert_arns: list[str] = [],
    public: bool = True,
    proxy_protocol: bool = True,
    name: str = "ingress-nginx",
    chart: str = "ingress-nginx",
    version: str = "4.2.5",
    repo: str = "https://kubernetes.github.io/ingress-nginx",
    namespace: str = "default",
    skip_await: bool = False,
    depends_on: list = [],
  )->Release:

  service_annotations = {
    "service.beta.kubernetes.io/aws-load-balancer-name": f"k8s-{name_suffix}",
    "service.beta.kubernetes.io/aws-load-balancer-type": "external",
    "service.beta.kubernetes.io/aws-load-balancer-scheme": "internet-facing" if public else "internal",
    "service.beta.kubernetes.io/aws-load-balancer-nlb-target-type": "instance",
    "service.beta.kubernetes.io/aws-load-balancer-backend-protocol": "tcp",
    "service.beta.kubernetes.io/load-balancer-source-ranges": "0.0.0.0/0",
    "service.beta.kubernetes.io/aws-load-balancer-manage-backend-security-group-rules": True,
    "service.beta.kubernetes.io/aws-load-balancer-connection-idle-timeout": 300,
    "service.beta.kubernetes.io/aws-load-balancer-attributes": "load_balancing.cross_zone.enabled=true",
    "service.beta.kubernetes.io/aws-load-balancer-target-group-attributes": "deregistration_delay.timeout_seconds=10,deregistration_delay.connection_termination.enabled=true",
    # Health check options
    "service.beta.kubernetes.io/aws-load-balancer-healthcheck-protocol": "tcp",
    "service.beta.kubernetes.io/aws-load-balancer-healthcheck-path": "/healthz",
    "service.beta.kubernetes.io/aws-load-balancer-healthcheck-timeout": 2,
    "service.beta.kubernetes.io/aws-load-balancer-healthcheck-healthy-threshold": 5,
    "service.beta.kubernetes.io/aws-load-balancer-healthcheck-unhealthy-threshold": 2,
    "service.beta.kubernetes.io/aws-load-balancer-healthcheck-interval": 5,
    # Proxy protocol options
    "service.beta.kubernetes.io/aws-load-balancer-proxy-protocol": "*" if proxy_protocol else "",
  }

  ssl_enabled_service_annotations = {
    # SSL options
    "service.beta.kubernetes.io/aws-load-balancer-ssl-ports": 443,
    "service.beta.kubernetes.io/aws-load-balancer-ssl-cert": ",".join(acm_cert_arns),
    "service.beta.kubernetes.io/aws-load-balancer-ssl-negotiation-policy": "ELBSecurityPolicy-TLS13-1-2-2021-06",
  }
  
  if ssl_enabled:
    service_annotations.update(ssl_enabled_service_annotations)

  ingress_nginx_release = release(
      name=name,
      chart=chart,
      version=version,
      repo=repo,
      namespace=namespace,
      skip_await=skip_await,
      depends_on=depends_on,
      provider=provider,
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
              "ingressClass": f"nginx-{name_suffix}",
              "ingressClassResource": {
                  "name": f"nginx-{name_suffix}",
                  "enabled": True,
                  "default": False,
                  "controllerValue": f"k8s.io/ingress-nginx-{name_suffix}"
              },
              "electionID": f"ingress-controller-{name_suffix}-leader",
              "config": {
                  "ssl-redirect": False,
                  "redirect-to-https": True,
                  "use-forwarded-headers": True,
                  "use-proxy-protocol": True,
                  "skip-access-log-urls": "/healthz,/healthz/",
                  "no-tls-redirect-locations": "/healthz,/healthz/",
                  "log-format-upstream": '$remote_addr - $host [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent" $request_length $request_time [$proxy_upstream_name] [$proxy_alternative_upstream_name] $upstream_addr $upstream_response_length $upstream_response_time $upstream_status $req_id',
                  "server-snippet": "if ($proxy_protocol_server_port != '443'){ return 301 https://$host$request_uri; }",
              },
              "containerPort": {
                  "http": 80,
                  "https": 443,
              },
              "service": {
                  "enabled": True,
                  "type": "LoadBalancer",
                  "enableHttp": True,  # Enables the HTTP port (80) on the load balancer
                  "enableHttps": ssl_enabled, # Enables the HTTPS port (443) on the load balancer
                  "ports": {
                      "http": 80,      # Port to open in the load balancer for HTTP traffic
                      "https": 443     # Port to open in the load balancer for HTTPS traffic
                  },
                  "targetPorts": {
                      "http": "http", # Service port 80 is forwarded to DaemonSet port 2443 ( tohttps)
                      "https": "http"    # Service port 443 is forwarded to DaemonSet port 80 (http)
                  },
                  "httpPort": {
                      "enable": True,
                      "targetPort": "http"
                  },
                  "httpsPort": {
                      "enable": ssl_enabled,
                      "targetPort": "http"
                  },
                  # https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.6/guide/service/annotations/
                  "annotations": service_annotations,
              },
          },
      }
  )
  
  return ingress_nginx_release
