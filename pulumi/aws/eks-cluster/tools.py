import pulumi
from pulumi_aws import eks
from os import environ, path
import ssl
import hashlib
import requests
import netaddr
import yaml

def ignore_changes(args: pulumi.ResourceTransformationArgs):
  
    admission = {
      "resources": [
        "kubernetes:admissionregistration.k8s.io/v1:ValidatingWebhookConfiguration",
        "kubernetes:admissionregistration.k8s.io/v1:MutatingWebhookConfiguration"
      ],
      "properties": [
        "webhooks[*].clientConfig.caBundle",
      ]
    }
    
    secret = {
      "resources": [
        "kubernetes:core/v1:Secret"
      ],
      "properties": [
        'data["ca.crt"]',
        'data["tls.crt"]',
        'data["tls.key"]',
        'data["ca-cert.pem"]',
        'data["server-key.pem"]',
        'data["server-cert.pem"]',
      ]
    }

    if args.type_ in admission['resources']:
        return pulumi.ResourceTransformationResult(
            props=args.props,
            opts=pulumi.ResourceOptions.merge(args.opts, pulumi.ResourceOptions(
                ignore_changes=admission['properties'],
            )))
    if args.type_ in secret['resources']:
        return pulumi.ResourceTransformationResult(
            props=args.props,
            opts=pulumi.ResourceOptions.merge(args.opts, pulumi.ResourceOptions(
                ignore_changes=secret['properties'],
            )))

def get_ssl_cert_fingerprint(host: str, port: int = 443):
  cert = ssl.get_server_certificate((host, port))
  der_cert = ssl.PEM_cert_to_DER_cert(cert)
  sha1 = hashlib.sha1(der_cert).hexdigest()
  return sha1

def get_ssh_public_key_from_gh(username: str):
  url = f"https://github.com/{username}.keys"
  r = requests.get(url)
  return r.text.rstrip()

def get_ssh_public_key(public_key_file: str, resolve_path: bool = True):
  public_key_file_path = ''
  if resolve_path:
    public_key_file_path = f"{environ.get('HOME')}/.ssh/{public_key_file}"
  with open(public_key_file_path, "r") as f:
    public_key = f.read()
  return public_key.rstrip()

def get_public_ip():
  return requests.get('https://checkip.amazonaws.com').text.rstrip()

def create_kubeconfig(eks_cluster: eks.Cluster, region: pulumi.Input[str]):
  kubeconfig_yaml = pulumi.Output.all(eks_cluster.name, eks_cluster.endpoint, eks_cluster.certificate_authority).apply(lambda o: f"""
apiVersion: v1
kind: Config
current-context: {o[0]}
preferences:
  colors: true
clusters:
  - name: {o[0]}
    cluster:
      api-version: v1
      server: {o[1]}
      certificate-authority-data: {o[2]['data']}
contexts:
  - name: {o[0]}
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

def subnet_calc(network: str, cidr_mask: int, idx: int):
  ip = netaddr.IPNetwork(network)
  subnets = ip.subnet(cidr_mask)
  c = 0
  for i in subnets:
    if c == idx:
      return str(i)
    c += 1

def update_kubeconfig(kubeconfig: str):
  kubeconfig_file_path = path.join( str(environ.get('HOME')), ".kube", "config")
  kubeconfig_obj = yaml.safe_load(open(kubeconfig_file_path, "r").read())
  kubeconfig_obj.update(kubeconfig)
  print(kubeconfig_obj)
