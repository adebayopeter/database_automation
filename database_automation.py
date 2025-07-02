#!/usr/bin/env python3
"""
Database Automation Suite
A comprehensive automation framework for PostgreSQL and SQL Server database management
Author: Adebayo Olaonipekun
Date: July 2025
"""

import psycopg2
import psycopg2.pool
import pymssql
import logging
import yaml
import json
import time
import os
import argparse
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import schedule
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import threading
import signal
from contextlib import contextmanager
from pathlib import Path
import subprocess

# Load environment variables
load_dotenv()


# Configure structured logging
def setup_logging(log_level: str = 'INFO', log_file: str = 'db_automation.log') -> logging.Logger:
    """Setup structured logging with both file and console handlers"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized with level: {log_level}")
    return logger


logger = setup_logging()

# Prometheus metrics
db_connection_counter = Counter('db_connections_total', 'Total database connections', ['database', 'status'])
db_query_duration = Histogram('db_query_duration_seconds', 'Database query duration', ['database', 'query_type'])
db_health_gauge = Gauge('db_health_status', 'Database health status', ['database'])
backup_counter = Counter('db_backups_total', 'Total database backups', ['database', 'status'])
backup_size_gauge = Gauge('db_backup_size_bytes', 'Database backup size in bytes', ['database'])


@dataclass
class DatabaseConfig:
    """Database configuration class"""
    host: str
    port: int
    database: str
    username: str
    password: str
    db_type: str  # 'postgresql' or 'sqlserver'
    connection_pool_size: int = 10
    ssl_mode: str = 'prefer'
    connect_timeout: int = 30
    

@dataclass
class AlertConfig:
    """Alert configuration class"""
    enabled: bool = False
    smtp_server: str = ''
    smtp_port: int = 587
    from_email: str = ''
    password: str = ''
    recipients: List[str] = field(default_factory=list)
    

@dataclass
class BackupConfig:
    """Backup configuration class"""
    schedule: str = '0 2 * * *'
    retention_days: int = 7
    backup_path: str = '/var/backups'
    compression: bool = True
    parallel_jobs: int = 2


class DatabaseAutomation:
    """Main database automation class with enhanced error handling and connection pooling"""

    def __init__(self, config_file: str = 'db_config.yaml'):
        self.config_file = config_file
        self.config = self._load_config(config_file)
        self.connection_pools = {}
        self.monitoring_metrics = {}
        self.alert_config = self._load_alert_config()
        self.backup_config = self._load_backup_config()
        self.shutdown_event = threading.Event()
        self.start_time = time.time()
        self._setup_signal_handlers()
        self._initialize_connection_pools()
        
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_event.set()
        self.close_all_connections()
        sys.exit(0)

    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from YAML file with environment variable substitution"""
        try:
            if not Path(config_file).exists():
                logger.warning(f"Configuration file {config_file} not found, creating default")
                return self._create_default_config()
                
            with open(config_file, 'r') as file:
                config_content = file.read()
                
            # Replace environment variables in config
            config_content = os.path.expandvars(config_content)
            config = yaml.safe_load(config_content)
            
            # Validate required configuration sections
            required_sections = ['databases', 'monitoring', 'backup']
            for section in required_sections:
                if section not in config:
                    logger.error(f"Missing required configuration section: {section}")
                    raise ValueError(f"Invalid configuration: missing {section} section")
                    
            logger.info(f"Configuration loaded successfully from {config_file}")
            return config
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {config_file}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise

    def _create_default_config(self) -> Dict:
        """Create default configuration"""
        return {
            'databases': {
                'postgres_primary': {
                    'host': 'localhost',
                    'port': 5432,
                    'database': 'postgres',
                    'username': 'postgres',
                    'password': 'password',
                    'db_type': 'postgresql'
                },
                'sqlserver_primary': {
                    'host': 'localhost',
                    'port': 1433,
                    'database': 'master',
                    'username': 'sa',
                    'password': 'password',
                    'db_type': 'sqlserver'
                }
            },
            'monitoring': {
                'check_interval': 300,  # 5 minutes
                'alert_thresholds': {
                    'cpu_usage': 80,
                    'memory_usage': 85,
                    'disk_usage': 90,
                    'connection_count': 100
                }
            },
            'backup': {
                'schedule': '0 2 * * *',  # Daily at 2 AM
                'retention_days': 7,
                'backup_path': '/var/backups/postgres'
            }
        }
            
    def _load_alert_config(self) -> AlertConfig:
        """Load alert configuration"""
        alert_config = self.config.get('monitoring', {}).get('email_alerts', {})
        return AlertConfig(
            enabled=alert_config.get('enabled', False),
            smtp_server=alert_config.get('smtp_server', ''),
            smtp_port=alert_config.get('smtp_port', 587),
            from_email=alert_config.get('from_email', ''),
            password=os.getenv('SMTP_PASSWORD', ''),
            recipients=alert_config.get('alert_recipients', [])
        )
        
    def _load_backup_config(self) -> BackupConfig:
        """Load backup configuration"""
        backup_config = self.config.get('backup', {})
        return BackupConfig(
            schedule=backup_config.get('schedule', '0 2 * * *'),
            retention_days=backup_config.get('retention_days', 7),
            backup_path=backup_config.get('backup_path', '/var/backups'),
            compression=backup_config.get('compression', True),
            parallel_jobs=backup_config.get('parallel_jobs', 2)
        )

    def _initialize_connection_pools(self):
        """Initialize connection pools for all configured databases"""
        for db_name, db_config in self.config['databases'].items():
            # Check if database is enabled via environment variable
            enabled = str(db_config.get('enabled', 'true')).lower() == 'true'
            if not enabled:
                logger.info(f"Database {db_name} is disabled via configuration, skipping...")
                continue
                
            try:
                if db_config['db_type'] == 'postgresql':
                    pool = psycopg2.pool.ThreadedConnectionPool(
                        minconn=1,
                        maxconn=db_config.get('connection_pool_size', 10),
                        host=db_config['host'],
                        port=db_config['port'],
                        database=db_config['database'],
                        user=db_config['username'],
                        password=os.getenv(f"{db_name.upper()}_PASSWORD", db_config['password']),
                        sslmode=db_config.get('ssl_mode', 'prefer'),
                        connect_timeout=db_config.get('connect_timeout', 30)
                    )
                    self.connection_pools[db_name] = pool
                    logger.info(f"Connection pool initialized for {db_name}")
                    db_connection_counter.labels(database=db_name, status='pool_created').inc()
                    
                elif db_config['db_type'] == 'sqlserver':
                    # SQL Server doesn't have built-in connection pooling in pymssql
                    # We'll implement a simple connection manager
                    self.connection_pools[db_name] = {
                        'config': db_config,
                        'type': 'sqlserver',
                        'max_connections': db_config.get('connection_pool_size', 10)
                    }
                    logger.info(f"Connection configuration set for SQL Server: {db_name}")
                    
            except Exception as e:
                logger.error(f"Failed to initialize connection pool for {db_name}: {e}")
                db_connection_counter.labels(database=db_name, status='pool_failed').inc()
                raise
    
    def get_enabled_databases(self) -> List[str]:
        """Get list of enabled database names"""
        enabled_dbs = []
        for db_name, db_config in self.config['databases'].items():
            enabled = str(db_config.get('enabled', 'true')).lower() == 'true'
            if enabled:
                enabled_dbs.append(db_name)
        return enabled_dbs
    
    @contextmanager
    def get_connection(self, db_name: str):
        """Get database connection from pool with proper resource management"""
        if db_name not in self.connection_pools:
            raise ValueError(f"Database {db_name} not configured")
            
        conn = None
        try:
            pool_config = self.connection_pools[db_name]
            
            if isinstance(pool_config, psycopg2.pool.ThreadedConnectionPool):
                conn = pool_config.getconn()
                db_connection_counter.labels(database=db_name, status='acquired').inc()
                yield conn
                
            elif pool_config['type'] == 'sqlserver':
                db_config = pool_config['config']
                conn = pymssql.connect(
                    server=db_config['host'],
                    port=db_config['port'],
                    database=db_config['database'],
                    user=db_config['username'],
                    password=os.getenv(f"{db_name.upper()}_PASSWORD", db_config['password']),
                    timeout=db_config.get('connect_timeout', 30)
                )
                db_connection_counter.labels(database=db_name, status='acquired').inc()
                yield conn
                
        except Exception as e:
            logger.error(f"Connection error for {db_name}: {e}")
            db_connection_counter.labels(database=db_name, status='failed').inc()
            raise
        finally:
            if conn:
                try:
                    if isinstance(self.connection_pools[db_name], psycopg2.pool.ThreadedConnectionPool):
                        self.connection_pools[db_name].putconn(conn)
                    else:
                        conn.close()
                    db_connection_counter.labels(database=db_name, status='released').inc()
                except Exception as e:
                    logger.error(f"Error releasing connection for {db_name}: {e}")

    def execute_query(self, db_name: str, query: str, params: tuple = None, query_type: str = 'unknown') -> List[Dict]:
        """Execute query with timing metrics and proper error handling"""
        start_time = time.time()
        
        try:
            with self.get_connection(db_name) as conn:
                cursor = conn.cursor()
                
                logger.debug(f"Executing query on {db_name}: {query[:100]}...")
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                if query.strip().upper().startswith('SELECT'):
                    columns = [desc[0] for desc in cursor.description]
                    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    logger.debug(f"Query returned {len(results)} rows")
                    return results
                else:
                    conn.commit()
                    affected_rows = cursor.rowcount
                    logger.debug(f"Query affected {affected_rows} rows")
                    return [{'affected_rows': affected_rows}]
                    
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error executing query on {db_name}: {e}")
            raise
        except pymssql.Error as e:
            logger.error(f"SQL Server error executing query on {db_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error executing query on {db_name}: {e}")
            raise
        finally:
            duration = time.time() - start_time
            db_query_duration.labels(database=db_name, query_type=query_type).observe(duration)
            logger.debug(f"Query execution time: {duration:.3f}s")

    def close_all_connections(self):
        """Close all database connection pools"""
        for db_name, pool in self.connection_pools.items():
            try:
                if isinstance(pool, psycopg2.pool.ThreadedConnectionPool):
                    pool.closeall()
                logger.info(f"Connection pool closed for {db_name}")
            except Exception as e:
                logger.error(f"Error closing connection pool for {db_name}: {e}")
                
    def send_alert(self, subject: str, message: str, severity: str = 'INFO'):
        """Send email alert if configured"""
        if not self.alert_config.enabled:
            logger.debug("Email alerts not enabled")
            return
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.alert_config.from_email
            msg['To'] = ', '.join(self.alert_config.recipients)
            msg['Subject'] = f"[DB-AUTOMATION-{severity}] {subject}"
            
            body = f"""
            Database Automation Alert
            
            Severity: {severity}
            Timestamp: {datetime.now().isoformat()}
            
            Message:
            {message}
            
            ---
            Database Automation Suite
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.alert_config.smtp_server, self.alert_config.smtp_port) as server:
                server.starttls()
                if self.alert_config.password:
                    server.login(self.alert_config.from_email, self.alert_config.password)
                server.send_message(msg)
                
            logger.info(f"Alert sent: {subject}")
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")

    def monitor_database_health(self, db_name: str) -> Dict[str, Any]:
        """Monitor database health metrics with alerting"""
        try:
            db_config = self.config['databases'][db_name]
            
            logger.info(f"Starting health check for {db_name}")
            
            if db_config['db_type'] == 'postgresql':
                health_data = self._monitor_postgres_health(db_name)
            elif db_config['db_type'] == 'sqlserver':
                health_data = self._monitor_sqlserver_health(db_name)
            else:
                raise ValueError(f"Unsupported database type: {db_config['db_type']}")
                
            # Update Prometheus metrics
            if health_data.get('status') == 'healthy':
                db_health_gauge.labels(database=db_name).set(1)
            else:
                db_health_gauge.labels(database=db_name).set(0)
                
            # Check for alerts
            self._check_health_alerts(db_name, health_data)
            
            logger.info(f"Health check completed for {db_name}")
            return health_data
            
        except Exception as e:
            logger.error(f"Health monitoring failed for {db_name}: {e}")
            db_health_gauge.labels(database=db_name).set(0)
            
            # Send critical alert
            self.send_alert(
                f"Health Check Failed: {db_name}",
                f"Database health monitoring failed: {str(e)}",
                'CRITICAL'
            )
            
            return {'status': 'error', 'message': str(e), 'timestamp': datetime.now().isoformat()}

    def _check_health_alerts(self, db_name: str, health_data: Dict[str, Any]):
        """Check health metrics against thresholds and send alerts"""
        thresholds = self.config['monitoring']['alert_thresholds']
        alerts = []
        
        # Check connection count
        if 'connection_count' in health_data:
            conn_count = health_data['connection_count'][0].get('connections', 0)
            if conn_count > thresholds.get('connection_count', 100):
                alerts.append(f"High connection count: {conn_count}")
                
        # Check long running queries
        if 'long_running_queries' in health_data:
            long_queries = health_data['long_running_queries']
            if isinstance(long_queries, list) and len(long_queries) > 0:
                alerts.append(f"Found {len(long_queries)} long-running queries")
                
        # Send alerts if any found
        if alerts:
            alert_message = f"\\n".join(alerts)
            self.send_alert(
                f"Database Health Alert: {db_name}",
                alert_message,
                'WARNING'
            )

    def _monitor_postgres_health(self, db_name: str) -> Dict[str, Any]:
        """Monitor PostgreSQL specific health metrics"""
        queries = {
            'connection_count': """
                SELECT count(*) as connections 
                FROM pg_stat_activity 
                WHERE state = 'active'
            """,
            'database_size': """
                SELECT 
                    pg_size_pretty(pg_database_size(current_database())) as size,
                    pg_database_size(current_database()) as size_bytes
            """,
            'long_running_queries': """
                SELECT 
                    pid, 
                    now() - pg_stat_activity.query_start AS duration, 
                    query,
                    state,
                    usename
                FROM pg_stat_activity 
                WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes'
                AND state = 'active'
                AND query NOT LIKE '%pg_stat_activity%'
            """,
            'table_stats': """
                SELECT 
                    schemaname, 
                    relname AS tablename, 
                    n_tup_ins, 
                    n_tup_upd, 
                    n_tup_del,
                    n_live_tup,
                    n_dead_tup
                FROM pg_stat_user_tables
                ORDER BY n_tup_ins DESC
                LIMIT 10
            """,
            'index_usage': """
                SELECT 
                    schemaname, 
                    relname AS tablename, 
                    indexrelname AS indexname, 
                    idx_scan, 
                    idx_tup_read, 
                    idx_tup_fetch
                FROM pg_stat_user_indexes
                WHERE idx_scan > 0
                ORDER BY idx_scan DESC
                LIMIT 10
            """,
            'replication_status': """
                SELECT 
                    client_addr,
                    state,
                    sent_lsn,
                    write_lsn,
                    flush_lsn,
                    replay_lsn,
                    sync_state
                FROM pg_stat_replication
            """,
            'database_conflicts': """
                SELECT 
                    confl_tablespace,
                    confl_lock,
                    confl_snapshot,
                    confl_bufferpin,
                    confl_deadlock
                FROM pg_stat_database_conflicts
                WHERE datname = current_database()
            """
        }

        metrics = {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
        
        for metric_name, query in queries.items():
            try:
                result = self.execute_query(db_name, query, query_type='health_check')
                metrics[metric_name] = result
                logger.debug(f"Collected {metric_name} metrics: {len(result)} rows")
            except Exception as e:
                logger.warning(f"Failed to collect {metric_name} for {db_name}: {e}")
                metrics[metric_name] = {'error': str(e)}
                metrics['status'] = 'degraded'

        return metrics

    def _monitor_sqlserver_health(self, db_name: str) -> Dict[str, Any]:
        """Monitor SQL Server specific health metrics"""
        queries = {
            'connection_count': """
                SELECT COUNT(*) as connections 
                FROM sys.dm_exec_sessions 
                WHERE is_user_process = 1
            """,
            'database_size': """
                SELECT 
                    DB_NAME() as database_name,
                    CAST(SUM(size) * 8.0 / 1024 AS DECIMAL(10,2)) as size_mb
                FROM sys.master_files 
                WHERE database_id = DB_ID()
            """,
            'wait_stats': """
                SELECT TOP 10
                    wait_type,
                    wait_time_ms,
                    waiting_tasks_count
                FROM sys.dm_os_wait_stats
                WHERE wait_time_ms > 0
                ORDER BY wait_time_ms DESC
            """
        }

        metrics = {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
        
        for metric_name, query in queries.items():
            try:
                result = self.execute_query(db_name, query, query_type='health_check')
                metrics[metric_name] = result
                logger.debug(f"Collected {metric_name} metrics: {len(result)} rows")
            except Exception as e:
                logger.warning(f"Failed to collect {metric_name} for {db_name}: {e}")
                metrics[metric_name] = {'error': str(e)}
                metrics['status'] = 'degraded'

        return metrics

    def automated_backup(self, db_name: str) -> Dict[str, Any]:
        """Perform automated database backup with enhanced error handling"""
        start_time = time.time()
        backup_counter.labels(database=db_name, status='started').inc()
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = self.backup_config.backup_path
            
            # Ensure backup directory exists
            Path(backup_path).mkdir(parents=True, exist_ok=True)
            
            db_config = self.config['databases'][db_name]
            logger.info(f"Starting backup for {db_name}")

            if db_config['db_type'] == 'postgresql':
                result = self._postgres_backup(db_name, timestamp, backup_path)
            elif db_config['db_type'] == 'sqlserver':
                result = self._sqlserver_backup(db_name, timestamp, backup_path)
            else:
                raise ValueError(f"Unsupported database type: {db_config['db_type']}")
                
            # Update metrics
            if result.get('status') == 'success':
                backup_counter.labels(database=db_name, status='success').inc()
                backup_size_gauge.labels(database=db_name).set(result.get('file_size_mb', 0) * 1024 * 1024)
                
                # Send success notification
                self.send_alert(
                    f"Backup Completed: {db_name}",
                    f"Backup successful for {db_name}\\nFile: {result.get('backup_file')}\\nSize: {result.get('file_size_mb')} MB",
                    'INFO'
                )
            else:
                backup_counter.labels(database=db_name, status='failed').inc()
                
            duration = time.time() - start_time
            logger.info(f"Backup completed for {db_name} in {duration:.2f}s")
            
            return result

        except Exception as e:
            logger.error(f"Backup failed for {db_name}: {e}")
            backup_counter.labels(database=db_name, status='failed').inc()
            
            # Send failure alert
            self.send_alert(
                f"Backup Failed: {db_name}",
                f"Backup failed for {db_name}: {str(e)}",
                'CRITICAL'
            )
            
            return {
                'status': 'failed', 
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def _postgres_backup(self, db_name: str, timestamp: str, backup_path: str) -> Dict[str, Any]:
        """PostgreSQL backup using pg_dump with compression and error handling"""
        db_config = self.config['databases'][db_name]
        
        # Determine file extension based on compression setting
        if self.backup_config.compression:
            filename = f"{db_name}_{timestamp}.sql.gz"
            compress_flag = "--compress=6"
        else:
            filename = f"{db_name}_{timestamp}.sql"
            compress_flag = ""
            
        full_path = os.path.join(backup_path, filename)
        
        # Get password from environment or config
        password = os.getenv(f"{db_name.upper()}_PASSWORD", db_config['password'])

        # Construct pg_dump command with proper escaping
        cmd_parts = [
            'pg_dump',
            f'-h {db_config["host"]}',
            f'-p {db_config["port"]}',
            f'-U {db_config["username"]}',
            f'-d {db_config["database"]}',
            f'-f "{full_path}"',
            '--verbose',
            '--no-password',
            compress_flag
        ]
        
        cmd = ' '.join(filter(None, cmd_parts))
        
        # Set environment variable for password
        env = os.environ.copy()
        env['PGPASSWORD'] = password
        
        logger.debug(f"Executing backup command: {cmd}")
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                if os.path.exists(full_path):
                    file_size = os.path.getsize(full_path)
                    logger.info(f"PostgreSQL backup successful: {full_path} ({file_size} bytes)")
                    return {
                        'status': 'success',
                        'backup_file': full_path,
                        'file_size_mb': round(file_size / (1024 * 1024), 2),
                        'timestamp': timestamp,
                        'compressed': self.backup_config.compression
                    }
                else:
                    return {'status': 'failed', 'message': 'Backup file not created'}
            else:
                error_msg = result.stderr or f'pg_dump failed with exit code {result.returncode}'
                logger.error(f"pg_dump error: {error_msg}")
                return {'status': 'failed', 'message': error_msg}
                
        except subprocess.TimeoutExpired:
            return {'status': 'failed', 'message': 'Backup timeout (1 hour limit exceeded)'}
        except Exception as e:
            return {'status': 'failed', 'message': f'Backup execution error: {str(e)}'}

    def _sqlserver_backup(self, db_name: str, timestamp: str, backup_path: str) -> Dict[str, Any]:
        """SQL Server backup using T-SQL with compression and error handling"""
        filename = f"{db_name}_{timestamp}.bak"
        full_path = os.path.join(backup_path, filename)
        
        # Ensure Windows path format for SQL Server
        if os.name == 'nt':
            full_path = full_path.replace('/', '\\\\')

        # Build backup query with compression if supported
        backup_options = [
            'FORMAT',
            'INIT',
            'SKIP',
            'NOREWIND',
            'NOUNLOAD',
            'STATS = 10'
        ]
        
        if self.backup_config.compression:
            backup_options.append('COMPRESSION')
            
        backup_query = f"""
        BACKUP DATABASE [{self.config['databases'][db_name]['database']}]
        TO DISK = N'{full_path}'
        WITH {', '.join(backup_options)}
        """

        try:
            logger.debug(f"Executing SQL Server backup: {backup_query}")
            result = self.execute_query(db_name, backup_query, query_type='backup')
            
            if os.path.exists(full_path):
                file_size = os.path.getsize(full_path)
                logger.info(f"SQL Server backup successful: {full_path} ({file_size} bytes)")
                return {
                    'status': 'success',
                    'backup_file': full_path,
                    'file_size_mb': round(file_size / (1024 * 1024), 2),
                    'timestamp': timestamp,
                    'compressed': self.backup_config.compression,
                    'query_result': result
                }
            else:
                return {'status': 'failed', 'message': 'Backup file not created'}
                
        except Exception as e:
            logger.error(f"SQL Server backup error: {e}")
            return {'status': 'failed', 'message': str(e)}

    def cleanup_old_backups(self, retention_days: int = None) -> Dict[str, Any]:
        """Clean up old backup files with enhanced safety checks"""
        if retention_days is None:
            retention_days = self.backup_config.retention_days

        backup_path = self.backup_config.backup_path
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        deleted_files = []
        total_size_freed = 0
        errors = []

        try:
            if not os.path.exists(backup_path):
                logger.warning(f"Backup path does not exist: {backup_path}")
                return {'status': 'warning', 'message': 'Backup path does not exist'}
                
            logger.info(f"Cleaning up backups older than {retention_days} days from {backup_path}")
            
            # Get list of backup files (filter by extension)
            backup_extensions = ['.sql', '.sql.gz', '.bak', '.dump']
            
            for filename in os.listdir(backup_path):
                file_path = os.path.join(backup_path, filename)
                
                # Only process files with backup extensions
                if not any(filename.endswith(ext) for ext in backup_extensions):
                    continue
                    
                if os.path.isfile(file_path):
                    try:
                        file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        if file_modified < cutoff_date:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            deleted_files.append({
                                'filename': filename,
                                'size_mb': round(file_size / (1024 * 1024), 2),
                                'modified_date': file_modified.isoformat()
                            })
                            total_size_freed += file_size
                            logger.debug(f"Deleted old backup: {filename}")
                            
                    except Exception as e:
                        error_msg = f"Error processing {filename}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)

            result = {
                'status': 'success' if not errors else 'partial_success',
                'deleted_files': deleted_files,
                'files_deleted': len(deleted_files),
                'space_freed_mb': round(total_size_freed / (1024 * 1024), 2),
                'retention_days': retention_days,
                'cutoff_date': cutoff_date.isoformat()
            }
            
            if errors:
                result['errors'] = errors
                
            logger.info(f"Cleanup completed: {len(deleted_files)} files deleted, {result['space_freed_mb']} MB freed")
            return result

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return {'status': 'failed', 'message': str(e)}

    def performance_optimization(self, db_name: str) -> Dict[str, Any]:
        """Automated performance optimization"""
        db_config = self.config['databases'][db_name]

        if db_config['db_type'] == 'postgresql':
            return self._postgres_optimization(db_name)
        elif db_config['db_type'] == 'sqlserver':
            return self._sqlserver_optimization(db_name)

    def _postgres_optimization(self, db_name: str) -> Dict[str, Any]:
        """PostgreSQL performance optimization"""
        optimizations = []

        # Analyze and vacuum tables
        analyze_query = "ANALYZE;"
        vacuum_query = "VACUUM ANALYZE;"

        try:
            self.execute_query(db_name, analyze_query, query_type='optimization')
            optimizations.append("Statistics updated with ANALYZE")

            self.execute_query(db_name, vacuum_query, query_type='optimization')
            optimizations.append("Tables vacuumed and analyzed")

            # Check for missing indexes
            missing_indexes_query = """
            SELECT schemaname, relname AS tablename, attname, n_distinct, correlation
            FROM pg_stats
            WHERE n_distinct > 100 AND correlation < 0.1
            ORDER BY n_distinct DESC
            LIMIT 5;
            """

            missing_indexes = self.execute_query(db_name, missing_indexes_query, query_type='optimization')
            if missing_indexes:
                optimizations.append(f"Found {len(missing_indexes)} potential index candidates")

            return {
                'status': 'success',
                'optimizations': optimizations,
                'missing_indexes': missing_indexes
            }

        except Exception as e:
            logger.error(f"PostgreSQL optimization failed for {db_name}: {e}")
            return {'status': 'failed', 'message': str(e)}

    def _sqlserver_optimization(self, db_name: str) -> Dict[str, Any]:
        """SQL Server performance optimization"""
        optimizations = []

        try:
            # Update statistics
            update_stats_query = "EXEC sp_updatestats;"
            self.execute_query(db_name, update_stats_query, query_type='optimization')
            optimizations.append("Statistics updated")

            # Check index fragmentation
            fragmentation_query = """
            SELECT 
                OBJECT_NAME(ips.object_id) AS table_name,
                si.name AS index_name,
                ips.avg_fragmentation_in_percent
            FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'SAMPLED') ips
            INNER JOIN sys.indexes si ON ips.object_id = si.object_id AND ips.index_id = si.index_id
            WHERE ips.avg_fragmentation_in_percent > 30
            ORDER BY ips.avg_fragmentation_in_percent DESC;
            """

            fragmented_indexes = self.execute_query(db_name, fragmentation_query, query_type='optimization')
            if fragmented_indexes:
                optimizations.append(f"Found {len(fragmented_indexes)} fragmented indexes")

            return {
                'status': 'success',
                'optimizations': optimizations,
                'fragmented_indexes': fragmented_indexes
            }

        except Exception as e:
            logger.error(f"SQL Server optimization failed for {db_name}: {e}")
            return {'status': 'failed', 'message': str(e)}

    def generate_health_report(self, db_name: str) -> Dict[str, Any]:
        """Generate comprehensive health report with enhanced metrics"""
        logger.info(f"Generating comprehensive health report for {db_name}")
        
        try:
            report = {
                'database': db_name,
                'timestamp': datetime.now().isoformat(),
                'report_version': '2.0',
                'database_config': {
                    'type': self.config['databases'][db_name]['db_type'],
                    'host': self.config['databases'][db_name]['host'],
                    'port': self.config['databases'][db_name]['port'],
                    'database': self.config['databases'][db_name]['database']
                },
                'health_metrics': self.monitor_database_health(db_name),
                'optimization_report': self.performance_optimization(db_name),
                'system_info': {
                    'python_version': sys.version,
                    'platform': os.name,
                    'hostname': os.uname().nodename if hasattr(os, 'uname') else 'unknown'
                }
            }
            
            # Add recent backup information
            backup_path = self.backup_config.backup_path
            if os.path.exists(backup_path):
                backup_files = []
                for file in os.listdir(backup_path):
                    if db_name in file and (file.endswith('.sql') or file.endswith('.bak') or file.endswith('.sql.gz')):
                        file_path = os.path.join(backup_path, file)
                        if os.path.isfile(file_path):
                            stat = os.stat(file_path)
                            backup_files.append({
                                'filename': file,
                                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                            })
                            
                # Sort by modification time (newest first)
                backup_files.sort(key=lambda x: x['modified'], reverse=True)
                report['recent_backups'] = backup_files[:5]  # Last 5 backups

            # Save report to file
            reports_dir = Path('reports')
            reports_dir.mkdir(exist_ok=True)
            
            report_filename = reports_dir / f"health_report_{db_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(report_filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)

            logger.info(f"Health report generated: {report_filename}")
            
            # Also create a summary text report
            summary_filename = reports_dir / f"health_summary_{db_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            self._create_text_summary(report, summary_filename)
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate health report for {db_name}: {e}")
            return {
                'database': db_name,
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
                'message': str(e)
            }

    def _create_text_summary(self, report: Dict[str, Any], filename: Path):
        """Create a human-readable text summary of the health report"""
        try:
            with open(filename, 'w') as f:
                f.write(f"Database Health Report Summary\\n")
                f.write(f"{'=' * 40}\\n\\n")
                f.write(f"Database: {report['database']}\\n")
                f.write(f"Report Generated: {report['timestamp']}\\n")
                f.write(f"Database Type: {report['database_config']['type']}\\n")
                f.write(f"Host: {report['database_config']['host']}:{report['database_config']['port']}\\n\\n")
                
                # Health Status
                health = report.get('health_metrics', {})
                f.write(f"Health Status: {health.get('status', 'Unknown')}\\n\\n")
                
                # Connection Count
                if 'connection_count' in health:
                    conn_data = health['connection_count']
                    if isinstance(conn_data, list) and len(conn_data) > 0:
                        f.write(f"Active Connections: {conn_data[0].get('connections', 'N/A')}\\n")
                        
                # Database Size
                if 'database_size' in health:
                    size_data = health['database_size']
                    if isinstance(size_data, list) and len(size_data) > 0:
                        f.write(f"Database Size: {size_data[0].get('size', 'N/A')}\\n")
                        
                # Long Running Queries
                if 'long_running_queries' in health:
                    long_queries = health['long_running_queries']
                    if isinstance(long_queries, list):
                        f.write(f"Long Running Queries: {len(long_queries)}\\n")
                        
                # Recent Backups
                if 'recent_backups' in report:
                    f.write(f"\\nRecent Backups:\\n")
                    for backup in report['recent_backups'][:3]:
                        f.write(f"  - {backup['filename']} ({backup['size_mb']} MB) - {backup['modified'][:10]}\\n")
                        
                # Optimization Summary
                optimization = report.get('optimization_report', {})
                f.write(f"\\nOptimization Status: {optimization.get('status', 'Unknown')}\\n")
                if 'optimizations' in optimization:
                    f.write("Recent Optimizations:\\n")
                    for opt in optimization['optimizations']:
                        f.write(f"  - {opt}\\n")
                        
            logger.info(f"Text summary created: {filename}")
            
        except Exception as e:
            logger.error(f"Failed to create text summary: {e}")

    def schedule_automated_tasks(self):
        """Schedule automated maintenance tasks based on configuration"""
        # Schedule daily backups based on cron schedule
        schedule.every().day.at("02:00").do(self.run_daily_maintenance)
        logger.info("Daily maintenance scheduled for 02:00")

        # Schedule health checks based on configuration
        check_interval = self.config['monitoring'].get('check_interval', 300)  # seconds
        if check_interval >= 3600:  # If >= 1 hour, schedule hourly
            schedule.every().hour.do(self.run_health_checks)
            logger.info("Health checks scheduled hourly")
        elif check_interval >= 60:  # If >= 1 minute, schedule every N minutes
            minutes = check_interval // 60
            schedule.every(minutes).minutes.do(self.run_health_checks)
            logger.info(f"Health checks scheduled every {minutes} minutes")
        else:
            # For very frequent checks, we'll run them in the monitoring loop
            logger.info(f"Health checks will run every {check_interval} seconds in monitoring loop")

        # Schedule weekly optimization
        schedule.every().sunday.at("01:00").do(self.run_weekly_optimization)
        logger.info("Weekly optimization scheduled for Sunday 01:00")
        
        # Schedule backup cleanup
        schedule.every().day.at("03:00").do(self.cleanup_old_backups)
        logger.info("Backup cleanup scheduled for 03:00")

        logger.info("All automated tasks scheduled successfully")

    def run_daily_maintenance(self):
        """Run daily maintenance tasks with parallel execution"""
        logger.info("Starting daily maintenance")
        
        # Run backups in parallel for enabled databases only
        enabled_databases = self.get_enabled_databases()
        with ThreadPoolExecutor(max_workers=self.backup_config.parallel_jobs) as executor:
            backup_futures = {
                executor.submit(self.automated_backup, db_name): db_name 
                for db_name in enabled_databases
            }
            
            backup_results = []
            for future in as_completed(backup_futures):
                db_name = backup_futures[future]
                try:
                    result = future.result()
                    backup_results.append((db_name, result))
                    logger.info(f"Backup for {db_name}: {result['status']}")
                except Exception as e:
                    logger.error(f"Backup failed for {db_name}: {e}")
                    backup_results.append((db_name, {'status': 'failed', 'message': str(e)}))

        # Cleanup old backups
        cleanup_result = self.cleanup_old_backups()
        logger.info(f"Backup cleanup: {cleanup_result['status']}")
        
        # Send daily summary
        successful_backups = sum(1 for _, result in backup_results if result['status'] == 'success')
        total_backups = len(backup_results)
        
        summary = f"""
        Daily Maintenance Summary:
        - Backups: {successful_backups}/{total_backups} successful
        - Cleanup: {cleanup_result['status']}
        - Files cleaned: {cleanup_result.get('files_deleted', 0)}
        - Space freed: {cleanup_result.get('space_freed_mb', 0)} MB
        """
        
        self.send_alert(
            "Daily Maintenance Summary",
            summary,
            'INFO' if successful_backups == total_backups else 'WARNING'
        )

    def run_health_checks(self):
        """Run health checks for all enabled databases with parallel execution"""
        enabled_databases = self.get_enabled_databases()
        with ThreadPoolExecutor(max_workers=max(1, len(enabled_databases))) as executor:
            health_futures = {
                executor.submit(self.monitor_database_health, db_name): db_name
                for db_name in enabled_databases
            }
            
            for future in as_completed(health_futures):
                db_name = health_futures[future]
                try:
                    health_metrics = future.result()
                    self.monitoring_metrics[db_name] = health_metrics
                    logger.info(f"Health check completed for {db_name}: {health_metrics.get('status', 'unknown')}")
                except Exception as e:
                    logger.error(f"Health check failed for {db_name}: {e}")
                    self.monitoring_metrics[db_name] = {
                        'status': 'error',
                        'message': str(e),
                        'timestamp': datetime.now().isoformat()
                    }

    def run_weekly_optimization(self):
        """Run weekly optimization tasks with parallel execution"""
        logger.info("Starting weekly optimization")
        
        enabled_databases = self.get_enabled_databases()
        with ThreadPoolExecutor(max_workers=max(1, len(enabled_databases))) as executor:
            optimization_futures = {
                executor.submit(self.performance_optimization, db_name): db_name
                for db_name in enabled_databases
            }
            
            optimization_results = []
            for future in as_completed(optimization_futures):
                db_name = optimization_futures[future]
                try:
                    result = future.result()
                    optimization_results.append((db_name, result))
                    logger.info(f"Optimization for {db_name}: {result['status']}")
                except Exception as e:
                    logger.error(f"Optimization failed for {db_name}: {e}")
                    optimization_results.append((db_name, {'status': 'failed', 'message': str(e)}))
                    
        # Send weekly optimization summary
        successful_optimizations = sum(1 for _, result in optimization_results if result['status'] == 'success')
        total_optimizations = len(optimization_results)
        
        summary = f"""
        Weekly Optimization Summary:
        - Optimizations: {successful_optimizations}/{total_optimizations} successful
        
        Details:
        """
        
        for db_name, result in optimization_results:
            summary += f"\\n{db_name}: {result['status']}"
            if 'optimizations' in result:
                for opt in result['optimizations']:
                    summary += f"\\n  - {opt}"
                    
        self.send_alert(
            "Weekly Optimization Summary",
            summary,
            'INFO' if successful_optimizations == total_optimizations else 'WARNING'
        )

    def start_monitoring(self):
        """Start the monitoring loop with graceful shutdown support"""
        logger.info("Starting database automation monitoring")
        
        try:
            while not self.shutdown_event.is_set():
                schedule.run_pending()
                
                # Sleep in small intervals to allow responsive shutdown
                for _ in range(60):  # 60 seconds total
                    if self.shutdown_event.is_set():
                        break
                    time.sleep(1)
                    
        except Exception as e:
            logger.error(f"Monitoring loop error: {e}")
            self.send_alert(
                "Monitoring Loop Error",
                f"Database monitoring encountered an error: {str(e)}",
                'CRITICAL'
            )
            raise
        finally:
            logger.info("Monitoring loop stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': time.time() - self.start_time,
            'databases': {},
            'system': {
                'version': '2.0.0',
                'config_file': self.config_file,
                'python_version': sys.version,
                'monitoring_enabled': not self.shutdown_event.is_set()
            }
        }
        
        # Quick health check for each enabled database
        for db_name, db_config in self.config['databases'].items():
            enabled = str(db_config.get('enabled', 'true')).lower() == 'true'
            if not enabled:
                status['databases'][db_name] = {
                    'status': 'disabled',
                    'type': db_config['db_type']
                }
                continue
                
            try:
                with self.get_connection(db_name) as conn:
                    status['databases'][db_name] = {
                        'status': 'connected',
                        'type': db_config['db_type']
                    }
            except Exception as e:
                status['databases'][db_name] = {
                    'status': 'error',
                    'error': str(e),
                    'type': db_config['db_type']
                }
                
        return status


def create_cli_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description='Database Automation Suite - Comprehensive database management and monitoring'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='db_config.yaml',
        help='Path to configuration file (default: db_config.yaml)'
    )
    
    parser.add_argument(
        '--log-level', '-l',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--database', '-d',
        type=str,
        help='Target specific database (default: all configured databases)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Health check command
    health_parser = subparsers.add_parser('health', help='Run health checks')
    health_parser.add_argument('--generate-report', action='store_true', help='Generate detailed health report')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Run database backups')
    backup_parser.add_argument('--cleanup', action='store_true', help='Clean up old backups after backup')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Start continuous monitoring')
    monitor_parser.add_argument('--metrics-port', type=int, default=8000, help='Prometheus metrics port')
    
    # Optimize command
    optimize_parser = subparsers.add_parser('optimize', help='Run performance optimization')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test database connections')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Get system status')
    
    return parser


def main():
    """Main function with CLI interface"""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    # Setup logging with specified level
    global logger
    logger = setup_logging(args.log_level)
    
    try:
        automation = DatabaseAutomation(args.config)
        
        # Start Prometheus metrics server if monitoring
        if args.command == 'monitor':
            start_http_server(args.metrics_port)
            logger.info(f"Prometheus metrics server started on port {args.metrics_port}")
        
        # Determine target databases (only enabled ones if no specific database specified)
        if args.database:
            target_databases = [args.database]
        else:
            target_databases = automation.get_enabled_databases()
        
        if args.command == 'health':
            logger.info("Starting health checks...")
            for db_name in target_databases:
                logger.info(f"Health check for {db_name}")
                health = automation.monitor_database_health(db_name)
                print(f"\\n{db_name} Health Status: {health.get('status', 'unknown')}")
                
                if args.generate_report:
                    report = automation.generate_health_report(db_name)
                    print(f"Detailed report generated for {db_name}")
                    
        elif args.command == 'backup':
            logger.info("Starting backup operations...")
            for db_name in target_databases:
                logger.info(f"Backing up {db_name}")
                result = automation.automated_backup(db_name)
                print(f"\\n{db_name} Backup: {result.get('status', 'unknown')}")
                if result.get('status') == 'success':
                    print(f"  File: {result.get('backup_file')}")
                    print(f"  Size: {result.get('file_size_mb', 0)} MB")
                    
            if args.cleanup:
                logger.info("Cleaning up old backups...")
                cleanup_result = automation.cleanup_old_backups()
                print(f"\\nBackup cleanup: {cleanup_result.get('status')}")
                print(f"Files deleted: {cleanup_result.get('files_deleted', 0)}")
                print(f"Space freed: {cleanup_result.get('space_freed_mb', 0)} MB")
                
        elif args.command == 'optimize':
            logger.info("Starting optimization...")
            for db_name in target_databases:
                logger.info(f"Optimizing {db_name}")
                result = automation.performance_optimization(db_name)
                print(f"\\n{db_name} Optimization: {result.get('status', 'unknown')}")
                if 'optimizations' in result:
                    for opt in result['optimizations']:
                        print(f"  - {opt}")
                        
        elif args.command == 'test':
            logger.info("Testing database connections...")
            for db_name in target_databases:
                try:
                    with automation.get_connection(db_name) as conn:
                        print(f"✓ {db_name}: Connection successful")
                except Exception as e:
                    print(f"✗ {db_name}: Connection failed - {e}")
                    
        elif args.command == 'status':
            logger.info("Getting system status...")
            status = automation.get_status()
            print(f"\\n=== Database Automation Suite Status ===")
            print(f"Uptime: {status['uptime_seconds']:.0f} seconds")
            print(f"Version: {status['system']['version']}")
            print(f"Config: {status['system']['config_file']}")
            print(f"\\nDatabase Status:")
            for db_name, db_status in status['databases'].items():
                print(f"  {db_name} ({db_status['type']}): {db_status['status']}")
                if 'error' in db_status:
                    print(f"    Error: {db_status['error']}")
                    
        elif args.command == 'monitor':
            logger.info("Starting continuous monitoring...")
            automation.schedule_automated_tasks()
            automation.start_monitoring()
            
        else:
            # Default behavior - show status
            print("=== Database Automation Suite ===")
            print(f"Configuration: {args.config}")
            print(f"Configured databases: {', '.join(automation.config['databases'].keys())}")
            print("\\nUse --help to see available commands")
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)
    finally:
        if 'automation' in locals():
            automation.close_all_connections()
            logger.info("Database automation suite shutdown complete")


if __name__ == "__main__":
    main()