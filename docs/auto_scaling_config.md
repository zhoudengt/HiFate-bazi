# 自动扩展配置指南

## 一、阿里云弹性伸缩配置

### 1.1 创建启动模板

在阿里云控制台创建ECS启动模板：

**基本信息**：
- 模板名称：`HiFate-bazi-app-template`
- 镜像：自定义镜像（包含应用代码）或公共镜像 + 用户数据脚本
- 实例规格：`ecs.c6.2xlarge`（8核32GB）
- 网络：专有网络VPC
- 安全组：开放80、443、22端口

**用户数据脚本**（自动部署）：
```bash
#!/bin/bash
# 自动部署脚本

# 1. 安装Docker
yum install -y docker
systemctl start docker
systemctl enable docker

# 2. 安装Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 3. 从OSS拉取应用代码（需要配置OSS访问密钥）
export OSS_ACCESS_KEY_ID=your_access_key
export OSS_ACCESS_KEY_SECRET=your_secret_key
export OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
export OSS_BUCKET=your-bucket-name

# 安装ossutil
wget http://gosspublic.alicdn.com/ossutil/1.7.14/ossutil64
chmod 755 ossutil64
mv ossutil64 /usr/local/bin/ossutil

# 配置ossutil
ossutil config --endpoint ${OSS_ENDPOINT} --access-key-id ${OSS_ACCESS_KEY_ID} --access-key-secret ${OSS_ACCESS_KEY_SECRET}

# 拉取应用代码
mkdir -p /opt/HiFate-bazi
ossutil cp oss://${OSS_BUCKET}/app.tar.gz /opt/app.tar.gz
tar -xzf /opt/app.tar.gz -C /opt/HiFate-bazi

# 4. 配置环境变量
cat > /opt/HiFate-bazi/.env <<EOF
MYSQL_HOST=your-mysql-host
MYSQL_PORT=3306
MYSQL_DB=hifate_bazi
MYSQL_USER=bazi_user
MYSQL_PASSWORD=your_password
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
COZE_ACCESS_TOKEN=your_coze_token
COZE_BOT_ID=your_bot_id
EOF

# 5. 启动服务
cd /opt/HiFate-bazi
docker-compose up -d

# 6. 等待服务启动
sleep 30

# 7. 健康检查
curl -f http://localhost:8001/health || exit 1

# 8. 注册到SLB（需要SLB API）
# 使用阿里云CLI或API将实例添加到SLB后端服务器组
# aliyun slb AddBackendServers --LoadBalancerId your-lb-id --BackendServers "[{\"ServerId\":\"$(curl -s http://100.100.100.200/latest/meta-data/instance-id)\",\"Weight\":100}]"
```

### 1.2 创建伸缩组

**基本信息**：
- 伸缩组名称：`HiFate-bazi-scaling-group`
- 网络类型：专有网络
- 多可用区：是（选择2-3个可用区）
- 实例移除策略：最早创建的实例

**实例配置**：
- 启动模板：选择上面创建的模板
- 最小实例数：3
- 最大实例数：10
- 期望实例数：5

**网络配置**：
- VPC：选择你的VPC
- 交换机：选择多个可用区的交换机
- 负载均衡：选择SLB实例

### 1.3 创建伸缩规则

#### 扩容规则

**规则1：CPU使用率过高扩容**
- 规则名称：`scale-out-cpu-high`
- 执行操作：增加2台实例
- 冷却时间：300秒（5分钟）

**规则2：QPS过高扩容**
- 规则名称：`scale-out-qps-high`
- 执行操作：增加2台实例
- 冷却时间：300秒

#### 缩容规则

**规则1：CPU使用率过低缩容**
- 规则名称：`scale-in-cpu-low`
- 执行操作：减少1台实例
- 冷却时间：600秒（10分钟）

### 1.4 创建报警任务

#### 报警任务1：CPU使用率 > 70%

```json
{
  "name": "cpu-high-alert",
  "metric": "CPUUtilization",
  "threshold": 70,
  "comparison": ">",
  "period": 300,
  "times": 3,
  "action": "scale-out-cpu-high"
}
```

#### 报警任务2：CPU使用率 < 30%

```json
{
  "name": "cpu-low-alert",
  "metric": "CPUUtilization",
  "threshold": 30,
  "comparison": "<",
  "period": 600,
  "times": 3,
  "action": "scale-in-cpu-low"
}
```

#### 报警任务3：QPS > 400

```json
{
  "name": "qps-high-alert",
  "metric": "CustomMetric.QPS",
  "threshold": 400,
  "comparison": ">",
  "period": 300,
  "times": 2,
  "action": "scale-out-qps-high"
}
```

### 1.5 使用阿里云CLI配置

```bash
# 安装阿里云CLI
pip install aliyun-python-sdk-core aliyun-python-sdk-ess

# 创建伸缩组
aliyun ess CreateScalingGroup \
  --ScalingGroupName HiFate-bazi-scaling-group \
  --MinSize 3 \
  --MaxSize 10 \
  --DesiredCapacity 5 \
  --LaunchTemplateId lt-xxxxx \
  --VSwitchIds '["vsw-xxxxx","vsw-yyyyy"]' \
  --LoadBalancerIds '["lb-xxxxx"]'

# 创建扩容规则
aliyun ess CreateScalingRule \
  --ScalingGroupId asg-xxxxx \
  --ScalingRuleName scale-out-cpu-high \
  --AdjustmentType QuantityChangeInCapacity \
  --AdjustmentValue 2 \
  --Cooldown 300

# 创建缩容规则
aliyun ess CreateScalingRule \
  --ScalingGroupId asg-xxxxx \
  --ScalingRuleName scale-in-cpu-low \
  --AdjustmentType QuantityChangeInCapacity \
  --AdjustmentValue -1 \
  --Cooldown 600

# 创建报警任务
aliyun cms PutResourceMetricRule \
  --RuleName cpu-high-alert \
  --Namespace acs_ecs_dashboard \
  --MetricName CPUUtilization \
  --Dimensions '[{"instanceId":"*"}]' \
  --Period 300 \
  --Statistics Average \
  --Threshold 70 \
  --ComparisonOperator GreaterThanThreshold \
  --EvaluationCount 3 \
  --AlarmActions '["acs:ess:cn-hangzhou:your-account-id:scalingrule/scale-out-cpu-high"]'
```

## 二、腾讯云弹性伸缩配置

### 2.1 创建启动配置

在腾讯云控制台创建启动配置：

**基本信息**：
- 配置名称：`HiFate-bazi-launch-config`
- 机型：标准型S5（8核32GB）
- 镜像：自定义镜像或公共镜像
- 系统盘：40GB SSD
- 数据盘：200GB SSD

**用户数据脚本**（同阿里云，但使用腾讯云OSS）

### 2.2 创建伸缩组

- 伸缩组名称：`HiFate-bazi-asg`
- 最小实例数：3
- 最大实例数：10
- 期望实例数：5
- 启动配置：选择上面创建的配置
- 负载均衡：选择CLB实例

### 2.3 创建伸缩策略

使用腾讯云控制台或API创建伸缩策略，配置同阿里云。

## 三、AWS Auto Scaling配置

### 3.1 创建Launch Template

```json
{
  "LaunchTemplateName": "HiFate-bazi-template",
  "ImageId": "ami-xxxxx",
  "InstanceType": "c5.2xlarge",
  "UserData": "base64-encoded-user-data-script",
  "SecurityGroupIds": ["sg-xxxxx"],
  "IamInstanceProfile": {
    "Arn": "arn:aws:iam::account-id:instance-profile/your-profile"
  }
}
```

### 3.2 创建Auto Scaling Group

```bash
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name HiFate-bazi-asg \
  --launch-template LaunchTemplateName=HiFate-bazi-template \
  --min-size 3 \
  --max-size 10 \
  --desired-capacity 5 \
  --vpc-zone-identifier "subnet-xxxxx,subnet-yyyyy" \
  --target-group-arns "arn:aws:elasticloadbalancing:region:account-id:targetgroup/your-tg"
```

### 3.3 创建Scaling Policy

```bash
# 扩容策略
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name HiFate-bazi-asg \
  --policy-name scale-out-cpu \
  --adjustment-type ChangeInCapacity \
  --scaling-adjustment 2 \
  --cooldown 300

# 缩容策略
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name HiFate-bazi-asg \
  --policy-name scale-in-cpu \
  --adjustment-type ChangeInCapacity \
  --scaling-adjustment -1 \
  --cooldown 600
```

### 3.4 创建CloudWatch Alarm

```bash
# CPU使用率告警
aws cloudwatch put-metric-alarm \
  --alarm-name cpu-high-alert \
  --alarm-description "Alert when CPU exceeds 70%" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 70 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 3 \
  --alarm-actions "arn:aws:autoscaling:region:account-id:scalingPolicy:policy-id"
```

## 四、Kubernetes HPA配置

### 4.1 部署应用

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: web-app
        image: HiFate-bazi:latest
        ports:
        - containerPort: 8001
        resources:
          requests:
            cpu: 1000m
            memory: 2Gi
          limits:
            cpu: 4000m
            memory: 8Gi
        env:
        - name: MYSQL_HOST
          value: "mysql-master"
        - name: REDIS_HOST
          value: "redis-master"
```

### 4.2 创建HPA

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 60
      - type: Pods
        value: 2
        periodSeconds: 60
      selectPolicy: Max
```

### 4.3 应用HPA配置

```bash
kubectl apply -f hpa-config.yaml
```

### 4.4 查看HPA状态

```bash
kubectl get hpa web-app-hpa
kubectl describe hpa web-app-hpa
```

## 五、监控指标配置

### 5.1 自定义QPS指标（阿里云）

创建自定义监控指标：

```python
# 应用代码中上报QPS指标
from aliyunsdkcore.client import AcsClient
from aliyunsdkcms.request.v20190101 import PutCustomMetricRequest

def report_qps(qps_value):
    client = AcsClient(
        'your-access-key-id',
        'your-access-key-secret',
        'cn-hangzhou'
    )
    
    request = PutCustomMetricRequest.PutCustomMetricRequest()
    request.set_MetricName('QPS')
    request.set_Value(str(qps_value))
    request.set_Unit('Count/Second')
    
    response = client.do_action_with_exception(request)
    return response
```

### 5.2 Prometheus指标（Kubernetes）

在应用代码中暴露Prometheus指标：

```python
from prometheus_client import Counter, Gauge, Histogram

# 定义指标
request_count = Counter('http_requests_total', 'Total HTTP requests')
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')
active_connections = Gauge('active_connections', 'Active connections')

# 在请求处理中使用
@app.middleware("http")
async def metrics_middleware(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    request_count.inc()
    request_duration.observe(duration)
    
    return response
```

## 六、测试自动扩展

### 6.1 压力测试脚本

```python
import requests
import concurrent.futures
import time

def send_request(url):
    try:
        response = requests.get(url, timeout=10)
        return response.status_code
    except Exception as e:
        return str(e)

def stress_test(url, concurrent_users=100, duration=300):
    """压力测试"""
    end_time = time.time() + duration
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        while time.time() < end_time:
            futures = [executor.submit(send_request, url) for _ in range(concurrent_users)]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
            time.sleep(1)
    
    return results

# 使用
if __name__ == "__main__":
    url = "http://your-load-balancer-url/api/v1/bazi"
    results = stress_test(url, concurrent_users=500, duration=600)
    print(f"Total requests: {len(results)}")
    print(f"Success rate: {sum(1 for r in results if r == 200) / len(results) * 100:.2f}%")
```

### 6.2 监控扩展过程

```bash
# 阿里云
aliyun ess DescribeScalingActivities --ScalingGroupId asg-xxxxx

# 腾讯云
tccli as DescribeAutoScalingActivities --AutoScalingGroupId asg-xxxxx

# Kubernetes
watch kubectl get pods -l app=web-app
```

## 七、最佳实践

### 7.1 扩展策略

1. **渐进式扩容**：每次增加2-3台，避免一次性增加太多
2. **保守式缩容**：每次减少1台，冷却时间更长（10分钟）
3. **多指标触发**：CPU、内存、QPS、响应时间综合考虑

### 7.2 冷却时间设置

- **扩容冷却时间**：300秒（5分钟），避免频繁扩容
- **缩容冷却时间**：600秒（10分钟），避免频繁缩容导致服务不稳定

### 7.3 最小/最大实例数

- **最小实例数**：至少3台，保证高可用
- **最大实例数**：根据预算和需求设置，建议10-20台

### 7.4 健康检查

确保新实例启动后通过健康检查才加入负载均衡：

```bash
# 健康检查脚本
#!/bin/bash
MAX_RETRIES=30
RETRY_INTERVAL=10

for i in $(seq 1 $MAX_RETRIES); do
    if curl -f http://localhost:8001/health; then
        echo "Health check passed"
        exit 0
    fi
    echo "Health check failed, retrying... ($i/$MAX_RETRIES)"
    sleep $RETRY_INTERVAL
done

echo "Health check failed after $MAX_RETRIES retries"
exit 1
```

## 八、故障处理

### 8.1 扩展失败

- 检查启动模板配置
- 检查用户数据脚本
- 检查安全组规则
- 查看实例启动日志

### 8.2 扩展过快

- 增加冷却时间
- 调整告警阈值
- 检查是否有异常流量

### 8.3 扩展过慢

- 减少冷却时间
- 调整扩容策略（增加每次扩容数量）
- 检查告警任务是否正常触发

---

**注意**：自动扩展配置需要根据实际业务情况调整，建议先在测试环境验证后再应用到生产环境。

