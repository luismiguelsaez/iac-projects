
- Create stack

```bash
pulumi stack init dev
pulumi up
```

- Get `kubeconfig` file contents

```bash
pulumi stack output kubeconfig > kubeconfig.yml
export KUBECONFIG=./kubeconfig.yml
```

## Deploy controllers

```bash
helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller --version 1.6.0 -f k8s/values/aws-load-balancer-controller.yaml -n kube-system --create-namespace
```

```bash
helm upgrade --install external-dns external-dns/external-dns --version 1.13.0 -f k8s/values/external-dns.yaml -n kube-system --create-namespace
```
