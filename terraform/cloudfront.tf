# ─── AWS CloudFront Distribution ─────────────────────────────────────────────

resource "aws_cloudfront_distribution" "app_cdn" {
  comment             = "Zestora Global CloudFront CDN Originating from ALB"
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = ""

  origin {
    domain_name = aws_lb.app_alb.dns_name
    origin_id   = "ALB-${aws_lb.app_alb.name}"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # Default cache behavior for Static Assets & SPA
  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "ALB-${aws_lb.app_alb.name}"

    forwarded_values {
      query_string = true
      cookies {
        forward = "all"
      }
    }

    viewer_protocol_policy = "allow-all"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  # Ordered Cache Behavior for /api/* (Dynamic requests - no caching)
  ordered_cache_behavior {
    path_pattern     = "/api/*"
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "ALB-${aws_lb.app_alb.name}"

    forwarded_values {
      query_string = true
      headers      = ["*"]
      cookies {
        forward = "all"
      }
    }

    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
    viewer_protocol_policy = "allow-all"
  }

  price_class = "PriceClass_100" # US, Canada, Europe (Lowest cost / Free tier eligible)

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name        = "${var.project_name}-cloudfront"
    Environment = var.environment
  }
}
