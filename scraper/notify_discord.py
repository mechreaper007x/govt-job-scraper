# notify_discord.py
# Handles sending batched job alerts to Discord via Incoming Webhook

import os
import requests

def format_discord_message(new_postings, orgs_config):
    """
    Formats new postings into markdown segments under 2000 characters.
    """
    intro = "🔔 **[Job Notification Tracker] New Openings Detected!**\n\n"
    chunks = []
    current_chunk = intro

    for org_key, postings in new_postings.items():
        org_name = orgs_config.get(org_key, {}).get("name", org_key.upper())
        org_section = f"**{org_name}**\n"
        
        for post in postings:
            title = post["title"]
            if post.get("relevance") == "uncertain":
                title = f"⚠️ [Uncertain] {title}"
            link = post["link"]
            date_info = f" (Deadline: {post['date']})" if post["date"] else ""
            line = f"• [{title}]({link}){date_info}\n"
            
            # If the current chunk is getting too large, push it and start a new one
            if len(current_chunk) + len(org_section) + len(line) > 1900:
                chunks.append(current_chunk)
                current_chunk = ""
                
            if not current_chunk.startswith(f"**{org_name}**") and current_chunk != "":
                current_chunk += org_section
            elif current_chunk == "":
                current_chunk += org_section
                
            current_chunk += line
            
        current_chunk += "\n"

    if current_chunk.strip():
        # Clean trailing newlines
        chunks.append(current_chunk.strip())
        
    return chunks

def send_discord_notifications(new_postings, orgs_config):
    """
    Pushes batched postings to Discord if webhook URL is configured.
    """
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("Warning: DISCORD_WEBHOOK_URL is not set. Skipping Discord notification.")
        return

    print("Sending Discord notifications...")
    chunks = format_discord_message(new_postings, orgs_config)
    
    for idx, chunk in enumerate(chunks):
        try:
            r = requests.post(webhook_url, json={"content": chunk}, timeout=10)
            r.raise_for_status()
            print(f"Sent Discord message chunk {idx + 1}/{len(chunks)}")
        except Exception as e:
            print(f"Error sending message chunk {idx + 1} to Discord: {e}")
