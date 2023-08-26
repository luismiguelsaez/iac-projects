
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
