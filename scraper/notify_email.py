# notify_email.py
# Handles sending batched job alerts via SMTP (Gmail)

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

def send_email_notifications(new_postings, orgs_config):
    """
    Constructs and sends a multipart HTML/text email containing new job listings.
    """
    smtp_email = os.environ.get("SMTP_EMAIL")
    smtp_app_password = os.environ.get("SMTP_APP_PASSWORD")
    notify_email_to = os.environ.get("NOTIFY_EMAIL_TO")
    
    if not (smtp_email and smtp_app_password and notify_email_to):
        print("Warning: Email credentials (SMTP_EMAIL, SMTP_APP_PASSWORD, NOTIFY_EMAIL_TO) are not fully set. Skipping email notification.")
        return
        
    print("Preparing email notifications...")
    date_str = datetime.now().strftime("%d %b %Y")
    subject = f"[Govt Job Tracker] New Job Postings Found - {date_str}"
    
    text_content = f"Government Job Notification Tracker\nNew Job Postings Detected on {date_str}\n\n"
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }}
            h1 {{ color: #003366; border-bottom: 2px solid #003366; padding-bottom: 8px; font-size: 1.8em; }}
            h2 {{ color: #00509d; border-bottom: 1px solid #ddd; padding-bottom: 4px; font-size: 1.3em; margin-top: 20px; }}
            ul {{ list-style-type: none; padding-left: 0; }}
            li {{ margin-bottom: 12px; padding: 8px; background-color: #f9f9f9; border-left: 4px solid #00509d; border-radius: 2px; }}
            a {{ color: #0066cc; text-decoration: none; font-weight: bold; }}
            a:hover {{ text-decoration: underline; }}
            .deadline {{ color: #cc0000; font-size: 0.9em; font-weight: bold; margin-left: 10px; }}
            .footer {{ font-size: 0.8em; color: #777; margin-top: 30px; border-top: 1px solid #eee; padding-top: 10px; }}
        </style>
    </head>
    <body>
        <h1>Government Job Notification Tracker</h1>
        <p>The following new recruitment notifications were detected on <strong>{date_str}</strong>:</p>
    """
    
    for org_key, postings in new_postings.items():
        org_name = orgs_config.get(org_key, {}).get("name", org_key.upper())
        text_content += f"=== {org_name} ===\n"
        html_content += f"<h2>{org_name}</h2><ul>"
        
        for post in postings:
            title = post["title"]
            is_uncertain = post.get("relevance") == "uncertain"
            display_title = f"⚠️ [Uncertain] {title}" if is_uncertain else title
            link = post["link"]
            date_info = f" (Deadline: {post['date']})" if post["date"] else ""
            
            text_content += f"- {display_title}: {link}{date_info}\n"
            
            deadline_html = f'<span class="deadline">{date_info}</span>' if date_info else ''
            li_style = ' style="border-left: 4px solid #ff9900; background-color: #fffdf5;"' if is_uncertain else ''
            html_content += f'<li{li_style}><a href="{link}">{display_title}</a>{deadline_html}</li>'
            
        text_content += "\n"
        html_content += "</ul>"
        
    html_content += """
        <br>
        <div class="footer">
            <p>This is an automated notification from your personal Government Job Tracker running on GitHub Actions.</p>
        </div>
    </body>
    </html>
    """
    
    # Assemble MIMEMultipart email
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = smtp_email
    msg['To'] = notify_email_to
    
    msg.attach(MIMEText(text_content, 'plain'))
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        # Establish secure STARTTLS connection with Gmail
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=15)
        server.starttls()
        server.login(smtp_email, smtp_app_password)
        server.sendmail(smtp_email, notify_email_to, msg.as_string())
        server.quit()
        print("Email notifications sent successfully.")
    except Exception as e:
        print(f"Error sending email notification: {e}")
