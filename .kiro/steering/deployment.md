# Deployment Steering — ReviveOps

- The hosted app runs in **demo mode** (`REVIVEOPS_DEMO_MODE=true`): it must never read arbitrary server paths.
- Local mode is the default and must keep working unchanged; never make demo mode the default.
- No AWS, Azure, or GCP services. Prefer a free host that can run a Docker container.
- No secrets or API keys in the repository; configuration comes from environment variables.
- Anything fetched from outside (such as a GitHub clone) is untrusted: validate input strictly, bound size and time, never execute it, and delete it afterwards.
- Do not weaken the existing safety rules: scans are read-only, revival writes only to a copy.
