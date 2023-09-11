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
  timeout: int = 60,
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
    values=values,
    timeout=timeout,
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
    default_storage_class_name: str = "ebs",
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
                  "name": default_storage_class_name,
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
    target_node_labels: list[str] = [],
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
  
  target_node_labels_service_annotations = {
    "service.beta.kubernetes.io/aws-load-balancer-target-node-labels": ",".join(target_node_labels),
  }
  
  if ssl_enabled:
    service_annotations.update(ssl_enabled_service_annotations)

  if len(target_node_labels) > 0:
    service_annotations.update(target_node_labels_service_annotations)

  ingress_nginx_release = release(
      name=name,
      chart=chart,
      version=version,
      repo=repo,
      namespace=namespace,
      skip_await=skip_await,
      depends_on=depends_on,
      provider=provider,
      timeout=600,
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

def release_argocd(
    provider,
    ingress_hostname: str,
    ingress_protocol: str,
    ingress_class_name: str,
    name: str = "argo-cd",
    chart: str = "argo-cd",
    version: str = "5.46.0",
    repo: str = "https://argoproj.github.io/argo-helm",
    namespace: str = "default",
    skip_await: bool = False,
    depends_on: list = [],  
  )->Release:
  
  argocd_release = release(
    name=name,
    chart=chart,
    version=version,
    repo=repo,
    namespace=namespace,
    timeout=600,
    skip_await=skip_await,
    depends_on=depends_on,
    provider=provider,
    values=      {
        "global": {
            "additionalLabels": {
                "app": "argo-cd"
            },
            "revisionHistoryLimit": 3,
            "affinity": {
                "podAntiAffinity": "soft",
                "nodeAffinity": {
                    "type": "hard",
                    "matchExpressions": [
                        {
                            "key": "app",
                            "operator": "In",
                            "values": ["argo-cd"]
                        },
                    ],
                },
            },
        },
        "configs": {
            "cm": {
                "url": f"{ingress_protocol}://{ingress_hostname}",
                "exec.enabled": "true",
                "admin.enabled": "true",
                "timeout.reconciliation": "180s",
            },
            "params": {
                # Server
                "server.insecure": "true",
                "server.disable.auth": "false",
                # Application controller
                "controller.status.processors": 20,
                "controller.operation.processors": 10,
                "controller.self.heal.timeout.seconds": 5,
                "controller.repo.server.timeout.seconds": 60,
                # ApplicationSet
                "applicationsetcontroller.policy": "sync",
                "applicationsetcontroller.enable.progressive.syncs": "false",
                # Repo server
                "reposerver.parallelism.limit": 0,
            },
        },
        "redis": {
            "enabled": True,
            "name": "redis",
            "podLabels": {
                "app": "redis",
            },
            "resources": {
                "requests": {
                    "cpu": "500m",
                    "memory": "256Mi"
                },
                "limits": {
                    "cpu": "1000m",
                    "memory": "512Mi"
                }
            },
            "affinity": {
                "nodeAffinity": {
                    "requiredDuringSchedulingIgnoredDuringExecution": {
                        "nodeSelectorTerms": [
                            {
                                "matchExpressions": [
                                    {
                                        "key": "app",
                                        "operator": "In",
                                        "values": ["redis"]
                                    }
                                ],
                            },
                        ],
                    },
                },
            },
        },
        "redis-ha": {
            "enabled": True,
            "persistentVolume": {
                "enabled": "false",
            },
            "redis": {
                "config": {
                    "save": '"900 1"'
                }
            },
            "haproxy": {
                "enabled": True,
                "hardAntiAffinity": True,
                "affinity": "",
                "additionalAffinities": {
                    "nodeAffinity": {
                        "requiredDuringSchedulingIgnoredDuringExecution": {
                            "nodeSelectorTerms": [
                                {
                                    "matchExpressions": [
                                        {
                                            "key": "app",
                                            "operator": "In",
                                            "values": ["redis"]
                                        }
                                    ],
                                },
                            ],
                        },
                    },
                },
            },
            "topologySpreadConstraints": {
                "enabled": "true",
                "maxSkew": 1,
                "topologyKey": "topology.kubernetes.io/zone",
                "whenUnsatisfiable": "DoNotSchedule",
            },
            "hardAntiAffinity": True,
            "additionalAffinities": {
                "nodeAffinity": {
                    "requiredDuringSchedulingIgnoredDuringExecution": {
                        "nodeSelectorTerms": [
                            {
                                "matchExpressions": [
                                    {
                                        "key": "app",
                                        "operator": "In",
                                        "values": ["redis"]
                                    }
                                ],
                            },
                        ],
                    },
                },
            },
        },
        "controller": {
            "replicas": 2,
            "affinity": {
                "nodeAffinity": {
                    "requiredDuringSchedulingIgnoredDuringExecution": {
                        "nodeSelectorTerms": [
                            {
                                "matchExpressions": [
                                    {
                                        "key": "app",
                                        "operator": "In",
                                        "values": ["argo-cd"]
                                    }
                                ],
                            },
                        ],
                    },
                },
            },
        },
        "server": {
            "autoscaling": {
                "enabled": "true",
                "minReplicas": 2,
                "maxReplicas": 4,
            },
            "ingress": {
                "enabled": "true",
                "ingressClassName": ingress_class_name,
                "hosts": [ ingress_hostname ],
                "paths": [ "/" ],
                "pathType": "Prefix",
                "extraPaths": [],
                "tls": [],
            },
        },
        "repoServer": {
            "autoscaling": {
                "enabled": "true",
                "minReplicas": 2,
                "maxReplicas": 5,
            },
            "affinity": {
                "nodeAffinity": {
                    "requiredDuringSchedulingIgnoredDuringExecution": {
                        "nodeSelectorTerms": [
                            {
                                "matchExpressions": [
                                    {
                                        "key": "app",
                                        "operator": "In",
                                        "values": ["argo-cd"]
                                    }
                                ],
                            },
                        ],
                    },
                },
            },
        },
        "applicationSet": {
            "replicas": 2,
        },
        "extraObjects": [
            {
                "apiVersion": "karpenter.sh/v1alpha5",
                "kind": "Provisioner",
                "metadata": {
                    "labels": {
                        "app": "argo-cd",
                    },
                    "name": "argo-cd",
                },
                "spec": {
                    "consolidation": {
                        "enabled": True,
                    },
                    "labels": {
                        "app": "argo-cd",
                    },
                    "taints": [],
                    "providerRef": {
                        "name": "default",
                    },
                    "requirements": [
                        { "key": "karpenter.k8s.aws/instance-category", "operator": "In", "values": [ "t" ] },
                        { "key": "karpenter.k8s.aws/instance-cpu", "operator": "In", "values": [ "2" ] },
                        { "key": "karpenter.k8s.aws/instance-memory", "operator": "In", "values": [ "4096" ] },
                        { "key": "kubernetes.io/arch", "operator": "In", "values": [ "arm64" ] },
                        { "key": "kubernetes.io/os", "operator": "In", "values": [ "linux" ] },
                        { "key": "karpenter.sh/capacity-type", "operator": "In", "values": [ "spot", "on-demand" ] },
                    ],
                },
            },
            {
                "apiVersion": "karpenter.sh/v1alpha5",
                "kind": "Provisioner",
                "metadata": {
                    "labels": {
                        "app": "redis",
                    },
                    "name": "redis",
                },
                "spec": {
                    "consolidation": {
                        "enabled": True,
                    },
                    "labels": {
                        "app": "redis",
                    },
                    "taints": [],
                    "providerRef": {
                        "name": "default",
                    },
                    "requirements": [
                        { "key": "karpenter.k8s.aws/instance-category", "operator": "In", "values": [ "t" ] },
                        { "key": "karpenter.k8s.aws/instance-cpu", "operator": "In", "values": [ "2" ] },
                        { "key": "karpenter.k8s.aws/instance-memory", "operator": "In", "values": [ "2048" ] },
                        { "key": "kubernetes.io/arch", "operator": "In", "values": [ "arm64" ] },
                        { "key": "kubernetes.io/os", "operator": "In", "values": [ "linux" ] },
                        { "key": "karpenter.sh/capacity-type", "operator": "In", "values": [ "spot", "on-demand" ] },
                    ],
                },
            },
        ],
    }
  )

  return argocd_release

def release_prometheus_stack(
    provider,
    ingress_domain: str,
    ingress_class_name: str,
    storage_class_name: str,
    eks_sa_role_arn: str = "",
    thanos_enabled: bool = False,
    prometheus_tsdb_retention: str = "30d",
    prometheus_external_label_env: str = "dev",
    obj_storage_bucket: str = "",
    name_override: str = "prom-stack",
    name: str = "kube-prometheus-stack",
    chart: str = "kube-prometheus-stack",
    version: str = "50.3.1",
    repo: str = "https://prometheus-community.github.io/helm-charts",
    namespace: str = "default",
    skip_await: bool = False,
    depends_on: list = [],  
  )->Release:

  sidecar_containers = [
    {
        "name": "thanos",
        "image": "quay.io/thanos/thanos:v0.32.2",
        "args": [
            "sidecar",
            "--log.level=debug",
            "--log.format=logfmt",
            "--tsdb.path=/prometheus",
            "--prometheus.url=http://localhost:9090",
            "--http-address=0.0.0.0:10901",
            "--grpc-address=0.0.0.0:10902",
            f"--objstore.config=type: S3\nconfig:\n  bucket: {obj_storage_bucket}\n  endpoint: s3.eu-central-1.amazonaws.com\n  aws_sdk_auth: true\n"
        ],
        "env": [],
        "ports": [
            {
                "name": "http",
                "containerPort": 10901,
                "protocol": "TCP"
            },
            {
                "name": "grpc",
                "containerPort": 10902,
                "protocol": "TCP"
            }
        ],
        "volumeMounts": [
            {
                "mountPath": "/prometheus",
                "name": f"prometheus-{name_override}-prometheus-db",
                "subPath": "prometheus-db"
            }
        ],
        "securityContext": {
            "runAsNonRoot": True,
            "runAsUser": 1000,
            "runAsGroup": 2000
        }
    }
  ]

  prometheus_stack_release = release(
    name=name,
    chart=chart,
    version=version,
    repo=repo,
    namespace=namespace,
    timeout=600,
    skip_await=skip_await,
    depends_on=depends_on,
    provider=provider,
    values={
        "crds": {
            "enabled": True
        },
        # Overridding fullname to avoid name random data volume name
        "fullnameOverride": name_override,
        "prometheusOperator": {
            "enabled": True,
            "logFormat": "logfmt",
            "logLevel": "debug",
            "affinity": {},
            "tolerations": []
        },
        "prometheus": {
            "enabled": True,
            "serviceAccount": {
                "create": True,
                "annotations": {
                    "eks.amazonaws.com/role-arn": eks_sa_role_arn,
                }
            },
            "thanosService": {
                "enabled": thanos_enabled,
                "type": "ClusterIP",
                "clusterIP": "None",
                "portName": "grpc",
                "port": 10901,
                "targetPort": "grpc",
                "httpPortName": "http",
                "httpPort": 10902,
                "targetHttpPort": "http"
            },
            "thanosIngress": {
                "enabled": thanos_enabled,
                "ingressClassName": ingress_class_name,
                "hosts": [
                    f"thanos-gateway.{ingress_domain}"
                ],
                "paths": [
                    "/"
                ],
                "pathType": "Prefix"
            },
            "ingress": {
                "enabled": True,
                "ingressClassName": ingress_class_name,
                "hosts": [
                    f"prometheus.{ingress_domain}"
                ],
                "paths": [
                    "/"
                ],
                "pathType": "Prefix",
                "tls": []
            },
            "prometheusSpec": {
                "replicas": 3,
                "replicaExternalLabelName": "prometheus_replica",
                "prometheusExternalLabelName": "prometheus_instance",
                "retention": prometheus_tsdb_retention,
                "disableCompaction": thanos_enabled,
                "enableAdminAPI": True,
                "externalLabels": {
                    "env": "dev"
                },
                "scrapeInterval": "15s",
                "scrapeTimeout": "14s",
                "serviceMonitorSelector": {},
                "serviceMonitorNamespaceSelector": {},
                "serviceMonitorSelectorNilUsesHelmValues": False,
                "podMonitorSelector": {},
                "podMonitorNamespaceSelector": {},
                "podMonitorSelectorNilUsesHelmValues": False,
                "containers": sidecar_containers if thanos_enabled else [],
                "resources": {
                    "requests": {
                        "cpu": "1000m",
                        "memory": "2048Mi"
                    },
                    "limits": {
                        "cpu": "2000m",
                        "memory": "4096Mi"
                    }
                },
                "affinity": {
                    "nodeAffinity": {
                        "requiredDuringSchedulingIgnoredDuringExecution": {
                            "nodeSelectorTerms": [
                                {
                                    "matchExpressions": [
                                        { "key": "app", "operator": "In", "values": ["prometheus"] }
                                    ]
                                }
                            ]
                        }
                    }
                },
                "tolerations": [],
                "podMetadata": {
                    "labels": {
                        "app": "prometheus"
                    }
                },
                "topologySpreadConstraints": [
                    {
                        "maxSkew": 1,
                        "topologyKey": "topology.kubernetes.io/zone",
                        "whenUnsatisfiable": "ScheduleAnyway",
                        "labelSelector": {
                            "matchLabels": {
                                "app": "prometheus"
                            }
                        }
                    },
                    {
                        "maxSkew": 1,
                        "topologyKey": "kubernetes.io/hostname",
                        "whenUnsatisfiable": "ScheduleAnyway",
                        "labelSelector": {
                            "matchLabels": {
                                "app": "prometheus"
                            }
                        }
                    }
                ],
                "storageSpec": {
                    "volumeClaimTemplate": {
                        "spec": {
                            "storageClassName": "ebs",
                            "accessModes": ["ReadWriteOnce"],
                            "resources": {
                                "requests": {
                                    "storage": "20Gi"
                                }
                            }
                        }
                    }
                }
            }
        },
        "alertmanager": {
            "enabled": True,
            "ingress": {
            "enabled": True,
                "ingressClassName": ingress_class_name,
                "hosts": [
                    f"alertmanager.{ingress_domain}"
                ],
                "paths": [
                    "/"
                ],
                "pathType": "Prefix",
                "tls": []
            },
            "alertmanagerSpec": {
                "replicas": 1,
                "retention": "120h",
                "storage": {
                    "volumeClaimTemplate": {
                        "spec": {
                            "storageClassName": storage_class_name,
                            "accessModes": ["ReadWriteOnce"],
                            "resources": {
                                "requests": {
                                    "storage": "20Gi"
                                }
                            }
                        }
                    }
                },
                "affinity": {},
                "tolerations": []
            }
        },
        "grafana": {
            "enabled": True,
            "adminPassword": "prom-operator",
            "ingress": {
                "enabled": True,
                "ingressClassName": ingress_class_name,
                "hosts": [
                    f"grafana.{ingress_domain}"
                ],
                "paths": [
                    "/"
                ],
                "pathType": "Prefix",
                "tls": []
            },
            "sidecar": {
                "dashboards": {
                    "enabled": True
                },
                "datasources": {
                    "enabled": True
                }
            },
            "additionalDataSources": [
                {
                    "name": "thanos",
                    "type": "prometheus",
                    "access": "proxy",
                    # Depends on the value of fullnameOverride in the Thanos Stack release
                    "url": "http://thanos-stack-query.prometheus.svc.cluster.local:9090",
                    "isDefault": False
                }
            ]
        },
        "nodeExporter": {
            "enabled": True
        },
        "extraManifests": [
            {
                "apiVersion": "karpenter.sh/v1alpha5",
                "kind": "Provisioner",
                "metadata": {
                    "labels": {
                        "app": "prometheus"
                    },
                    "name": "prometheus"
                },
                "spec": {
                    "consolidation": {
                        "enabled": False
                    },
                    "ttlSecondsAfterEmpty": 30,
                    "ttlSecondsUntilExpired": 2592000,
                    "labels": {
                        "karpenter": "enabled",
                        "app": "prometheus"
                    },
                    "taints": [],
                    "providerRef": {
                        "name": "bottlerocket"
                    },
                    "requirements": [
                        { "key": "karpenter.k8s.aws/instance-category", "operator": "In", "values": ["t"] },
                        { "key": "karpenter.k8s.aws/instance-cpu", "operator": "In", "values": ["2"] },
                        { "key": "karpenter.k8s.aws/instance-memory", "operator": "In", "values": ["4096"] },
                        { "key": "kubernetes.io/arch", "operator": "In", "values": ["amd64", "arm64"] },
                        { "key": "kubernetes.io/os", "operator": "In", "values": ["linux"] },
                        { "key": "karpenter.sh/capacity-type", "operator": "In", "values": ["on-demand"] }
                    ]
                }
            }
        ]
    }
  )

  return prometheus_stack_release

def release_thanos_stack(
    provider,
    aws_region: str,
    ingress_domain: str,
    ingress_class_name: str,
    storage_class_name: str,
    eks_sa_role_arn: str = "",
    obj_storage_bucket: str = "",
    name_override: str = "",
    name: str = "thanos",
    chart: str = "thanos",
    version: str = "12.13.1",
    repo: str = "https://charts.bitnami.com/bitnami",
    namespace: str = "default",
    skip_await: bool = False,
    depends_on: list = [],  
  )->Release:

  thanos_stack_release = release(
    name=name,
    chart=chart,
    version=version,
    repo=repo,
    timeout=600,
    namespace=namespace,
    skip_await=skip_await,
    depends_on=depends_on,
    provider=provider,
    values={
        "fullnameOverride": name_override,
        "extraDeploy": [
            {
                "apiVersion": "karpenter.sh/v1alpha5",
                "kind": "Provisioner",
                "metadata": {
                    "labels": {
                        "app": "thanos"
                    },
                    "name": "thanos"
                },
                "spec": {
                    "consolidation": {
                        "enabled": True
                    },
                    "labels": {
                        "karpenter": "enabled",
                        "app": "thanos"
                    },
                    "taints": [],
                    "providerRef": {
                        "name": "bottlerocket"
                    },
                    "requirements": [
                        { "key": "karpenter.k8s.aws/instance-category", "operator": "In", "values": ["t"] },
                        { "key": "karpenter.k8s.aws/instance-cpu", "operator": "In", "values": ["2"] },
                        { "key": "karpenter.k8s.aws/instance-memory", "operator": "In", "values": ["4096"] },
                        { "key": "kubernetes.io/arch", "operator": "In", "values": ["arm64"] },
                        { "key": "kubernetes.io/os", "operator": "In", "values": ["linux"] },
                        { "key": "karpenter.sh/capacity-type", "operator": "In", "values": ["on-demand"] },
                    ]
                }
            }
        ],
        "objstoreConfig": {
            "type": "S3",
            "config": {
                "bucket": obj_storage_bucket,
                "endpoint": f"s3.{aws_region}.amazonaws.com",
                "aws_sdk_auth": True
            }
        },
        "query": {
            "enabled": True,
            "replicaCount": 3,
            "podLabels": {
                "app": "thanos-query"
            },
            "logLevel": "info",
            "logFormat": "logfmt",
            "service": {
                "type": "ClusterIP",
                "ports": {
                    "http": 9090
                },
                "annotations": {}
            },
            "serviceGrpc": {
                "type": "ClusterIP",
                "ports": {
                    "grpc": 10901
                },
                "annotations": {}
            },
            "ingress": {
                "enabled": True,
                "ingressClassName": ingress_class_name,
                "annotations": {},
                "labels": {},
                "hostname": f"thanos-query.{ingress_domain}",
                "pathType": "Prefix",
                "path": "/",
                "tls": False,
                "grpc": {
                    "enabled": False,
                    "hostname": f"thanos-query-grpc.{ingress_domain}"
                }
            },
            "replicaLabel": [
                "prometheus_replica"
            ],
            "stores": [
                # Naming based on `fullNameOverride` in `prometheus-stack` release ( prom-stack )
                "prom-stack-thanos-discovery.prometheus.svc.cluster.local:10902",
                # Namin based on `fullNameOverride` in `thanos-stack` release ( thanos-stack )
                "thanos-stack-storegateway.prometheus.svc.cluster.local:10901"
            ],
            "sdConfig": "",
            "resources": {
                "requests": {
                    "memory": "512Mi",
                    "cpu": "500m"
                },
                "limits": {
                    "memory": "1024Mi",
                    "cpu": 1
                }
            },
            "affinity": {
                "nodeAffinity": {
                    "requiredDuringSchedulingIgnoredDuringExecution": {
                        "nodeSelectorTerms": [
                            {
                                "matchExpressions": [
                                    {
                                        "key": "app",
                                        "operator": "In",
                                        "values": [
                                            "thanos"
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                },
                "podAntiAffinity": {
                    "requiredDuringSchedulingIgnoredDuringExecution": [
                        {
                            "topologyKey": "kubernetes.io/hostname",
                            "labelSelector": {
                                "matchLabels": {
                                    "app": "thanos-query"
                                }
                            }
                        }
                    ]
                }
            },
            "topologySpreadConstraints": [
                {
                    "maxSkew": 1,
                    "topologyKey": "topology.kubernetes.io/zone",
                    "whenUnsatisfiable": "DoNotSchedule",
                    "labelSelector": {
                        "matchLabels": {
                            "app": "thanos-query"
                        }
                    }
                },
                {
                    "maxSkew": 1,
                    "topologyKey": "kubernetes.io/hostname",
                    "whenUnsatisfiable": "DoNotSchedule",
                    "labelSelector": {
                        "matchLabels": {
                            "app": "thanos-query"
                        }
                    }
                }
            ]
        },
        "queryFrontend": {
            "enabled": False,
            "recplicaCount": 1,
            "podLabels": {},
            "logLevel": "info",
            "logFormat": "logfmt"
        },
        "bucketweb": {
            "enabled": True,
            "recplicaCount": 1,
            "podLabels": {
                "app": "thanos-bucketweb"
            },
            "logLevel": "info",
            "logFormat": "json",
            "refresh": "5m",
            "timeout": "5m",
            "extraFlags": [],
            "serviceAccount": {
                "create": True,
                "annotations": {
                    "eks.amazonaws.com/role-arn": eks_sa_role_arn
                }
            },
            "ingress": {
                "enabled": True,
                "ingressClassName": ingress_class_name,
                "annotations": {},
                "labels": {},
                "hostname": f"thanos-bucketweb.{ingress_domain}",
                "pathType": "Prefix",
                "path": "/",
                "tls": False
            },
            "resources": {
                "requests": {
                    "memory": "128Mi",
                    "cpu": "100m"
                },
                "limits": {
                    "memory": "128Mi",
                    "cpu": "100m"
                }
            },
            "affinity": {
                "nodeAffinity": {
                    "requiredDuringSchedulingIgnoredDuringExecution": {
                        "nodeSelectorTerms": [
                            {
                                "matchExpressions": [
                                    {
                                        "key": "app",
                                        "operator": "In",
                                        "values": [
                                            "thanos"
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        },
        "compactor": {
            "enabled": True,
            "podLabels": {
                "app": "thanos-compactor"
            },
            "logLevel": "info",
            "logFormat": "logfmt",
            "retentionResolutionRaw": "7d",
            "retentionResolution5m": "30d",
            "retentionResolution1h": "1y",
            "consistencyDelay": "30m",
            "serviceAccount": {
                "create": True,
                "annotations": {
                    "eks.amazonaws.com/role-arn": eks_sa_role_arn
                }
            },
            "resources": {
                "requests": {
                    "memory": "128Mi",
                    "cpu": "200m"
                },
                "limits": {
                    "memory": "256Mi",
                    "cpu": "500m"
                }
            },
            "affinity": {
                "nodeAffinity": {
                    "requiredDuringSchedulingIgnoredDuringExecution": {
                        "nodeSelectorTerms": [
                            {
                                "matchExpressions": [
                                    {
                                        "key": "app",
                                        "operator": "In",
                                        "values": [
                                            "thanos"
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        },
        "storegateway": {
            "enabled": True,
            "replicaCount": 3,
            "podLabels": {
                "app": "thanos-storegateway"
            },
            "service": {
                "type": "ClusterIP",
                "ports": {
                    "http": 9090,
                    "grpc": 10901
                },
                "annotations": {}
            },
            "extraFlags": [],
            "serviceAccount": {
                "create": True,
                "annotations": {
                    "eks.amazonaws.com/role-arn": eks_sa_role_arn
                }
            },
            "ingress": {
                "enabled": True,
                "ingressClassName": "nginx-external",
                "annotations": {},
                "labels": {},
                "hostname": f"thanos-storegateway.{ingress_domain}",
                "pathType": "Prefix",
                "path": "/",
                "tls": False,
                "grpc": {
                    "enabled": False,
                    "hostname": f"thanos-storegateway-grpc.{ingress_domain}"
                }
            },
            "persistence": {
                "enabled": True,
                "storageClass": storage_class_name,
                "accessModes": [
                    "ReadWriteOnce"
                ],
                "size": "8Gi"
            },
            "resources": {
                "requests": {
                    "memory": "512Mi",
                    "cpu": "500m"
                },
                "limits": {
                    "memory": "1024Mi",
                    "cpu": 1
                }
            },
            "affinity": {
                "nodeAffinity": {
                    "requiredDuringSchedulingIgnoredDuringExecution": {
                        "nodeSelectorTerms": [
                            {
                                "matchExpressions": [
                                    {
                                        "key": "app",
                                        "operator": "In",
                                        "values": [
                                            "thanos"
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                },
                "podAntiAffinity": {
                    "requiredDuringSchedulingIgnoredDuringExecution": [
                        {
                            "topologyKey": "kubernetes.io/hostname",
                            "labelSelector": {
                                "matchLabels": {
                                    "app": "thanos-storegateway"
                                }
                            }
                        }
                    ]
                }
            },
            "topologySpreadConstraints": [
                {
                    "maxSkew": 1,
                    "topologyKey": "topology.kubernetes.io/zone",
                    "whenUnsatisfiable": "DoNotSchedule",
                    "labelSelector": {
                        "matchLabels": {
                            "app": "thanos-storegateway"
                        }
                    }
                },
                {
                    "maxSkew": 1,
                    "topologyKey": "kubernetes.io/hostname",
                    "whenUnsatisfiable": "DoNotSchedule",
                    "labelSelector": {
                        "matchLabels": {
                            "app": "thanos-storegateway"
                        }
                    }
                }
            ]
        },
        "ruler": {
            "enabled": False
        },
        "receive": {
            "enabled": False,
            "replicaCount": 3,
            "podLabels": {},
            "tsdbRetention": "15d",
            "replicationFactor": 2,
            "logLevel": "debug",
            "logFormat": "logfmt",
            "service": {
                "type": "ClusterIP",
                "ports": {
                    "http": 10902,
                    "grpc": 10901,
                    "remote": 19291
                },
                "annotations": {}
            },
            "replicaLabel": "replica"
        },
        "receiveDistributor": {
            "enabled": False
        },
        "metrics": {
            "enabled": False
        }
    }
)
  
  return thanos_stack_release
