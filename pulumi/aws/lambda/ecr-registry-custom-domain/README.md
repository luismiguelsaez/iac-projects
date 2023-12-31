# ECR registry custom domain

## TEST

- Logging in to ECR

```bash
aws ecr --profile dev get-login-password --region eu-central-1 | docker login -u AWS --password-stdin https://ecr.dev.lokalise.cloud
```

- Using ECR credentials helper ( not working atm a)

It cannot be configured to the custom `ecr.dev.lokalise.cloud` domain, but to the default `484308071187.dkr.ecr.eu-central-1.amazonaws.com` domain; otherwise, the helper will throw an error, saying it doesn't work with non-AWS domains ( see log file at `~/.ecr/log/ecr-login.log` )

```
time="2023-08-31T19:40:24+02:00" level=error msg="Error parsing the serverURL" error="docker-credential-ecr-login can only be used with Amazon Elastic Container Registry." serverURL=ecr.dev.lokalise.cloud
```

Contents of `~/.docker/config.json`:

```json
{
  "credHelpers": {
    "484308071187.dkr.ecr.eu-central-1.amazonaws.com": "ecr-login"
  }
}
```

**If using `~/.aws/credentials` file, the `[default]` profile needs to be pointing to the environment being used**

- Push an image to ECR

```bash
docker pull alpine:3.17
docker tag alpine:3.17 ecr.dev.lokalise.cloud/alpine:3.17
docker push ecr.dev.lokalise.cloud/alpine:3.17
```
