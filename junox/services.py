import requests
from django.conf import settings


API_URL = settings.API_URL


def get_device_list(token):
    """
    Fetches the inventory from FastAPI.
    The middleware ensures the token passed here is fresh.
    """
    url = f"{API_URL}/devices"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json()
        return []
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        return None


def get_device_interfaces(token, device_id):
    """
    Fetches a single device interfaces from FastAPI.
    The middleware ensures the token passed here is fresh.
    """
    url = f"{API_URL}/interfaces/{device_id}/interfaces_db"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        return None


def service_get_device_vlans(token, device_id):
    """
    Fetches a single device vlans from FastAPI.
    """
    url = f"{API_URL}/vlans/{device_id}/fetch_vlans_db"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        return None

def service_assign_vlan(token, device_id, interface_name, vlan_id):
    """
    Assigns a VLAN to an interface on a device using FastAPI.
    """
    url = f"{API_URL}/vlans/access_vlan/{device_id}/{vlan_id}?interface_name={interface_name}"
    headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {token}',
            
        }
    try:
        response = requests.post(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        return {"success": False, "error": "Failed to assign VLAN"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def service_get_vlan_catalog(token):
    """
    Fetches the VLAN catalog from FastAPI.
    """
    url = f"{API_URL}/vlans/get_vlan_catalog_db"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return {"success": True, "vlans": response.json()}
        return {"success": False, "error": "Failed to fetch VLAN catalog"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def service_get_all_jobs(token):
    """
    Fetches the job list from FastAPI.
    """
    url = f"{API_URL}/other/jobs/all"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return {"success": True, "jobs": response.json()}
        return {"success": False, "error": "Failed to fetch jobs"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def service_add_device(token, hostname, username, password, session_id):
    """
    Adds a new device to the inventory using FastAPI.
    """
    url = f"{API_URL}/devices/provision/{hostname}"
    headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {token}',
            
        }
    
    # Form-urlencoded data, we move data to payload, don't prefer in the URL.
    payload = {
            'username': username,
            'password': password,
            'session_id': session_id
        }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        
        # Return a dictionary so the view knows exactly what happened
        if response.status_code in [200, 201,202]:
            return {"success": True, "data": response.json()}
        else:
            # Capture the error message from FastAPI if available
            error_msg = response.json().get('detail', 'Provisioning failed')
            return {"success": False, "error": error_msg}
            
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"API Connection Error: {str(e)}"}

