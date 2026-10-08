# Job Market Data Platform v1.0

Versiune de portofoliu pentru ingestie API, transformare, validare, UPSERT PostgreSQL, procesare PySpark, arhivare Azure optionala si raportare Power BI.

## Modificari

- Programari oprite implicit, cu variantele PORNIT comentate in cele trei DAG-uri.
- Job template Databricks PAUSED si referinta JSONC pentru reactivare.
- Serviciul ETL independent are profil manual; pornirea normala Compose nu lanseaza procesarea.
- Ghid unic de operare si documentatie actualizata cu executiile automate confirmate.

## Verificari

Instalare locala verificata la 8 octombrie 2026 intr-un proiect Docker izolat, cu volume noi, credentiale temporare si Azure dezactivat. Build din sursele publice cu cache Docker. Schema si view-uri create, Airflow initializat, autentificare API reusita, DAG-uri importate fara erori. Rulare orchestrata: 5 task-uri success la prima incercare, 131 acceptate, 0 respinse, 131 inserate si Parquet local verificat. Teste: 62 passed, 1 skipped pentru snapshotul demonstrativ absent din clone.

Rularile automate Airflow pentru 5–7 octombrie au fost confirmate; doua au pornit tarziu. Databricks By scheduler / Succeeded pentru 5–7 octombrie si pauza ulterioara sunt confirmate vizual.

## Limite

Mediu de dezvoltare local, SimpleAuthManager si credentiale demonstrative pentru metadate. Nu este o instalare de productie. Uploadul Azure ramane optional. Databricks Free Edition primeste snapshotul manual, fara transfer sau dependenta automata fata de Airflow. Nu exista retentie automata a fisierelor. Instalarea pe un cont Azure nou, workspace nou Databricks si refresh-ul direct Power BI nu au fost repetate in verificarea locala.

Vezi [ghidul de operare](OPERATIONS.md). Datele existente sunt pastrate; activarea unei rulari manuale cu upload Azure poate consuma stocare/credit.
