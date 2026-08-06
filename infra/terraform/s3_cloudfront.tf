# =====================================================================
# S3 + CloudFront — diffusion du portail public statique (CLAUDE.md §1)
# =====================================================================

resource "aws_s3_bucket" "public_site" {
  bucket = "${local.name_prefix}-public-site-${data.aws_caller_identity.current.account_id}"
  tags   = local.tags
}

resource "aws_s3_bucket_public_access_block" "public_site" {
  bucket                  = aws_s3_bucket.public_site.id
  block_public_acls       = true
  block_public_policy     = false # nécessaire pour la policy OAC ci-dessous
  ignore_public_acls      = true
  restrict_public_buckets = false
}

resource "aws_cloudfront_origin_access_control" "public_site" {
  name                              = "${local.name_prefix}-public-site-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "public_site" {
  enabled             = true
  default_root_object = "index.html"
  comment             = "${local.name_prefix} — portail public OptiProcure"
  price_class         = "PriceClass_100"

  origin {
    domain_name              = aws_s3_bucket.public_site.bucket_regional_domain_name
    origin_id                = "s3-public-site"
    origin_access_control_id = aws_cloudfront_origin_access_control.public_site.id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "s3-public-site"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  # Pages d'erreur SPA-friendly ; à ajuster si le rendu Next.js statique
  # génère déjà des pages 404 dédiées.
  custom_error_response {
    error_code         = 404
    response_code      = 404
    response_page_path = "/404.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
    # Passer à un certificat ACM (us-east-1) + aliases une fois
    # public_site_domain défini.
  }

  tags = local.tags
}

data "aws_iam_policy_document" "public_site_bucket_policy" {
  statement {
    sid       = "AllowCloudFrontOAC"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.public_site.arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.public_site.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "public_site" {
  bucket = aws_s3_bucket.public_site.id
  policy = data.aws_iam_policy_document.public_site_bucket_policy.json
}

# --- Bucket des manifestes de publication (CLAUDE.md §6.1) -------------
# GitHub Actions ne reçoit que le batchId ; le détail reste dans S3.

resource "aws_s3_bucket" "manifests" {
  bucket = "${local.name_prefix}-manifests-${data.aws_caller_identity.current.account_id}"
  tags   = local.tags
}

resource "aws_s3_bucket_public_access_block" "manifests" {
  bucket                  = aws_s3_bucket.manifests.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "manifests" {
  bucket = aws_s3_bucket.manifests.id
  rule {
    id     = "expire-old-manifests"
    status = "Enabled"
    expiration {
      days = 90
    }
  }
}

# --- Bucket des documents joints aux AO (DAO, cahier des charges) -----
# Téléchargement réservé aux abonnés selon leur plan (PRD §3.3) : accès
# via URL présignée générée par la Lambda métier, jamais public direct.

resource "aws_s3_bucket" "documents" {
  bucket = "${local.name_prefix}-tender-documents-${data.aws_caller_identity.current.account_id}"
  tags   = local.tags
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket                  = aws_s3_bucket.documents.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# --- Bucket des fichiers de migration SQL -------------------------------

resource "aws_s3_bucket" "migrations" {
  bucket = "${local.name_prefix}-db-migrations-${data.aws_caller_identity.current.account_id}"
  tags   = local.tags
}

resource "aws_s3_bucket_public_access_block" "migrations" {
  bucket                  = aws_s3_bucket.migrations.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "migrations" {
  bucket = aws_s3_bucket.migrations.id
  versioning_configuration {
    status = "Enabled"
  }
}

output "public_site_bucket_name" {
  value = aws_s3_bucket.public_site.bucket
}

output "cloudfront_domain_name" {
  value = aws_cloudfront_distribution.public_site.domain_name
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.public_site.id
}
