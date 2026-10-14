# Pornire si oprire

## Configuratie implicita

Cele patru DAG-uri folosesc schedule=None. Programarile anterioare sunt pastrate comentate. Template-ul Databricks este PAUSED. Serviciul etl are profilul manual: docker compose up -d nu il porneste. Datele si volumele existente nu sunt sterse.

## Baza unica dupa consolidarea din 14.10.2026

Folderul operator local este `D:/Proiecte/job-market-data-platform`. `.env` local pastreaza numele Compose `job-market-data-platform-sources` pentru a reutiliza volumele existente, cu PostgreSQL `localhost:15435` si Airflow `http://localhost:18083`. Numele tehnic nu inseamna ca exista doua baze active. Nu porniti Docker din vechiul worktree sources: configuratia lui locala a fost dezactivata prin golirea `COMPOSE_PROJECT_NAME`.

Baza business unica `job_market_db` are 1.388 de joburi: 1.341 Himalayas si 47 Arbeitnow. Au fost adaugate 550 de joburi lipsa din baza v1, fara suprascrierea celor 271 de identitati deja prezente. Istoricul vechi de audit a fost importat cu pastrarea inregistrarilor existente la conflict. Relatiile companii/competente au fost refacute pentru joburile importate; nu exista identitati duplicate sau companii nemapate pentru nume nenule.

Backup-urile ambelor baze au fost restaurate integral in baze temporare de verificare, apoi acele baze temporare au fost eliminate. Baza v1 si serviciile ei sunt oprite; volumul vechi este pastrat doar pentru recuperare. Backup-urile/configuratiile sunt locale in `data/backups/`, ignorate de Git. Baza metadata Airflow ramane separata, asa cum cere Airflow; nu este o a doua copie a datelor business.

Din folderul operator folositi `docker compose up -d airflow-api-server airflow-scheduler airflow-dag-processor`, respectiv `docker compose stop`. Cele patru DAG-uri raman pe pauza si cu programare oprita; Azure upload ramane false. Metadatele si logurile stivei sources au fost pastrate, iar artefactele locale au fost copiate in folderul principal cu arhivarea fisierelor inlocuite.

Raportul Sources foloseste in continuare `localhost:15435`. Conexiunile PostgreSQL din raportul original au fost aliniate la acelasi port; modul lui implicit ramane snapshot (`UsePostgreSQL=false`). Pentru date reale seteaza true. Dupa redeschiderea PBIP, executa Refresh in Desktop. **Refresh-ul dupa consolidare nu a fost verificat in Desktop**; importurile/capturile anterioare raman dovezi istorice, nu valori curente.

## Alte instalari si upgrade

COMPOSE_PROJECT_NAME, DB_HOST_PORT si AIRFLOW_HOST_PORT sunt obligatorii. .env.example descrie instalari separate pe volume noi. Configuratia locala consolidata descrisa mai sus are prioritate pe acest laptop.

Pentru upgrade-ul bazei principale existente, pastrati numele original job-market-data-platform, porturile5433/8080 si parola volumului in .env, faceti backup, opriti consumatorii si executati:

```powershell
docker compose stop airflow-scheduler airflow-api-server airflow-dag-processor
docker compose up -d db
docker compose run --rm db-migrate
# Dupa Exit 0:
docker compose up -d airflow-api-server airflow-scheduler airflow-dag-processor
```

Schema este migrata in tranzactie, cu blocare advisory pentru a evita doua initializari concurente. La eroare se face rollback si consumatorii nu trec de conditia de succes. Nu se sterg volume. Nu schimbati parola POSTGRES din .env pentru un volum existent fara schimbarea explicita a parolei in baza.

Pentru a verifica exclusiv noua schema fara Airflow: docker compose up -d db-migrate, apoi verificati Exit0 in docker compose ps -a. Pentru o stiva existenta, docker compose run --rm db-migrate forteaza reverificarea chiar daca un container one-shot anterior exista deja.

## Instalare pe un calculator nou

Ai nevoie de Docker Desktop cu Linux containers si Docker Compose, Internet, porturile alese explicit in .env libere (principal: 5433/8080; sources: 15435/18083). Power BI Desktop este optional pentru raport.

1. Cloneaza repository-ul si intra in folderul lui.
2. Copiaza .env.example in .env. Inlocuieste DB_PASSWORD, AIRFLOW_JWT_SECRET si AIRFLOW_API_SECRET_KEY cu valori locale. Pentru DB_PASSWORD foloseste caractere URL-safe deoarece conexiunea SQLAlchemy este construita ca URL. Pastreaza AZURE_UPLOAD_ENABLED=false pentru demonstratia locala. Nu publica .env.
3. Construieste si porneste serviciile:

```powershell
docker compose build airflow-init airflow-api-server airflow-scheduler airflow-dag-processor
docker compose up -d airflow-api-server airflow-scheduler airflow-dag-processor
docker compose ps -a
```

Pe volume noi, PostgreSQL aplica sql/init.sql, apoi db-migrate aplica atomic migrarile001–006 si analytics_views.sql/source_analytics_views.sql. Consumatorii DB asteapta succesul db-migrate; airflow-init migreaza separat metadatele. Un init terminat cu Exit 0 este normal.

4. Configuratia implicita foloseste SimpleAuthManager (doar pentru dezvoltare), cu utilizatorul admin. Parola este generata de API server la prima pornire. O poti vedea numai in terminalul tau local:

```powershell
docker compose exec airflow-api-server cat /opt/airflow/simple_auth_manager_passwords.json.generated
```

Nu publica rezultatul sau logurile care contin parola. Deschide portul AIRFLOW_HOST_PORT ales (http://localhost:8080 pentru principal sau http://localhost:18083 pentru sources) si autentifica-te. Fisierul generat nu este montat persistent in aceasta configuratie; dupa recrearea API serverului verifica parola din nou. Pentru productie este necesar un mecanism de autentificare adecvat. Nu folosi airflow users create: configuratia curenta nu foloseste FAB.

## O singura rulare Airflow

Pentru multi-source foloseste job_market_multi_source cu mode=live si cele4taskuri; mode=snapshot necesita fisierele locale ignorate din data/sources/input. Dupa succes pune DAG-ul inapoi pe pauza si executa Refresh in Power BI.

Pentru fluxul original: porneste Docker Desktop si serviciile ca mai sus. In UI foloseste Unpause pentru job_market_etl, apoi Trigger DAG. Cu schedule=None nu apar executii periodice. Verifica toate cele cinci task-uri: extract, transform, validate, load, spark_process. Dupa demonstratie poti pune DAG-ul din nou pe Pause.

Alternativa manuala pentru cele patru etape PostgreSQL (nu include task-ul Spark):

```powershell
docker compose run --rm --build etl
```

## Reactivarea programarii Airflow

In dags/job_market_dag.py comenteaza schedule=None si decomenteaza schedule="7 19 * * *". In dags/job_market_monitor_dag.py si dags/audit_reconcile_dag.py procedeaza identic pentru schedule="*/5 * * * *". Salveaza, asteapta preluarea de catre dag-processor, apoi foloseste Unpause pentru toate trei. Nu sunt necesare build-uri pentru modificarea DAG-urilor montate.

ETL ruleaza la 19:07 Europe/Bucharest, iar monitorizarea/reconcilierea la fiecare cinci minute. Calculatorul, Docker si serviciile trebuie sa fie active. Pentru oprire: Pause in UI si restaureaza schedule=None in fisiere. Pauza nu anuleaza un run deja inceput.

## Upload Azure

Pentru o demonstratie fara Azure, pastreaza AZURE_UPLOAD_ENABLED=false in .env. Pentru upload, foloseste true si completeaza credentialele aplicatiei, contul, containerele private raw/processed si rolurile Blob Data Contributor. Dupa schimbarea .env:

```powershell
docker compose up -d airflow-api-server airflow-scheduler airflow-dag-processor
```

Cu true, o rulare manuala poate incarca fisiere. Oprirea programarilor previne uploadurile periodice, dar datele existente pot consuma in continuare stocare/credit.

## Databricks Free Edition

Rulare manuala: actualizeaza /Volumes/workspace/default/raw/raw.json prin incarcare manuala si foloseste Run now la job_market_free_edition. Programarea poate ramane Paused.

Reactivare: Job > Schedules & Triggers > Resume/Unpause. Oprire: Pause; verifica eticheta Paused. Ora este 19:15:47 Europe/Bucharest. Modificarea job.template.json nu modifica Job-ul live. job.schedule-options.jsonc explica ambele variante, dar nu este un payload Jobs API.

Nu exista transfer automat intre Airflow/Azure si Free Edition. Fara inlocuirea raw.json, Job-ul reproceseaza acelasi snapshot.

## Oprirea serviciilor fara stergerea datelor

```powershell
docker compose stop
```

Repornire cu comanda explicita pentru cele trei servicii Airflow. Nu folosi docker compose down -v pe mediul cu date: elimina volumele bazei. Pauza Databricks se gestioneaza separat si nu depinde de Docker.

## Verificare si mentenanta

Metadatele Airflow confirma starea completa a DAG-ului; job_runs descrie cele patru etape PostgreSQL. Spark poate esua dupa ce load a actualizat deja baza. Pentru esec exclusiv Spark reia numai spark_process; pentru refacerea etapelor precedente reia si dependentele.

Testele necesita Python 3.11, Java 17, requirements.txt si requirements.spark.txt. Pentru integrare configureaza TEST_DATABASE_URL catre o baza dedicata cu nume terminat in _test si AZURE_UPLOAD_ENABLED=false. Nu folosi baza de business.

Nu exista curatare automata a artefactelor sau politica de retentie Azure in aceasta versiune.


## Verificarea bootstrap-ului — 14.10.2026

Testata configuratia Compose reala pe un proiect temporar cu volum nou si port aleator: db-migrate Exit0, coloanele de provenienta NOT NULL, tabelele de audit si ambele seturi de view-uri prezente. A doua rulare a reusit. Pe o baza v1 temporara, randul existent si-a pastrat identitatea si linkul, provenienta a fost completata, apoi loaderul a inserat un rand si l-a omis la repetare. O migrare invalida introdusa numai in test a esuat, iar DDL-ul precedent din aceeasi tranzactie a fost rollback.

Configuratia fara nume/porturi explicite a fost refuzata inainte de pornire. Loaderul s-a construit si a pornit cu imaginea derivata dintr-un alt nume Compose. Regresia Python/PostgreSQL: 78passed, 3module Spark omise in imaginea fara PySpark; cele5teste Spark trecute anterior nu au fost repetate pentru schimbari limitate la setup/documentatie. Verificarea de schema si backfill este adaugata in GitHub Actions; workflow-ul a trecut ulterior pe PR #1 si pe main (commit be1a4db). Serviciile reale Airflow nu au fost recreate in aceasta verificare, iar bazele reale nu au fost migrate sau combinate.


## Verificare dupa consolidare — 14.10.2026

Rulare manuala live `manual__post_consolidation_20261014`: toate cele4 taskuri Airflow success. Himalayas: 351 acceptate, 351 omise ca neschimbate. Arbeitnow: 21 acceptate, 2 inserate, 10 actualizate, 9 omise. Zero respingeri tehnice si zero identitati duplicate. Baza are acum 1.390 de joburi (1.341 Himalayas, 49 Arbeitnow), dintre care604 cu salariu.

Refresh complet Schema and data verificat in Power BI Desktop: 1.390 anunturi,604 cu salariu,43,5% acoperire; tabelul surselor corespunde SQL. Raportul a fost salvat. Toate cele4 DAG-uri au revenit pe pauza; programarile raman None si Azure upload false. Valorile1388 din consolidare si838 din demonstratia anterioara sunt istorice, nu totaluri curente. Dovezi agregate: `docs/evidence/post-consolidation-demo-20261014.json`.
