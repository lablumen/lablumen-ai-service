import io

import boto3
import pypdf

_s3 = boto3.client("s3")


def extract_text(bucket: str, key: str) -> str:
    pdf_bytes = _s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)
