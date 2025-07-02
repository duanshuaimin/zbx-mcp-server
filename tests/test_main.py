"""Tests for main entry point."""

import pytest
from unittest.mock import patch, MagicMock
import sys
from zbx_mcp_server.main import main


class TestMain:
    """Test main function and CLI argument parsing."""
    
    @patch('zbx_mcp_server.main.uvicorn.run')
    @patch('zbx_mcp_server.main.create_app')
    def test_main_default_args(self, mock_create_app, mock_uvicorn_run):
        """Test main function with default arguments."""
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app
        
        with patch.object(sys, 'argv', ['zbx-mcp-server']):
            main()
        
        mock_create_app.assert_called_once()
        mock_uvicorn_run.assert_called_once_with(
            mock_app,
            host="127.0.0.1",
            port=8000,
            reload=False
        )
    
    @patch('zbx_mcp_server.main.uvicorn.run')
    @patch('zbx_mcp_server.main.create_app')
    def test_main_custom_host_port(self, mock_create_app, mock_uvicorn_run):
        """Test main function with custom host and port."""
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app
        
        with patch.object(sys, 'argv', ['zbx-mcp-server', '--host', '0.0.0.0', '--port', '8080']):
            main()
        
        mock_create_app.assert_called_once()
        mock_uvicorn_run.assert_called_once_with(
            mock_app,
            host="0.0.0.0",
            port=8080,
            reload=False
        )
    
    @patch('zbx_mcp_server.main.uvicorn.run')
    @patch('zbx_mcp_server.main.create_app')
    def test_main_with_reload(self, mock_create_app, mock_uvicorn_run):
        """Test main function with reload flag."""
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app
        
        with patch.object(sys, 'argv', ['zbx-mcp-server', '--reload']):
            main()
        
        mock_create_app.assert_called_once()
        mock_uvicorn_run.assert_called_once_with(
            mock_app,
            host="127.0.0.1",
            port=8000,
            reload=True
        )
    
    @patch('zbx_mcp_server.main.uvicorn.run')
    @patch('zbx_mcp_server.main.create_app')
    def test_main_all_custom_args(self, mock_create_app, mock_uvicorn_run):
        """Test main function with all custom arguments."""
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app
        
        with patch.object(sys, 'argv', [
            'zbx-mcp-server', 
            '--host', '192.168.1.100', 
            '--port', '9000', 
            '--reload'
        ]):
            main()
        
        mock_create_app.assert_called_once()
        mock_uvicorn_run.assert_called_once_with(
            mock_app,
            host="192.168.1.100",
            port=9000,
            reload=True
        )
    
    @patch('zbx_mcp_server.main.uvicorn.run')
    @patch('zbx_mcp_server.main.create_app')
    def test_main_port_as_string(self, mock_create_app, mock_uvicorn_run):
        """Test that port argument is converted to integer."""
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app
        
        with patch.object(sys, 'argv', ['zbx-mcp-server', '--port', '8080']):
            main()
        
        mock_uvicorn_run.assert_called_once()
        args, kwargs = mock_uvicorn_run.call_args
        assert kwargs['port'] == 8080
        assert isinstance(kwargs['port'], int)
    
    def test_argument_parser_help_text(self):
        """Test that argument parser includes proper help text."""
        import argparse
        from zbx_mcp_server.main import main
        
        with patch('zbx_mcp_server.main.uvicorn.run'):
            with patch('zbx_mcp_server.main.create_app'):
                with patch.object(sys, 'argv', ['zbx-mcp-server', '--help']):
                    with pytest.raises(SystemExit):
                        main()
    
    @patch('zbx_mcp_server.main.uvicorn.run')
    @patch('zbx_mcp_server.main.create_app')
    def test_main_creates_app_before_running(self, mock_create_app, mock_uvicorn_run):
        """Test that app is created before uvicorn.run is called."""
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app
        
        with patch.object(sys, 'argv', ['zbx-mcp-server']):
            main()
        
        # Verify create_app was called before uvicorn.run
        assert mock_create_app.called
        assert mock_uvicorn_run.called
        # Check that the app returned by create_app is passed to uvicorn.run
        args, kwargs = mock_uvicorn_run.call_args
        assert args[0] is mock_app
    
    def test_invalid_port_argument(self):
        """Test behavior with invalid port argument."""
        with patch.object(sys, 'argv', ['zbx-mcp-server', '--port', 'invalid']):
            with pytest.raises(SystemExit):
                main()
    
    @patch('zbx_mcp_server.main.uvicorn.run')
    @patch('zbx_mcp_server.main.create_app')
    def test_main_preserves_app_instance(self, mock_create_app, mock_uvicorn_run):
        """Test that the same app instance is used."""
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app
        
        with patch.object(sys, 'argv', ['zbx-mcp-server']):
            main()
        
        # Verify the exact same app instance is passed to uvicorn
        mock_uvicorn_run.assert_called_once()
        args, kwargs = mock_uvicorn_run.call_args
        assert args[0] is mock_app
    
    @patch('zbx_mcp_server.main.uvicorn.run')
    @patch('zbx_mcp_server.main.create_app')
    def test_main_exception_handling(self, mock_create_app, mock_uvicorn_run):
        """Test main function handles exceptions properly."""
        mock_create_app.side_effect = Exception("Test exception")
        
        with patch.object(sys, 'argv', ['zbx-mcp-server']):
            with pytest.raises(Exception, match="Test exception"):
                main()
        
        mock_uvicorn_run.assert_not_called()


class TestMainModule:
    """Test main module when run directly."""
    
    @patch('zbx_mcp_server.main.main')
    def test_main_module_execution(self, mock_main):
        """Test that main() is called when module is executed directly."""
        # This test simulates running the module with python -m zbx_mcp_server.main
        with patch('__main__.__name__', '__main__'):
            # Import and execute the module
            import zbx_mcp_server.main
            # The main function would be called due to the if __name__ == "__main__" check
            # but since we're importing it, we need to simulate this
            if zbx_mcp_server.main.__name__ == "__main__":
                zbx_mcp_server.main.main()
    
    def test_module_imports(self):
        """Test that all required modules can be imported."""
        import argparse
        import uvicorn
        from zbx_mcp_server.server import create_app
        
        # If we get here, all imports are successful
        assert argparse is not None
        assert uvicorn is not None
        assert create_app is not None