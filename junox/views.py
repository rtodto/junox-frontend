from django.shortcuts import render,redirect
from django.contrib import messages
from django.core.paginator import Paginator
import requests
from .services import *
from django.conf import settings
from django.utils.safestring import mark_safe
from functools import wraps
from django.http import JsonResponse

API_URL = settings.API_URL

#DECORATOR
def token_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('auth_token'):
            # User is not logged in, send them to login page
            return redirect('junox:login_junox')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


#@token_required
# def login_view(request):
#     # If user has a token in their session, send them to dashboard
#     if request.session.get('auth_token'):
#         return redirect('junox:dashboard')
    
#     # Otherwise, send them to login
#     return render(request, 'junox/login.html')


def login_junox(request):
    if request.session.get('auth_token'):
        return redirect('junox:dashboard')

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

@token_required
def device_dashboard_view(request):
    token = request.session.get('auth_token')
    
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


@token_required
def assign_vlan_view(request):
    token = request.session.get('auth_token')
    
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


@token_required
def vlan_catalog_view(request):
    token = request.session.get('auth_token')
    
    result = service_get_vlan_catalog(token)
    if not result.get("success"):
        messages.error(request, result["error"])
        return redirect('junox:dashboard')
    
    return render(request, 'junox/vlan_catalog.html', {'catalog': result['vlans']})


@token_required
def device_detail_view(request, device_id, hostname):

    token = request.session.get('auth_token')
    
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


@token_required
def add_device_view(request):
    token = request.session.get('auth_token')

    session_id = None # Initialize so it's always in scope

    if request.method == 'POST':
        hostname = request.POST.get('hostname')
        user = request.POST.get('username')
        pwd = request.POST.get('password')
        session_id = request.POST.get('session_id')

        # Call the API service
        result = service_add_device(token, hostname, user, pwd, session_id)

        # Check if the request came from JavaScript (Fetch)
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        if result["success"]:
            if is_ajax:
                # Return JSON to keep the page still and terminal open
                return JsonResponse({"status": "processing", "job_id": result["data"].get('job_id')})
            
            # Standard flow: Redirect to dashboard
            messages.success(request, f"Device {hostname} registration initiated.")
            return redirect('junox:device_dashboard')
        else:
            if is_ajax:
                # Return 400 so the terminal can print the error message
                return JsonResponse({"error": result["error"]}, status=400)
            
            messages.error(request, result["error"])

    return render(request, 'junox/add_device.html', {'session_id': session_id})

@token_required
def jobs_list_view(request):
    token = request.session.get('auth_token')

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
    return redirect('junox:login_junox')

@token_required
def check_session(request):
    """We check if the user still has a valid session"""
    
    #Get the token from the session
    token = request.session.get('auth_token')
    
    try:
        response = requests.get(API_URL + "/ping", headers={'Authorization': f'Bearer {token}'})
        if response.status_code == 200:
            return redirect('junox:dashboard')
        else:
            return redirect('junox:login_junox')
    except requests.exceptions.RequestException:
        return redirect('junox:login_junox')

@token_required
def dashboard_view(request):
    # 1. Fetch aggregated data from FastAPI
    # Ensure this URL matches your internal docker/local network address
    token = request.session.get('auth_token')
    api_url = f"{settings.API_URL}/devices/inventory/stats"
    headers = {"Authorization": f"Bearer {token}"}
    
    context = {
        "stats": {}
    }

    try:
        # 2. Get the data (set a timeout so the dashboard doesn't hang if API is down)
        response = requests.get(api_url, timeout=3, headers=headers)
        if response.status_code == 200:
            context["stats"] = response.json()
        else:
            print(f"Error fetching stats: {response.status_code}")
    except Exception as e:
        print(f"API Connection Error: {e}")
        # We pass empty stats so the page loads (just without charts)

    return render(request, 'junox/dashboard.html', context)

