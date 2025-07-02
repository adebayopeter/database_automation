# Database Automation Monitoring Setup

This directory contains the monitoring infrastructure for the Database Automation Suite using Prometheus and Grafana.

## Overview

- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and dashboards
- **Alerting**: Comprehensive alert rules for database health

## Components

### Prometheus Configuration
- `prometheus.yml`: Main Prometheus configuration
- `prometheus-rules.yml`: Alert rules for database monitoring

### Grafana Setup
- `grafana/provisioning/datasources/`: Prometheus datasource configuration
- `grafana/provisioning/dashboards/`: Dashboard provisioning
- `grafana/dashboards/`: Dashboard JSON files

## Quick Start

### Using Docker Compose

1. **Start the monitoring stack:**
   ```bash
   docker-compose up -d prometheus grafana
   ```

2. **Access Grafana:**
   - URL: http://localhost:3000
   - Default credentials: admin/admin123
   - Dashboards will be automatically provisioned

3. **Access Prometheus:**
   - URL: http://localhost:9090
   - View targets: http://localhost:9090/targets
   - View alerts: http://localhost:9090/alerts

### Manual Setup

1. **Start Prometheus:**
   ```bash
   docker run -d \
     --name prometheus \
     -p 9090:9090 \
     -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
     -v $(pwd)/prometheus-rules.yml:/etc/prometheus/rules/prometheus-rules.yml \
     prom/prometheus:v2.45.0 \
     --config.file=/etc/prometheus/prometheus.yml \
     --storage.tsdb.path=/prometheus \
     --web.enable-lifecycle
   ```

2. **Start Grafana:**
   ```bash
   docker run -d \
     --name grafana \
     -p 3000:3000 \
     -v $(pwd)/grafana/provisioning:/etc/grafana/provisioning \
     -v $(pwd)/grafana/dashboards:/var/lib/grafana/dashboards \
     -e GF_SECURITY_ADMIN_PASSWORD=admin123 \
     grafana/grafana:10.0.0
   ```

## Available Dashboards

### 1. Database Automation Suite - Overview
- **File**: `grafana/dashboards/database-automation-overview.json`
- **Features**:
  - Database health status
  - Connection monitoring
  - Query performance metrics
  - Backup operation tracking
  - System resource utilization

### 2. PostgreSQL Detailed Metrics
- **File**: `grafana/dashboards/postgresql-detailed.json`
- **Features**:
  - PostgreSQL-specific metrics
  - Table and index statistics
  - Query performance percentiles
  - Database size monitoring
  - Index usage efficiency

## Metrics Exposed

The Database Automation Suite exposes the following Prometheus metrics:

### Connection Metrics
- `db_connections_total`: Total database connections by status
- `db_health_status`: Database health status (1=healthy, 0=unhealthy)

### Query Performance
- `db_query_duration_seconds`: Histogram of query execution times
- Buckets: 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, +Inf seconds

### Backup Metrics
- `db_backups_total`: Total backup operations by status
- `db_backup_size_bytes`: Size of backup files in bytes

## Alert Rules

### Critical Alerts
- **DatabaseDown**: Database is unreachable for >2 minutes
- **VerySlowQueries**: 95th percentile query time >30 seconds
- **BackupFailure**: Backup operation failed in last 24 hours
- **ConnectionPoolExhaustion**: High rate of failed connections

### Warning Alerts
- **HighDatabaseConnections**: Connection count above threshold
- **SlowQueries**: 95th percentile query time >5 seconds
- **NoRecentBackup**: No successful backup in 24 hours
- **LargeBackupSize**: Backup size exceeds 10GB
- **HighQueryVolume**: Query rate >1000 queries/second

## Configuration

### Environment Variables

Update your `.env` file with monitoring-specific settings:

```env
# Monitoring Ports
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# Grafana Admin Password
GRAFANA_ADMIN_PASSWORD=your_secure_password

# Alert Manager (if using)
ALERTMANAGER_URL=http://alertmanager:9093
```

### Customizing Dashboards

1. **Modify existing dashboards:**
   - Edit JSON files in `grafana/dashboards/`
   - Restart Grafana to reload changes

2. **Add new dashboards:**
   - Export dashboard JSON from Grafana UI
   - Save to `grafana/dashboards/`
   - Restart Grafana

3. **Dashboard variables:**
   - Most dashboards include database selection variables
   - Use `$database` variable in queries to filter by database

### Customizing Alerts

1. **Modify thresholds:**
   - Edit `prometheus-rules.yml`
   - Adjust `expr` values for alert conditions
   - Reload Prometheus: `curl -X POST http://localhost:9090/-/reload`

2. **Add new alerts:**
   - Add new rules to `prometheus-rules.yml`
   - Follow existing pattern for labels and annotations
   - Test with PromQL queries in Prometheus UI

## Troubleshooting

### Common Issues

1. **Prometheus can't reach targets:**
   - Check Docker network connectivity
   - Verify service names in `prometheus.yml`
   - Check firewall settings

2. **Grafana dashboards not loading:**
   - Verify provisioning directory mounts
   - Check Grafana logs: `docker logs grafana`
   - Ensure JSON syntax is valid

3. **No metrics appearing:**
   - Verify Database Automation Suite is exposing metrics on `/metrics`
   - Check Prometheus targets page
   - Verify scrape intervals and timeouts

### Useful Commands

```bash
# Check Prometheus configuration
curl http://localhost:9090/api/v1/status/config

# Reload Prometheus configuration
curl -X POST http://localhost:9090/-/reload

# Check Grafana health
curl http://localhost:3000/api/health

# View Prometheus targets
curl http://localhost:9090/api/v1/targets

# Test PromQL queries
curl 'http://localhost:9090/api/v1/query?query=db_health_status'
```

## Security Considerations

1. **Change default passwords:**
   - Update Grafana admin password
   - Use strong passwords in production

2. **Network security:**
   - Consider using reverse proxy with SSL
   - Restrict access to monitoring ports
   - Use authentication for Prometheus

3. **Data retention:**
   - Configure appropriate retention policies
   - Monitor disk usage for time-series data
   - Implement backup strategies for monitoring data

## Performance Tuning

1. **Prometheus:**
   - Adjust scrape intervals based on needs
   - Configure retention time appropriately
   - Monitor memory usage for high-cardinality metrics

2. **Grafana:**
   - Optimize dashboard queries
   - Use appropriate time ranges
   - Consider query caching

## Integration with Alerting

To set up alerting notifications:

1. **Configure Alertmanager:**
   - Add alertmanager service to docker-compose.yml
   - Configure notification channels (email, Slack, PagerDuty)

2. **Update Prometheus configuration:**
   - Uncomment alertmanager configuration in prometheus.yml
   - Specify alertmanager targets

3. **Test alerting:**
   - Trigger test alerts
   - Verify notification delivery
   - Adjust alert thresholds as needed

This monitoring setup provides comprehensive visibility into your database automation operations and helps ensure reliable, performant database management.