#!/usr/bin/env python3
"""
Integration tests for PostgreSQL database operations
"""

import unittest
import os
import sys
import time
from unittest.mock import patch
import tempfile
import yaml

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database_automation import DatabaseAutomation


class TestPostgreSQLIntegration(unittest.TestCase):
    """Integration tests for PostgreSQL operations"""

    @classmethod
    def setUpClass(cls):
        """Set up test class with PostgreSQL connection"""
        cls.test_config = {
            'databases': {
                'test_postgres': {
                    'host': os.getenv('POSTGRES_HOST', 'localhost'),
                    'port': int(os.getenv('POSTGRES_PORT', 5432)),
                    'database': os.getenv('POSTGRES_DB', 'test_automation'),
                    'username': os.getenv('POSTGRES_USER', 'test_user'),
                    'password': os.getenv('POSTGRES_PASSWORD', 'test_password'),
                    'db_type': 'postgresql',
                    'connection_pool_size': 5
                }
            },
            'monitoring': {
                'check_interval': 30,
                'alert_thresholds': {
                    'connection_count': 50,
                    'cpu_usage': 80
                },
                'email_alerts': {'enabled': False}
            },
            'backup': {
                'schedule': '0 2 * * *',
                'retention_days': 1,
                'backup_path': tempfile.mkdtemp(),
                'compression': True,
                'parallel_jobs': 1
            }
        }
        
        # Create temporary config file
        cls.temp_dir = tempfile.mkdtemp()
        cls.config_file = os.path.join(cls.temp_dir, 'test_config.yaml')
        
        with open(cls.config_file, 'w') as f:
            yaml.dump(cls.test_config, f)
        
        # Initialize automation instance
        try:
            cls.automation = DatabaseAutomation(cls.config_file)
            
            # Test connection
            with cls.automation.get_connection('test_postgres') as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1')
                result = cursor.fetchone()
                assert result[0] == 1, "Database connection test failed"
                
        except Exception as e:
            raise unittest.SkipTest(f"PostgreSQL not available for integration tests: {e}")

    @classmethod
    def tearDownClass(cls):
        """Clean up test class"""
        import shutil
        if hasattr(cls, 'automation'):
            cls.automation.close_all_connections()
        if hasattr(cls, 'temp_dir'):
            shutil.rmtree(cls.temp_dir, ignore_errors=True)
        if hasattr(cls, 'test_config'):
            backup_path = cls.test_config['backup']['backup_path']
            if os.path.exists(backup_path):
                shutil.rmtree(backup_path, ignore_errors=True)

    def test_database_connection(self):
        """Test basic database connection"""
        with self.automation.get_connection('test_postgres') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT version()')
            result = cursor.fetchone()
            self.assertIsNotNone(result)
            self.assertIn('PostgreSQL', result[0])

    def test_health_monitoring(self):
        """Test PostgreSQL health monitoring"""
        health_data = self.automation.monitor_database_health('test_postgres')
        
        self.assertIn('status', health_data)
        self.assertIn(health_data['status'], ['healthy', 'degraded'])
        self.assertIn('timestamp', health_data)
        self.assertIn('connection_count', health_data)
        self.assertIn('database_size', health_data)

    def test_query_execution(self):
        """Test query execution functionality"""
        # Test SELECT query
        result = self.automation.execute_query(
            'test_postgres', 
            'SELECT count(*) as user_count FROM automation.test_users',
            query_type='test'
        )
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIn('user_count', result[0])
        self.assertGreaterEqual(result[0]['user_count'], 0)

    def test_query_execution_with_parameters(self):
        """Test parameterized query execution"""
        result = self.automation.execute_query(
            'test_postgres',
            'SELECT username FROM automation.test_users WHERE id = %s',
            params=(1,),
            query_type='test'
        )
        
        self.assertIsInstance(result, list)
        if len(result) > 0:
            self.assertIn('username', result[0])

    def test_table_statistics_collection(self):
        """Test collection of table statistics"""
        health_data = self.automation._monitor_postgres_health('test_postgres')
        
        self.assertIn('table_stats', health_data)
        table_stats = health_data['table_stats']
        
        if isinstance(table_stats, list) and len(table_stats) > 0:
            stat = table_stats[0]
            expected_keys = ['schemaname', 'tablename', 'n_tup_ins', 'n_tup_upd', 'n_tup_del']
            for key in expected_keys:
                self.assertIn(key, stat)

    def test_index_usage_monitoring(self):
        """Test index usage monitoring"""
        health_data = self.automation._monitor_postgres_health('test_postgres')
        
        self.assertIn('index_usage', health_data)
        index_usage = health_data['index_usage']
        
        self.assertIsInstance(index_usage, list)
        # Index usage data may be empty in test environment

    def test_long_running_queries_detection(self):
        """Test long-running queries detection"""
        health_data = self.automation._monitor_postgres_health('test_postgres')
        
        self.assertIn('long_running_queries', health_data)
        long_queries = health_data['long_running_queries']
        
        self.assertIsInstance(long_queries, list)

    def test_replication_status_monitoring(self):
        """Test replication status monitoring"""
        health_data = self.automation._monitor_postgres_health('test_postgres')
        
        self.assertIn('replication_status', health_data)
        replication_status = health_data['replication_status']
        
        self.assertIsInstance(replication_status, list)
        # Replication may not be configured in test environment

    def test_performance_optimization(self):
        """Test PostgreSQL performance optimization"""
        optimization_result = self.automation._postgres_optimization('test_postgres')
        
        self.assertIn('status', optimization_result)
        self.assertEqual(optimization_result['status'], 'success')
        self.assertIn('optimizations', optimization_result)
        self.assertIsInstance(optimization_result['optimizations'], list)
        
        # Should include ANALYZE and VACUUM operations
        optimizations = optimization_result['optimizations']
        self.assertGreater(len(optimizations), 0)

    def test_backup_creation(self):
        """Test PostgreSQL backup creation"""
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        backup_path = self.test_config['backup']['backup_path']
        
        result = self.automation._postgres_backup('test_postgres', timestamp, backup_path)
        
        self.assertEqual(result['status'], 'success')
        self.assertIn('backup_file', result)
        self.assertIn('file_size_mb', result)
        self.assertIn('timestamp', result)
        
        # Verify backup file exists
        backup_file = result['backup_file']
        self.assertTrue(os.path.exists(backup_file))
        self.assertGreater(os.path.getsize(backup_file), 0)

    def test_backup_cleanup(self):
        """Test backup cleanup functionality"""
        # Create some test backup files
        backup_path = self.test_config['backup']['backup_path']
        
        # Create old backup file
        old_file = os.path.join(backup_path, 'old_backup_20220101_120000.sql')
        with open(old_file, 'w') as f:
            f.write('-- Old backup file')
        
        # Set file time to be old
        old_time = time.time() - (10 * 24 * 60 * 60)  # 10 days ago
        os.utime(old_file, (old_time, old_time))
        
        # Create recent backup file
        recent_file = os.path.join(backup_path, 'recent_backup_20240701_120000.sql')
        with open(recent_file, 'w') as f:
            f.write('-- Recent backup file')
        
        # Run cleanup
        cleanup_result = self.automation.cleanup_old_backups(retention_days=7)
        
        self.assertIn('status', cleanup_result)
        self.assertIn(cleanup_result['status'], ['success', 'partial_success'])
        self.assertIn('files_deleted', cleanup_result)
        self.assertIn('space_freed_mb', cleanup_result)
        
        # Verify old file was deleted and recent file remains
        self.assertFalse(os.path.exists(old_file))
        self.assertTrue(os.path.exists(recent_file))

    def test_health_report_generation(self):
        """Test comprehensive health report generation"""
        report = self.automation.generate_health_report('test_postgres')
        
        self.assertIn('database', report)
        self.assertEqual(report['database'], 'test_postgres')
        self.assertIn('timestamp', report)
        self.assertIn('report_version', report)
        self.assertIn('database_config', report)
        self.assertIn('health_metrics', report)
        self.assertIn('optimization_report', report)
        self.assertIn('system_info', report)
        
        # Verify database config
        db_config = report['database_config']
        self.assertEqual(db_config['type'], 'postgresql')
        self.assertIn('host', db_config)
        self.assertIn('port', db_config)

    def test_connection_pool_management(self):
        """Test connection pool functionality"""
        # Test multiple concurrent connections
        connections = []
        
        try:
            for i in range(3):
                conn_context = self.automation.get_connection('test_postgres')
                conn = conn_context.__enter__()
                connections.append((conn_context, conn))
                
                # Test that each connection works
                cursor = conn.cursor()
                cursor.execute('SELECT %s as test_id', (i,))
                result = cursor.fetchone()
                self.assertEqual(result[0], i)
                
        finally:
            # Clean up connections
            for conn_context, conn in connections:
                try:
                    conn_context.__exit__(None, None, None)
                except:
                    pass

    def test_error_handling(self):
        """Test error handling for invalid queries"""
        with self.assertRaises(Exception):
            self.automation.execute_query(
                'test_postgres',
                'SELECT * FROM nonexistent_table',
                query_type='test'
            )

    def test_transaction_handling(self):
        """Test transaction handling"""
        with self.automation.get_connection('test_postgres') as conn:
            cursor = conn.cursor()
            
            try:
                # Start transaction
                cursor.execute('BEGIN')
                
                # Insert test data
                cursor.execute(
                    "INSERT INTO automation.test_users (username, email) VALUES (%s, %s)",
                    ('test_integration_user', 'integration@test.com')
                )
                
                # Rollback transaction
                cursor.execute('ROLLBACK')
                
                # Verify data was not committed
                cursor.execute(
                    "SELECT count(*) FROM automation.test_users WHERE username = %s",
                    ('test_integration_user',)
                )
                count = cursor.fetchone()[0]
                self.assertEqual(count, 0)
                
            except Exception as e:
                cursor.execute('ROLLBACK')
                raise

    def test_concurrent_operations(self):
        """Test concurrent database operations"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def health_check_worker():
            try:
                health_data = self.automation.monitor_database_health('test_postgres')
                results.put(('health', health_data['status']))
            except Exception as e:
                results.put(('health', f'error: {e}'))
        
        def query_worker():
            try:
                result = self.automation.execute_query(
                    'test_postgres',
                    'SELECT count(*) FROM automation.test_users'
                )
                results.put(('query', result[0]))
            except Exception as e:
                results.put(('query', f'error: {e}'))
        
        # Start concurrent operations
        threads = [
            threading.Thread(target=health_check_worker),
            threading.Thread(target=query_worker)
        ]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join(timeout=10)
        
        # Check results
        health_result = None
        query_result = None
        
        while not results.empty():
            operation, result = results.get()
            if operation == 'health':
                health_result = result
            elif operation == 'query':
                query_result = result
        
        self.assertIsNotNone(health_result)
        self.assertIsNotNone(query_result)
        self.assertIn(health_result, ['healthy', 'degraded'])


if __name__ == '__main__':
    # Check if PostgreSQL is available
    import psycopg2
    
    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database=os.getenv('POSTGRES_DB', 'test_automation'),
            user=os.getenv('POSTGRES_USER', 'test_user'),
            password=os.getenv('POSTGRES_PASSWORD', 'test_password')
        )
        conn.close()
        
        # Run tests if PostgreSQL is available
        unittest.main(verbosity=2)
        
    except Exception as e:
        print(f"Skipping PostgreSQL integration tests: {e}")
        print("To run these tests, ensure PostgreSQL is running and accessible with the configured credentials.")