# lablumen-ai-service

A serverless AWS Lambda function that processes lab report PDFs automatically after they are uploaded. It runs OCR on the document, generates a plain-English summary, and stores searchable vector embeddings — making the AI chat feature in the report service possible.

This service runs entirely outside the Kubernetes cluster and is deployed using AWS SAM (Serverless Application Model).

---

## What It Does

When a staff member uploads a report PDF, S3 fires an event to Amazon EventBridge, which triggers this Lambda. The processing happens asynchronously in the background — staff get an immediate upload confirmation, and the AI content becomes available to the patient once the Lambda completes.

**Processing pipeline per report:**

1. Resolve the `report_id` from the S3 object key by querying `lab_reports`.
2. Extract text from the PDF using AWS Textract (`detect_document_text`).
3. Generate a plain-English summary (max 600 tokens, temperature 0.2) using Amazon Nova Lite via Bedrock.
4. Split the extracted text into paragraph-aware chunks of up to 800 characters.
5. Convert each chunk into a 1,536-dimension vector using Amazon Titan Embed.
6. Write the summary to `lab_reports.ai_layman_summary` and all chunk vectors to `report_embeddings` in RDS PostgreSQL.

---

## Tech Stack

| Component | Detail |
|---|---|
| Runtime | Python 3.12 (AWS Lambda) |
| Deployment | AWS SAM (`template.yaml`) |
| OCR | AWS Textract (`detect_document_text`) |
| Summarization | Amazon Nova Lite via Bedrock Converse API |
| Embeddings | Amazon Titan Embed (`amazon.titan-embed-text-v1`) via Bedrock |
| Database driver | psycopg3 sync (Lambda has no async event loop) |
| Secrets | AWS Secrets Manager (DB DSN fetched at cold start and cached) |

---

## Source Layout

```
src/
  handler.py       Lambda entry point (lambda_handler); orchestrates the pipeline
  bedrock.py       Bedrock client setup via STS cross-account AssumeRole; summarize and embed functions
  textract_ocr.py  Calls Textract and joins LINE blocks into plain text
  chunking.py      Splits text into paragraph-aware chunks of ≤800 characters
  db.py            Reads DB DSN from Secrets Manager at cold start; psycopg3 sync connection
template.yaml      SAM template — function definition, EventBridge trigger, VPC config, environment variables
events/
  s3-put.json      Sample EventBridge event payload for local testing
```

---

## Deployment

This Lambda is deployed via SAM CI, not through the ECR/ArgoCD pipeline used by EKS services.

```bash
# Build in a Lambda-matching container (required for psycopg3 native binary compatibility)
sam build --use-container

# Deploy — reads VPC config, IAM role ARN, and bucket name from SSM Parameter Store
sam deploy --stack-name lablumen-ai \
  --s3-bucket <sam-artifacts-bucket> \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    "ReportsBucketName=..." \
    "ExecutionRoleArn=..." \
    "SubnetIds=..." \
    "SecurityGroupId=..." \
    "BedrockCrossAccountRoleArn=..."
```

Terraform manages the IAM execution role, security group, VPC subnets, and S3 bucket. The Lambda only owns its own function code and CloudWatch log group.

---

## Configuration

Environment variables are set in `template.yaml` and resolved from SSM at SAM deploy time.

| Variable | Description |
|---|---|
| `DATABASE_SECRET_ID` | Secrets Manager secret name for the DB DSN (`lablumen/app/database-url`) |
| `BEDROCK_EMBED_MODEL_ID` | `amazon.titan-embed-text-v1` |
| `BEDROCK_TEXT_MODEL_ID` | `amazon.nova-lite-v1:0` |
| `BEDROCK_CROSS_ACCOUNT_ROLE_ARN` | Cross-account IAM role for Bedrock access |

---

## Cross-Account Bedrock

The AWS organization's SCP restricts Bedrock access to a separate account. At cold start, the Lambda assumes a cross-account IAM role via STS `AssumeRole` to create the Bedrock client. This client is cached in module-level state for the lifetime of the Lambda execution environment, so subsequent invocations skip the STS call.

---

## CI/CD

| Trigger | What Happens |
|---|---|
| Pull request | Lint (`ruff`) + unit tests (`pytest`) |
| Merge to `main` | `sam build --use-container` → reads SSM params → `sam deploy` |

Defined in `.github/workflows/ci.yml`. Uses the `lablumen-ai-lambda-deploy` IAM role via GitHub OIDC.
