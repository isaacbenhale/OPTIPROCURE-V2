# =====================================================================
# S3 + CloudFront — portail back-office (frontend-admin/, module 03)
# =====================================================================
# Hébergement séparé du portail public (public_site) : deux portails
# distincts (PRD §2) — celui-ci sert une SPA authentifiée par Cognito, pas
# du contenu statique public/SEO. Même pattern que s3_cloudfront.tf.

resource "aws_s3_bucket" "admin_site" {
  bucket = "${local.name_prefix}-admin-site-${data.aws_caller_identity.current.account_id}"
  tags   = local.tags
}

resource "aws_s3_bucket_public_access_block" "admin_site" {
  bucket                  = aws_s3_bucket.admin_site.id
  block_public_acls       = true
  block_public_policy     = false # nécessaire pour la policy OAC ci-dessous
  ignore_public_acls      = true
  restrict_public_buckets = false
}

resource "aws_cloudfront_origin_access_control" "admin_site" {
  name                              = "${local.name_prefix}-admin-site-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "admin_site" {
  enabled             = true
  default_root_object = "index.html"
  comment             = "${local.name_prefix} — back-office OptiProcure (SPA)"
  price_class         = "PriceClass_100"

  origin {
    domain_name              = aws_s3_bucket.admin_site.bucket_regional_domain_name
    origin_id                = "s3-admin-site"
    origin_access_control_id = aws_cloudfront_origin_access_control.admin_site.id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "s3-admin-site"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  # SPA (react-router) : toute route inconnue de S3 (refresh sur une URL
  # profonde, ex. /tenders/abc) doit servir index.html en 200, pas une
  # erreur — contrairement au portail public qui a de vraies pages 404.
  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = local.tags
}

data "aws_iam_policy_document" "admin_site_bucket_policy" {
  statement {
    sid       = "AllowCloudFrontOAC"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.admin_site.arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.admin_site.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "admin_site" {
  bucket = aws_s3_bucket.admin_site.id
  policy = data.aws_iam_policy_document.admin_site_bucket_policy.json
}

output "admin_site_bucket_name" {
  value = aws_s3_bucket.admin_site.bucket
}

output "admin_cloudfront_domain_name" {
  value = aws_cloudfront_distribution.admin_site.domain_name
}

output "admin_cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.admin_site.id
}
