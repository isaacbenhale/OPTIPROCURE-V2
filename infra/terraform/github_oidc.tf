# =====================================================================
# Fédération OIDC GitHub → AWS (CLAUDE.md §4.3 : "plutôt que des clés
# AWS statiques conservées dans GitHub Secrets")
# =====================================================================

data "tls_certificate" "github_oidc" {
  url = "https://token.actions.githubusercontent.com/.well-known/openid-configuration"
}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github_oidc.certificates[0].sha1_fingerprint]

  tags = local.tags
}

data "aws_iam_policy_document" "github_actions_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = [for b in var.github_allowed_branches : "repo:${var.github_org}/${var.github_repo}:ref:refs/heads/${b}"]
    }
  }
}

resource "aws_iam_role" "github_actions_deploy" {
  name               = "${local.name_prefix}-github-actions-deploy"
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume.json
  tags               = local.tags
}

# Permissions strictement limitées au déploiement du frontend statique :
# upload S3 + invalidation CloudFront ciblée (CLAUDE.md : "invalidations
# CloudFront ciblées sur les URL réellement modifiées").
data "aws_iam_policy_document" "github_actions_deploy_policy" {
  statement {
    sid       = "SyncPublicSite"
    actions   = ["s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
    resources = [aws_s3_bucket.public_site.arn, "${aws_s3_bucket.public_site.arn}/*"]
  }
  statement {
    sid       = "ReadManifests"
    actions   = ["s3:GetObject", "s3:ListBucket"]
    resources = [aws_s3_bucket.manifests.arn, "${aws_s3_bucket.manifests.arn}/*"]
  }
  statement {
    sid       = "InvalidateCloudFront"
    actions   = ["cloudfront:CreateInvalidation"]
    resources = [aws_cloudfront_distribution.public_site.arn]
  }
}

resource "aws_iam_role_policy" "github_actions_deploy" {
  name   = "${local.name_prefix}-github-actions-deploy-policy"
  role   = aws_iam_role.github_actions_deploy.id
  policy = data.aws_iam_policy_document.github_actions_deploy_policy.json
}

output "github_actions_deploy_role_arn" {
  description = "À utiliser dans .github/workflows/*.yml via aws-actions/configure-aws-credentials"
  value       = aws_iam_role.github_actions_deploy.arn
}
