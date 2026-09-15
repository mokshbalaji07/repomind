import datetime
import logging
from typing import Optional, List
import boto3

from . import config

logger = logging.getLogger(__name__)

class StateManager:
    def __init__(self, table_name=config.DYNAMODB_TABLE, region=config.AWS_REGION):
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)

    def _now(self):
        return datetime.datetime.utcnow().isoformat() + 'Z'

    def create_job(self, repo: str, job_id: str, commit_sha: str) -> dict:
        now = self._now()
        item = {
            'PK': f"REPO#{repo}",
            'SK': f"JOB#{job_id}",
            'job_id': job_id,
            'repo': repo,
            'commit_sha': commit_sha,
            'status': 'STARTED',
            'files_total': 0,
            'files_processed': 0,
            'files_skipped': 0,
            'files_failed': 0,
            'created_at': now,
            'updated_at': now
        }
        try:
            self.table.put_item(Item=item)
            return item
        except Exception as e:
            logger.error(f"Error creating job {job_id} for {repo}: {e}")
            raise

    def update_job_status(self, repo: str, job_id: str, status: str, files_total: Optional[int] = None, 
                          files_processed: Optional[int] = None, files_skipped: Optional[int] = None, 
                          files_failed: Optional[int] = None, error: Optional[str] = None):
        update_expr = ["#status = :status", "#updated = :updated"]
        expr_attr_names = {"#status": "status", "#updated": "updated_at"}
        expr_attr_values = {":status": status, ":updated": self._now()}

        if files_total is not None:
            update_expr.append("files_total = :ft")
            expr_attr_values[":ft"] = files_total
        if files_processed is not None:
            update_expr.append("files_processed = :fp")
            expr_attr_values[":fp"] = files_processed
        if files_skipped is not None:
            update_expr.append("files_skipped = :fs")
            expr_attr_values[":fs"] = files_skipped
        if files_failed is not None:
            update_expr.append("files_failed = :ff")
            expr_attr_values[":ff"] = files_failed
        if error is not None:
            update_expr.append("error = :err")
            expr_attr_values[":err"] = error

        try:
            self.table.update_item(
                Key={'PK': f"REPO#{repo}", 'SK': f"JOB#{job_id}"},
                UpdateExpression="SET " + ", ".join(update_expr),
                ExpressionAttributeNames=expr_attr_names,
                ExpressionAttributeValues=expr_attr_values
            )
        except Exception as e:
            logger.error(f"Error updating job {job_id} for {repo}: {e}")

    def is_commit_processed(self, repo: str, commit_sha: str) -> bool:
        try:
            response = self.table.get_item(
                Key={'PK': f"REPO#{repo}", 'SK': f"COMMIT#{commit_sha}"}
            )
            item = response.get('Item')
            return item is not None and item.get('status') == 'COMPLETED'
        except Exception as e:
            logger.error(f"Error checking commit {commit_sha} for {repo}: {e}")
            return False

    def mark_commit_processed(self, repo: str, commit_sha: str, job_id: str):
        try:
            self.table.put_item(Item={
                'PK': f"REPO#{repo}",
                'SK': f"COMMIT#{commit_sha}",
                'job_id': job_id,
                'status': 'COMPLETED',
                'updated_at': self._now()
            })
        except Exception as e:
            logger.error(f"Error marking commit {commit_sha} processed for {repo}: {e}")

    def upsert_file_metadata(self, repo: str, file_path: str, commit_sha: str, chunk_count: int, s3_key: str):
        try:
            self.table.put_item(Item={
                'PK': f"REPO#{repo}",
                'SK': f"FILE#{file_path}",
                'file_path': file_path,
                'commit_sha': commit_sha,
                'chunk_count': chunk_count,
                's3_key': s3_key,
                'updated_at': self._now()
            })
        except Exception as e:
            logger.error(f"Error upserting file metadata for {file_path} in {repo}: {e}")

    def delete_file_metadata(self, repo: str, file_path: str):
        try:
            self.table.delete_item(
                Key={'PK': f"REPO#{repo}", 'SK': f"FILE#{file_path}"}
            )
        except Exception as e:
            logger.error(f"Error deleting file metadata for {file_path} in {repo}: {e}")

    def get_file_metadata(self, repo: str, file_path: str) -> Optional[dict]:
        try:
            response = self.table.get_item(
                Key={'PK': f"REPO#{repo}", 'SK': f"FILE#{file_path}"}
            )
            return response.get('Item')
        except Exception as e:
            logger.error(f"Error getting file metadata for {file_path} in {repo}: {e}")
            return None

    def list_indexed_files(self, repo: str) -> List[dict]:
        try:
            response = self.table.query(
                KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
                ExpressionAttributeValues={
                    ":pk": f"REPO#{repo}",
                    ":sk_prefix": "FILE#"
                }
            )
            return response.get('Items', [])
        except Exception as e:
            logger.error(f"Error listing indexed files for {repo}: {e}")
            return []

    def get_job(self, repo: str, job_id: str) -> Optional[dict]:
        try:
            response = self.table.get_item(
                Key={'PK': f"REPO#{repo}", 'SK': f"JOB#{job_id}"}
            )
            return response.get('Item')
        except Exception as e:
            logger.error(f"Error getting job {job_id} for {repo}: {e}")
            return None
