import frappe
import json

import requests
import base64

def get_lark_credentials():
    site_config = frappe.get_cached_doc("Lark HD Settings")

    app_id = site_config.app_id
    app_secret = site_config.get_password("app_secret")

    if not app_id or not app_secret:
        frappe.throw("Lark App ID or App Secret not configured in Lark Settings.")

    return app_id, app_secret

@frappe.whitelist(allow_guest=True)
def oauth2_login(code: str, state: str):
    """
	Callback for processing code and state for user added providers
	"""

    parsed = base64.b64decode(state) 
    parsed = json.loads(parsed)
    headers = {
        'Content-Type': 'application/json',
    } 

    app_id, app_secret = get_lark_credentials()
    body = {
        "app_id": app_id,
        "app_secret": app_secret,
    }

    cache = frappe.cache()
    cached_app_tok = cache.get_value("app_access_token")

    if cached_app_tok:
        app_access_token = cached_app_tok
        print("Using cached app access token:", app_access_token)
    else:
        response = requests.post('https://open.larksuite.com/open-apis/auth/v3/app_access_token/internal', headers=headers, json=body)
        response = response.json()
        app_access_token = response.get("app_access_token")

        cache.set_value("app_access_token", app_access_token, expires_in_sec=3600)

    headers = {
        'Authorization': f'Bearer {app_access_token}',
        'Content-Type': 'application/json'
    }

    body = {
        "grant_type": "authorization_code",
        "code": code,
    }

    response = requests.post('https://open.larksuite.com/open-apis/authen/v1/oidc/access_token', headers=headers, json=body)
    response = response.json()

    print("User Token Response: ", response)

    user_access_token = response.get('data').get("access_token")
    headers = {
        'Authorization': f'Bearer {user_access_token}',
        'Content-Type': 'application/json'
    }

    response = requests.get('https://open.larksuite.com/open-apis/authen/v1/user_info', headers=headers)
    response = response.json()

    email = response.get('data').get("email")
    user_row = frappe.get_list("User",
        filters={"email": email, "enabled": 1},
        fields=["name"],
        limit_page_length=1,
        ignore_permissions=True,
    )

    if not user_row:
        frappe.throw("User not found", frappe.AuthenticationError)

    user_name = user_row[0].name

    login_manager = frappe.auth.LoginManager()
    login_manager.user = user_name
    login_manager.post_login()

    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = "/helpdesk"
