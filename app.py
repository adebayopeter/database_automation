#!/usr/bin/env python3
"""
PostgreSQL Database Automation Suite
A comprehensive automation framework for PostgreSQL database management
Author: Interview Candidate
Date: July 2025
"""

import psycopg2
import pymssql
import logging
import yaml
import json
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import schedule
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('db_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration class"""
    host: str
    port: int
    database: str
    username: str
    password: str
    db_type: str  # 'postgresql' or 'sqlserver'


class DatabaseAutomation:
    """Main database automation class"""

    def __init__(self, config_file: str = 'db_config.yaml'):
        self.config = self._load_config(config_file)
        self.connections = {}
        self.monitoring_metrics = {}

    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_file, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logger.error(f"Configuration file {config_file} not found")
            return self._create_default_config()

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

    def get_connection(self, db_name: str):
        """Get database connection"""
        if db_name not in self.connections:
            db_config = self.config['databases'][db_name]

            if db_config['db_type'] == 'postgresql':
                conn = psycopg2.connect(
                    host=db_config['host'],
                    port=db_config['port'],
                    database=db_config['database'],
                    user=db_config['username'],
                    password=db_config['password']
                )
            elif db_config['db_type'] == 'sqlserver':
                conn = pymssql.connect(
                    server=db_config['host'],
                    port=db_config['port'],
                    database=db_config['database'],
                    user=db_config['username'],
                    password=db_config['password']
                )

            self.connections[db_name] = conn

        return self.connections[db_name]

    def execute_query(self, db_name: str, query: str, params: tuple = None) -> List[Dict]:
        """Execute query and return results"""
        try:
            conn = self.get_connection(db_name)
            cursor = conn.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if query.strip().upper().startswith('SELECT'):
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return results
            else:
                conn.commit()
                return [{'affected_rows': cursor.rowcount}]

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def monitor_database_health(self, db_name: str) -> Dict[str, Any]:
        """Monitor database health metrics"""
        try:
            db_config = self.config['databases'][db_name]

            if db_config['db_type'] == 'postgresql':
                return self._monitor_postgres_health(db_name)
            elif db_config['db_type'] == 'sqlserver':
                return self._monitor_sqlserver_health(db_name)

        except Exception as e:
            logger.error(f"Health monitoring failed for {db_name}: {e}")
            return {'status': 'error', 'message': str(e)}

    def _monitor_postgres_health(self, db_name: str) -> Dict[str, Any]:
        """Monitor PostgreSQL specific health metrics"""
        queries = {
            'connection_count': """
                SELECT count(*) as connections 
                FROM pg_stat_activity 
                WHERE state = 'active'
            """,
            'database_size': """
                SELECT pg_size_pretty(pg_database_size(current_database())) as size
            """,
            'long_running_queries': """
                SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
                FROM pg_stat_activity 
                WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes'
                AND state = 'active'
            """,
            'table_stats': """
                SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del
                FROM pg_stat_user_tables
                ORDER BY n_tup_ins DESC
                LIMIT 10
            """,
            'index_usage': """
                SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
                FROM pg_stat_user_indexes
                WHERE idx_scan > 0
                ORDER BY idx_scan DESC
                LIMIT 10
            """
        }

        metrics = {}
        for metric_name, query in queries.items():
            try:
                result = self.execute_query(db_name, query)
                metrics[metric_name] = result
            except Exception as e:
                metrics[metric_name] = f"Error: {e}"

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

        metrics = {}
        for metric_name, query in queries.items():
            try:
                result = self.execute_query(db_name, query)
                metrics[metric_name] = result
            except Exception as e:
                metrics[metric_name] = f"Error: {e}"

        return metrics

    def automated_backup(self, db_name: str) -> Dict[str, Any]:
        """Perform automated database backup"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = self.config['backup']['backup_path']

            db_config = self.config['databases'][db_name]

            if db_config['db_type'] == 'postgresql':
                return self._postgres_backup(db_name, timestamp, backup_path)
            elif db_config['db_type'] == 'sqlserver':
                return self._sqlserver_backup(db_name, timestamp, backup_path)

        except Exception as e:
            logger.error(f"Backup failed for {db_name}: {e}")
            return {'status': 'failed', 'message': str(e)}

    def _postgres_backup(self, db_name: str, timestamp: str, backup_path: str) -> Dict[str, Any]:
        """PostgreSQL backup using pg_dump"""
        db_config = self.config['databases'][db_name]
        filename = f"{db_name}_{timestamp}.sql"
        full_path = os.path.join(backup_path, filename)

        # Construct pg_dump command
        cmd = f"""
        PGPASSWORD={db_config['password']} pg_dump \
        -h {db_config['host']} \
        -p {db_config['port']} \
        -U {db_config['username']} \
        -d {db_config['database']} \
        -f {full_path} \
        --verbose
        """

        exit_code = os.system(cmd)

        if exit_code == 0:
            file_size = os.path.getsize(full_path)
            return {
                'status': 'success',
                'backup_file': full_path,
                'file_size_mb': round(file_size / (1024 * 1024), 2),
                'timestamp': timestamp
            }
        else:
            return {'status': 'failed', 'message': f'pg_dump failed with exit code {exit_code}'}

    def _sqlserver_backup(self, db_name: str, timestamp: str, backup_path: str) -> Dict[str, Any]:
        """SQL Server backup using T-SQL"""
        filename = f"{db_name}_{timestamp}.bak"
        full_path = os.path.join(backup_path, filename)

        backup_query = f"""
        BACKUP DATABASE [{self.config['databases'][db_name]['database']}]
        TO DISK = '{full_path}'
        WITH FORMAT, INIT, SKIP, NOREWIND, NOUNLOAD, STATS = 10
        """

        try:
            self.execute_query(db_name, backup_query)
            file_size = os.path.getsize(full_path)
            return {
                'status': 'success',
                'backup_file': full_path,
                'file_size_mb': round(file_size / (1024 * 1024), 2),
                'timestamp': timestamp
            }
        except Exception as e:
            return {'status': 'failed', 'message': str(e)}

    def cleanup_old_backups(self, retention_days: int = None) -> Dict[str, Any]:
        """Clean up old backup files"""
        if retention_days is None:
            retention_days = self.config['backup']['retention_days']

        backup_path = self.config['backup']['backup_path']
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        deleted_files = []
        total_size_freed = 0

        try:
            for filename in os.listdir(backup_path):
                file_path = os.path.join(backup_path, filename)
                if os.path.isfile(file_path):
                    file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_modified < cutoff_date:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        deleted_files.append(filename)
                        total_size_freed += file_size

            return {
                'status': 'success',
                'deleted_files': deleted_files,
                'files_deleted': len(deleted_files),
                'space_freed_mb': round(total_size_freed / (1024 * 1024), 2)
            }

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
            self.execute_query(db_name, analyze_query)
            optimizations.append("Statistics updated with ANALYZE")

            self.execute_query(db_name, vacuum_query)
            optimizations.append("Tables vacuumed and analyzed")

            # Check for missing indexes
            missing_indexes_query = """
            SELECT schemaname, tablename, attname, n_distinct, correlation
            FROM pg_stats
            WHERE n_distinct > 100 AND correlation < 0.1
            ORDER BY n_distinct DESC
            LIMIT 5;
            """

            missing_indexes = self.execute_query(db_name, missing_indexes_query)
            if missing_indexes:
                optimizations.append(f"Found {len(missing_indexes)} potential index candidates")

            return {
                'status': 'success',
                'optimizations': optimizations,
                'missing_indexes': missing_indexes
            }

        except Exception as e:
            return {'status': 'failed', 'message': str(e)}

    def _sqlserver_optimization(self, db_name: str) -> Dict[str, Any]:
        """SQL Server performance optimization"""
        optimizations = []

        try:
            # Update statistics
            update_stats_query = "EXEC sp_updatestats;"
            self.execute_query(db_name, update_stats_query)
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

            fragmented_indexes = self.execute_query(db_name, fragmentation_query)
            if fragmented_indexes:
                optimizations.append(f"Found {len(fragmented_indexes)} fragmented indexes")

            return {
                'status': 'success',
                'optimizations': optimizations,
                'fragmented_indexes': fragmented_indexes
            }

        except Exception as e:
            return {'status': 'failed', 'message': str(e)}

    def generate_health_report(self, db_name: str) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        report = {
            'database': db_name,
            'timestamp': datetime.now().isoformat(),
            'health_metrics': self.monitor_database_health(db_name),
            'optimization_report': self.performance_optimization(db_name)
        }

        # Save report to file
        report_filename = f"health_report_{db_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Health report generated: {report_filename}")
        return report

    def schedule_automated_tasks(self):
        """Schedule automated maintenance tasks"""
        # Schedule daily backups
        schedule.every().day.at("02:00").do(self.run_daily_maintenance)

        # Schedule hourly health checks
        schedule.every().hour.do(self.run_health_checks)

        # Schedule weekly optimization
        schedule.every().sunday.at("01:00").do(self.run_weekly_optimization)

        logger.info("Automated tasks scheduled")

    def run_daily_maintenance(self):
        """Run daily maintenance tasks"""
        logger.info("Starting daily maintenance")

        for db_name in self.config['databases'].keys():
            # Backup
            backup_result = self.automated_backup(db_name)
            logger.info(f"Backup for {db_name}: {backup_result['status']}")

        # Cleanup old backups
        cleanup_result = self.cleanup_old_backups()
        logger.info(f"Backup cleanup: {cleanup_result['status']}")

    def run_health_checks(self):
        """Run health checks for all databases"""
        for db_name in self.config['databases'].keys():
            health_metrics = self.monitor_database_health(db_name)
            self.monitoring_metrics[db_name] = health_metrics
            logger.info(f"Health check completed for {db_name}")

    def run_weekly_optimization(self):
        """Run weekly optimization tasks"""
        logger.info("Starting weekly optimization")

        for db_name in self.config['databases'].keys():
            optimization_result = self.performance_optimization(db_name)
            logger.info(f"Optimization for {db_name}: {optimization_result['status']}")

    def start_monitoring(self):
        """Start the monitoring loop"""
        logger.info("Starting database automation monitoring")

        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    def close_connections(self):
        """Close all database connections"""
        for db_name, conn in self.connections.items():
            try:
                conn.close()
                logger.info(f"Connection closed for {db_name}")
            except Exception as e:
                logger.error(f"Error closing connection for {db_name}: {e}")


def main():
    """Main function to demonstrate the automation suite"""
    automation = DatabaseAutomation()

    try:
        # Example usage
        print("=== PostgreSQL Database Automation Suite ===")

        # Test connection and health monitoring
        for db_name in automation.config['databases'].keys():
            print(f"\nTesting {db_name}...")

            # Health check
            health = automation.monitor_database_health(db_name)
            print(f"Health Status: {health}")

            # Generate report
            report = automation.generate_health_report(db_name)
            print(f"Report generated for {db_name}")

        # Schedule tasks (uncomment to run continuous monitoring)
        # automation.schedule_automated_tasks()
        # automation.start_monitoring()

    except KeyboardInterrupt:
        print("\nShutting down automation suite...")
    finally:
        automation.close_connections()


if __name__ == "__main__":
    main()
