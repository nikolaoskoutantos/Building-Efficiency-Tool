# Jenkins

This folder contains the Jenkins setup used for CI/CD and infrastructure automation in the QoE Application project.

## Purpose

This Jenkins instance is intended to act as the automation hub for the repository. In practice, that means:

- running build and validation pipelines
- orchestrating deployment steps
- supporting Docker-based automation jobs
- centralizing repeatable operational workflows for the project infrastructure

In short, this folder is not application code. It is the infrastructure needed to run Jenkins as an internal automation tool for delivery and ops.

## What Is Included

- [`Dockerfile`](./Dockerfile)
  Custom Jenkins image based on `jenkins/jenkins:lts-jdk17`, with Docker installed inside the container so Jenkins jobs can interact with Docker on the host.
- [`docker-compose.yml`](./docker-compose.yml)
  Local Jenkins deployment for development or standalone usage.
- [`docker-compose.prod.yml`](./docker-compose.prod.yml)
  Production overlay that connects Jenkins to the shared `proxy` network and exposes it through Traefik with TLS and Authelia protection.
- [`plugins.txt`](./plugins.txt)
  Jenkins plugins required for this setup, including pipeline, GitHub integration, Docker workflow, Blue Ocean, and credentials support.
- [`init.groovy.d/basic-security.groovy`](./init.groovy.d/basic-security.groovy)
  Bootstrap security script that creates the admin user from environment variables and disables anonymous access.
- [`init.groovy.d/jenkins-location.groovy`](./init.groovy.d/jenkins-location.groovy)
  Sets the Jenkins base URL from environment variables.
- [`.env.example`](./.env.example)
  Example environment variables for admin credentials, host URL, and deployment mode.

## How It Works

The Jenkins container is built from the custom Dockerfile, then started with Docker Compose.

Key behaviors:

- Jenkins persists data in the `jenkins_home` Docker volume
- the host Docker socket is mounted into the container
- Jenkins can therefore launch or manage Docker-based tasks on the host
- startup Groovy scripts apply initial security and instance configuration automatically

This makes the instance reproducible and easier to bootstrap across environments.

## Local Usage

1. Copy [`.env.example`](./.env.example) to `.env`
2. Change the default admin password
3. Start Jenkins:

```sh
docker compose up -d
```

Access it at:

- `http://localhost:18081`

## Production Usage

For production-style deployment behind Traefik:

```sh
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

In this mode:

- Jenkins joins the shared `proxy` network
- Traefik routes traffic using `JENKINS_HOST`
- HTTPS is handled through Traefik and Let's Encrypt

## Environment Variables

Important variables used by this setup:

- `JENKINS_ADMIN_ID`
- `JENKINS_ADMIN_PASSWORD`
- `JENKINS_URL`
- `JENKINS_HOST`

See [`.env.example`](./.env.example) for the expected format.

## Notes

- Change the default credentials before using this outside local testing
- Mounting `/var/run/docker.sock` gives Jenkins strong control over the host Docker daemon, so this setup should be treated as privileged infrastructure
- This folder prepares Jenkins itself; actual pipeline definitions may live in Jenkins jobs, Jenkinsfiles elsewhere in the repo, or future CI/CD automation work
