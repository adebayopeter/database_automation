#!/usr/bin/env python3
"""
Unit tests for configuration handling
"""

import unittest
from unittest.mock import Mock, patch, mock_open
import tempfile
import os
import yaml
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_automation import DatabaseAutomation, AlertConfig, BackupConfig


class TestConfiguration(unittest.TestCase):
    """Test cases for configuration handling"""

    def setUp(self):
        """Set up test fixtures"""
        self.sample_config = {
            'databases': {
                'postgres_primary': {
                    'host': 'localhost',
                    'port': 5432,
                    'database': 'test_db',
                    'username': 'postgres',
                    'password': 'password',
                    'db_type': 'postgresql',
                    'connection_pool_size': 10
                },
                'sqlserver_primary': {
                    'host': 'localhost',
                    'port': 1433,
                    'database': 'master',
                    'username': 'sa',
                    'password': 'password',
                    'db_type': 'sqlserver',
                    'connection_pool_size': 5
                }
            },
            'monitoring': {
                'check_interval': 300,
                'alert_thresholds': {
                    'cpu_usage': 80,
                    'memory_usage': 85,
                    'disk_usage': 90,
                    'connection_count': 100
                },
                'email_alerts': {
                    'enabled': True,
                    'smtp_server': 'smtp.example.com',
                    'smtp_port': 587,
                    'from_email': 'db-alerts@example.com',
                    'alert_recipients': ['admin@example.com', 'dba@example.com']
                }
            },
            'backup': {
                'schedule': '0 2 * * *',
                'retention_days': 14,
                'backup_path': '/var/backups/database',
                'compression': True,
                'parallel_jobs': 3
            }
        }

    @patch('database_automation.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('database_automation.yaml.safe_load')
    def test_load_config_success(self, mock_yaml_load, mock_file, mock_exists):
        """Test successful configuration loading"""
        mock_exists.return_value = True
        mock_yaml_load.return_value = self.sample_config
        mock_file.return_value.read.return_value = yaml.dump(self.sample_config)
        
        with patch.object(DatabaseAutomation, '_initialize_connection_pools'):
            automation = DatabaseAutomation.__new__(DatabaseAutomation)
            config = automation._load_config('test_config.yaml')
        
        self.assertEqual(config, self.sample_config)
        mock_file.assert_called_once_with('test_config.yaml', 'r')
        mock_yaml_load.assert_called_once()

    @patch('database_automation.Path.exists')
    def test_load_config_file_not_found(self, mock_exists):
        """Test configuration loading when file doesn't exist"""
        mock_exists.return_value = False
        
        with patch.object(DatabaseAutomation, '_initialize_connection_pools'):
            automation = DatabaseAutomation.__new__(DatabaseAutomation)
            with patch.object(automation, '_create_default_config') as mock_default:
                mock_default.return_value = self.sample_config
                config = automation._load_config('nonexistent.yaml')
        
        mock_default.assert_called_once()
        self.assertEqual(config, self.sample_config)

    @patch('database_automation.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('database_automation.yaml.safe_load')
    def test_load_config_yaml_error(self, mock_yaml_load, mock_file, mock_exists):
        """Test configuration loading with YAML parsing error"""
        mock_exists.return_value = True
        mock_yaml_load.side_effect = yaml.YAMLError("Invalid YAML")
        
        with patch.object(DatabaseAutomation, '_initialize_connection_pools'):
            automation = DatabaseAutomation.__new__(DatabaseAutomation)
            with self.assertRaises(yaml.YAMLError):
                automation._load_config('invalid.yaml')

    @patch('database_automation.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('database_automation.yaml.safe_load')
    def test_load_config_missing_section(self, mock_yaml_load, mock_file, mock_exists):
        """Test configuration validation with missing required section"""
        mock_exists.return_value = True
        incomplete_config = {
            'databases': self.sample_config['databases']
            # Missing 'monitoring' and 'backup' sections
        }
        mock_yaml_load.return_value = incomplete_config
        
        with patch.object(DatabaseAutomation, '_initialize_connection_pools'):
            automation = DatabaseAutomation.__new__(DatabaseAutomation)
            with self.assertRaises(ValueError) as context:
                automation._load_config('incomplete.yaml')
        
        self.assertIn('missing monitoring section', str(context.exception))

    @patch('database_automation.os.path.expandvars')
    @patch('database_automation.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('database_automation.yaml.safe_load')
    def test_load_config_environment_variable_substitution(self, mock_yaml_load, mock_file, mock_exists, mock_expandvars):
        """Test environment variable substitution in configuration"""
        mock_exists.return_value = True
        mock_expandvars.return_value = "expanded_config_content"
        mock_yaml_load.return_value = self.sample_config
        mock_file.return_value.read.return_value = "config_with_${ENV_VAR}"
        
        with patch.object(DatabaseAutomation, '_initialize_connection_pools'):
            automation = DatabaseAutomation.__new__(DatabaseAutomation)
            config = automation._load_config('config_with_envvars.yaml')
        
        mock_expandvars.assert_called_with("config_with_${ENV_VAR}")
        mock_yaml_load.assert_called_with("expanded_config_content")

    def test_create_default_config(self):
        """Test default configuration creation"""
        with patch.object(DatabaseAutomation, '_initialize_connection_pools'):
            automation = DatabaseAutomation.__new__(DatabaseAutomation)
            config = automation._create_default_config()
        
        # Verify all required sections are present
        self.assertIn('databases', config)
        self.assertIn('monitoring', config)
        self.assertIn('backup', config)
        
        # Verify default database configurations
        self.assertIn('postgres_primary', config['databases'])
        self.assertIn('sqlserver_primary', config['databases'])
        
        # Verify default values
        postgres_config = config['databases']['postgres_primary']
        self.assertEqual(postgres_config['db_type'], 'postgresql')
        self.assertEqual(postgres_config['port'], 5432)
        
        sqlserver_config = config['databases']['sqlserver_primary']
        self.assertEqual(sqlserver_config['db_type'], 'sqlserver')
        self.assertEqual(sqlserver_config['port'], 1433)

    def test_load_alert_config(self):
        """Test alert configuration loading"""
        config = {
            'monitoring': {
                'email_alerts': {
                    'enabled': True,
                    'smtp_server': 'smtp.test.com',
                    'smtp_port': 587,
                    'from_email': 'alerts@test.com',
                    'alert_recipients': ['admin@test.com']
                }
            }
        }
        
        with patch.object(DatabaseAutomation, '_initialize_connection_pools'):
            automation = DatabaseAutomation.__new__(DatabaseAutomation)
            automation.config = config
            
            alert_config = automation._load_alert_config()
        
        self.assertTrue(alert_config.enabled)
        self.assertEqual(alert_config.smtp_server, 'smtp.test.com')
        self.assertEqual(alert_config.smtp_port, 587)
        self.assertEqual(alert_config.from_email, 'alerts@test.com')
        self.assertEqual(alert_config.recipients, ['admin@test.com'])

    def test_load_alert_config_defaults(self):
        """Test alert configuration with default values"""
        config = {'monitoring': {}}  # Empty monitoring section
        
        with patch.object(DatabaseAutomation, '_initialize_connection_pools'):
            automation = DatabaseAutomation.__new__(DatabaseAutomation)
            automation.config = config
            
            alert_config = automation._load_alert_config()
        
        self.assertFalse(alert_config.enabled)
        self.assertEqual(alert_config.smtp_server, '')
        self.assertEqual(alert_config.smtp_port, 587)
        self.assertEqual(alert_config.recipients, [])

    @patch('database_automation.os.getenv')
    def test_load_alert_config_with_environment_password(self, mock_getenv):
        """Test alert configuration loading with environment variable password"""
        mock_getenv.return_value = 'env_password'
        config = {
            'monitoring': {
                'email_alerts': {
                    'enabled': True,
                    'smtp_server': 'smtp.test.com'
                }
            }
        }
        
        with patch.object(DatabaseAutomation, '_initialize_connection_pools'):
            automation = DatabaseAutomation.__new__(DatabaseAutomation)
            automation.config = config
            
            alert_config = automation._load_alert_config()
        
        mock_getenv.assert_called_with('SMTP_PASSWORD', '')
        self.assertEqual(alert_config.password, 'env_password')

    def test_load_backup_config(self):
        """Test backup configuration loading"""
        config = {
            'backup': {
                'schedule': '0 3 * * *',
                'retention_days': 30,
                'backup_path': '/custom/backup/path',
                'compression': False,
                'parallel_jobs': 4
            }
        }
        
        with patch.object(DatabaseAutomation, '_initialize_connection_pools'):
            automation = DatabaseAutomation.__new__(DatabaseAutomation)
            automation.config = config
            
            backup_config = automation._load_backup_config()
        
        self.assertEqual(backup_config.schedule, '0 3 * * *')
        self.assertEqual(backup_config.retention_days, 30)
        self.assertEqual(backup_config.backup_path, '/custom/backup/path')
        self.assertFalse(backup_config.compression)
        self.assertEqual(backup_config.parallel_jobs, 4)

    def test_load_backup_config_defaults(self):
        """Test backup configuration with default values"""
        config = {'backup': {}}  # Empty backup section
        
        with patch.object(DatabaseAutomation, '_initialize_connection_pools'):
            automation = DatabaseAutomation.__new__(DatabaseAutomation)
            automation.config = config
            
            backup_config = automation._load_backup_config()
        
        self.assertEqual(backup_config.schedule, '0 2 * * *')
        self.assertEqual(backup_config.retention_days, 7)
        self.assertEqual(backup_config.backup_path, '/var/backups')
        self.assertTrue(backup_config.compression)
        self.assertEqual(backup_config.parallel_jobs, 2)

    def test_alert_config_dataclass(self):
        """Test AlertConfig dataclass functionality"""
        alert_config = AlertConfig(
            enabled=True,
            smtp_server='smtp.example.com',
            smtp_port=465,
            from_email='test@example.com',
            password='secret',
            recipients=['admin@example.com', 'ops@example.com']
        )
        
        self.assertTrue(alert_config.enabled)
        self.assertEqual(alert_config.smtp_server, 'smtp.example.com')
        self.assertEqual(alert_config.smtp_port, 465)
        self.assertEqual(alert_config.from_email, 'test@example.com')
        self.assertEqual(alert_config.password, 'secret')
        self.assertEqual(len(alert_config.recipients), 2)

    def test_backup_config_dataclass(self):
        """Test BackupConfig dataclass functionality"""
        backup_config = BackupConfig(
            schedule='0 1 * * *',
            retention_days=21,
            backup_path='/tmp/backups',
            compression=False,
            parallel_jobs=1
        )
        
        self.assertEqual(backup_config.schedule, '0 1 * * *')
        self.assertEqual(backup_config.retention_days, 21)
        self.assertEqual(backup_config.backup_path, '/tmp/backups')
        self.assertFalse(backup_config.compression)
        self.assertEqual(backup_config.parallel_jobs, 1)

    def test_alert_config_defaults(self):
        """Test AlertConfig default values"""
        alert_config = AlertConfig()
        
        self.assertFalse(alert_config.enabled)
        self.assertEqual(alert_config.smtp_server, '')
        self.assertEqual(alert_config.smtp_port, 587)
        self.assertEqual(alert_config.from_email, '')
        self.assertEqual(alert_config.password, '')
        self.assertEqual(alert_config.recipients, [])

    def test_backup_config_defaults(self):
        """Test BackupConfig default values"""
        backup_config = BackupConfig()
        
        self.assertEqual(backup_config.schedule, '0 2 * * *')
        self.assertEqual(backup_config.retention_days, 7)
        self.assertEqual(backup_config.backup_path, '/var/backups')
        self.assertTrue(backup_config.compression)
        self.assertEqual(backup_config.parallel_jobs, 2)

    def test_config_validation_all_sections_present(self):
        """Test configuration validation when all required sections are present"""
        complete_config = {
            'databases': {'test_db': {}},
            'monitoring': {'check_interval': 300},
            'backup': {'retention_days': 7}
        }
        
        with patch('database_automation.Path.exists', return_value=True):
            with patch('builtins.open', mock_open()):
                with patch('database_automation.yaml.safe_load', return_value=complete_config):
                    with patch.object(DatabaseAutomation, '_initialize_connection_pools'):
                        automation = DatabaseAutomation.__new__(DatabaseAutomation)
                        config = automation._load_config('test.yaml')
        
        self.assertEqual(config, complete_config)

    def test_config_validation_multiple_missing_sections(self):
        """Test configuration validation with multiple missing sections"""
        incomplete_config = {
            'databases': {'test_db': {}}
            # Missing both 'monitoring' and 'backup'
        }
        
        with patch('database_automation.Path.exists', return_value=True):
            with patch('builtins.open', mock_open()):
                with patch('database_automation.yaml.safe_load', return_value=incomplete_config):
                    with patch.object(DatabaseAutomation, '_initialize_connection_pools'):
                        automation = DatabaseAutomation.__new__(DatabaseAutomation)
                        with self.assertRaises(ValueError) as context:
                            automation._load_config('incomplete.yaml')
        
        # Should fail on the first missing section (monitoring)
        self.assertIn('monitoring', str(context.exception))


if __name__ == '__main__':
    unittest.main()