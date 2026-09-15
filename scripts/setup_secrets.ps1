Write-Host @'
RepoMind Secret Setup
=====================

Run these commands to set the required secrets:

1. Gemini API Key:
   aws ssm put-parameter --name "/repomind/prod/gemini-api-key" --value "YOUR_GEMINI_API_KEY" --type SecureString --region ap-south-1 --overwrite

2. GitHub Token (for private repo access):
   aws ssm put-parameter --name "/repomind/prod/github-token" --value "YOUR_GITHUB_TOKEN" --type SecureString --region ap-south-1 --overwrite

NOTE: Replace YOUR_GEMINI_API_KEY and YOUR_GITHUB_TOKEN with actual values.
NEVER commit actual secret values to Git.
'@
