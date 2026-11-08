"""Generate truthful draft documents in memory, using only candidate evidence."""
from io import BytesIO
from docx import Document
from .core import llm_json

def draft_application(profile,job,assessment):
    if not assessment.get('eligible'):
        raise ValueError('Cannot draft for unverified eligibility')
    response=llm_json('Write a concise, factual job application. Return keys cover_letter and cv_summary as strings. Only use facts explicitly present in the candidate profile. Never invent years, degrees, names, or certifications.',str({'profile':profile,'job':job,'assessment':assessment}))
    if not response or not isinstance(response.get('cover_letter'),str) or not isinstance(response.get('cv_summary'),str):
        raise RuntimeError('Gemini draft unavailable; no fabricated document produced')
    return response

def draft_docx(text,title):
    doc=Document();doc.add_heading(title,0)
    for paragraph in text.split('\n'):
        if paragraph.strip():doc.add_paragraph(paragraph.strip())
    stream=BytesIO();doc.save(stream);return stream.getvalue()
