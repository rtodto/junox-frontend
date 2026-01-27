from django.shortcuts import render,redirect
from django.contrib import messages
from django.core.paginator import Paginator
import requests
from .services import *
from django.conf import settings

API_URL = settings.API_URL


def login_view(request):
    return render(request, 'junox/login.html')

def login_junox(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        # The data FastAPI's OAuth2PasswordRequestForm expects
        payload = {
            'username': username,
            'password': password
        }

        try:
            # 1. Post to FastAPI (Note: use 'data=' for form-data, not 'json=')
            response = requests.post(API_URL + "/token", data=payload)
            
            if response.status_code == 200:
                # 2. Extract the token
                data = response.json()
                token = data.get('access_token')
                refresh_token = data.get('refresh_token')

                # 3. Store the token in a Django Session
                # This keeps the user "logged in" across the dashboard
                request.session['auth_token'] = token
                request.session['refresh_token'] = refresh_token
                request.session['username'] = username
                
                return redirect('junox:dashboard') # Redirect to dashboard
            else:
                # Handle 400 error from FastAPI
                messages.error(request, "Invalid credentials or unauthorized access. Please try again.")
                return render(request, 'junox/login.html')


        except requests.exceptions.RequestException:
            messages.error(request, "Backend server unreachable. Please try again.")
            return render(request, 'junox/login.html')

    return render(request, 'junox/login.html')


def dashboard_view(request):
    
    username = request.session.get('username')
    token = request.session.get('auth_token')
    
    if not token:
        return redirect('junox:login')

    device_list = get_device_list(token)
    if not device_list:
        return render(request, 'junox/dashboard.html', {'error': 'API Connection Error'})
    
    return render(request, 'junox/dashboard.html', {'device_list': device_list})


def device_dashboard_view(request):
    token = request.session.get('auth_token')
    if not token:
        return redirect('junox:login')
    
    # 1. Get Search Query and Page Number
    search_query = request.GET.get('q', '').strip()
    try:
        current_page = int(request.GET.get('page', 1))
    except (ValueError, TypeError):
        current_page = 1
    
    items_per_page = 15
    all_devices = get_device_list(token)
    
    if all_devices is None:
        return render(request, 'junox/device_dasboard.html', {'error': 'API Connection Error'})
    
    # 2. FILTERING LOGIC
    # We filter the list based on hostname, IP, or Serial Number
    if search_query:
        all_devices = [
            d for d in all_devices 
            if search_query.lower() in str(d.get('hostname', '')).lower() 
            or search_query.lower() in str(d.get('ip_address', '')).lower()
            or search_query.lower() in str(d.get('serialnumber', '')).lower()
            or search_query.lower() in str(d.get('model', '')).lower()
        ]
    
    # 3. Calculate totals and bounds based on the (potentially filtered) list
    total_count = len(all_devices)
    last_page = (total_count + items_per_page - 1) // items_per_page if total_count > 0 else 1
    
    # Safety check
    if current_page > last_page: current_page = last_page
    if current_page < 1: current_page = 1

    # 4. Slice the list for the current page
    start = (current_page - 1) * items_per_page
    end = start + items_per_page
    device_list = all_devices[start:end]
    
    page_numbers_all = []
    for p in range(1, last_page + 1):
        page_numbers_all.append({
            'num': p,
            'status': 'selected' if p == current_page else ''
        })

    # SLIDING WINDOW FOR BUTTONS
    page_range = [p for p in range(current_page - 2, current_page + 3) if 0 < p <= last_page]

    context = {
        'device_list': device_list,
        'total_count': total_count,
        'current_page': current_page,
        'last_page': last_page,
        'has_next': current_page < last_page,
        'has_prev': current_page > 1,
        'next_page': current_page + 1,
        'prev_page': current_page - 1,
        'page_range': page_range,
        'page_numbers_all': page_numbers_all,
        'search_query': search_query, # Pass this back to keep the input filled
    }
    return render(request, 'junox/device_dasboard.html', context)

def assign_vlan_view(request):
    token = request.session.get('auth_token')
    if not token:
        return redirect('junox:login')
    
    if request.method == 'POST':
        interface_name = request.POST.get('interface_name')
        hostname = request.POST.get('hostname')
        vlan_id = request.POST.get('vlan_id')
        device_id = request.POST.get('device_id')
        
        result = service_assign_vlan(token, device_id, interface_name, vlan_id)


        
        if result.get("success"):
            job_id = result["data"]["job_id"]
            messages.success(request, f"Job ID: {job_id} assigned to {interface_name} on {hostname}")
            return redirect('junox:device_detail', device_id=device_id, hostname=hostname)
        else:
            messages.error(request, result["error"])
            return redirect('junox:device_detail', device_id=device_id, hostname=hostname)


def vlan_catalog_view(request):
    token = request.session.get('auth_token')
    if not token:
        return redirect('junox:login')
    
    result = service_get_vlan_catalog(token)
    if not result.get("success"):
        messages.error(request, result["error"])
        return redirect('junox:dashboard')
    
    return render(request, 'junox/vlan_catalog.html', {'catalog': result['vlans']})


def device_detail_view(request, device_id, hostname):

    token = request.session.get('auth_token')
    if not token:
        return redirect('junox:login')
    
    interfaces = get_device_interfaces(token, device_id)
    vlans = service_get_device_vlans(token, device_id)


    if not interfaces:
        return render(request, 'junox/device_detail.html', {'error': 'API Connection Error'})
    
    return render(request, 'junox/device_detail.html', {
               'device_interfaces': interfaces['interfaces'],
               'hostname':hostname,
               'vlan_list': vlans,
               'device_id': device_id,
               })




def add_device_view(request):
    """Here we send request to FastAPI to add a new device
       but the API call is inside services.py module.
    """

    token = request.session.get('auth_token')
    if not token:
        return redirect('junox:login')

    if request.method == 'POST':
        # 1. Extract data from the form
        hostname = request.POST.get('hostname')
        user = request.POST.get('username')
        pwd = request.POST.get('password')

        # 2. Call the service
        result = service_add_device(token, hostname, user, pwd)

        # 3. Handle the result
        if result["success"]:
            messages.success(request, f"Device {hostname} registration request has been sent successfully! JOB-ID: {result['data']}")
            return redirect('junox:device_dashboard')

        else:
            # Return to the form with the specific error message
            return render(request, 'junox/add_device.html', {
                'error': result["error"],
                'hostname': hostname, # keep the input so they don't have to retype
                'username': user
            })

    return render(request, 'junox/add_device.html')


def jobs_list_view(request):
    token = request.session.get('auth_token')
    if not token:
        return redirect('junox:login')

    result = service_get_all_jobs(token)
    all_jobs = result.get('jobs', [])

    # 1. SEARCH LOGIC
    search_query = request.GET.get('q', '').lower()
    if search_query:
        all_jobs = [
            j for j in all_jobs 
            if search_query in str(j.get('id', '')).lower() 
            or search_query in str(j.get('target', '')).lower()
        ]

    # 2. SORT LOGIC
    sort_by = request.GET.get('sort', 'created_at') # Default sort
    reverse_sort = request.GET.get('order', 'desc') == 'desc'
    
    try:
        all_jobs.sort(key=lambda x: x.get(sort_by) or '', reverse=reverse_sort)
    except Exception:
        pass # Fallback if field missing

    # 3. PAGINATION
    paginator = Paginator(all_jobs, 15)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'junox/jobs_list.html', {
        'jobs': page_obj,
        'search_query': search_query,
        'current_sort': sort_by,
        'current_order': request.GET.get('order', 'desc')
    })
    

def logout_view(request):
    request.session.flush() # Completely destroys the session and cookies
    return redirect('junox:login')


def check_session(request):
    """We check if the user still has a valid session"""
    
    #Get the token from the session
    token = request.session.get('auth_token')
    if not token:
        return redirect('junox:login')
    
    
    try:
        response = requests.get(API_URL + "/ping", headers={'Authorization': f'Bearer {token}'})
        if response.status_code == 200:
            return redirect('junox:dashboard')
        else:
            return redirect('junox:login')
    except requests.exceptions.RequestException:
        return redirect('junox:login')