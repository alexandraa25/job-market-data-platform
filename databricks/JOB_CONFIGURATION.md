# Configuratia Job-ului Free Edition

## Fisiere

- job.template.json: setarile exportate, cu calea notebookului inlocuita cu <NOTEBOOK_PATH> si programarea PAUSED pentru instalari noi.
- job.schedule-options.jsonc: exemplu comentat PORNIT/OPRIT, doar pentru lectura; Jobs API necesita JSON strict.
- job.observed.json: setari si executii verificate, cu datele si sursa confirmarii.
- job.export.json: exportul original din workspace, pastrat local si ignorat de Git deoarece include calea personala a notebookului.

## Configuratie

Job: job_market_free_edition. Task: process_job_market, Notebook / WORKSPACE, cu notebookul Job_Market_PySpark_Complet. Compute: Serverless; nu este inclus un cluster clasic. Concurenta maxima 1, queue enabled, PERFORMANCE_OPTIMIZED, task activ ALL_SUCCESS. Timeout Job/task 0 inseamna fara limita configurata. Nu sunt destinatari de notificari sau parametri de task expliciti; se folosesc valorile widgeturilor notebookului. Versiunea mediului Serverless nu este presupusa.

Programarea optionala: Quartz 47 15 19 * * ?, Europe/Bucharest, adica 19:15:47. Implicit PAUSED. Rularile By scheduler din 5, 6 si 7 octombrie 2026 au fost confirmate Succeeded prin captura utilizatoarei, examinata la 8 octombrie. Pauza live a fost confirmata ulterior prin eticheta Paused. Orele complete si ID-urile acelor rulari sunt trunchiate in captura, deci nu sunt deduse.

## Reproducere

1. Creeaza volumele managed workspace.default.raw si workspace.default.processed.
2. Incarca manual raw.json in /Volumes/workspace/default/raw/raw.json.
3. Importa Job_Market_PySpark_FreeEdition.py cu numele Job_Market_PySpark_Complet.
4. Intr-o copie a template-ului, inlocuieste <NOTEBOOK_PATH> cu calea reala din workspace. Nu publica tokenuri sau credentiale.
5. Creeaza Job-ul prin UI sau Jobs API autentificat, pastrand programarea PAUSED. Daca exista deja, actualizeaza Job-ul existent, fara duplicate.
6. Foloseste Run now, verifica Succeeded si manifestul rezultatului.

Sursa ramane snapshotul incarcat manual; nu exista sincronizare automata Azure/Airflow cu Free Edition. Nu este necesara modificarea abonamentului Azure la Pay-As-You-Go pentru aceasta demonstratie Free Edition.

## Pornire si oprire

In Job > Schedules & Triggers foloseste Resume/Unpause pentru activare si Pause pentru oprire. Confirma eticheta Paused. Modificarea unui fisier local nu modifica Job-ul live. Run now ramane disponibil cand programarea este pe pauza. Inainte de analiza unor date noi, inlocuieste raw.json.

Ghidul unic pentru Airflow, Docker, Azure si Databricks: [operare](../docs/OPERATIONS.md).

Referinta: [Jobs API](https://docs.databricks.com/api/jobs/v2/job), [Serverless notebook jobs](https://docs.databricks.com/aws/en/dev-tools/bundles/examples).
