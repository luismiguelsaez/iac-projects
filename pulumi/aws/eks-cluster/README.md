
## Create infra

- Create stack

```bash
pulumi stack init dev
pulumi up
```

- Get `kubeconfig` file contents

```bash
pulumi stack output kubeconfig > kubeconfig.yaml
export KUBECONFIG=./kubeconfig.yaml
```

## Deploy testing application

```bash
kubectl apply -f k8s/manifests/deployment.yaml -n default
```

## Check

```bash
klf -l app.kubernetes.io/instance=aws-load-balancer-controller -n kube-system
klf -l app.kubernetes.io/instance=external-dns -n kube-system
```

## Deploy AWSnodetemplates

```bash
k apply -f k8s/manifests/karpenter/awsnodetemplate
```

## Deploy Prometheus Stack

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack --version 50.3.0 -f k8s/values/prometheus-stack.yaml -n monitoring --create-namespace

helm repo add bitnami https://charts.bitnami.com/bitnami
helm upgrade --install thanos bitnami/thanos --version 12.13.1 -f k8s/values/thanos-stack.yaml -n monitoring --create-namespace
```

*To enable Thanos, we first need to create a S3 bucket*

## Deploy ArgoCD

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm upgrade --install argocd argo/argo-cd --version 5.43.7 -f k8s/values/argocd.yaml -n argocd --create-namespace
```

## Deploy Opensearch to test EBS volumes

```bash
helm repo add opensearch https://argoproj.github.io/argo-helm
helm upgrade --install opensearch opensearch/opensearch --version 2.14.1 -n opensearch --create-namespace -f k8s/values/opensearch.yaml
```

## Deploy testing application

### Apply manifests

```bash
k apply -f k8s/manifests/nginx -n default
```

### Execute load testing

```bash
k6 run test/load/nginx.js
```

### Scale the deployment during load testing

```bash
k scale deploy nginx-deployment --replicas 60 -n default
```

## Cleanup

```bash
k delete -f k8s/manifests/nginx -n default
helm uninstall prometheus -n monitoring
helm uninstall opensearch -n opensearch
helm uninsall argocd -n argocd
pulumi destroy
```

## Trouble shooting

### Replace specific resources in case of error

```bash
PULUMI_K8S_ENABLE_PATCH_FORCE="true" pulumi up --target="**Deployment::karpenter"
```
