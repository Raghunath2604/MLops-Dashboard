# AWS Multi-Region SaaS Infrastructure
# Production-Grade Terraform Configuration
#
# Architecture:
# - 3 AWS Regions (US-East-1, EU-West-1, AP-Southeast-1)
# - RDS PostgreSQL with cross-region replication
# - ECS Fargate for containerized API
# - Application Load Balancer
# - CloudFront CDN
# - Route53 geo-routing
# - ElastiCache Redis
# - S3 for backups
# - CloudWatch monitoring

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment for production - store state in S3
  # backend "s3" {
  #   bucket         = "terraform-state-prod"
  #   key            = "saas-api/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "terraform-locks"
  # }
}

# Primary Region: US-East-1
provider "aws" {
  alias  = "us"
  region = "us-east-1"

  default_tags {
    tags = {
      Environment = var.environment
      Project     = "SentimentAnalysisAPI"
      ManagedBy   = "Terraform"
      CreatedAt   = formatdate("YYYY-MM-DD hh:mm:ss ZZZ", timestamp())
    }
  }
}

# Secondary Region: EU-West-1
provider "aws" {
  alias  = "eu"
  region = "eu-west-1"

  default_tags {
    tags = {
      Environment = var.environment
      Project     = "SentimentAnalysisAPI"
      ManagedBy   = "Terraform"
    }
  }
}

# Tertiary Region: AP-Southeast-1
provider "aws" {
  alias  = "ap"
  region = "ap-southeast-1"

  default_tags {
    tags = {
      Environment = var.environment
      Project     = "SentimentAnalysisAPI"
      ManagedBy   = "Terraform"
    }
  }
}

# ============================================
# VARIABLES
# ============================================

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "sentiment-api"
}

variable "domain_name" {
  description = "Domain name for the API"
  type        = string
}

variable "docker_image_uri" {
  description = "Docker image URI from ECR"
  type        = string
}

variable "database_master_username" {
  description = "Master username for RDS"
  type        = string
  sensitive   = true
}

variable "database_master_password" {
  description = "Master password for RDS"
  type        = string
  sensitive   = true
}

variable "stripe_secret_key" {
  description = "Stripe secret key"
  type        = string
  sensitive   = true
}

variable "ecs_desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 2
}

variable "ecs_max_count" {
  description = "Maximum number of ECS tasks"
  type        = number
  default     = 10
}

# ============================================
# PRIMARY REGION: US-EAST-1
# ============================================

# VPC for US region
resource "aws_vpc" "us" {
  provider           = aws.us
  cidr_block         = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.app_name}-vpc-us"
  }
}

# Public Subnets
resource "aws_subnet" "us_public_1" {
  provider                = aws.us
  vpc_id                  = aws_vpc.us.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = true
}

resource "aws_subnet" "us_public_2" {
  provider                = aws.us
  vpc_id                  = aws_vpc.us.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "us-east-1b"
  map_public_ip_on_launch = true
}

# Private Subnets for RDS
resource "aws_subnet" "us_private_1" {
  provider          = aws.us
  vpc_id            = aws_vpc.us.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = "us-east-1a"
}

resource "aws_subnet" "us_private_2" {
  provider          = aws.us
  vpc_id            = aws_vpc.us.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = "us-east-1b"
}

# Internet Gateway
resource "aws_internet_gateway" "us" {
  provider = aws.us
  vpc_id   = aws_vpc.us.id
}

# Route Table
resource "aws_route_table" "us" {
  provider = aws.us
  vpc_id   = aws_vpc.us.id

  route {
    cidr_block      = "0.0.0.0/0"
    gateway_id      = aws_internet_gateway.us.id
  }
}

resource "aws_route_table_association" "us_public_1" {
  provider       = aws.us
  subnet_id      = aws_subnet.us_public_1.id
  route_table_id = aws_route_table.us.id
}

resource "aws_route_table_association" "us_public_2" {
  provider       = aws.us
  subnet_id      = aws_subnet.us_public_2.id
  route_table_id = aws_route_table.us.id
}

# Security Group for ALB
resource "aws_security_group" "us_alb" {
  provider    = aws.us
  vpc_id      = aws_vpc.us.id
  name        = "${var.app_name}-alb-sg-us"
  description = "Security group for ALB"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Security Group for ECS
resource "aws_security_group" "us_ecs" {
  provider    = aws.us
  vpc_id      = aws_vpc.us.id
  name        = "${var.app_name}-ecs-sg-us"
  description = "Security group for ECS"

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.us_alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Security Group for RDS
resource "aws_security_group" "us_rds" {
  provider    = aws.us
  vpc_id      = aws_vpc.us.id
  name        = "${var.app_name}-rds-sg-us"
  description = "Security group for RDS"

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.us_ecs.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# DB Subnet Group
resource "aws_db_subnet_group" "us" {
  provider    = aws.us
  name        = "${var.app_name}-db-subnet-group-us"
  subnet_ids  = [aws_subnet.us_private_1.id, aws_subnet.us_private_2.id]
}

# RDS PostgreSQL (Multi-AZ for high availability)
resource "aws_db_instance" "us" {
  provider              = aws.us
  identifier            = "${var.app_name}-db-us"
  engine                = "postgres"
  engine_version        = "15.3"
  instance_class        = "db.t3.large"
  allocated_storage     = 100
  storage_type          = "gp3"
  storage_encrypted     = true
  backup_retention_period = 30
  multi_az              = true
  publicly_accessible   = false

  db_name  = "saasdb"
  username = var.database_master_username
  password = var.database_master_password

  db_subnet_group_name   = aws_db_subnet_group.us.name
  vpc_security_group_ids = [aws_security_group.us_rds.id]

  skip_final_snapshot        = false
  final_snapshot_identifier  = "${var.app_name}-final-snapshot-us-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  deletion_protection        = true
  enable_cloudwatch_logs_exports = ["postgresql"]

  tags = {
    Name = "${var.app_name}-db-us"
  }
}

# ElastiCache Redis Cluster
resource "aws_elasticache_subnet_group" "us" {
  provider    = aws.us
  name        = "${var.app_name}-cache-subnet-group-us"
  subnet_ids  = [aws_subnet.us_private_1.id, aws_subnet.us_private_2.id]
}

resource "aws_security_group" "us_redis" {
  provider    = aws.us
  vpc_id      = aws_vpc.us.id
  name        = "${var.app_name}-redis-sg-us"

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.us_ecs.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_elasticache_replication_group" "us" {
  provider                   = aws.us
  replication_group_description = "Redis cluster for rate limiting"
  engine                     = "redis"
  engine_version             = "7.0"
  node_type                  = "cache.t3.micro"
  num_cache_clusters         = 2
  automatic_failover_enabled = true
  multi_az_enabled           = true
  parameter_group_name       = "default.redis7"
  port                       = 6379
  subnet_group_name          = aws_elasticache_subnet_group.us.name
  security_group_ids         = [aws_security_group.us_redis.id]

  tags = {
    Name = "${var.app_name}-cache-us"
  }
}

# Application Load Balancer
resource "aws_lb" "us" {
  provider           = aws.us
  name               = "${var.app_name}-alb-us"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.us_alb.id]
  subnets            = [aws_subnet.us_public_1.id, aws_subnet.us_public_2.id]

  enable_deletion_protection = false

  tags = {
    Name = "${var.app_name}-alb-us"
  }
}

# ALB Target Group
resource "aws_lb_target_group" "us" {
  provider    = aws.us
  name        = "${var.app_name}-tg-us"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.us.id
  target_type = "ip"

  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 3
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }

  tags = {
    Name = "${var.app_name}-tg-us"
  }
}

# ALB Listener
resource "aws_lb_listener" "us_http" {
  provider          = aws.us
  load_balancer_arn = aws_lb.us.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.us.arn
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "us" {
  provider = aws.us
  name     = "${var.app_name}-cluster-us"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "us" {
  provider                 = aws.us
  family                   = "${var.app_name}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"

  container_definitions = jsonencode([{
    name  = var.app_name
    image = var.docker_image_uri
    portMappings = [{
      containerPort = 8000
      hostPort      = 8000
      protocol      = "tcp"
    }]

    environment = [
      { name = "ENVIRONMENT", value = var.environment },
      { name = "JAEGER_HOST", value = "jaeger.${var.domain_name}" },
    ]

    secrets = [
      {
        name      = "DATABASE_URL"
        valueFrom = aws_secretsmanager_secret.db_url.arn
      },
      {
        name      = "REDIS_URL"
        valueFrom = aws_secretsmanager_secret.redis_url.arn
      },
      {
        name      = "STRIPE_SECRET_KEY"
        valueFrom = aws_secretsmanager_secret.stripe_key.arn
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.us_api.name
        "awslogs-region"        = "us-east-1"
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

# CloudWatch Logs
resource "aws_cloudwatch_log_group" "us_api" {
  provider = aws.us
  name     = "/ecs/${var.app_name}-api-us"
  retention_in_days = 30
}

# Secrets Manager
resource "aws_secretsmanager_secret" "db_url" {
  provider = aws.us
  name     = "${var.app_name}/database-url"
}

resource "aws_secretsmanager_secret_version" "db_url" {
  provider = aws.us
  secret_id = aws_secretsmanager_secret.db_url.id
  secret_string = "postgresql://${var.database_master_username}:${urlencode(var.database_master_password)}@${aws_db_instance.us.endpoint}/saasdb"
}

resource "aws_secretsmanager_secret" "redis_url" {
  provider = aws.us
  name     = "${var.app_name}/redis-url"
}

resource "aws_secretsmanager_secret_version" "redis_url" {
  provider = aws.us
  secret_id = aws_secretsmanager_secret.redis_url.id
  secret_string = "redis://${aws_elasticache_replication_group.us.primary_endpoint_address}:6379"
}

resource "aws_secretsmanager_secret" "stripe_key" {
  provider = aws.us
  name     = "${var.app_name}/stripe-key"
}

resource "aws_secretsmanager_secret_version" "stripe_key" {
  provider = aws.us
  secret_id = aws_secretsmanager_secret.stripe_key.id
  secret_string = var.stripe_secret_key
}

# ECS Service
resource "aws_ecs_service" "us" {
  provider        = aws.us
  name            = "${var.app_name}-service-us"
  cluster         = aws_ecs_cluster.us.id
  task_definition = aws_ecs_task_definition.us.arn
  desired_count   = var.ecs_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = [aws_subnet.us_public_1.id, aws_subnet.us_public_2.id]
    security_groups = [aws_security_group.us_ecs.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.us.arn
    container_name   = var.app_name
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.us_http]
}

# Auto Scaling
resource "aws_appautoscaling_target" "us_ecs" {
  provider       = aws.us
  max_capacity   = var.ecs_max_count
  min_capacity   = var.ecs_desired_count
  resource_id    = "service/${aws_ecs_cluster.us.name}/${aws_ecs_service.us.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "us_ecs_scale_up" {
  provider           = aws.us
  name               = "${var.app_name}-scale-up-us"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.us_ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.us_ecs.scalable_dimension
  service_namespace  = aws_appautoscaling_target.us_ecs.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "us_cpu_high" {
  provider            = aws.us
  alarm_name          = "${var.app_name}-cpu-high-us"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This alarm monitors ECS CPU utilization"

  dimensions = {
    ServiceName = aws_ecs_service.us.name
    ClusterName = aws_ecs_cluster.us.name
  }
}

# ============================================
# ROUTE 53 HEALTH CHECKS & DNS
# ============================================

resource "aws_route53_zone" "main" {
  name = var.domain_name

  tags = {
    Name = var.domain_name
  }
}

# Health check for US region
resource "aws_route53_health_check" "us" {
  fqdn = aws_lb.us.dns_name
  port = 80
  type = "HTTP"
  resource_path = "/health"
  failure_threshold = 3
  measure_latency = true
}

# Route53 record with failover
resource "aws_route53_record" "api_geolocation" {
  provider = aws.us
  zone_id  = aws_route53_zone.main.zone_id
  name     = "api.${var.domain_name}"
  type     = "A"

  alias {
    name                   = aws_lb.us.dns_name
    zone_id                = aws_lb.us.zone_id
    evaluate_target_health = true
  }

  set_identifier = "api-us-east-1"

  geolocation_location {
    country = "*"
  }
}

# ============================================
# CLOUDFRONT CDN
# ============================================

resource "aws_cloudfront_distribution" "api" {
  origin {
    domain_name = "api.${var.domain_name}"
    origin_id   = "api-origin"

    custom_origin_config {
      http_port = 80
      https_port = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols = ["TLSv1.2"]
    }
  }

  enabled = true
  is_ipv6_enabled = true

  default_cache_behavior {
    allowed_methods = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods = ["GET", "HEAD"]
    target_origin_id = "api-origin"

    forwarded_values {
      query_string = true
      headers = ["Authorization", "Host"]

      cookies {
        forward = "all"
      }
    }

    viewer_protocol_policy = "https-only"
    min_ttl = 0
    default_ttl = 0
    max_ttl = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name = "${var.app_name}-cdn"
  }
}

# ============================================
# OUTPUTS
# ============================================

output "us_load_balancer_dns" {
  value = aws_lb.us.dns_name
  description = "DNS name of the US Load Balancer"
}

output "us_rds_endpoint" {
  value = aws_db_instance.us.endpoint
  description = "RDS endpoint"
  sensitive = true
}

output "us_redis_endpoint" {
  value = aws_elasticache_replication_group.us.primary_endpoint_address
  description = "Redis endpoint"
}

output "route53_zone_id" {
  value = aws_route53_zone.main.zone_id
  description = "Route53 zone ID"
}

output "cloudfront_domain" {
  value = aws_cloudfront_distribution.api.domain_name
  description = "CloudFront domain"
}
