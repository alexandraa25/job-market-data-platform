# Pornire si oprire

Acest branch foloseste stiva Docker job-market-data-platform-ml, separata de folderul stabil. PostgreSQL: localhost:15434; Airflow: localhost:18081. Nu copia .env sau datele din folderul stabil.

## Configuratie implicita

Cele trei DAG-uri folosesc schedule=None. Programarile anterioare sunt pastrate comentate. Template-ul Databricks este PAUSED. Serviciul etl are profilul manual: docker compose up -d nu il porneste. Datele si volumele existente nu sunt sterse.

## Instalare pe un calculator nou

Ai nevoie de Docker Desktop cu Linux containers si Docker Compose, Internet, porturile 15434 si 18081 libere. Power BI Desktop este optional pentru raport.

1. Cloneaza repository-ul si intra in folderul lui.
2. Copiaza .env.example in .env. Inlocuieste DB_PASSWORD, AIRFLOW_JWT_SECRET si AIRFLOW_API_SECRET_KEY cu valori locale. Pentru DB_PASSWORD foloseste caractere URL-safe deoarece conexiunea SQLAlchemy este construita ca URL. Pastreaza AZURE_UPLOAD_ENABLED=false pentru demonstratia locala. Nu publica .env.
3. Construieste si porneste serviciile:

```powershell
docker compose build airflow-init airflow-api-server airflow-scheduler airflow-dag-processor
docker compose up -d airflow-api-server airflow-scheduler airflow-dag-processor
docker compose ps -a
```

Pe volume noi, PostgreSQL aplica sql/init.sql si analytics_views.sql; airflow-init migreaza metadatele. Un init terminat cu Exit 0 este normal.

4. Configuratia implicita foloseste SimpleAuthManager (doar pentru dezvoltare), cu utilizatorul admin. Parola este generata de API server la prima pornire. O poti vedea numai in terminalul tau local:

```powershell
docker compose exec airflow-api-server cat /opt/airflow/simple_auth_manager_passwords.json.generated
```

Nu publica rezultatul sau logurile care contin parola. Deschide http://localhost:18081 si autentifica-te. Fisierul generat nu este montat persistent in aceasta configuratie; dupa recrearea API serverului verifica parola din nou. Pentru productie este necesar un mecanism de autentificare adecvat. Nu folosi airflow users create: configuratia curenta nu foloseste FAB.

## O singura rulare Airflow

Porneste Docker Desktop si serviciile ca mai sus. In UI foloseste Unpause pentru job_market_etl, apoi Trigger DAG. Cu schedule=None nu apar executii periodice. Verifica toate cele cinci task-uri: extract, transform, validate, load, spark_process. Dupa demonstratie poti pune DAG-ul din nou pe Pause.

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
