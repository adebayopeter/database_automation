#!/usr/bin/env python3
"""
Unit tests for Database Automation Suite
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import json
import os
import tempfile
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the parent directory to the path so we can import our module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_automation import DatabaseAutomation, AlertConfig, BackupConfig
import psycopg2.pool
import pymssql


class TestDatabaseAutomation(unittest.TestCase):
    """Test cases for DatabaseAutomation class"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_config = {
            'databases': {
                'test_postgres': {
                    'host': 'localhost',
                    'port': 5432,
                    'database': 'test_db',
                    'username': 'test_user',
                    'password': 'test_pass',
                    'db_type': 'postgresql',
                    'connection_pool_size': 5
                },
                'test_sqlserver': {
                    'host': 'localhost',
                    'port': 1433,
                    'database': 'test_db',
                    'username': 'test_user',
                    'password': 'test_pass',
                    'db_type': 'sqlserver',
                    'connection_pool_size': 5
                }
            },
            'monitoring': {
                'check_interval': 300,
                'alert_thresholds': {
                    'connection_count': 100,
                    'cpu_usage': 80
                },
                'email_alerts': {
                    'enabled': True,
                    'smtp_server': 'smtp.test.com',
                    'smtp_port': 587,
                    'from_email': 'test@test.com',
                    'alert_recipients': ['admin@test.com']
                }
            },
            'backup': {
                'schedule': '0 2 * * *',
                'retention_days': 7,
                'backup_path': '/tmp/test_backups',
                'compression': True,
                'parallel_jobs': 2
            }
        }
        
        # Create temporary config file
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.yaml')
        
        # Mock the _initialize_connection_pools to avoid actual database connections
        with patch.object(DatabaseAutomation, '_initialize_connection_pools'):
            self.automation = DatabaseAutomation.__new__(DatabaseAutomation)
            self.automation.config_file = self.config_file
            self.automation.config = self.test_config
            self.automation.connection_pools = {}
            self.automation.monitoring_metrics = {}
            self.automation.alert_config = AlertConfig(
                enabled=True,
                smtp_server='smtp.test.com',
                smtp_port=587,
                from_email='test@test.com',
                recipients=['admin@test.com']
            )
            self.automation.backup_config = BackupConfig(
                schedule='0 2 * * *',
                retention_days=7,
                backup_path='/tmp/test_backups',
                compression=True,
                parallel_jobs=2
            )
            self.automation.shutdown_event = Mock()
            self.automation.start_time = 1234567890

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_alert_config_creation(self):
        """Test AlertConfig dataclass creation"""
        alert_config = AlertConfig(
            enabled=True,
            smtp_server='smtp.example.com',
            smtp_port=587,
            from_email='test@example.com',
            recipients=['admin@example.com']
        )
        
        self.assertTrue(alert_config.enabled)
        self.assertEqual(alert_config.smtp_server, 'smtp.example.com')
        self.assertEqual(alert_config.smtp_port, 587)

    def test_backup_config_creation(self):
        """Test BackupConfig dataclass creation"""
        backup_config = BackupConfig(
            schedule='0 2 * * *',
            retention_days=14,
            backup_path='/tmp/backups',
            compression=True,
            parallel_jobs=3
        )
        
        self.assertEqual(backup_config.retention_days, 14)
        self.assertTrue(backup_config.compression)
        self.assertEqual(backup_config.parallel_jobs, 3)

    @patch('database_automation.yaml.safe_load')
    @patch('builtins.open')
    @patch('database_automation.Path.exists')
    def test_load_config_success(self, mock_exists, mock_open, mock_yaml_load):
        """Test successful configuration loading"""
        mock_exists.return_value = True
        mock_yaml_load.return_value = self.test_config
        mock_open.return_value.__enter__.return_value.read.return_value = 'test config'
        
        with patch.object(DatabaseAutomation, '_initialize_connection_pools'):
            automation = DatabaseAutomation.__new__(DatabaseAutomation)
            config = automation._load_config('test_config.yaml')
        
        self.assertEqual(config, self.test_config)
        mock_open.assert_called_once()

    @patch('database_automation.Path.exists')
    def test_load_config_file_not_found(self, mock_exists):
        """Test configuration loading when file doesn't exist"""
        mock_exists.return_value = False
        
        with patch.object(DatabaseAutomation, '_initialize_connection_pools'):
            automation = DatabaseAutomation.__new__(DatabaseAutomation)
            with patch.object(automation, '_create_default_config') as mock_default:
                mock_default.return_value = self.test_config
                config = automation._load_config('nonexistent.yaml')
        
        mock_default.assert_called_once()
        self.assertEqual(config, self.test_config)

    def test_create_default_config(self):
        """Test default configuration creation"""
        with patch.object(DatabaseAutomation, '_initialize_connection_pools'):
            automation = DatabaseAutomation.__new__(DatabaseAutomation)
            config = automation._create_default_config()
        
        self.assertIn('databases', config)
        self.assertIn('monitoring', config)
        self.assertIn('backup', config)
        self.assertIn('postgres_primary', config['databases'])

    @patch('database_automation.psycopg2.pool.ThreadedConnectionPool')
    def test_initialize_connection_pools_postgres(self, mock_pool):
        """Test PostgreSQL connection pool initialization"""
        mock_pool_instance = Mock()
        mock_pool.return_value = mock_pool_instance
        
        with patch.object(DatabaseAutomation, '_setup_signal_handlers'):
            automation = DatabaseAutomation.__new__(DatabaseAutomation)
            automation.config = self.test_config
            automation.connection_pools = {}
            automation._initialize_connection_pools()
        
        mock_pool.assert_called()
        self.assertIn('test_postgres', automation.connection_pools)

    def test_initialize_connection_pools_sqlserver(self):
        """Test SQL Server connection pool initialization"""
        with patch.object(DatabaseAutomation, '_setup_signal_handlers'):
            automation = DatabaseAutomation.__new__(DatabaseAutomation)
            automation.config = self.test_config
            automation.connection_pools = {}
            automation._initialize_connection_pools()
        
        self.assertIn('test_sqlserver', automation.connection_pools)
        self.assertEqual(automation.connection_pools['test_sqlserver']['type'], 'sqlserver')

    @patch('database_automation.smtplib.SMTP')
    def test_send_alert_success(self, mock_smtp):
        """Test successful email alert sending"""
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        self.automation.send_alert("Test Alert", "Test message", "INFO")
        
        mock_smtp.assert_called_once()
        mock_server.starttls.assert_called_once()
        mock_server.send_message.assert_called_once()

    @patch('database_automation.smtplib.SMTP')
    def test_send_alert_disabled(self, mock_smtp):
        """Test email alert when disabled"""
        self.automation.alert_config.enabled = False
        
        self.automation.send_alert("Test Alert", "Test message", "INFO")
        
        mock_smtp.assert_not_called()

    @patch('database_automation.smtplib.SMTP')
    def test_send_alert_failure(self, mock_smtp):
        """Test email alert failure handling"""
        mock_smtp.side_effect = Exception("SMTP Error")
        
        # Should not raise exception, just log error
        self.automation.send_alert("Test Alert", "Test message", "INFO")
        
        mock_smtp.assert_called_once()

    def test_execute_query_mock_connection(self):
        """Test query execution with mocked connection"""
        # Mock the get_connection context manager
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.description = [('id',), ('name',)]
        mock_cursor.fetchall.return_value = [(1, 'test'), (2, 'test2')]
        
        with patch.object(self.automation, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_conn
            
            result = self.automation.execute_query('test_postgres', 'SELECT id, name FROM test_table')
        
        expected = [{'id': 1, 'name': 'test'}, {'id': 2, 'name': 'test2'}]
        self.assertEqual(result, expected)

    def test_execute_query_non_select(self):
        """Test non-SELECT query execution"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 5
        
        with patch.object(self.automation, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_conn
            
            result = self.automation.execute_query('test_postgres', 'UPDATE test_table SET name = ?', ('new_name',))
        
        expected = [{'affected_rows': 5}]
        self.assertEqual(result, expected)

    def test_monitor_postgres_health(self):
        """Test PostgreSQL health monitoring"""
        mock_results = {
            'connection_count': [{'connections': 10}],
            'database_size': [{'size': '100 MB', 'size_bytes': 104857600}],
            'long_running_queries': []
        }
        
        with patch.object(self.automation, 'execute_query') as mock_execute:
            mock_execute.side_effect = lambda db, query, query_type=None: mock_results.get(
                next((k for k in mock_results.keys() if k in query), 'default'), 
                []
            )
            
            health_data = self.automation._monitor_postgres_health('test_postgres')
        
        self.assertEqual(health_data['status'], 'healthy')
        self.assertIn('timestamp', health_data)
        self.assertIn('connection_count', health_data)

    def test_monitor_sqlserver_health(self):
        """Test SQL Server health monitoring"""
        mock_results = {
            'connection_count': [{'connections': 15}],
            'database_size': [{'database_name': 'test_db', 'size_mb': 200}],
            'wait_stats': []
        }
        
        with patch.object(self.automation, 'execute_query') as mock_execute:
            mock_execute.side_effect = lambda db, query, query_type=None: mock_results.get(
                next((k for k in mock_results.keys() if k in query), 'default'), 
                []
            )
            
            health_data = self.automation._monitor_sqlserver_health('test_sqlserver')
        
        self.assertEqual(health_data['status'], 'healthy')
        self.assertIn('timestamp', health_data)
        self.assertIn('connection_count', health_data)

    @patch('database_automation.subprocess.run')
    @patch('database_automation.os.path.exists')
    @patch('database_automation.os.path.getsize')
    @patch('database_automation.Path.mkdir')
    def test_postgres_backup_success(self, mock_mkdir, mock_getsize, mock_exists, mock_subprocess):
        """Test successful PostgreSQL backup"""
        mock_subprocess.return_value.returncode = 0
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024  # 1 MB
        
        result = self.automation._postgres_backup('test_postgres', '20230701_120000', '/tmp/backups')
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['file_size_mb'], 1.0)
        self.assertIn('backup_file', result)

    @patch('database_automation.subprocess.run')
    def test_postgres_backup_failure(self, mock_subprocess):
        """Test PostgreSQL backup failure"""
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = "pg_dump: error"
        
        result = self.automation._postgres_backup('test_postgres', '20230701_120000', '/tmp/backups')
        
        self.assertEqual(result['status'], 'failed')
        self.assertIn('pg_dump: error', result['message'])

    @patch('database_automation.os.path.exists')
    @patch('database_automation.os.path.getsize')
    def test_sqlserver_backup_success(self, mock_getsize, mock_exists):
        """Test successful SQL Server backup"""
        mock_exists.return_value = True
        mock_getsize.return_value = 2 * 1024 * 1024  # 2 MB
        
        with patch.object(self.automation, 'execute_query') as mock_execute:
            mock_execute.return_value = [{'affected_rows': 1}]
            
            result = self.automation._sqlserver_backup('test_sqlserver', '20230701_120000', '/tmp/backups')
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['file_size_mb'], 2.0)

    def test_sqlserver_backup_failure(self):
        """Test SQL Server backup failure"""
        with patch.object(self.automation, 'execute_query') as mock_execute:
            mock_execute.side_effect = Exception("Backup failed")
            
            result = self.automation._sqlserver_backup('test_sqlserver', '20230701_120000', '/tmp/backups')
        
        self.assertEqual(result['status'], 'failed')
        self.assertIn('Backup failed', result['message'])

    @patch('database_automation.os.listdir')
    @patch('database_automation.os.path.exists')
    @patch('database_automation.os.path.isfile')
    @patch('database_automation.os.path.getmtime')
    @patch('database_automation.os.path.getsize')
    @patch('database_automation.os.remove')
    def test_cleanup_old_backups(self, mock_remove, mock_getsize, mock_getmtime, 
                                mock_isfile, mock_exists, mock_listdir):
        """Test cleanup of old backup files"""
        mock_exists.return_value = True
        mock_listdir.return_value = ['old_backup.sql', 'new_backup.sql', 'other_file.txt']
        mock_isfile.return_value = True
        mock_getsize.return_value = 1024 * 1024  # 1 MB
        
        # Mock file times - old file is 10 days old, new file is 1 day old
        old_time = (datetime.now() - timedelta(days=10)).timestamp()
        new_time = (datetime.now() - timedelta(days=1)).timestamp()
        mock_getmtime.side_effect = lambda path: old_time if 'old_backup' in path else new_time
        
        result = self.automation.cleanup_old_backups(retention_days=7)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['files_deleted'], 1)
        mock_remove.assert_called_once()

    @patch('database_automation.os.path.exists')
    def test_cleanup_old_backups_no_path(self, mock_exists):
        """Test cleanup when backup path doesn't exist"""
        mock_exists.return_value = False
        
        result = self.automation.cleanup_old_backups()
        
        self.assertEqual(result['status'], 'warning')
        self.assertIn('does not exist', result['message'])

    def test_postgres_optimization(self):
        """Test PostgreSQL performance optimization"""
        mock_results = [
            [{'affected_rows': 1}],  # ANALYZE
            [{'affected_rows': 1}],  # VACUUM ANALYZE
            [{'schemaname': 'public', 'tablename': 'test', 'attname': 'id', 'n_distinct': 1000, 'correlation': 0.05}]  # Missing indexes
        ]
        
        with patch.object(self.automation, 'execute_query') as mock_execute:
            mock_execute.side_effect = mock_results
            
            result = self.automation._postgres_optimization('test_postgres')
        
        self.assertEqual(result['status'], 'success')
        self.assertIn('optimizations', result)
        self.assertEqual(len(result['optimizations']), 3)

    def test_sqlserver_optimization(self):
        """Test SQL Server performance optimization"""
        mock_results = [
            [{'affected_rows': 1}],  # Update statistics
            [{'table_name': 'test_table', 'index_name': 'test_idx', 'avg_fragmentation_in_percent': 45.5}]  # Fragmentation
        ]
        
        with patch.object(self.automation, 'execute_query') as mock_execute:
            mock_execute.side_effect = mock_results
            
            result = self.automation._sqlserver_optimization('test_sqlserver')
        
        self.assertEqual(result['status'], 'success')
        self.assertIn('optimizations', result)
        self.assertIn('fragmented_indexes', result)

    def test_get_status(self):
        """Test system status reporting"""
        with patch.object(self.automation, 'get_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_get_conn.return_value.__enter__.return_value = mock_conn
            
            status = self.automation.get_status()
        
        self.assertIn('timestamp', status)
        self.assertIn('uptime_seconds', status)
        self.assertIn('databases', status)
        self.assertIn('system', status)
        self.assertEqual(len(status['databases']), 2)

    def test_check_health_alerts(self):
        """Test health alert checking"""
        health_data = {
            'connection_count': [{'connections': 150}],  # Over threshold of 100
            'long_running_queries': [{'pid': 123, 'duration': '10 minutes'}]
        }
        
        with patch.object(self.automation, 'send_alert') as mock_send_alert:
            self.automation._check_health_alerts('test_postgres', health_data)
        
        mock_send_alert.assert_called_once()
        args, kwargs = mock_send_alert.call_args
        self.assertIn('Health Alert', args[0])
        self.assertEqual(kwargs.get('severity', args[2]), 'WARNING')


class TestDatabaseAutomationIntegration(unittest.TestCase):
    """Integration tests for DatabaseAutomation class"""

    def setUp(self):
        """Set up integration test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.yaml')
        
        # Create a test configuration file
        test_config = {
            'databases': {
                'mock_postgres': {
                    'host': 'localhost',
                    'port': 5432,
                    'database': 'test_db',
                    'username': 'test_user',
                    'password': 'test_pass',
                    'db_type': 'postgresql'
                }
            },
            'monitoring': {
                'check_interval': 300,
                'alert_thresholds': {'connection_count': 100},
                'email_alerts': {'enabled': False}
            },
            'backup': {
                'schedule': '0 2 * * *',
                'retention_days': 7,
                'backup_path': self.temp_dir
            }
        }
        
        import yaml
        with open(self.config_file, 'w') as f:
            yaml.dump(test_config, f)

    def tearDown(self):
        """Clean up integration test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('database_automation.psycopg2.pool.ThreadedConnectionPool')
    def test_full_initialization(self, mock_pool):
        """Test full DatabaseAutomation initialization"""
        mock_pool_instance = Mock()
        mock_pool.return_value = mock_pool_instance
        
        with patch('database_automation.signal.signal'):
            automation = DatabaseAutomation(self.config_file)
        
        self.assertIsNotNone(automation.config)
        self.assertIsNotNone(automation.alert_config)
        self.assertIsNotNone(automation.backup_config)
        self.assertEqual(automation.config_file, self.config_file)

    @patch('database_automation.psycopg2.pool.ThreadedConnectionPool')
    @patch('database_automation.Path.mkdir')
    def test_automated_backup_workflow(self, mock_mkdir, mock_pool):
        """Test complete backup workflow"""
        mock_pool_instance = Mock()
        mock_pool.return_value = mock_pool_instance
        
        with patch('database_automation.signal.signal'):
            automation = DatabaseAutomation(self.config_file)
        
        with patch.object(automation, '_postgres_backup') as mock_backup:
            mock_backup.return_value = {
                'status': 'success',
                'backup_file': '/tmp/test_backup.sql',
                'file_size_mb': 10.5
            }
            
            with patch.object(automation, 'send_alert') as mock_alert:
                result = automation.automated_backup('mock_postgres')
        
        self.assertEqual(result['status'], 'success')
        mock_backup.assert_called_once()
        mock_alert.assert_called_once()

    @patch('database_automation.psycopg2.pool.ThreadedConnectionPool')
    def test_health_monitoring_workflow(self, mock_pool):
        """Test complete health monitoring workflow"""
        mock_pool_instance = Mock()
        mock_pool.return_value = mock_pool_instance
        
        with patch('database_automation.signal.signal'):
            automation = DatabaseAutomation(self.config_file)
        
        with patch.object(automation, '_monitor_postgres_health') as mock_health:
            mock_health.return_value = {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
            
            with patch.object(automation, '_check_health_alerts') as mock_alerts:
                result = automation.monitor_database_health('mock_postgres')
        
        self.assertEqual(result['status'], 'healthy')
        mock_health.assert_called_once()
        mock_alerts.assert_called_once()


if __name__ == '__main__':
    unittest.main()