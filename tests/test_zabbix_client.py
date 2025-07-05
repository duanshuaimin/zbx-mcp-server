import pytest
from unittest.mock import AsyncMock, patch
from zbx_mcp_server.zabbix_client import ZabbixClient, ZabbixAPIError

@pytest.fixture
def client():
    """Create a ZabbixClient instance for testing."""
    return ZabbixClient(url="http://zabbix.example.com", username="Admin", password="password")

@pytest.mark.asyncio
async def test_get_problems_success(client):
    """Test successful retrieval of problems."""
    mock_response = [{"problem_id": "1", "name": "Test Problem"}]
    client.session_token = "dummy_token"
    
    with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        
        problems = await client.get_problems()
        
        assert problems == mock_response
        mock_request.assert_called_once_with("problem.get", {
            "output": "extend",
            "selectAcknowledges": "extend",
            "selectTags": "extend",
            "selectSuppressionData": "extend"
        })

@pytest.mark.asyncio
async def test_get_problems_api_error(client):
    """Test API error during problem retrieval."""
    client.session_token = "dummy_token"
    with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = ZabbixAPIError("Failed to get problems")
        
        with pytest.raises(ZabbixAPIError):
            await client.get_problems()

@pytest.mark.asyncio
async def test_get_items_success(client):
    """Test successful retrieval of items."""
    mock_response = [{"itemid": "1", "name": "CPU Utilization"}]
    client.session_token = "dummy_token"

    with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        items = await client.get_items(hostids=["1001"])

        assert items == mock_response
        mock_request.assert_called_once_with("item.get", {
            "output": "extend",
            "hostids": ["1001"],
            "search": {},
            "sortfield": "name",
            "sortorder": "ASC"
        })