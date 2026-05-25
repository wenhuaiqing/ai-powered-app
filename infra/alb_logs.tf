# S3 bucket capturing ALB access logs.
#
# Every HTTP request that hits the load balancer (frontend SPA hits, API
# calls, /orb/chat SSE opens, etc.) lands as a single line in a gzipped
# log file under `AWSLogs/<account>/elasticloadbalancing/<region>/...`.
# Athena reads the bucket directly -- no transform job needed.
#
# Bucket name suffixed with account ID for global uniqueness. Setup +
# query examples in infra/README.md ("ALB access logs + Athena").

resource "aws_s3_bucket" "alb_logs" {
  bucket        = "${local.name}-alb-logs-${data.aws_caller_identity.current.account_id}"
  force_destroy = true   # demo: don't block `terraform destroy`
  tags          = { Name = "${local.name}-alb-logs" }
}

resource "aws_s3_bucket_public_access_block" "alb_logs" {
  bucket                  = aws_s3_bucket.alb_logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Expire log objects after 90 days -- pennies for typical demo traffic
# but cleanup keeps it tidy + bounded.
resource "aws_s3_bucket_lifecycle_configuration" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  rule {
    id     = "expire-old-logs"
    status = "Enabled"

    filter {}

    expiration {
      days = 90
    }
  }
}

# The ELB service identity in the current region. AWS rotates this per
# region; this data source returns the correct AWS-account ARN.
data "aws_elb_service_account" "main" {}

# Only the ELB service principal for this region can write objects under
# `AWSLogs/`. Nothing else can put / list / read.
resource "aws_s3_bucket_policy" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "ELBLogDelivery"
      Effect    = "Allow"
      Principal = { AWS = data.aws_elb_service_account.main.arn }
      Action    = "s3:PutObject"
      Resource  = "${aws_s3_bucket.alb_logs.arn}/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
    }]
  })
}
