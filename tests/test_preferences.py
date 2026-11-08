from hiremed.preferences import evaluate

def test_approved_job():
    job={'title':'IT Support','description':'English speaking remote position','location':'Poland','arrangement':'remote','salary_monthly_gross_pln':9000,'language':'en'}
    assert evaluate(job)['allowed']

def test_low_salary_rejected():
    job={'title':'IT Support','description':'English remote','location':'Poland','arrangement':'remote','salary_monthly_gross_pln':7000,'language':'en'}
    assert evaluate(job)['rejected']

def test_missing_salary_requires_review():
    job={'title':'IT Support','description':'English remote','location':'Poland','arrangement':'remote','language':'en'}
    assert not evaluate(job)['allowed']
    assert 'Gross monthly salary unconfirmed' in evaluate(job)['unknown']

def test_onsite_rejected():
    job={'title':'IT Support','location':'Poland','arrangement':'onsite','salary_monthly_gross_pln':9000,'language':'en'}
    assert evaluate(job)['rejected']
