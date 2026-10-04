import pytest
from sqlalchemy import text
from test_load_integration import engine, jobs
from src.load import upsert_jobs
from src.reconcile import reconcile
from src.audit import begin_stage


def test_dimensions_update_and_repeat(engine,jobs):
    upsert_jobs(jobs,engine)
    upsert_jobs(jobs,engine)
    with engine.connect() as c:
        assert c.execute(text('SELECT count(*) FROM companies')).scalar_one()==1
        assert c.execute(text('SELECT count(*) FROM job_skills')).scalar_one()==2
        assert c.execute(text('SELECT company_id FROM jobs')).scalar_one() is not None
    changed=jobs.copy()
    changed['has_python']=0
    changed['companyName']='Other Company'
    upsert_jobs(changed,engine)
    with engine.connect() as c:
        assert c.execute(text('SELECT count(*) FROM job_skills')).scalar_one()==1
        assert c.execute(text('SELECT name FROM companies JOIN jobs USING(company_id)')).scalar_one()=='Other Company'


@pytest.mark.parametrize('state,expected',[('success','success'),('failed','failed'),('running','running')])
def test_reconcile_terminal_only(engine,state,expected):
    with engine.begin() as c:
        c.execute(text('CREATE TABLE dag_run(dag_id TEXT,run_id TEXT,state TEXT,end_date TIMESTAMPTZ)'))
        c.execute(text('CREATE TABLE task_instance(dag_id TEXT,run_id TEXT,task_id TEXT,state TEXT,map_index INTEGER)'))
        c.execute(text("INSERT INTO dag_run VALUES ('job_market_etl','run',:state,CURRENT_TIMESTAMP-INTERVAL '5 minutes')"),{'state':state})
        c.execute(text("INSERT INTO task_instance VALUES ('job_market_etl','run','extract',:state,-1)"),{'state':state})
    begin_stage(engine,'run','extract','airflow')
    begin_stage(engine,'manual','extract','manual')
    assert reconcile(engine,engine)==(0 if state=='running' else 1)
    assert reconcile(engine,engine)==0
    with engine.connect() as c:
        assert c.execute(text("SELECT status FROM job_runs WHERE run_id='run'")).scalar_one()==expected
        assert c.execute(text("SELECT status FROM job_runs WHERE run_id='manual'")).scalar_one()=='running'
        assert c.execute(text("SELECT inserted FROM job_runs WHERE run_id='run'")).scalar_one() is None
