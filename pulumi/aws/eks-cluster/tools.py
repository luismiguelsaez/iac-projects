import pulumi

def create_kubeconfig(eks_cluster):
  kubeconfig_yaml = pulumi.Output.all(eks_cluster.name, eks_cluster.endpoint, eks_cluster.certificate_authority).apply(lambda o: f"""
apiVersion: v1
current-context: aws
clusters:
- name: {o[0]}
  cluster:
    api-version: v1
    server: {o[1]}
    certificate-authority-data: {o[2]}
contexts:
- name: aws
  context:
    cluster: {o[0]}
    namespace: default
    user: aws
kind: Config
preferences:
  colors: true
users:
- name: aws
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1alpha1
      command: aws-iam-authenticator
      args:
        - "token"
        - "-i"
        - "{o[1]}"
""")
  
  return kubeconfig_yaml
