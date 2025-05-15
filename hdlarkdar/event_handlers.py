import frappe
import requests

from frappe.utils import now

def get_webhook_url():
    settings = frappe.get_cached_doc("Lark DAR Settings")

    return settings.webhook

def is_webhook_required():
    settings = frappe.get_cached_doc("Lark DAR Settings")

    return settings.require_webhook

def is_admin_reply_disallowed():
    settings = frappe.get_cached_doc("Lark DAR Settings")

    return settings.disallow_admin_reply

def is_servio_deal_required():
    settings = frappe.get_cached_doc("Lark DAR Settings")

    return settings.require_servio_deal

def ticket_reply(doc, method):
    if doc.reference_doctype != "HD Ticket":
        return

    hd_ticket = frappe.get_doc("HD Ticket", doc.reference_name)

    if not hd_ticket.servio_deal and is_servio_deal_required():
        frappe.throw("Ticket must have a deal, assign a valid Servio Deal.")

    if doc.user == "Administrator" and is_admin_reply_disallowed():
        frappe.throw("Administrator replies are not allowed. See Lark DAR Settings.")

    webhook_url = get_webhook_url()
    if not webhook_url and is_webhook_required():
        frappe.throw("Webhook URL is not set in Lark DAR Settings. See Lark DAR Settings.") 

def confirmed_ticket_reply(doc, method):
    hd_ticket = frappe.get_doc("HD Ticket", doc.reference_name)
    webhook_url = get_webhook_url()

    subject = doc.subject
    agent_name = doc.user

    # Determine servio deal ID or None
    servio_deal_id = None
    customer_deal = None
    if hd_ticket.servio_deal:
        servio_deal = frappe.get_doc("Servio Registry Deal", hd_ticket.servio_deal)
        servio_deal_id = servio_deal.record_id
        customer_deal = servio_deal.name

    new_submission = frappe.get_doc({
        "doctype": "Lark DAR Submission",
        "hd_ticket": hd_ticket.name,
        "assigned_to": doc.user,
        "reply_date": now(),
        "subject": subject,
        "customer_deal": customer_deal,
    })

    new_submission.insert(ignore_permissions=True)
    frappe.db.commit()

    body = {
        "Deal-Name": servio_deal_id,
        "Submitted-By": agent_name,
        "Specific-Activity": subject,
        "Communication-Link": f"https://erp.serviotech.com{doc.get_url()}"
    }

    if webhook_url:
        requests.post(webhook_url, json=body)

    # debug logs
    print("Deal ID:", servio_deal_id)
    print("Comm Link:", f"https://erp.serviotech.com{doc.get_url()}")
    print("Subject:", subject)
    print("User:", agent_name)