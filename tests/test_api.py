import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.auth import create_access_token

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data

def test_root_redirect(client):
    """Test root URL redirects to dashboard"""
    response = client.get("/", allow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/dashboard"

def test_login_page(client):
    """Test login page"""
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_google_auth_redirect(client):
    """Test Google OAuth redirect"""
    with patch('app.main.create_google_oauth_flow') as mock_flow_creator:
        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = ("https://accounts.google.com/oauth", "state")
        mock_flow_creator.return_value = mock_flow
        
        response = client.get("/auth/google", allow_redirects=False)
        assert response.status_code == 307

def test_dashboard_requires_auth(client):
    """Test dashboard requires authentication"""
    response = client.get("/dashboard")
    assert response.status_code == 401

def test_dashboard_with_auth(client, test_user):
    """Test dashboard with authentication"""
    # Create access token
    token = create_access_token(data={"sub": test_user.email})
    
    # Set cookie
    client.cookies.set("access_token", token)
    
    response = client.get("/dashboard")
    assert response.status_code == 200

def test_api_packages_requires_auth(client):
    """Test packages API requires authentication"""
    response = client.get("/api/packages")
    assert response.status_code == 401

def test_api_packages_with_auth(client, test_user, test_package):
    """Test packages API with authentication"""
    # Mock the dependency
    def mock_get_current_user():
        return test_user
    
    from app.main import app
    app.dependency_overrides[app.dependency_overrides_map.get('get_current_user', lambda: None)] = mock_get_current_user
    
    response = client.get("/api/packages")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["package_name"] == test_package.package_name

def test_api_process_emails(client, test_user):
    """Test email processing API"""
    def mock_get_current_user():
        return test_user
    
    with patch('app.main.Thread') as mock_thread:
        from app.main import app
        app.dependency_overrides[app.dependency_overrides_map.get('get_current_user', lambda: None)] = mock_get_current_user
        
        response = client.post("/api/process-emails")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Email processing started"

def test_api_delete_package(client, test_user, test_package):
    """Test package deletion API"""
    def mock_get_current_user():
        return test_user
    
    from app.main import app
    app.dependency_overrides[app.dependency_overrides_map.get('get_current_user', lambda: None)] = mock_get_current_user
    
    response = client.delete(f"/api/packages/{test_package.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Package deleted"

def test_api_delete_package_not_found(client, test_user):
    """Test deleting non-existent package"""
    def mock_get_current_user():
        return test_user
    
    from app.main import app
    app.dependency_overrides[app.dependency_overrides_map.get('get_current_user', lambda: None)] = mock_get_current_user
    
    response = client.delete("/api/packages/999")
    assert response.status_code == 404

def test_admin_panel_requires_admin(client, test_user):
    """Test admin panel requires admin privileges"""
    # Regular user should not access admin panel
    token = create_access_token(data={"sub": test_user.email})
    client.cookies.set("access_token", token)
    
    response = client.get("/admin")
    assert response.status_code == 403

def test_admin_panel_with_admin(client, test_admin_user):
    """Test admin panel with admin user"""
    token = create_access_token(data={"sub": test_admin_user.email})
    client.cookies.set("access_token", token)
    
    response = client.get("/admin")
    assert response.status_code == 200

def test_admin_api_users(client, test_admin_user):
    """Test admin users API"""
    def mock_get_current_admin_user():
        return test_admin_user
    
    from app.main import app
    app.dependency_overrides[app.dependency_overrides_map.get('get_current_admin_user', lambda: None)] = mock_get_current_admin_user
    
    response = client.get("/admin/api/users")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1

def test_admin_toggle_user_active(client, test_admin_user, test_user):
    """Test admin toggle user active status"""
    def mock_get_current_admin_user():
        return test_admin_user
    
    from app.main import app
    app.dependency_overrides[app.dependency_overrides_map.get('get_current_admin_user', lambda: None)] = mock_get_current_admin_user
    
    response = client.post(f"/admin/api/users/{test_user.id}/toggle-active")
    assert response.status_code == 200
    data = response.json()
    assert "activated" in data["message"] or "deactivated" in data["message"]

def test_admin_process_all_emails(client, test_admin_user):
    """Test admin process all emails"""
    def mock_get_current_admin_user():
        return test_admin_user
    
    with patch('app.main.email_scheduler') as mock_scheduler:
        from app.main import app
        app.dependency_overrides[app.dependency_overrides_map.get('get_current_admin_user', lambda: None)] = mock_get_current_admin_user
        
        response = client.post("/admin/api/process-all-emails")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Email processing triggered for all users"
        mock_scheduler.trigger_immediate_processing.assert_called_once()

def test_admin_scheduler_status(client, test_admin_user):
    """Test admin scheduler status"""
    def mock_get_current_admin_user():
        return test_admin_user
    
    mock_status = {"running": True, "jobs": [], "check_interval_minutes": 30}
    
    with patch('app.main.email_scheduler') as mock_scheduler:
        mock_scheduler.get_status.return_value = mock_status
        
        from app.main import app
        app.dependency_overrides[app.dependency_overrides_map.get('get_current_admin_user', lambda: None)] = mock_get_current_admin_user
        
        response = client.get("/admin/api/scheduler-status")
        assert response.status_code == 200
        data = response.json()
        assert data["running"] is True
        assert data["check_interval_minutes"] == 30