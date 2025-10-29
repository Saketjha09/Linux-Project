# Example Voting App — Quick Commands (one-page)

A short, copy-paste friendly guide to run the example-voting-app locally with Docker Compose (and optional Kubernetes seed/demo steps).

## Summary
A multi-container voting demo (vote frontend, redis, worker, postgres, result UI). Uses Docker Compose; Kubernetes manifests live in `k8s-specifications/`.

## Prerequisites
- Docker (daemon running). On Linux: install `docker.io` or Docker Engine from docs.docker.com.
- Docker Compose v2 (the `docker compose` command). Often bundled with Docker.
- git
- Optional (Kubernetes demo): `kubectl` and `minikube` or `kind`.

Quick checks:

```powershell
# PowerShell (Windows)
docker --version
docker compose version
git --version
```

```bash
# Linux / WSL
docker --version
docker compose version
git --version
```

Notes:
- On Windows use Docker Desktop (WSL2 recommended). If you see pipe/permission errors, start Docker Desktop and/or run PowerShell as Administrator.
- If `docker` requires sudo on Linux, prefix commands with `sudo` or add your user to the `docker` group.

## Clone the repo

```bash
git clone https://github.com/dockersamples/example-voting-app.git
cd example-voting-app
```

## Run with Docker Compose (recommended)

Start in foreground (useful for demos):

```powershell
# from repository root
docker compose up
```

Start detached:

```powershell
docker compose up -d
```

Ports (defaults from `docker-compose.yml`):
- Voting UI (vote)  -> http://localhost:8080
- Results UI (result) -> http://localhost:8081

If a port is already in use, either stop the conflicting service or edit `docker-compose.yml` to change the host port mapping.

## Seed the database (populate votes)

The repo includes a `seed` profile that runs a short load job and exits. Run once to populate sample votes:

```powershell
# runs the seed job (runs and exits)
docker compose --profile seed up --remove-orphans
```

Or run detached (it will exit when finished):

```powershell
docker compose --profile seed up -d
```

## Useful Docker Compose commands

```powershell
# show running containers for this compose app
docker compose ps

# stream logs for all services
docker compose logs -f

# stream logs for a single service (example: vote)
docker compose logs -f vote

# execute a shell in a running container (example: vote)
docker compose exec vote sh

# scale a stateless service (example: worker)
docker compose up --scale worker=3 -d

# stop and remove containers, networks, volumes created by compose
docker compose down

# remove volumes too (if you used -d)
docker compose down --volumes --remove-orphans

# show exact host port mapping for a service
docker compose port vote 80
```

## Quick troubleshooting

1. Docker daemon unreachable / pipe errors:
   - Ensure Docker Desktop or the Docker Engine service is running.
   - On Windows, open Docker Desktop and wait until it reports "Docker is running".
   - Switch context if needed: `docker context ls` and `docker context use default` (or appropriate context).

2. Port conflict (example we ran into):
   - Find containers using ports: `docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Ports}}"`
   - Stop a conflicting container: `docker stop <container-name-or-id>` (example: `docker stop aiops-bot`).

3. Database errors (missing table):
   - Run the seed job (see section above) to populate sample votes.
   - Inspect logs: `docker compose logs -f result` or `docker compose logs -f db`.

4. If images fail to build because of missing tools or network issues: try `docker compose pull` to pull prebuilt images (if available).

## Optional: Run on Kubernetes (minikube)

Start minikube, then apply the manifests in `k8s-specifications/`:

```bash
minikube start
kubectl create -f k8s-specifications/

# get service URLs with minikube
minikube service --url vote
minikube service --url result
```

To delete resources:

```bash
kubectl delete -f k8s-specifications/
minikube stop
```

## Short demo script (what to show)

1. Explain goal: "A simple distributed voting app demonstrating containerized services + messaging + persistence."
2. Show repository & architecture diagram (file `architecture.excalidraw.png` exists in repo).
3. Start app (detached):

```powershell
docker compose up -d
```

4. Open UIs in browser:
- Vote: http://localhost:8080
- Results: http://localhost:8081

5. Show logs, e.g.:

```powershell
docker compose logs -f worker
```

6. Show scaling:

```powershell
docker compose up --scale worker=3 -d
```

7. Cleanup:

```powershell
docker compose down --volumes
```

## Slide snippets (copy into PPT)

- Title: Web Based Voting App — multi-container demo using Docker Compose
- Architecture: client → vote(frontend) → redis → worker → postgres → result(frontend)
- Tech: Docker, Docker Compose, Redis, Postgres, Python/.NET/Node.js, (Kubernetes optional)
- Commands: `git clone ...`, `docker compose up -d`, `docker compose --profile seed up`.
- Takeaways: container portability, isolation, scaling, orchestration
- Caveats: production concerns — security, persistent volumes, monitoring

---

If you'd like, I can also:
- Create a ready-to-paste 6-slide deck content next, or
- Save the current HTML of the two UIs to files for screenshots, or
- Add a small GitHub Actions workflow that builds the images.

Tell me which next step you want: `slides`, `screenshots`, `ci`, or `done`.
