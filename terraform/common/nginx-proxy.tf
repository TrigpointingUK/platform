# Nginx Reverse Proxy to Legacy Server - DECOMMISSIONED
# This service previously proxied requests from the ALB to the legacy EC2 server.
# Legacy server has been switched off and all traffic now goes to the new SPA.
# Keeping this file for historical reference but all resources are commented out.

# Legacy server details (data source - not managed by Terraform)
# data "aws_instance" "legacy" {
#   instance_id = "i-02ea789e9d1265a51"
# }

# SSM Parameter for nginx configuration
# resource "aws_ssm_parameter" "nginx_proxy_config" {
#   name        = "/${var.project_name}/nginx-proxy/config"
#   description = "Nginx configuration for legacy server reverse proxy"
#   type        = "String"
#   value = templatefile("${path.module}/nginx-proxy-config.tpl", {
#     legacy_server_ip = data.aws_instance.legacy.public_ip
#   })
#
#   tags = {
#     Name = "${var.project_name}-nginx-proxy-config"
#   }
# }

# Target Group for nginx proxy
# resource "aws_lb_target_group" "nginx_proxy" {
#   name        = "${var.project_name}-nginx-proxy-tg"
#   port        = 80
#   protocol    = "HTTP"
#   vpc_id      = aws_vpc.main.id
#   target_type = "ip"
#
#   health_check {
#     enabled             = true
#     healthy_threshold   = 2
#     interval            = 30
#     matcher             = "200"
#     path                = "/nginx-health"
#     port                = "traffic-port"
#     protocol            = "HTTP"
#     timeout             = 5
#     unhealthy_threshold = 2
#   }
#
#   tags = {
#     Name = "${var.project_name}-nginx-proxy-tg"
#   }
# }

# Listener rule for trigpointing.uk root domain (priority 990 - low priority catch-all)
# REMOVED: trigpointing.uk now routes to production SPA (defined in terraform/production/spa.tf)
# resource "aws_lb_listener_rule" "nginx_proxy" {
#   listener_arn = aws_lb_listener.app_https[0].arn
#   priority     = 990
#
#   action {
#     type             = "forward"
#     target_group_arn = aws_lb_target_group.nginx_proxy.arn
#   }
#
#   condition {
#     host_header {
#       values = ["trigpointing.uk", "www.trigpointing.uk"]
#     }
#   }
#
#   tags = {
#     Name = "${var.project_name}-nginx-proxy-listener-rule"
#   }
# }

# Nginx Proxy ECS Service
# module "nginx_proxy" {
#   source = "../modules/nginx-proxy"
#
#   project_name                = var.project_name
#   environment                 = "common"
#   aws_region                  = var.aws_region
#   ecs_cluster_id              = aws_ecs_cluster.main.id
#   ecs_cluster_name            = aws_ecs_cluster.main.name
#   ecs_task_execution_role_arn = aws_iam_role.ecs_task_execution_role.arn
#   ecs_task_role_arn           = aws_iam_role.ecs_task_role.arn
#   ecs_security_group_id       = aws_security_group.nginx_proxy_ecs.id
#   private_subnet_ids          = aws_subnet.private[*].id
#   target_group_arn            = aws_lb_target_group.nginx_proxy.arn
#
#   # Configuration
#   desired_count               = 1
#   min_capacity                = 1
#   max_capacity                = 3
#   cpu                         = 256
#   memory                      = 512
#   cpu_target_value            = 70
#   legacy_server_target        = "https://${data.aws_instance.legacy.public_ip}"
#   nginx_config_parameter_name = aws_ssm_parameter.nginx_proxy_config.name
# }

