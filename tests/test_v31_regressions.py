from datetime import datetime, timedelta, timezone
from io import BytesIO
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from hiremed.core import cv_text
from hiremed.freshness import freshness
from hiremed.resume_optimizer import make_package, to_docx, to_pdf
from pypdf import PdfReader


def test_docx_labeled_hyperlink_extracted(tmp_path):
    doc = Document()
    p = doc.add_paragraph('LinkedIn: ')
    rel = p.part.relate_to('https://www.linkedin.com/in/test-person', RT.HYPERLINK, is_external=True)
    h = OxmlElement('w:hyperlink'); h.set(qn('r:id'), rel)
    r = OxmlElement('w:r'); t = OxmlElement('w:t'); t.text = 'My profile'; r.append(t); h.append(r); p._p.append(h)
    file = tmp_path/'cv.docx'; doc.save(file)
    assert 'https://www.linkedin.com/in/test-person' in cv_text(file)


def test_links_clickable_in_both_exports():
    text = 'Test Candidate\nGitHub https://github.com/testcandidate\nLinkedIn https://linkedin.com/in/testcandidate\nSUMMARY\nPython engineer.'
    package = make_package(text, {'title':'Engineer', 'description':'Python engineer'}, use_ai=False)
    doc = Document(BytesIO(to_docx(package)))
    targets = [r.target_ref for r in doc.part.rels.values() if r.reltype == RT.HYPERLINK]
    assert 'https://github.com/testcandidate' in targets
    assert 'https://linkedin.com/in/testcandidate' in targets
    reader = PdfReader(BytesIO(to_pdf(package)))
    uris = [str(a.get_object().get('/A', {}).get('/URI')) for page in reader.pages for a in page.get('/Annots', [])]
    assert 'https://github.com/testcandidate' in uris
    assert 'https://linkedin.com/in/testcandidate' in uris


def test_original_date_overrides_fresh_repost():
    now = datetime(2026, 11, 9, tzinfo=timezone.utc)
    assert not freshness({'posted_at':(now-timedelta(days=1)).isoformat(), 'original_posted_at':(now-timedelta(days=12)).isoformat()}, now)['allowed']
