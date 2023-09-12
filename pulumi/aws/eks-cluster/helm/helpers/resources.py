from pulumi import ResourceOptions
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts, Release, ReleaseArgs, RepositoryOptsArgs
from pulumi_kubernetes import Provider

def release(
  provider,
  name: str,
  chart: str,
  version: str,
  repo: str,
  namespace: str = "default",
  skip_await: bool = False,
  timeout: int = 60,
  values: dict = {},
  depends_on: list = []
  )->Release:
  
  repo_opts_args = RepositoryOptsArgs(
    repo=repo
  )

  release_args = ReleaseArgs(
    chart=chart,
    version=version,
    repository_opts=repo_opts_args,
    namespace=namespace,
    skip_await=skip_await,
    values=values,
    timeout=timeout,
  )
  
  resource_options = ResourceOptions(provider=provider, depends_on=depends_on)

  release = Release(
    name,
    args=release_args,
    opts=resource_options
  )
  
  return release

def chart(
  provider: Provider,
  name: str,
  chart: str,
  version: str,
  repo: str,
  namespace: str = "default",
  skip_await: bool = False,
  values: dict = {},
  depends_on: list = [],
  transformations: list = []
  )->Chart:
  
  fetch_opts = FetchOpts(
    repo=repo
  )

  chart_opts = ChartOpts(
    chart=chart,
    version=version,
    fetch_opts=fetch_opts,
    namespace=namespace,
    skip_await=skip_await,
    values=values
  )

  resource_options = ResourceOptions(provider=provider, depends_on=depends_on, transformations=transformations)

  helm_chart = Chart(
    release_name=name,
    config=chart_opts,
    opts=resource_options
  )
  
  return helm_chart