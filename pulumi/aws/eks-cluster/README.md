
- Create stack

```bash
pulumi stack init dev
pulumi up
```

- Get `kubeconfig` file contents

```bash
pulumi stack output kubeconfig > kubeconfig.yml
KUBECONFIG=./kubeconfig.yml kubectl get nodes
```
