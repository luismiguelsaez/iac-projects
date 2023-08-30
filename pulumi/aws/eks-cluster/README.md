
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

## Bootstrap ArgoCD repository

- https://argocd-autopilot.readthedocs.io/en/stable/Modifying-Argo-CD/#ingress-configuration

```bash
export GIT_TOKEN=ghp_****
export GIT_REPO=https://github.com/luismiguelsaez/argocd-autopilot.git/clusters/eks/dev

pulumi stack output kubeconfig > kubeconfig-argocd.yaml

argocd-autopilot repo bootstrap --app https://github.com/argoproj-labs/argocd-autopilot/manifests/ha?ref=v0.4.15
```

## Cleanup

```bash
argocd-autopilot repo uninstall
k delete -f k8s/manifests/deployment.yaml -n default
pulumi destroy
```

## Trouble shooting

### Replace specific resources in case of error

```bash
PULUMI_K8S_ENABLE_PATCH_FORCE="true" pulumi up --target="**Deployment::karpenter"
```
