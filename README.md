# SWE40006---GroupProject
# Online Convenience Store System – CI/CD on Azure

A Python web app for an online convenience store, with a full **CI/CD pipeline** that tests, packages and deploys it to **Azure App Service**. The pipeline checks that each new version is live and **rolls back automatically** if it is not.

> **Code → Check → Pack → Store → Test → Live**

---

## Contents

- [How it works](#how-it-works)
- [Project structure](#project-structure)
- [Run locally](#run-locally)
- [Run with Docker](#run-with-docker)
- [The CI/CD pipeline](#the-cicd-pipeline)
- [Rollback](#rollback)
- [Setup: secrets and Azure settings](#setup-secrets-and-azure-settings)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Lessons learned](#lessons-learned)

---

## How it works

| Stage | What happens | Where |
| --- | --- | --- |
| **Code** | Push code to `main` | GitHub |
| **Check** | Lint with Flake8, test with pytest | GitHub Actions |
| **Pack** | Build a Docker image | GitHub Actions |
| **Store** | Save the image, tagged with its commit ID | GitHub Container Registry (GHCR) |
| **Test** | Deploy, check the version, roll back if broken | Azure `YLS-TEST` |
| **Live** | Same steps on the live app | Azure `YLS-PROD` |

If any stage fails, every stage after it stops.

---

## Project structure

```
.
├── .github/
│   └── workflows/
│       └── deploy.yml              # CI/CD pipeline
└── Online-Convenience-Store-System/
    ├── Dockerfile                  # How the image is built
    ├── requirements.txt            # Python dependencies
    ├── app.py                      # Web app (gunicorn entry point: app:app)
    └── test_app.py                 # Unit tests
```

### Key endpoints

| Endpoint | Returns | Used by |
| --- | --- | --- |
| `/health` | `{"status":"OK"}` when the app is running | Smoke test, Azure health check |
| `/version` | The Git commit ID of the running build | Smoke test (confirms the new version is live) |

---

## Run locally

Requires **Python 3.10**.

```bash
cd Online-Convenience-Store-System
pip install -r requirements.txt
gunicorn --bind 0.0.0.0:8000 app:app
```

Open <http://localhost:8000/health>.

Run the checks the pipeline runs:

```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
pytest -v
```

---

## Run with Docker

### Build it yourself

```bash
cd Online-Convenience-Store-System
docker build --build-arg GIT_SHA=$(git rev-parse HEAD) -t convenience-store .
docker run -p 8000:8000 convenience-store
```

### Or pull a build made by the pipeline

Images are stored in **GitHub Container Registry**, next to the code. Docker Desktop only shows images you have pulled to your own machine.

```bash
# Only needed if the package is private (token needs read:packages)
docker login ghcr.io -u <your-github-username>

docker pull ghcr.io/treasure-mei-box/swe40006-group-project:sha-<commit>
docker run -p 8000:8000 ghcr.io/treasure-mei-box/swe40006-group-project:sha-<commit>
```

Then check:

- <http://localhost:8000/health> returns `{"status":"OK"}`
- <http://localhost:8000/version> returns the commit ID

---

## The CI/CD pipeline

File: [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml)

| Trigger | What runs |
| --- | --- |
| Push to `main` | All 4 jobs: test, build, deploy to Test, deploy to Production |
| Pull request to `main` | Checks and build only. Nothing is pushed or deployed. |

### Job 1 – Code Linting and Testing

- Installs dependencies on Python 3.10.
- **Flake8** fails the build on serious errors (syntax errors, undefined names) and reports style issues without failing.
- **pytest** runs the unit tests. A failed test, or no tests found, stops the pipeline.

### Job 2 – Container Packaging & Push

Builds the Docker image and pushes it to GHCR with three tags:

| Tag | Purpose |
| --- | --- |
| `sha-<full commit ID>` | Unique and permanent. **Used for deploy and rollback.** |
| `main` | Newest build from `main` |
| `latest` | Newest build. It always moves, so it is **never used for rollback**. |

The commit ID is passed into the image as `GIT_SHA`, so the app can report it on `/version`.

### Job 3 – Deploy to Test (`YLS-TEST`)

1. Deploys `sha-<this commit>` to Azure.
2. **Smoke test:** calls `/version` up to **40 times, 10 s apart**. Passes only when it returns **this exact commit ID**, then checks `/health`.
3. On success, records the deployed image in the run Summary.
4. On smoke test failure, **rolls back** (see below).

The app URL is never typed by hand. It comes from the deploy step (`steps.deploy.outputs.webapp-url`), which reads it from the publish profile.

### Job 4 – Deploy to Production (`YLS-PROD`)

Same steps as Job 3, against the live app. It only runs if Test passed, so a broken build never reaches Production.

---

## Rollback

If the smoke test fails, the pipeline redeploys the image from the **previous commit**:

```yaml
images: ${{ env.IMAGE }}:sha-${{ github.event.before }}
```

It then waits, checks `/health`, and writes a **ROLLED BACK** note with the failed and restored commit IDs to the run Summary. The job is still marked **failed** on purpose, so Production is not deployed.

Rollback runs only when:

- the **smoke test** failed (not the deploy step itself), and
- there is a previous commit (it skips on a brand new branch).

---

## Setup: secrets and Azure settings

### GitHub repository secrets

| Secret | Value |
| --- | --- |
| `TESTING` | Publish profile of Azure app `YLS-TEST` |
| `PRODUCTION` | Publish profile of Azure app `YLS-PROD` |

Get a publish profile from **Azure Portal → App Service → Overview → Download publish profile**, then paste the file contents into the secret. `GITHUB_TOKEN` is created automatically and is used to push images to GHCR.

### GitHub environments

Create two environments: `TEST` and `PRODUCTION`. You can add **required reviewers** to `PRODUCTION` for a manual approval before go-live.

### Azure App Service settings

| Setting | Value | Why |
| --- | --- | --- |
| `WEBSITES_PORT` | `8000` | Matches `EXPOSE 8000` in the Dockerfile. Without it Azure returns **503**. |
| Registry access | Public GHCR package, or registry credentials | So Azure can pull the image |

---

## Monitoring

`YLS-PROD` is monitored with an **Azure Monitor** dashboard (resource group `yls-devops-project`) covering:

- HTTP status codes (2xx, 4xx, 5xx)
- Health check status
- Server response time
- Total requests, data in/out, CPU time
- Disk I/O and memory

The pipeline checks the app once, at deploy time. The dashboard keeps checking it after that.

---

## Troubleshooting

Start with the **first red step** in the GitHub Actions run, then check **Azure Portal → Log stream** for container start-up errors.

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `no tests ran`, exit code 5 | Test file not pushed, or pytest run from the wrong folder | Commit `test_app.py`. Check the working directory of the test step. |
| App returns **503** | Azure does not know the port | Set `WEBSITES_PORT=8000` |
| `Could not resolve host` | Hand-typed URL | Use `steps.deploy.outputs.webapp-url` |
| Smoke test loops 40 times, then fails | `/version` does not return the commit ID | Dockerfile needs `ARG GIT_SHA` and `ENV GIT_SHA=$GIT_SHA` |
| Container exits on start-up | Wrong start command | Check `CMD` in the Dockerfile matches `app:app` |
| Deploy fails with an auth error | Publish profile out of date | Download a new one and update the secret |
| Rollback fails with `manifest unknown` | Previous commit has no `sha-` image | Redeploy a known good `sha-` tag by hand |
| `invalid reference format` | Uppercase letters in the image name | Keep the lowercase image name step |

---

## Lessons learned

1. **Check the version, not just the health.** The old container can still answer "OK".
2. **Tag every image with its commit.** You always know what is running and what to go back to.
3. **Never roll back to `latest`.** It always points to the newest build, even a broken one.
4. **Test the failure paths on purpose.** We found the rollback bugs by breaking the app deliberately.