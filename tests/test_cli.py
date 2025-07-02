#!/usr/bin/env python3
"""
Unit tests for CLI functionality
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import argparse
import tempfile

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_automation import create_cli_parser, main, DatabaseAutomation


class TestCLI(unittest.TestCase):
    """Test cases for CLI functionality"""

    def test_create_cli_parser(self):
        """Test CLI parser creation"""
        parser = create_cli_parser()
        
        self.assertIsInstance(parser, argparse.ArgumentParser)
        
        # Test default arguments
        args = parser.parse_args([])
        self.assertEqual(args.config, 'db_config.yaml')
        self.assertEqual(args.log_level, 'INFO')
        self.assertIsNone(args.database)
        self.assertIsNone(args.command)

    def test_cli_parser_with_arguments(self):
        """Test CLI parser with various arguments"""
        parser = create_cli_parser()
        
        # Test health command
        args = parser.parse_args(['--config', 'test.yaml', '--log-level', 'DEBUG', 'health', '--generate-report'])
        self.assertEqual(args.config, 'test.yaml')
        self.assertEqual(args.log_level, 'DEBUG')
        self.assertEqual(args.command, 'health')
        self.assertTrue(args.generate_report)

    def test_cli_parser_backup_command(self):
        """Test backup command parsing"""
        parser = create_cli_parser()
        
        args = parser.parse_args(['backup', '--cleanup'])
        self.assertEqual(args.command, 'backup')
        self.assertTrue(args.cleanup)

    def test_cli_parser_monitor_command(self):
        """Test monitor command parsing"""
        parser = create_cli_parser()
        
        args = parser.parse_args(['monitor', '--metrics-port', '9000'])
        self.assertEqual(args.command, 'monitor')
        self.assertEqual(args.metrics_port, 9000)

    def test_cli_parser_database_filter(self):
        """Test database filtering"""
        parser = create_cli_parser()
        
        args = parser.parse_args(['--database', 'test_db', 'health'])
        self.assertEqual(args.database, 'test_db')
        self.assertEqual(args.command, 'health')

    @patch('database_automation.DatabaseAutomation')
    @patch('database_automation.setup_logging')
    def test_main_health_command(self, mock_logging, mock_automation_class):
        """Test main function with health command"""
        mock_automation = Mock()
        mock_automation_class.return_value = mock_automation
        mock_automation.config = {'databases': {'test_db': {}}}
        mock_automation.monitor_database_health.return_value = {'status': 'healthy'}
        
        test_args = ['test_script', 'health']
        with patch.object(sys, 'argv', test_args):
            with patch('builtins.print') as mock_print:
                main()
        
        mock_automation.monitor_database_health.assert_called()
        mock_print.assert_called()

    @patch('database_automation.DatabaseAutomation')
    @patch('database_automation.setup_logging')
    def test_main_backup_command(self, mock_logging, mock_automation_class):
        """Test main function with backup command"""
        mock_automation = Mock()
        mock_automation_class.return_value = mock_automation
        mock_automation.config = {'databases': {'test_db': {}}}
        mock_automation.automated_backup.return_value = {'status': 'success', 'backup_file': '/tmp/test.sql', 'file_size_mb': 10}
        
        test_args = ['test_script', 'backup']
        with patch.object(sys, 'argv', test_args):
            with patch('builtins.print') as mock_print:
                main()
        
        mock_automation.automated_backup.assert_called()
        mock_print.assert_called()

    @patch('database_automation.DatabaseAutomation')
    @patch('database_automation.setup_logging')
    def test_main_test_command(self, mock_logging, mock_automation_class):
        """Test main function with test command"""
        mock_automation = Mock()
        mock_automation_class.return_value = mock_automation
        mock_automation.config = {'databases': {'test_db': {}}}
        
        # Mock successful connection
        mock_conn = Mock()
        mock_automation.get_connection.return_value.__enter__.return_value = mock_conn
        
        test_args = ['test_script', 'test']
        with patch.object(sys, 'argv', test_args):
            with patch('builtins.print') as mock_print:
                main()
        
        mock_automation.get_connection.assert_called()
        mock_print.assert_called()

    @patch('database_automation.DatabaseAutomation')
    @patch('database_automation.setup_logging')
    def test_main_test_command_failure(self, mock_logging, mock_automation_class):
        """Test main function with test command when connection fails"""
        mock_automation = Mock()
        mock_automation_class.return_value = mock_automation
        mock_automation.config = {'databases': {'test_db': {}}}
        
        # Mock connection failure
        mock_automation.get_connection.side_effect = Exception("Connection failed")
        
        test_args = ['test_script', 'test']
        with patch.object(sys, 'argv', test_args):
            with patch('builtins.print') as mock_print:
                main()
        
        mock_automation.get_connection.assert_called()
        mock_print.assert_called()

    @patch('database_automation.DatabaseAutomation')
    @patch('database_automation.setup_logging')
    def test_main_status_command(self, mock_logging, mock_automation_class):
        """Test main function with status command"""
        mock_automation = Mock()
        mock_automation_class.return_value = mock_automation
        mock_automation.config = {'databases': {'test_db': {'db_type': 'postgresql'}}}
        mock_automation.get_status.return_value = {
            'uptime_seconds': 3600,
            'system': {'version': '2.0.0', 'config_file': 'test.yaml'},
            'databases': {'test_db': {'status': 'connected', 'type': 'postgresql'}}
        }
        
        test_args = ['test_script', 'status']
        with patch.object(sys, 'argv', test_args):
            with patch('builtins.print') as mock_print:
                main()
        
        mock_automation.get_status.assert_called()
        mock_print.assert_called()

    @patch('database_automation.DatabaseAutomation')
    @patch('database_automation.setup_logging')
    @patch('database_automation.start_http_server')
    def test_main_monitor_command(self, mock_http_server, mock_logging, mock_automation_class):
        """Test main function with monitor command"""
        mock_automation = Mock()
        mock_automation_class.return_value = mock_automation
        mock_automation.config = {'databases': {'test_db': {}}}
        
        # Mock the monitoring to stop immediately
        mock_automation.start_monitoring.side_effect = KeyboardInterrupt()
        
        test_args = ['test_script', 'monitor', '--metrics-port', '8080']
        with patch.object(sys, 'argv', test_args):
            with patch('builtins.print'):
                main()
        
        mock_http_server.assert_called_with(8080)
        mock_automation.schedule_automated_tasks.assert_called()
        mock_automation.start_monitoring.assert_called()

    @patch('database_automation.DatabaseAutomation')
    @patch('database_automation.setup_logging')
    def test_main_optimize_command(self, mock_logging, mock_automation_class):
        """Test main function with optimize command"""
        mock_automation = Mock()
        mock_automation_class.return_value = mock_automation
        mock_automation.config = {'databases': {'test_db': {}}}
        mock_automation.performance_optimization.return_value = {
            'status': 'success',
            'optimizations': ['Statistics updated', 'Tables vacuumed']
        }
        
        test_args = ['test_script', 'optimize']
        with patch.object(sys, 'argv', test_args):
            with patch('builtins.print') as mock_print:
                main()
        
        mock_automation.performance_optimization.assert_called()
        mock_print.assert_called()

    @patch('database_automation.DatabaseAutomation')
    @patch('database_automation.setup_logging')
    def test_main_no_command(self, mock_logging, mock_automation_class):
        """Test main function with no command (default behavior)"""
        mock_automation = Mock()
        mock_automation_class.return_value = mock_automation
        mock_automation.config = {'databases': {'test_db': {}, 'test_db2': {}}}
        
        test_args = ['test_script']
        with patch.object(sys, 'argv', test_args):
            with patch('builtins.print') as mock_print:
                main()
        
        mock_print.assert_called()

    @patch('database_automation.DatabaseAutomation')
    @patch('database_automation.setup_logging')
    def test_main_keyboard_interrupt(self, mock_logging, mock_automation_class):
        """Test main function handling KeyboardInterrupt"""
        mock_automation = Mock()
        mock_automation_class.side_effect = KeyboardInterrupt()
        
        test_args = ['test_script', 'health']
        with patch.object(sys, 'argv', test_args):
            main()  # Should not raise exception
        
        mock_logging.assert_called()

    @patch('database_automation.DatabaseAutomation')
    @patch('database_automation.setup_logging')
    @patch('builtins.exit')
    def test_main_exception_handling(self, mock_exit, mock_logging, mock_automation_class):
        """Test main function handling general exceptions"""
        mock_automation_class.side_effect = Exception("Test error")
        
        test_args = ['test_script', 'health']
        with patch.object(sys, 'argv', test_args):
            main()
        
        mock_exit.assert_called_with(1)

    @patch('database_automation.DatabaseAutomation')
    @patch('database_automation.setup_logging')
    def test_main_cleanup_called(self, mock_logging, mock_automation_class):
        """Test that cleanup is called in finally block"""
        mock_automation = Mock()
        mock_automation_class.return_value = mock_automation
        mock_automation.config = {'databases': {'test_db': {}}}
        
        test_args = ['test_script', 'health']
        with patch.object(sys, 'argv', test_args):
            main()
        
        mock_automation.close_all_connections.assert_called()

    def test_cli_parser_invalid_log_level(self):
        """Test CLI parser with invalid log level"""
        parser = create_cli_parser()
        
        with self.assertRaises(SystemExit):
            parser.parse_args(['--log-level', 'INVALID'])

    def test_cli_parser_help(self):
        """Test CLI parser help functionality"""
        parser = create_cli_parser()
        
        with self.assertRaises(SystemExit):
            parser.parse_args(['--help'])


if __name__ == '__main__':
    unittest.main()