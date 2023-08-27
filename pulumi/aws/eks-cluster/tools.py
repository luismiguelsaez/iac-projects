import pulumi
from pulumi_aws import eks
from os import environ
import ssl
import hashlib

def ignore_changes(args: pulumi.ResourceTransformationArgs):
    if args.type_ == "kubernetes:admissionregistration.k8s.io/v1:ValidatingWebhookConfiguration" or args.type_ == "kubernetes:admissionregistration.k8s.io/v1:MutatingWebhookConfiguration":
        return pulumi.ResourceTransformationResult(
            props=args.props,
            opts=pulumi.ResourceOptions.merge(args.opts, pulumi.ResourceOptions(
                ignore_changes=[
                    "webhooks[*].clientConfig.caBundle",
                ],
            )))
    if args.type_ == "kubernetes:core/v1:Secret":
        return pulumi.ResourceTransformationResult(
            props=args.props,
            opts=pulumi.ResourceOptions.merge(args.opts, pulumi.ResourceOptions(
                ignore_changes=[
                    'data["ca.crt"]',
                    'data["tls.crt"]',
                    'data["tls.key"]',
                ],
            )))

def get_ssl_cert_fingerprint(host: str, port: int = 443):
  cert = ssl.get_server_certificate((host, port))
  der_cert = ssl.PEM_cert_to_DER_cert(cert)
  sha1 = hashlib.sha1(der_cert).hexdigest()
  return sha1

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
