
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

## Deploy controllers ( not needed )

```bash
helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller --version 1.6.0 -f k8s/values/aws-load-balancer-controller.yaml -n kube-system --create-namespace
```

```bash
helm upgrade --install external-dns external-dns/external-dns --version 1.13.0 -f k8s/values/external-dns.yaml -n kube-system --create-namespace
```

```bash
helm upgrade --install cluster-autoscaler cluster-autoscaler/cluster-autoscaler --version 9.29.2 -f k8s/values/cluster-autoscaler.yaml -n kube-system --create-namespace
```

## Deploy Prometheus Stack

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack --version 50.3.0 -f k8s/values/prometheus-stack.yaml -n monitoring --create-namespace
```
```

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
