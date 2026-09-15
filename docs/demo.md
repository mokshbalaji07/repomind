# Demo Walkthrough

Follow these steps to demonstrate the full capabilities of the RepoMind pipeline.

## 1. Initial Setup
1. Ensure the infrastructure is deployed via Terraform.
2. Open `frontend/index.html` in your browser.
3. Configure the **Query API Endpoint** with the Lambda Function URL.

## 2. Indexing a Repository
1. In your configured target repository, push initial code (e.g., a simple Python API).
2. Show the GitHub Actions workflow triggering in the repository.
3. Open the AWS Step Functions console and show the visual state machine execution, highlighting the parallel Map state.
4. Show the resulting artifacts in S3 and metadata in DynamoDB.

## 3. Asking a Question
1. In the frontend, enter the repository name (e.g., `yourusername/test-repo`).
2. Ask a question: *"How does the application connect to the database?"*
3. Click **Ask RepoMind**.
4. Observe the loading state.
5. Review the Answer and the Source References cards (highlighting file paths and line numbers).

## 4. Modifying Code (Incremental Re-indexing)
1. In the repository, modify a file (e.g., change the database connection string logic).
2. Commit and push the change.
3. Show the GitHub Actions workflow running again.
4. In AWS Step Functions, show that the Map state *only* processed the modified file, skipping unchanged files.
5. Re-ask the same question in the UI and show that the answer updates based on the new code.

## 5. Deleting a File
1. Delete a file from the repository.
2. Push the change.
3. Show the ingestion pipeline cleaning up the S3 artifacts for that file.
4. Ask a question related to the deleted file to prove it is no longer in the context window.

## 6. Insufficient Evidence Test
1. Ask a question about a feature that doesn't exist in the code: *"Where is the Redis caching layer implemented?"*
2. RepoMind should intelligently respond that the information is not present in the repository, rather than hallucinating an answer.

## 7. Duplicate Commit Test
1. Manually trigger the ingestion pipeline with the same commit SHA.
2. Demonstrate that the pipeline recognizes the state is already indexed and gracefully exits without reprocessing.
