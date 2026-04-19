# Maually Running Archive Job

```bash
aws ecs run-task   --region eu-west-1   --cluster trigpointing-cluster   --task-definition trigpointing-archive   --launch-type FARGATE   --platform-version LATEST   --network-configuration 'awsvpcConfiguration={subnets=[subnet-01e6a0c671672b2b8,subnet-03d8491f3d39e497d],securityGroups=[sg-08b7e24bcfc59886d],assignPublicIp=DISABLED}'   --started-by cli-manual-archive
```
