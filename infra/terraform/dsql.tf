# =====================================================================
# Aurora DSQL — source de vérité des AO, abonnements et paiements
# =====================================================================
# Cluster mono-région pour démarrer (voir CLAUDE.md : pas de FK/trigger/
# vue, connexion IAM uniquement, 1 DDL par transaction). Passage en
# multi-région (witness_region + aws_dsql_cluster_peering) différé à une
# phase ultérieure si un besoin de haute disponibilité inter-région émerge.

resource "aws_dsql_cluster" "main" {
  deletion_protection_enabled = var.dsql_deletion_protection

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-dsql"
  })
}

locals {
  # Format documenté : {identifier}.dsql.{region}.on.aws
  dsql_endpoint = "${aws_dsql_cluster.main.identifier}.dsql.${var.aws_region}.on.aws"
}

output "dsql_cluster_identifier" {
  description = "Identifiant du cluster Aurora DSQL"
  value       = aws_dsql_cluster.main.identifier
}

output "dsql_endpoint" {
  description = "Endpoint de connexion du cluster Aurora DSQL"
  value       = local.dsql_endpoint
}
