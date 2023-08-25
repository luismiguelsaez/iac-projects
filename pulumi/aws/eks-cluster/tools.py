import pulumi
from pulumi_aws import eks
from os import environ

def get_ssh_public_key(public_key_file: str, resolve_path: bool = True):
  public_key_file_path = ''
  if resolve_path:
    public_key_file_path = f"{environ.get('HOME')}/.ssh/{public_key_file}"
  with open(public_key_file_path, "r") as f:
    public_key = f.read()
  return public_key.rstrip()

def create_kubeconfig(eks_cluster: eks.Cluster, region: pulumi.Input[str]):
  kubeconfig_yaml = pulumi.Output.all(eks_cluster.name, eks_cluster.endpoint, eks_cluster.certificate_authority).apply(lambda o: f"""
apiVersion: v1
kind: Config
current-context: aws
preferences:
  colors: true
clusters:
  - name: {o[0]}
    cluster:
      api-version: v1
      server: {o[1]}
      certificate-authority-data: {o[2]['data']}
contexts:
  - name: aws
    context:
      cluster: {o[0]}
      namespace: default
      user: aws
users:
  - name: aws
    user:
      exec:
        apiVersion: client.authentication.k8s.io/v1beta1
        command: aws
        args:
          - --region
          - {region}
          - eks
          - get-token
          - --cluster-name
          - {o[0]}
          - --output
          - json
""")
  
  return kubeconfig_yaml
