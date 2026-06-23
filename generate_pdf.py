import json
import os
import html
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib import colors

def create_job_pdf(json_path="scraped_jobs.json", output_path="jobs_report.pdf"):
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Data file {json_path} not found.")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # In case data has 'orgs' dict
    if "orgs" in data:
        orgs_data = data["orgs"]
    else:
        orgs_data = data

    doc = SimpleDocTemplate(output_path, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    title_style = styles['Title']
    org_title_style = ParagraphStyle(
        'OrgTitle',
        parent=styles['Heading1'],
        textColor=colors.HexColor('#293681'),
        spaceAfter=12
    )
    job_title_style = ParagraphStyle(
        'JobTitle',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=6
    )
    link_style = ParagraphStyle(
        'Link',
        parent=styles['Normal'],
        textColor=colors.blue,
        spaceAfter=12
    )
    normal_style = styles['Normal']

    story = []
    
    story.append(Paragraph("Government Job Scraper Report", title_style))
    story.append(Spacer(1, 20))

    has_jobs = False

    for org_key, org_info in orgs_data.items():
        if isinstance(org_info, dict) and "jobs" in org_info:
            jobs = org_info["jobs"]
            name = org_info.get("name", org_key.upper())
        elif isinstance(org_info, list):
            jobs = org_info
            name = org_key.upper()
        else:
            continue

        if not jobs:
            continue
            
        has_jobs = True
        story.append(Paragraph(html.escape(f"Organization: {name}"), org_title_style))
        
        for job in jobs:
            title = html.escape(job.get("title", "No Title"))
            link = html.escape(job.get("link", "#"))
            date = html.escape(job.get("date", ""))
            
            job_text = f"<b>{title}</b>"
            if date:
                job_text += f" (Date: {date})"
                
            story.append(Paragraph(job_text, job_title_style))
            
            if link and link != "#":
                # Create a clickable hyperlink in the PDF with short text to save space
                link_text = f'<link href="{link}"><font color="blue"><u>Click Here to View Job</u></font></link>'
                story.append(Paragraph(link_text, link_style))
            else:
                story.append(Paragraph("No Link Provided", normal_style))
        
        story.append(Spacer(1, 15))

    if not has_jobs:
        story.append(Paragraph("No active job listings found in the dataset.", normal_style))

    doc.build(story)
    return output_path

if __name__ == "__main__":
    create_job_pdf()
