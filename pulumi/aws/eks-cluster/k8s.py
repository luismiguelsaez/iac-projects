from pulumi_kubernetes.yaml import ConfigFile
from pulumi_kubernetes import Provider
from pulumi import ResourceOptions

def create_resource_from_file(name: str, file: str, depends_on: list = [], provider: Provider = Provider("k8s_default"))->ConfigFile:

  resource_options = ResourceOptions(provider=provider, depends_on=depends_on)
  resource = ConfigFile(
    name,
    file=file,
    opts=resource_options
  )
  return resource
