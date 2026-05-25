# S3 bucket holding the ML artefacts that don't belong in the container
# image: model.pkl (78 MB), reviews_embeddings.parquet, and
# regulations/embeddings.parquet. Backend tasks download these on boot
# (see backend Dockerfile CMD); the GitHub Actions deploy uploads new
# versions during the build step.
#
# Bucket name needs to be globally unique -- we suffix with the account ID
# to avoid collisions.

resource "aws_s3_bucket" "artefacts" {
  bucket = "${local.name}-artefacts-${data.aws_caller_identity.current.account_id}"
  tags = { Name = "${local.name}-artefacts" }
}

resource "aws_s3_bucket_public_access_block" "artefacts" {
  bucket = aws_s3_bucket.artefacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "artefacts" {
  bucket = aws_s3_bucket.artefacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "artefacts" {
  bucket = aws_s3_bucket.artefacts.id

  rule {
    id     = "expire-old-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# Task role -- backend container reads at boot.
resource "aws_iam_role_policy" "task_s3_read" {
  name = "${local.name}-task-s3-read"
  role = aws_iam_role.task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.artefacts.arn,
          "${aws_s3_bucket.artefacts.arn}/*",
        ]
      },
    ]
  })
}

# GitHub Actions deploy role -- upload step writes new artefact versions.
resource "aws_iam_role_policy" "gha_s3_write" {
  name = "${local.name}-gha-s3-write"
  role = aws_iam_role.github_actions_deploy.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:PutObject", "s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.artefacts.arn,
          "${aws_s3_bucket.artefacts.arn}/*",
        ]
      },
    ]
  })
}
