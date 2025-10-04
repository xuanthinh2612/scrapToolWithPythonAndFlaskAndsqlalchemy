from __future__ import print_function
import base64
import os.path
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.utils import parsedate_to_datetime
import re

from app.const import MAX_RESULTS

# Quyền cần để đọc Gmail
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def get_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES, redirect_uri="http://localhost:5000/"
            )
            creds = flow.run_local_server(port=5001)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)


def search_emails(query, max_results=MAX_RESULTS):
    service = get_service()
    emails = []
    page_token = None

    while len(emails) < max_results:
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=100,  # Gmail API giới hạn tối đa 100 / lần
            pageToken=page_token
        ).execute()

        messages = results.get('messages', [])
        for msg in messages:
            if len(emails) >= max_results:
                break
            txt = service.users().messages().get(userId='me', id=msg['id']).execute()
            payload = txt['payload']
            headers = payload.get('headers', [])
            subject, date = None, None
            for h in headers:
                if h['name'] == 'Subject':
                    subject = h['value']
                if h['name'] == 'Date':
                    date = h['value']

            parts = payload.get('parts')
            body = ""
            if parts:
                for part in parts:
                    if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode()
                        break
            else:
                if 'data' in payload['body']:
                    body = base64.urlsafe_b64decode(payload['body']['data']).decode()

            emails.append({
                'subject': subject,
                'date': date,
                'body': body
            })

        page_token = results.get('nextPageToken')
        if not page_token:
            break

    return emails


def get_order_detail():
    from app import db
    from app.models import OrderDetail

    # Tìm tất cả email của Uniqlo có chữ "ご注文を受付けました" (đặt hàng thành công)
    uniqlo_emails = search_emails('from:(noreply-order@ml.store.uniqlo.com) "ご注文を受付けました" newer_than:10d')
    # return uniqlo_emails
    for e in uniqlo_emails:
        send_date = parsedate_to_datetime(e['date']).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        mail_content = e['body']
        # receiver_name: lấy chuỗi kết thúc bằng "様"
        receiver_name_match = re.search(r"^(.*?)様", mail_content)
        receiver_name = receiver_name_match.group(0).strip() if receiver_name_match else None

        # order_code: sau ご注文番号：
        order_code_match = re.search(r"ご注文番号：([0-9\-]+)", mail_content)
        order_code = order_code_match.group(1) if order_code_match else None

        # delivery_plan: sau 配送予定日：
        delivery_plan_match = re.search(r"配送予定日：([0-9/]+ - [0-9/]+)", mail_content)
        delivery_plan = delivery_plan_match.group(1) if delivery_plan_match else None
        order = OrderDetail.query.filter_by(order_code=order_code).first()
        if not order:
            new_order = OrderDetail(
                send_date=send_date,
                mail_content=mail_content,
                update_date=send_date,
                sender="noreply-order@ml.store.uniqlo.com",
                receiver_name=receiver_name,
                order_code=order_code,
                delivery_plan=delivery_plan,
                order_status="ordered"

            )
            db.session.add(new_order)
    db.session.commit()


def update_order_detail():
    from app import db
    from app.models import OrderDetail

    # Tìm tất cả email của Uniqlo có chữ "ご注文商品の出荷準備が完了しました" (đặt hàng thành công)
    ready_to_delivery_emails = search_emails(
        'from:(noreply-order@ml.store.uniqlo.com) "ご注文商品の出荷準備が完了しました" newer_than:10d')
    ready_to_take_out_emails = search_emails(
        'from:(noreply-order@ml.store.uniqlo.com) "ご注文商品準備完了のお知らせ" newer_than:10d')
    delivered_emails = search_emails(
        'from:(mail@kuronekoyamato.co.jp) "お荷物お届け完了のお知らせ" newer_than:10d')
    canceled_emails = search_emails(
        'from:(noreply-order@ml.store.uniqlo.com) "ご注文をキャンセルしました" newer_than:10d')

    for e in ready_to_delivery_emails:
        update_date = parsedate_to_datetime(e['date']).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        mail_content = e['body']
        # Regex patterns
        order_pattern = r"ご注文番号：([0-9\-]+)"
        company_pattern = r"配送会社：(.+)"
        tracking_pattern = r"配送伝票番号：([0-9]+)"
        delivery_tracking_link_pattern = r"https?://toi\.kuronekoyamato\.co\.jp/cgi-bin/tneko\?[\w=&]+"

        delivery_tracking_link_match = re.search(delivery_tracking_link_pattern, mail_content)
        order_code_match = re.search(order_pattern, mail_content)
        delivery_company_match = re.search(company_pattern, mail_content)
        delivery_tracking_code_match = re.search(tracking_pattern, mail_content)

        order_code = order_code_match.group(1).strip() if order_code_match else None
        delivery_company = delivery_company_match.group(1).strip() if delivery_company_match else None
        delivery_tracking_code = delivery_tracking_code_match.group(1).strip() if delivery_tracking_code_match else None
        delivery_tracking_link = delivery_tracking_link_match.group()

        order = OrderDetail.query.filter_by(order_code=order_code).first()
        if order and order.order_status in ["ordered"]:
            order.order_status = "ready_to_delivery"
            order.update_date = update_date
            order.delivery_company = delivery_company
            order.delivery_tracking_code = delivery_tracking_code
            order.delivery_tracking_link = delivery_tracking_link
            db.session.add(order)

    for e in ready_to_take_out_emails:
        update_date = parsedate_to_datetime(e['date']).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        mail_content = e['body']
        # Regex patterns
        order_pattern = r"ご注文番号：([0-9\-]+)"
        store_name_pattern = r"受取店舗名：(.+)"
        receive_dead_line_pattern = r"受取期限：([0-9/]+)"

        order_code_match = re.search(order_pattern, mail_content)
        store_name_match = re.search(store_name_pattern, mail_content)
        receive_dead_line_match = re.search(receive_dead_line_pattern, mail_content)

        order_code = order_code_match.group(1).strip() if order_code_match else None
        store_name = store_name_match.group(1).strip() if store_name_match else None
        receive_dead_line = receive_dead_line_match.group(1).strip() if receive_dead_line_match else None

        order = OrderDetail.query.filter_by(order_code=order_code).first()
        if order and order.order_status in ["ordered"]:
            order.order_status = "ready_to_receive"
            order.store_name = store_name
            order.receive_dead_line = receive_dead_line
            order.update_date = update_date
            db.session.add(order)

    for e in delivered_emails:
        update_date = parsedate_to_datetime(e['date']).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        mail_content = e['body']
        # Regex patterns
        tracking_pattern = r"送り状番号\s*([0-9\-]+)"
        delivery_tracking_code_match = re.search(tracking_pattern, mail_content)
        delivery_tracking_code = (delivery_tracking_code_match.group(1).strip()
                                  .replace("-", "")) if delivery_tracking_code_match else None

        order = OrderDetail.query.filter_by(delivery_tracking_code=delivery_tracking_code).first()
        if order and order.order_status in ["ready_to_delivery"]:
            order.order_status = "completed"
            order.update_date = update_date
            db.session.add(order)

    for e in canceled_emails:
        update_date = parsedate_to_datetime(e['date']).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        mail_content = e['body']
        # Regex patterns
        order_pattern = r"ご注文番号：([0-9\-]+)"
        order_code_match = re.search(order_pattern, mail_content)
        order_code = order_code_match.group(1).strip() if order_code_match else None

        order = OrderDetail.query.filter_by(order_code=order_code).first()
        if order and order.order_status not in ["canceled"]:
            order.order_status = "canceled"
            order.update_date = update_date
            db.session.add(order)

    db.session.commit()


def start_scan_email():
    from run import app
    from datetime import datetime

    print("Scanning email...", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    with app.app_context():
        get_order_detail()
        time.sleep(30)
        update_order_detail()

    print("Scanning completed at: ", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
