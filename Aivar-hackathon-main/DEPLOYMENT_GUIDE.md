# AWS SAM Deployment Guide for Aivar Hackathon

## Step 1: Configure AWS Credentials

You need your AWS credentials (Access Key ID and Secret Access Key). Run the following in PowerShell:

```powershell
aws configure
```

You'll be prompted for:
- **AWS Access Key ID**: Paste your access key
- **AWS Secret Access Key**: Paste your secret key (won't be displayed)
- **Default region name**: us-east-1 (or your preferred region)
- **Default output format**: json

## Step 2: Build Your Application

Before deploying, build the SAM application:

```powershell
sam build
```

This will:
- Resolve dependencies from requirements.txt
- Prepare the application for deployment
- Create a `.aws-sam` directory with the built artifacts

## Step 3: Deploy Using SAM CLI

### Option A: Guided Deployment (Recommended for first time)

Run the guided deployment which will prompt you for configuration:

```powershell
sam deploy --guided
```

You'll be asked:
- **Stack Name**: aivar-hackathon-stack (recommended)
- **AWS Region**: us-east-1 (or your preferred region)
- **Parameter EnvironmentName**: dev, staging, or prod
- **Confirm changes before deploy**: y (yes)
- **Allow SAM CLI IAM role creation**: y (yes)
- **Save parameters to samconfig.toml**: y (yes)

### Option B: Standard Deployment (After initial guided setup)

For subsequent deployments, use:

```powershell
sam deploy
```

This will use the configuration saved in `samconfig.toml`.

## Step 4: Monitor Deployment

The deployment may take 5-10 minutes. SAM will show:
- CloudFormation stack creation progress
- Resource creation status
- Final stack outputs

## Step 5: Test Your Deployment

After deployment completes, you'll get an API endpoint URL. Test it:

```powershell
$apiUrl = "https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/dev"

$body = @{
    provider = "mock"
    prompt = "Hello, world!"
} | ConvertTo-Json

Invoke-WebRequest -Uri "$apiUrl/generate" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

## Step 6: View CloudWatch Logs

View Lambda function logs:

```powershell
sam logs -n FastAPIFunction --stack-name aivar-hackathon-stack
```

## Environment Variables

The Lambda function can access these environment variables:
- `AUDIT_TABLE`: DynamoDB table for audit logs
- `AUDIT_BUCKET`: S3 bucket for audit backup
- `ENVIRONMENT`: dev/staging/prod

Update `.env` file for provider API keys (OpenAI, Anthropic):
- These must be set as Lambda environment variables in the console or via SAM parameters

## Cleanup

To delete all AWS resources:

```powershell
sam delete --stack-name aivar-hackathon-stack
```

## Troubleshooting

### "User: arn:aws:iam::... is not authorized" error
- Ensure your AWS credentials have sufficient IAM permissions
- Required: CloudFormation, Lambda, API Gateway, DynamoDB, S3, IAM

### Lambda Timeout Issues
- Increase `Timeout` in template.yaml (currently 30 seconds)
- Increase `MemorySize` for better performance (currently 512 MB)

### Static Files Not Loading
- In Lambda environment, static files are served from the `/static` route
- Consider using S3 + CloudFront for static files in production

### Provider API Keys Not Working
- Set environment variables in the Lambda function via AWS Console
- Or update samconfig.toml with parameter overrides
