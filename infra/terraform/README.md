# AWS host for Docker Compose deployment

Provisions:

- VPC with public subnet and internet gateway
- Security group (SSH, API port 8000, dashboard port 5500)
- EC2 instance with Docker pre-installed via user-data
- IAM instance profile with read-only EC2/ECS/CloudWatch permissions

After `terraform apply`, SSH to the instance, clone this repo, copy `.env`, and run:

```bash
docker compose up -d --build
```

For GCP ingestion on the host, set `GOOGLE_APPLICATION_CREDENTIALS` or use `gcloud auth application-default login`.
