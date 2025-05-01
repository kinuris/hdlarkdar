import frappe
import requests

from frappe.utils import now, nowdate

def ticket_reply(doc, method):
    current_user = frappe.session.user
    agent_name = frappe.get_value(
        "HD Agent",
        {"user": current_user},
        "agent_name"
    )

    hd_ticket_name = doc.name
    subject = doc.subject or ""

    if doc.customer:
        customer = doc.customer
    else:
        raised_by = doc.raised_by
        contact = frappe.db.get_value(
            "Contact",
            {"email_id": raised_by},
            "company_name"
        )

        customer = frappe.db.get_value(
            "HD Customer",
            {"name": contact},
            "name"
        )

    today = nowdate()
    start_of_day = f"{today} 00:00:00"
    end_of_day = f"{today} 23:59:59"

    exists = frappe.db.exists(
        "Lark DAR Submission",
        {
            "customer": customer,
            "hd_ticket": hd_ticket_name,
            "subject": subject,
            "reply_date": ["between", (start_of_day, end_of_day)],
        },
    )

    if not exists:
        try:
            new_submission = frappe.get_doc({
                "doctype": "Lark DAR Submission",
                "customer": customer,
                "hd_ticket": hd_ticket_name,
                "assigned_to": current_user,
                "reply_date": now(),
                "subject": subject,
                "customer_deal": "N/A",
            })

            response = requests.post(
                'https://serviotech.sg.larksuite.com/base/workflow/webhook/event/W2OTa5iEiwWjCfhhB74lYKNCgWe',
                json={
                    "Client Name": customer,
                    "Deal Name": new_submission.customer_deal,
                    "Submitted By": agent_name,
                    "Specific Activity": subject,
                }
            )

            print("Status Code: ", response.status_code)
            print("Response Body: ", response.json())

            new_submission.insert(ignore_permissions=True)
            
            frappe.db.commit()
            frappe.log_info(f"Created Lark DAR Submission for {hd_ticket_name}", "Lark DAR Submission Success")
        except Exception as e:
            frappe.log_error(f"Failed to create Lark DAR Submission for {hd_ticket_name}: {e}", "Lark DAR Submission Error")