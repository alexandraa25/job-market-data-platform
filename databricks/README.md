# Databricks — pregătire pentru migrare

**Stare:** demonstrația independentă Databricks Free Edition a reușit pe Serverless la 5 octombrie 2026. Notebookul demonstrativ executat este `Job_Market_PySpark_Demo.py`; captura se află în `../docs/images/databricks-free-edition-success.png`. Integrarea parametrizată Unity Catalog/ADLS rămâne pregătită și testată local, fără execuție cloud verificată. Airflow continuă să folosească Spark local.

## Abonament și costuri

Utilizatoarea a confirmat la 5 octombrie 2026 că abonamentul Azure este încă Free Trial. [Documentația Microsoft](https://learn.microsoft.com/en-us/azure/databricks/getting-started/free-trial) cere un abonament care nu este Free Trial pentru fluxul Azure Databricks și descrie trecerea la Pay-As-You-Go. Această schimbare permite facturarea; nu a fost efectuată. Trial Databricks de 14 zile cu DBU gratuite nu înseamnă toate resursele Azure gratuite. Eligibilitatea, quota și prețurile trebuie verificate înainte de compute.

[Databricks Free Edition](https://learn.microsoft.com/en-us/azure/databricks/getting-started/free-edition-limitations) poate fi folosit pentru demonstrații fără cost de platformă, cu serverless și quota. Aceasta ar fi o demonstrație cu fișiere încărcate în volumele platformei, nu migrarea verificată a integrării Azure ADLS existente.

## Fișiere

- `databricks/job_market_notebook.py`: notebook Python importabil, parametri run_id/raw_volume/processed_volume, sesiunea Spark gestionată.
- `src/cloud_process.py`: citește JSON prin Spark cu schemă explicită, folosește transformările comune, scrie Parquet în directoare unice și verifică recitirea și egalitatea rândurilor; publică manifestul ultimul.
- `src/spark_process.py`: include raw_schema și transform_frame reutilizabile; CLI local și taskul Airflow rămân funcționale.
- `tests/test_cloud_process.py`: compatibilitate cu intrarea locală, rânduri respinse, manifest și blocarea batchului gol.

Nu se creează `local[2]` și nu se oprește sesiunea Databricks. Nu sunt necesare valori de secret în notebook. Datele sunt citite de Spark din volume; obiectul JSON actual conține un array jobs, astfel că un fișier mare rămâne o unitate de citire multiline. Pentru scalare suplimentară, raw va trebui schimbat în JSON Lines sau mai multe fișiere.

## Configurare Azure Databricks după stabilirea eligibilității

1. Workspace în North Europe, de exemplu `dbw-job-market-dev`, în grupul existent `rg-job-market-dev`. Nu presupune disponibilitatea regiunii, nivelului de preț sau compute pentru abonament.
2. Access Connector `ac-job-market-dev`, în North Europe, cu system-assigned managed identity. [Instrucțiuni Microsoft](https://learn.microsoft.com/en-us/azure/databricks/connect/unity-catalog/cloud-storage/azure-managed-identities).
3. Configurează rolurile pentru identitatea connectorului, separat de service principal local: modelul limitat descris de Microsoft folosește Storage Blob Delegator pe storage account și Storage Blob Data Contributor pe containerele raw/processed. Setează raw read-only la external location/volume pentru consumatorii Databricks și acordă doar READ VOLUME pe raw, READ/WRITE VOLUME pe processed.
4. În Catalog → External Data, creează Storage Credential din Access Connector și două External Locations pentru `abfss://raw@stjobmarketalex2026.dfs.core.windows.net/` și `abfss://processed@stjobmarketalex2026.dfs.core.windows.net/`. Nu activa file events pentru acest batch; nu sunt necesare roluri Queue/EventGrid.
5. Într-un catalog/schema disponibile, creează două External Volumes care acoperă aceste containere. Verifică drepturile USE CATALOG, USE SCHEMA și drepturile volume. Nu recrea sau șterge containerele existente. [Volume Unity Catalog](https://learn.microsoft.com/en-us/azure/databricks/volumes/utility-commands).
6. Importă repo-ul sau fișierele păstrând `src/` lângă `databricks/`; notebookul trebuie să ruleze din directorul databricks, într-un runtime cu suport Unity Catalog Volumes și funcțiile Spark utilizate. Compatibilitatea exactă cu runtime/serverless rămâne de verificat în workspace.
7. Setează run_id la identificatorul unei rulări raw existente și volumele reale, de exemplu `/Volumes/job_market/default/raw` și `/Volumes/job_market/default/processed`.
8. Rulează notebookul pe compute ales după verificarea costurilor. Dacă folosești compute clasic, configurează auto-termination și o configurație minimă acceptată de politica workspace-ului. Nu seta încă o programare repetată.

Output: `processed-volume/databricks/jobs/<run-hash>/<processing-id>/accepted`, `rejected` și `manifest.json`. Acest namespace separă verificarea cloud de versiunile produse de Spark local. Manifestul enumeră căile și contorii, cu engine=databricks-managed-spark; verificarea este după conținutul rândurilor Parquet, nu SHA256 byte cu byte precum uploaderul SDK local. O execuție întreruptă poate lăsa directoare fără manifest; retenția nu este automată.

## Verificare și trecerea Airflow

```bash
docker compose --profile spark run --rm --entrypoint python spark -m pytest tests/test_spark_process.py tests/test_cloud_process.py -q -p no:cacheprovider
```

Patru teste locale trecute: includ comparația snapshotului cu Pandas și citirea JSON/scrierea Parquet pe calea modulului cloud. Asta nu verifică autentificarea Unity Catalog, runtime-ul Databricks sau costurile. După notebook cloud reușit: creează un Job cu parametrul run_id, pregătește autentificarea API din Airflow, apoi înlocuiește execuția Spark locală cu declanșarea și așteptarea Job-ului. Aceste schimbări nu sunt încă implementate.

## Reproducerea demonstrației Free Edition

1. În Catalog, creează volume managed `raw` și `processed` sub `workspace.default`.
2. Încarcă un snapshot raw JSON local în rădăcina raw, ca `raw.json`. Datele brute nu sunt incluse în Git; folosește un artefact al pipeline-ului.
3. Importă `Job_Market_PySpark_Demo.py` din File → Import/Workspace Import și selectează Python/Serverless.
4. Rulează celulele în ordine. Notebookul este independent și nu necesită importul src sau secrete Azure.
5. Rezultatul demonstrat: 128 acceptate, 0 respinse; Parquet salvat în `/Volumes/workspace/default/processed/job_market/<uuid>/accepted`, recitit cu 128 rânduri. UUID-ul schimbă directorul la fiecare execuție. Modul overwrite a fost folosit deoarece mediul a respins errorifexists.

Limite ale notebookului executat: deduplicarea nu selectează determinist dintre duplicate diferite; salariile/datele neconvertibile devin null, fără flag separat; nu include extracția competențelor, validarea completă, persistarea rândurilor respinse sau manifestul. Verificarea Parquet este doar de număr de rânduri. `src/cloud_process.py` reprezintă varianta reutilizabilă mai completă, cu alt contract de căi (jobs/run-hash/raw.json), dar nu a fost executată în Free Edition. Nu confunda această demonstrație cu migrarea automată Azure/Airflow.

## Notebook completat pentru Free Edition

`Job_Market_PySpark_FreeEdition.py` este varianta independentă nouă, gata de import. `Job_Market_PySpark_Demo.py` păstrează exportul original demonstrat în captură. Varianta nouă a fost executată cu succes în workspace Free Edition pe Serverless la 5 octombrie 2026: 128 acceptate, 0 respinse, Parquet verificat și manifest publicat.

Importă fișierul Source .py ca notebook nou `Job_Market_PySpark_Complet`. Selectează Serverless și execută Run all. Parametrii `raw_path` și `processed_root` au implicit căile volumelor workspace.default existente. Nu sunt necesare repo import, secrete sau pachete Azure.

Funcțiile raw_schema, transform_frame și partition sunt incluse în notebook din regulile Spark ale proiectului. Schema explicită și flagurile originale disting salariile/datele neconvertibile de valorile lipsă. Conversiile, salariile negative/NaN/Infinity, intervalele inversate și câmpurile obligatorii sunt verificate; prima apariție GUID este păstrată după poziția din snapshot. Sunt derivate și cele 17 competențe. Timestampurile folosesc UTC. Nu se estimează salarii și nu se convertesc monede.

Output într-un director UUID nou: accepted/ și rejected/ în Parquet, quality_report.json cu input/deduplicated/duplicates_removed/accepted/rejected/rejected_percent/reason_counts, apoi manifest.json cu status success și căile rezultatului. Raportul este scris înainte de verificarea finală și poate avea status validated; numai manifestul final confirmă succesul complet. Verificarea recitește ambele Parqueturi și compară contorul și conținutul rândurilor în ambele direcții.

Dacă toate rândurile sunt respinse, notebookul păstrează rejected/ și raportul blocked_no_accepted_rows, ridică eroare și nu publică manifest. O întrerupere poate lăsa artefacte fără manifest; nu există retenție automată. Reexecutarea produce alt director. datele raw rămân snapshotul încărcat manual; Airflow/Azure rămân separate.

Teste locale:

```bash
docker compose --profile spark run --rm --entrypoint python spark -m pytest tests/test_free_notebook.py -q -p no:cacheprovider
```

Două teste verifică conversii greșite, negative/Infinity, deduplicarea deterministă, competențele, Parquet/manifest și batchul complet respins. Confirmarea în Free Edition este realizată prin captura notebookului Job_Market_PySpark_Complet: 128 acceptate, 0 respinse și manifest publicat.

Verificare Free Edition, 5 octombrie 2026: notebookul complet afișează 128 acceptate, 0 respinse, Parquet verificat și manifest la `/Volumes/workspace/default/processed/job_market/8ea0adbd6d0a4d43b81d5099c592cc26/manifest.json`. Aceasta confirmă execuția manuală a notebookului complet; încărcarea raw rămâne manuală, iar Job-ul Databricks a fost verificat ulterior prin Run now.

## Databricks Job verificat

La 5 octombrie 2026, Job-ul `job_market_free_edition`, task `process_job_market`, a executat notebookul complet pe Serverless cu starea **Succeeded**. Rularea a fost lansată manual prin Run now și a durat 1 minut și 18 secunde: 128 acceptate, 0 respinse, Parquet verificat și manifest nou publicat. Sursa rămâne snapshotul încărcat manual; nu există încă o programare cloud confirmată sau integrare de declanșare din Airflow.

## Actualizarea snapshotului și programarea Free Edition

Job-ul job_market_free_edition a fost programat de utilizatoare zilnic la 19:15:47, Europe/Bucharest; aceasta este confirmarea configurației raportată de utilizatoare, nu dovada unei execuții automate. Airflow colectează local la 19:07; aceste ore nu conectează automat sursa cu Databricks. Calculatorul/Docker sunt necesare Airflow, dar nu Job-ului cloud.

Pentru actualizare manuală: folosește raw.json din data/runs/<sha256(run_id)> al unei rulări reușite, încarcă-l în /Volumes/workspace/default/raw/raw.json și confirmă înlocuirea fișierului existent, apoi pornește Run now. Nu încărca snapshoturi pe jumătate cât timp un Job le citește. Programarea următoare va utiliza fișierul înlocuit. Snapshot actualizat pregătit din run databricks_snapshot_20261005_1520, colectat la 5 octombrie 2026, 15:20 Europe/Bucharest; toate cele cinci task-uri Airflow au reușit. Încărcarea actualizării în Databricks rămâne de făcut de utilizatoare.

Configurație reproductibilă Job: [instrucțiuni și setări](JOB_CONFIGURATION.md). Șablonul este salvat; exportul exact a fost furnizat de utilizatoare și păstrat local și nu s-a efectuat deploy.
