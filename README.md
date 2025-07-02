# Database Automation Suite

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![CI](https://github.com/adebayopeter/database_automation/actions/workflows/ci.yml/badge.svg)
[![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen.svg)](https://github.com/username/database_automation)

A comprehensive, production-ready database automation framework designed for **PostgreSQL** and **SQL Server** environments. Built for Site Reliability Engineering (SRE) teams, Database Administrators, and DevOps professionals who need robust, scalable database management automation with **Prometheus monitoring** and **Grafana visualization**.

## 🎯 Project Highlights

This project demonstrates **enterprise-level database automation capabilities** perfect for showcasing in technical interviews and production environments:

- **Multi-Database Architecture**: Native support for PostgreSQL and SQL Server with conditional enabling
- **Production-Ready Design**: Connection pooling, error handling, comprehensive monitoring, alerting
- **Cloud-Native**: Kubernetes-ready with Docker containerization and Helm charts
- **Full Observability Stack**: Prometheus metrics, Grafana dashboards, structured logging, health monitoring
- **Security-First**: Environment variable configuration, encrypted connections, audit logging
- **DevOps Integration**: CI/CD pipelines, automated testing, infrastructure as code
- **Complete Monitoring**: Pre-built Grafana dashboards with alerting rules

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL 12+ or SQL Server 2019+
- Docker & Docker Compose (for monitoring stack)
- Optional: Kubernetes cluster for production deployment

### Installation

```bash
# Clone the repository
git clone https://github.com/username/database_automation.git
cd database_automation

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your database credentials
```

### Basic Usage

```bash
# Test database connections
python database_automation.py test

# Run health checks
python database_automation.py health --generate-report

# Perform backups
python database_automation.py backup --cleanup

# Start complete monitoring stack (Recommended)
docker-compose up -d

# Or start database automation only
python database_automation.py monitor --metrics-port 8000

# Performance optimization
python database_automation.py optimize
```

### Quick Monitoring Setup

```bash
# Start complete stack with Grafana + Prometheus
docker-compose up -d

# Access Grafana dashboards
open http://localhost:3000  # admin/admin123

# View Prometheus metrics
open http://localhost:9090

# Check automation metrics
curl http://localhost:8000/metrics
```

## 📋 Features

### 🔍 Database Health Monitoring

- **Real-time Metrics**: Connection counts, query performance, resource utilization
- **PostgreSQL Monitoring**: Table statistics, index usage, replication status, conflicts
- **SQL Server Monitoring**: Wait statistics, index fragmentation, database sizing
- **Automated Alerting**: Threshold-based email notifications
- **Health Reports**: Comprehensive JSON and text reports

### 🗃️ Automated Backup & Recovery

- **Multi-format Support**: SQL dumps, native backups, compressed archives
- **Intelligent Scheduling**: Cron-based scheduling with parallel execution
- **Retention Management**: Automated cleanup with configurable retention policies
- **Verification**: Backup integrity checks and size validation
- **Cross-platform**: Works on Linux, Windows, and macOS

### ⚡ Performance Optimization

- **Automated Maintenance**: VACUUM, ANALYZE, statistics updates
- **Index Management**: Fragmentation detection and optimization recommendations
- **Query Analysis**: Long-running query identification and reporting
- **Resource Monitoring**: CPU, memory, and disk utilization tracking

### 📊 Complete Monitoring Stack

- **Prometheus Metrics**: Custom metrics for backup status, query performance, health, connections
- **Grafana Dashboards**: Pre-built dashboards with database health, performance, and backup monitoring
- **Alert Rules**: Comprehensive alerting for database issues, slow queries, backup failures
- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Health Endpoints**: REST API for health checks and status reporting
- **Docker Compose Stack**: One-command deployment of complete monitoring infrastructure

### 🔐 Security & Compliance

- **Encrypted Connections**: TLS/SSL enforcement for all database connections
- **Secrets Management**: Environment variable and external secrets integration
- **Audit Logging**: Comprehensive operation tracking and compliance reporting
- **Access Control**: Role-based access patterns and authentication

## 🏗️ Architecture

### System Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │   SQL Server    │    │     Grafana     │
│   Databases     │    │   Databases     │    │   Dashboards    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       ▲
         └───────────────────────┼───────────────────────│─────┐
                                 │                       │     │
         ┌───────────────────────▼───────────────────────│─────▼──┐
         │         Database Automation Suite             │        │
         │  ┌─────────────────────────────────────────┐  │ ┌──────▼── ┐
         │  │        Connection Pool Manager          │  │ │Prometheus│
         │  └─────────────────────────────────────────┘  │ │ Metrics  │
         │  ┌─────────────────────────────────────────┐  │ │ & Rules  │
         │  │         Health Monitor Engine           │  │ └──────┬── ┘
         │  └─────────────────────────────────────────┘  │        │
         │  ┌─────────────────────────────────────────┐  │        │
         │  │       Backup & Recovery Engine          │  │        │
         │  └─────────────────────────────────────────┘  │        │
         │  ┌─────────────────────────────────────────┐  │        │
         │  │      Performance Optimizer              │  │        │
         │  └─────────────────────────────────────────┘  │        │
         │  ┌─────────────────────────────────────────┐  │        │
         │  │       Prometheus Exporter               │  │        │
         │  └─────────────────────────────────────────┘  │        │
         └───────────────────────────────────────────────┘        │
                                 │                                │
         ┌───────────────────────▼───────────────────────────────▼─┐
         │                    Outputs                              │
         │  • Grafana Dashboards  • Prometheus Alerts              │
         │  • Email Notifications • Backup Files                   │
         │  • Health Reports      • Audit Logs                     │
         │  • Performance Metrics • Query Analytics                │
         └─────────────────────────────────────────────────────────┘
```

### Key Components

1. **DatabaseAutomation**: Main orchestration class
2. **Connection Pool Manager**: Thread-safe connection pooling
3. **Health Monitor**: Multi-database health checking
4. **Backup Engine**: Automated backup and retention management
5. **Performance Optimizer**: Database maintenance automation
6. **Alert System**: Email and webhook notifications
7. **Metrics Exporter**: Prometheus-compatible metrics

## ⚙️ Configuration

### Database Configuration (`db_config.yaml`)

```yaml
databases:
  postgres_primary:
    host: "${DB_HOST:-localhost}"
    port: 5432
    database: "${POSTGRES_DB:-production_db}"
    username: "${POSTGRES_USER:-postgres}"
    password: "${POSTGRES_PASSWORD}"
    db_type: postgresql
    connection_pool_size: 20
    ssl_mode: require

  sqlserver_primary:
    host: "${SQLSERVER_HOST:-localhost}"
    port: 1433
    database: "${SQLSERVER_DB:-master}"
    username: "${SQLSERVER_USER:-sa}"
    password: "${SQLSERVER_PASSWORD}"
    db_type: sqlserver
    connection_pool_size: 15

monitoring:
  check_interval: 300  # seconds
  alert_thresholds:
    connection_count: 100
    query_duration_minutes: 5
    disk_usage: 90

  email_alerts:
    enabled: true
    smtp_server: "${SMTP_SERVER}"
    smtp_port: 587
    from_email: "${ALERT_FROM_EMAIL}"
    alert_recipients:
      - "${DBA_EMAIL}"
      - "${SRE_EMAIL}"

backup:
  schedule: "0 2 * * *"  # Daily at 2 AM
  retention_days: 30
  backup_path: "${BACKUP_PATH:-/var/backups}"
  compression: true
  parallel_jobs: 4

  remote_storage:
    enabled: true
    type: s3
    bucket: "${BACKUP_BUCKET}"
    region: "${AWS_REGION}"
```

### Environment Variables

```bash
# Database Credentials
POSTGRES_PASSWORD=secure_password
SQLSERVER_PASSWORD=secure_password

# Database Controls (NEW)
POSTGRES_ENABLED=true
SQL_SERVER_ENABLED=false

# Email Configuration  
SMTP_SERVER=smtp.company.com
SMTP_PASSWORD=email_password
ALERT_FROM_EMAIL=db-automation@company.com
DBA_EMAIL=dba-team@company.com
SRE_EMAIL=sre-team@company.com

# Monitoring Stack (NEW)
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_ADMIN_PASSWORD=admin123

# Backup Configuration
BACKUP_PATH=/var/backups/databases
BACKUP_BUCKET=company-database-backups
AWS_REGION=us-west-2

# Security
DATABASE_ENCRYPTION_KEY=your-encryption-key
```

## 🐳 Docker Deployment

### Build and Run

```bash
# Build the Docker image
docker build -t database-automation:latest .

# Run with volume mounts
docker run -d \\
  --name db-automation \\
  -v $(pwd)/db_config.yaml:/app/db_config.yaml \\
  -v /var/backups:/var/backups \\
  -p 8000:8000 \\
  --env-file .env \\
  database-automation:latest
```

### Complete Docker Compose Stack

```yaml
version: '3.8'

services:
  # Database Automation Suite
  db-automation:
    build: .
    container_name: database-automation
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./db_config.yaml:/app/db_config.yaml:ro
      - backup-data:/var/backups
      - ./logs:/app/logs
    environment:
      - LOG_LEVEL=INFO
    env_file:
      - .env
    depends_on:
      - postgres-db
      - prometheus
    healthcheck:
      test: ["CMD", "/app/healthcheck.sh"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Test PostgreSQL Database
  postgres-db:
    image: postgres:15-alpine
    container_name: test-postgres
    restart: unless-stopped
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=test_automation
      - POSTGRES_USER=automation_user
      - POSTGRES_PASSWORD=secure_password
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./scripts/init-postgres.sql:/docker-entrypoint-initdb.d/init.sql:ro

  # Prometheus Monitoring
  prometheus:
    image: prom/prometheus:v2.45.0
    container_name: prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./monitoring/prometheus-rules.yml:/etc/prometheus/rules/prometheus-rules.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.enable-lifecycle'
      - '--storage.tsdb.retention.time=30d'

  # Grafana Dashboards
  grafana:
    image: grafana/grafana:10.0.0
    container_name: grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards:ro
    depends_on:
      - prometheus

volumes:
  backup-data:
  postgres-data:
  prometheus-data:
  grafana-data:
```

## ☸️ Kubernetes Deployment

### Basic Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: database-automation
  namespace: database-ops
spec:
  replicas: 1
  selector:
    matchLabels:
      app: database-automation
  template:
    metadata:
      labels:
        app: database-automation
    spec:
      containers:
      - name: automation
        image: database-automation:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        env:
        - name: LOG_LEVEL
          value: "INFO"
        envFrom:
        - secretRef:
            name: database-secrets
        - configMapRef:
            name: database-config
        volumeMounts:
        - name: config
          mountPath: /app/db_config.yaml
          subPath: db_config.yaml
        - name: backup-storage
          mountPath: /var/backups
      volumes:
      - name: config
        configMap:
          name: database-automation-config
      - name: backup-storage
        persistentVolumeClaim:
          claimName: backup-pvc
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=database_automation --cov-report=html

# Run specific test categories
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m "not slow"     # Skip slow tests

# Verbose output
pytest -v --tb=short
```

### Test Structure

```
tests/
├── __init__.py
├── test_database_automation.py    # Core functionality tests
├── test_cli.py                   # CLI interface tests
├── test_config.py                # Configuration tests
├── integration/
│   ├── test_postgres_integration.py
│   └── test_sqlserver_integration.py
└── fixtures/
    ├── sample_configs/
    └── test_data/
```

## 📈 Complete Monitoring Stack

### Quick Start

```bash
# Start complete monitoring stack
docker-compose up -d

# Access Grafana
open http://localhost:3000  # admin/admin123

# View Prometheus
open http://localhost:9090
```

### Available Dashboards

1. **Database Automation Suite - Overview** (`/monitoring/grafana/dashboards/database-automation-overview.json`)
   - Database health status indicators
   - Connection monitoring by status
   - Query performance metrics (50th, 95th percentiles)
   - Backup operation tracking and file sizes
   - Real-time metrics with 30-second refresh

2. **PostgreSQL Detailed Metrics** (`/monitoring/grafana/dashboards/postgresql-detailed.json`)
   - PostgreSQL-specific connection statistics
   - Table and index usage analytics
   - Query performance percentiles (50th, 95th, 99th)
   - Database size growth monitoring
   - Index efficiency and usage patterns

### Prometheus Metrics

```python
# Core Database Metrics
db_connections_total{database, status}      # Total connections by status
db_query_duration_seconds{database, query_type}  # Query execution histogram
db_health_status{database}                  # Health status (1=healthy, 0=down)

# Backup Metrics
db_backups_total{database, status}          # Backup operations (success/failed)
db_backup_size_bytes{database}              # Backup file sizes in bytes

# PostgreSQL Specific (when available)
pg_stat_user_tables_n_tup_ins{database, table}  # Table insert statistics
pg_database_size_bytes{database}            # Database sizes
pg_stat_user_indexes_idx_scan{database, table}  # Index scan statistics
```

### Alert Rules

Comprehensive alerting configured in `/monitoring/prometheus-rules.yml`:

**Critical Alerts:**
- Database Down (>2 minutes)
- Very Slow Queries (95th percentile >30s)
- Backup Failures (last 24h)
- Connection Pool Exhaustion

**Warning Alerts:**
- High Database Connections (>threshold)
- Slow Queries (95th percentile >5s)
- No Recent Backup (>24h)
- Large Backup Size (>10GB)
- High Query Volume (>1000 QPS)

## 🔧 CLI Reference

### Commands

```bash
# Health monitoring
python database_automation.py health [--generate-report] [--database DB_NAME]

# Backup operations
python database_automation.py backup [--cleanup] [--database DB_NAME]

# Performance optimization
python database_automation.py optimize [--database DB_NAME]

# Connection testing
python database_automation.py test [--database DB_NAME]

# System status
python database_automation.py status

# Continuous monitoring
python database_automation.py monitor [--metrics-port PORT]
```

### Global Options

```bash
--config, -c        Configuration file path (default: db_config.yaml)
--log-level, -l     Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
--database, -d      Target specific database
--help, -h          Show help message
```

## 🚀 Production Deployment

### High Availability Setup

1. **Load Balancer Configuration**
   ```yaml
   # HAProxy configuration for multiple instances
   backend db-automation
     balance roundrobin
     server auto1 10.0.1.10:8000 check
     server auto2 10.0.1.11:8000 check
   ```

2. **Database Replication Support**
   ```yaml
   databases:
     postgres_primary:
       host: postgres-primary.internal
       # ... config
     postgres_replica:
       host: postgres-replica.internal
       # ... config
   ```

3. **Backup Replication**
   ```yaml
   backup:
     remote_storage:
       enabled: true
       replicas:
         - type: s3
           bucket: primary-backups
         - type: azure
           container: backup-replica
   ```

### Security Hardening

1. **Network Security**
   - Use VPC/private networks
   - Configure security groups/firewalls
   - Enable database connection encryption

2. **Secrets Management**
   ```bash
   # Using Kubernetes secrets
   kubectl create secret generic database-secrets \\
     --from-literal=postgres-password=secure_password \\
     --from-literal=smtp-password=email_password
   ```

3. **Access Control**
   ```yaml
   # RBAC configuration
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     name: database-automation
   rules:
   - apiGroups: [""]
     resources: ["secrets", "configmaps"]
     verbs: ["get", "list"]
   ```

## 🤝 Contributing

### Development Setup

```bash
# Clone and setup development environment
git clone https://github.com/username/database_automation.git
cd database_automation

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Code formatting
black database_automation.py
flake8 database_automation.py
```

### Code Quality

- **Black**: Code formatting
- **Flake8**: Linting
- **MyPy**: Type checking
- **pytest**: Testing framework
- **Pre-commit**: Git hooks for quality

### Pull Request Guidelines

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Ensure all tests pass (`pytest`)
5. Run code quality checks (`black`, `flake8`, `mypy`)
6. Commit changes (`git commit -m 'Add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🎯 Interview Talking Points

This project demonstrates several key competencies valuable in technical interviews:

### Technical Skills
- **Multi-database Architecture**: PostgreSQL and SQL Server expertise
- **Python Best Practices**: Type hints, dataclasses, context managers, error handling
- **Testing**: Comprehensive unit and integration tests with mocking
- **Security**: Environment variables, connection encryption, secrets management
- **Monitoring**: Prometheus metrics, structured logging, health checks

### DevOps & SRE Skills
- **Containerization**: Docker and Docker Compose with multi-service orchestration
- **Monitoring Stack**: Complete Prometheus + Grafana implementation with custom dashboards
- **Observability**: Comprehensive metrics, logging, alerting, and distributed tracing readiness
- **Kubernetes**: Production-ready manifests with RBAC, networking, and resource management
- **CI/CD**: GitHub Actions pipeline with security scanning, testing, and automated deployment
- **Infrastructure as Code**: Automated deployment, configuration management, and environment provisioning

### Software Engineering Practices
- **Clean Code**: Well-structured, documented, and maintainable codebase
- **Design Patterns**: Connection pooling, factory pattern, observer pattern
- **Error Handling**: Comprehensive exception handling with graceful degradation
- **Configuration Management**: Flexible, environment-aware configuration
- **Documentation**: Thorough README, code comments, and API documentation

### Production Readiness
- **Scalability**: Connection pooling, parallel processing, resource optimization
- **Reliability**: Health checks, automated recovery, backup verification
- **Maintainability**: Modular design, comprehensive logging, monitoring
- **Security**: Encryption, secrets management, audit logging

---

## 📞 Support

For questions, issues, or contributions:

- **Issues**: [GitHub Issues](https://github.com/adebayopeter/database_automation/issues)
- **Discussions**: [GitHub Discussions](https://github.com/adebayopeter/database_automation/discussions)
- **Email**: [pekunmi@live.com](mailto:pekunmi@live.com)

---

**Built with ❤️ for the Database and SRE community**