# Pilot Himalayas + Arbeitnow

## Stare

Folder: D:\Proiecte\job-market-data-platform-sources. Branch feature/multiple-sources pornit din v1.0. main si feature/ml-classification raman separate, fara merge. Implementat adaptor si pilot offline de transformare/validare; integrarea multi-source in DAG, audit si baza de date NU este implementata.

## Ce face fiecare fisier nou

- src/sources/arbeitnow.py: citire GET publica, timeout30, retry limitat pentru429/5xx, backoff si Retry-After, paginare controlata (maximum20), respingerea linkurilor externe/ciclurilor si deduplicare dupa slug. Prima aparitie este pastrata. Nu porneste automat.
- src/sources/adapters.py: mapare explicita la coloanele cerute de transformarea existenta, curatare HTML, provenienta si filtru larg de titluri. source_tags sunt pastrate separat, nu confundate cu skill-uri sau categorii normalizate.
- src/sources_pilot.py: citeste numai snapshoturi locale, combina datele, foloseste transformarea si regulile de calitate existente, apoi salveaza acceptate/respinse/raport/candidati duplicate in data/sources/. Fara DB sau Azure.
- tests/test_sources.py: fixture-uri sintetice pentru identitate, duplicate, URL-uri de paginare, valori lipsa si date invalide.

## Schema si decizii

Arbeitnow slug devine source_job_id, cu guid calificat arbeitnow:<slug>. GUID-ul Himalayas existent este pastrat pentru compatibilitate. source, source_job_id, source_url, location_text, remote si source_tags sunt retinute in artefactele pilotului. Persistarea source/source_job_id/source_url este implementata in loader si migratia 004, verificata intr-o baza temporara. Aplicarea pe baza persistenta este inca neexecutata. location_text/remote/source_tags raman numai in artefactele pilotului.

created_at se mapeaza la pubDate epoch; invaliditatea este verificata de transform/quality. company_name devine companyName. URL-ul este un link la anunt, nu garantat aplicare directa. job_types devine text de employmentType fara a pretinde o taxonomie uniforma. Salariu, moneda, perioada salariului si expirare lipsa raman NULL. location este location_text; nu este copiat ca restrictie de eligibilitate.

Filtrul larg gaseste candidati; politica versionata src/sources/policy.py decide include/exclude/review. Include numai titluri explicite pentru cele patru roluri, inclusiv Data Platform Engineer si Analyste Data. Exclude protectia datelor, centrele de date fizice, pre-sales si rolurile medicale/clinice explicite. Managementul, arhitectura, consultanta si titlurile mixte necesita revizuire. Descrierile au ajutat inspectia, dar politica automata foloseste numai titlul; nu exista un benchmark uman de relevanta. Regulile Himalayas si ML raman neschimbate.

In interiorul sursei eliminam slug-uri repetate intre pagini. Intre surse, titlu+companie normalizate genereaza numai candidati pentru revizuire; nu stergem sau unim automat. Pot exista diferente de locatie ori posturi multiple cu acelasi titlu.

## Rulare offline

Docker Desktop trebuie sa fie activ. Din folderul sources:

```powershell
docker compose --profile sources build sources-pilot
docker compose --profile sources run --rm sources-pilot python -m pytest tests/test_sources.py tests/test_transform.py tests/test_quality.py tests/test_stages.py tests/test_extract.py tests/test_azure_storage.py -q
docker compose --profile sources run --rm sources-pilot python -m src.sources_pilot --himalayas data/sources/input/himalayas.json --arbeitnow data/sources/input/page-1.json data/sources/input/page-2.json data/sources/input/page-3.json --output data/sources/pilot-policy-20261010
```

Outputul trebuie sa fie un director nou; nu suprascriem rezultatele. accepted.json si rejected.json pastreaza provenienta; quality_report.json include numere si roluri pe sursa; duplicate_candidates.json contine candidatii fara modificarea randurilor. Snapshoturile sunt locale/ignorate si nu sunt incluse intr-un clone Git. Exemplarele locale provin din explorari read-only: Himalayas8octombrie, Arbeitnow10octombrie, deci nu reprezinta aceeasi perioada.

Serviciul sources-pilot are profil optional, network_mode:none, fara env Azure/DB si fara depends_on. Ruleaza independent, fara a porni Airflow sau PostgreSQL. Citirea live src/arbeitnow.fetch_jobs necesita o retea disponibila, se testeaza ulterior explicit; pilotul offline nu o apeleaza.

## Izolare si costuri

Compose project job-market-data-platform-sources, PostgreSQL localhost15435 si Airflow localhost18083, ambele bind127.0.0.1. .env are secrete locale noi si Azurefalse, fara credentiale copiate. Nu porni stiva completa pentru acest pilot. Nu copia .env stabil si nu folosi numele proiectului Docker stabil. Programarile DAG raman schedule=None si template-ul Databricks PAUSED.

Conditiile API Arbeitnow cer link catre https://www.arbeitnow.com/ ; atribuirea este inclusa in raport si trebuie pastrata in viitoarea prezentare/dashboard. Cod si fixture-uri sintetice versionabile; dataseturile brute raman locale.

## Urmatoarele etape, neimplementate

1. Revizuirea umana a candidatilor ambigui si validarea politicii de relevanta.
2. Persistenta provenientei si audit separat pentru surse, cu migrari si teste DB.
3. Orchestrare Airflow cu extrageri separate si transform/validate/load comune, comportament explicit la esecul unei surse.
4. Comparatii Power BI si deduplicare intre surse, fara pierderea provenientei.

Referinte: https://www.arbeitnow.com/blog/job-board-api ; https://www.arbeitnow.com/terms .


## Rezultat verificat — 10 octombrie 2026

Build Docker reusit; **37 de teste trecute** (7 multi-source si 30 regresii de baza). Pilot offline: 131 Himalayas + 46 candidati Arbeitnow = 177 acceptate tehnic, 0 respinse. Arbeitnow: 750 aparitii, 719 slug-uri unice, 31 repetari eliminate si 673 titluri filtrate.

Roluri Arbeitnow: 8 Data Engineer, 4 Data Scientist, 6 Machine Learning Engineer, 28 Other, 0 Data Analyst. Acceptarea tehnica nu confirma relevanta; politica celor 28 Other trebuie rafinata inainte de load.

Artefacte locale: data/sources/pilot-20261010/accepted.json, rejected.json, quality_report.json, duplicate_candidates.json. Provenienta, identitatile unice si cele 46 de salarii Arbeitnow NULL au fost verificate. Zero grupuri candidate dupa titlu + companie intre aceste snapshoturi; nu este o concluzie generala despre duplicate.

Config offline verificat. Nu s-au testat DB, Spark, DAG sau clientul live nou; nu exista load, upload ori integrarea sursei in audit. main ramane a9420b6, ML b9f9aa3; fara merge, push sau commit. Docker a fost pornit de utilizatoare; programarile raman oprite.


## Politica rafinata — 10 octombrie 2026

Din cei 46 de candidati: **21 inclusi, 10 exclusi, 15 pentru revizuire**. Din cele 28 Other initiale, 3 primesc rol explicit (2 Data Platform Engineer si 1 Analyste Data), 10 sunt excluse si 15 raman ambigue. Pilotul nou pastreaza 131 Himalayas + 21 Arbeitnow = **152 acceptate tehnic, 0 respinse la calitate**. Arbeitnow: 10 Data Engineer, 4 Data Scientist, 6 Machine Learning Engineer, 1 Data Analyst.

review.json pastreaza randurile ambigue cu explicatii; source_selection.json inregistreaza decizia, motivul si versiunea pentru toate cele 719 identitati Arbeitnow. Excluderea pentru relevanta este separata de respingerea pentru calitate. Cele 15 cazuri nu sunt incarcate si nu sunt fortate intr-o categorie. Rezultatele initiale raman in directorul anterior; noul output este data/sources/pilot-policy-20261010/. **46 teste trecute**, inclusiv clasificari ambigue/negative si separarea revizuirii de calitate. Nu s-a executat load, upload sau activare de programari.


## Revizuire asistata pe snapshot — 10 octombrie 2026

Responsabilitatile din descrieri sustin 3 includeri suplimentare Data Engineer si 4 excluderi din taxonomia actuala; 8 cazuri mixte raman review. Aceste decizii sunt facute de asistent, nu reprezinta un benchmark validat uman. Conducerea Data Science/Platform, arhitectura si rolurile mixte raman vizibile separat.

src/sources/review.py aplica optional decizii explicite legate de SHA-256 al titlului, companiei si descrierii. Modificarea continutului, identitati necunoscute/repetate si decizii invalide sunt respinse. Deciziile reale sunt locale; nu se generalizeaza regulile la toate anunturile similare. Fara optiune, pilotul foloseste politica automata anterioara.

```powershell
docker compose --profile sources run --rm sources-pilot python -m src.sources_pilot --himalayas data/sources/input/himalayas.json --arbeitnow data/sources/input/page-1.json data/sources/input/page-2.json data/sources/input/page-3.json --review-decisions data/sources/review-decisions-20261010.json --output data/sources/pilot-reviewed-20261010
```

Rezultat verificat: 24 incluse, 14 excluse, 8 review din 46 candidati; 131 Himalayas + 24 Arbeitnow = 155 acceptate tehnic, 0 respinse. Roluri Arbeitnow: DE13/DS4/MLE6/DA1. 47 teste trecute. Continutul celor 8 review nu intra in accepted.json; review.json si source_selection.json pastreaza motivele. Fara DB/Azure/Airflow, fara merge. Snapshoturile si deciziile reale nu sunt distribuite in Git; testele folosesc date sintetice.


## Organizarea codului

Clientii si logica de integrare sunt in src/sources/: arbeitnow.py (API), adapters.py (schema comuna), policy.py (selectie automata), review.py (revizuiri pe snapshot). src/sources_pilot.py ramane punctul de intrare CLI, pentru a pastra comenzile existente. Modulele ETL de baza si punctele de intrare Airflow raman direct in src; nu introducem foldere suplimentare pentru fiecare fisier. Aceasta reorganizare nu modifica comportamentul sau datele.


## Provenienta PostgreSQL — implementare testata izolat

004_source_provenance.sql adauga source/source_job_id/source_url, completeaza randurile istorice din acest proiect ca Himalayas si creeaza index unic pe (source, source_job_id). GUID-urile existente raman intacte. Aplicati explicit aceasta migrare dupa 001–003 in baza dedicata branch-ului, inainte de rularea loaderului modificat. Nu se aplica automat unei baze existente prin Docker restart. Backfill-ul presupune date istorice exclusiv Himalayas; nu reutilizati pe o baza cu alte surse neidentificate.

upsert_jobs pastreaza sursa si linkul, actualizeaza linkul modificat si refuza schimbarea identitatii unui GUID existent. Loturile legacy fara provenienta sunt compatibile ca Himalayas; loturile Arbeitnow necesita campuri explicite. Teste sintetice reale PostgreSQL: 28 trecute, plus 47 offline. Nicio incarcare de snapshot real si nicio migrare a bazei stabile/persistente nu au fost executate. Auditul pe sursa si DAG-ul multi-source raman neimplementate.

```powershell
docker compose -p job-market-sources-tests -f compose.sources-test.yaml up --abort-on-container-exit --exit-code-from test-runner
docker compose -p job-market-sources-tests -f compose.sources-test.yaml down
```

Imaginea runnerului este construita cu comanda build sources-pilot de mai sus. Baza de test este temporara (tmpfs), fara porturi publicate si pe retea interna; autentificarea trust este limitata acestei stive de teste sintetice. Nu utilizati aceasta configuratie pentru date persistente. Nu stergeti volumele proiectului pentru aplicarea migrarilor.


## Incarcare persistenta verificata — 10 octombrie 2026

Migrarile 001–004 au fost aplicate bazei dedicate sources, initial goala. src/sources_load.py reverifica snapshotul acceptat si converteste datele ISO inainte de UPSERT. Serviciul manual sources-load primeste numai configuratia DB, fara Azure. Auditul pe surse nu este inca implementat pentru aceasta comanda.

```powershell
docker compose up -d --wait db
Get-Content sql/migrations/*.sql | docker compose exec -T db psql -v ON_ERROR_STOP=1 -1 -U postgres -d job_market_db
docker compose --profile sources run --rm sources-load python -m src.sources_load --accepted data/sources/pilot-reviewed-20261010/accepted.json
```

Rulati numai din worktree-ul sources, cu .env propriu. Rezultat: 155 insert la prima rulare, prima repetare 2 update/153 skip din comparatia float cu NUMERIC. Dupa uniformizare Decimal: 155 skip, zero update. SQL confirma 131 Himalayas + 24 Arbeitnow cu identitati si linkuri, zero duplicate (source, source_job_id). Cele 8 review nu sunt incarcate. Baza dedicata ramane pornita; docker compose stop db din acest folder o poate opri pastrand datele. Versiunea stabila, Azure si programarile sunt neschimbate.


## Audit LOAD pe sursa — verificat 10 octombrie 2026

Migratia005 este aplicata bazei sources. sources_load produce run_id UUID nou la fiecare apel si cate un rand source_load_runs pentru fiecare sursa. Istoricul nu este suprascris. Auditul include timpi, status, input_rows, accepted/rejected si metrici UPSERT. Mutatiile intregului lot si auditul success sunt atomice. La esec, lotul este rollback si sursele sunt marcate failed, cu zero mutatii si numai tipul exceptiei.

Auditul se refera la snapshotul incarcat/revalidat: input_rows nu inseamna numarul tuturor joburilor extrase de API. Excluderile de relevanta si review sunt in artefactele pilotului, nu in rejected. Continut JSON ilizibil sau sursa lipsa esueaza inainte de a putea identifica sursele. Intreruperea brusca poate lasa running; reconcilierea nu este implementata in acest pas. Nu este inca auditul extragerii live sau DAG-ului multi-source.

30 teste PostgreSQL trecute. Lot real: Himalayas131/Arbeitnow24, ambele success, zero insert/update/reject, skipped131/24. Interogare:

```sql
SELECT run_id, source, status, input_rows, accepted, rejected,
       inserted, updated, skipped, started_at, finished_at, error_type
FROM source_load_runs ORDER BY started_at DESC;
```


## Orchestrare Airflow multi-source — demonstratie snapshot verificata

job_market_multi_source ruleaza doua extrageri paralele, apoi process (transformare, selectie, validare impreuna), apoi load. Programare None, implicit mode=snapshot; mode=live se selecteaza explicit si nu a fost verificat in demonstratia aceasta. Snapshoturile ignorate trebuie sa existe in data/sources/input. Nu aplica automat revizuirile asistate ale snapshotului vechi. Se foloseste politica automata: 131 Hima +21 Arbeitnow in demo. Cele3randuri suplimentare deja existente nu sunt sterse.

Migratia006 este aplicata bazei sources. source_extraction_attempts retine tentativele pe sursa, mode, numarul extras, status si tipul erorii; ultimele tentative ale ambelor surse trebuie sa fie success. source_load_runs.workflow_run_id coreleaza incarcarea cu run_id Airflow. Numerele extrase sunt cele unice din snapshot/client, nu toate aparitiile brute ale paginilor. Auditul selectiei si calitatii detaliate ramane in quality_report.json/source_selection.json/review.json; process nu are tabela proprie de tentative. Intreruperile bruste pot lasa running; reconcilierea ramane viitoare.

31 teste DB trecute, zero erori import DAG. Run manual__sources_demo_20261010 este success, toate4taskuri success. Extract snapshot131/719, load152skipped (131/21), zero insert/update. Confirmat prin CLI si auditDB, fara captura UI sau verificare live/API. DAG repus pe pauza, stiva sources ramane pornita la localhost18083.

```powershell
docker compose exec -T airflow-scheduler airflow dags unpause job_market_multi_source
docker compose exec -T airflow-scheduler airflow dags trigger job_market_multi_source
docker compose exec -T airflow-scheduler airflow dags pause job_market_multi_source
```

Puneti pe pauza dupa terminarea demonstratiei, nu imediat dupa trigger. Run-urile noi au directoare distincte dupa hashul run_id, iar procesarea foloseste director separat pentru fiecare tentativa. Pentru o demonstrație din UI, folositi DAG-ul nou si mode=snapshot. Nu schimbati schedule pentru demonstrație.


## Rulare live verificata — 10 octombrie 2026

Run manual__sources_live_20261010, mode=live: DAG si toate4taskurile success in circa26sec. API Himalayas324; Arbeitnow745identitati unice, maxim3pagini. Filtru Arbeitnow51candidati:24incluse/10excluse/17review. Lot348acceptate,0qualityrejected. Rolurile Other Himalayas raman limita clasificarii existente; acceptarea tehnica nu confirma relevanta.

UPSERT pe surse: Himalayas309insert/9update/6skip; Arbeitnow4insert/9update/11skip. Reincarcare a fisierului acceptat, fara API:0insert/0update/348skip. Baza cumulata468joburi (440Hima/28Ar), zero duplicate de identitate. Nu stergem joburile care nu apar in lotul curent. Auditul coreleaza extragerea si incarcarea cu run_id Airflow; revizuirile snapshotului vechi nu sunt aplicate datelor noi.

Programarea ramaneNone, DAG repus pause dupa succes. Confirmare prin CLI, auditDB si raport JSON; UI screenshot/log serving prin browser nu au fost verificate. Azure si proiectul stabil nu au fost modificate. Serviciile sources raman pornite. Aceasta sectiune actualizeaza limitarile istorice despre fluxul live neverificat.


## Comparatii BI pregatite
View-uri source_summary/source_roles/source_skills aplicate. JobMarketSources.pbip este un model separat cu snapshot468joburi. Raportul are doua pagini verificate in Desktop la 11.10.2026; refresh snapshot, filtre sursa/rol si procente DAX validate. Importul PostgreSQL din Desktop a fost verificat la 14.10.2026: Refresh fara erori, 468 anunturi, filtre Arbeitnow/Data Engineer si procente conforme SQL. Raport salvat cu UsePostgreSQL=true; pentru snapshot offline se foloseste false. Actualizare manuala, fara refresh programat Service. Vezi powerbi/SOURCES_README.md pentru cele2pagini, filtre, interpretare si checklist. Raportul original intact.


## Demonstrație completă — 14 octombrie 2026

Run `manual__demo_complete_20261014`, mod `live`: extragere Himalayas + Arbeitnow → process → load → Refresh Power BI. Toate cele patru taskuri Airflow au reușit din prima încercare, între 12:11:29 și 12:12:05 Europe/Bucharest (aproximativ 36 secunde). DAG-ul a fost repus pe pauză; `schedule=None` rămâne neschimbat.

| Sursă | Extrase | Acceptate tehnic | Inserate | Actualizate | Omise | Respinse de calitate |
|---|---:|---:|---:|---:|---:|---:|
| Himalayas | 351 | 351 | 351 | 0 | 0 | 0 |
| Arbeitnow | 822 | 20 | 19 | 0 | 1 | 0 |

Arbeitnow: 49 candidate după titlu, 20 incluse, 3 excluse și 26 pentru revizuire; alte 773 în afara filtrului. Cele 26 ambigue nu sunt încărcate și nu reprezintă respingeri tehnice de calitate. Acceptarea tehnică Himalayas nu confirmă relevanța; 252 din lot sunt clasificate Other de regulile existente.

Baza cumulată a crescut de la **468 la 838 anunțuri**: 791 Himalayas și 47 Arbeitnow. Nu se șterg anunțurile istorice care lipsesc din lotul nou. Zero duplicate de identitate `(source, source_job_id)`; nu s-a verificat/eliminat dublarea semantică între surse. Auditul extragerii și auditul încărcării sunt corelate prin run_id.

Refresh din PostgreSQL în Power BI a reușit: **838 anunțuri, 369 cu salariu, 44,0% acoperire globală**. Filtrul Arbeitnow + Data Engineer: **22 anunțuri, Python 16/72,7%, SQL 13/59,1%**, conforme SQL; total procentual gol. Filtrele au fost resetate și raportul salvat. Eticheta veche cu data snapshotului a fost înlocuită cu explicația actualizării manuale; snapshotul offline inclus rămâne cel din 10.10.2026 (468), separat de baza actuală.

Dovezi agregate fără date brute sau credențiale: `docs/evidence/demo-multi-source-20261014.json`. Verificarea Airflow a folosit stările CLI și metadatele DB; nu este o verificare nouă a UI sau a log serving. Nu s-au rulat teste de idempotentă suplimentare în această demonstrație și nu se pretinde că regula de relevanță este validată de oameni. Azure și celelalte proiecte nu au fost modificate. Fără commit/push/merge.

Pentru repetare: pornește Docker și serviciile sources, scoate temporar DAG-ul `job_market_multi_source` de pe pauză, declanșează un run cu ID nou și `mode=live`, așteaptă succesul tuturor taskurilor, verifică auditul, apoi repune DAG-ul pe pauză și apasă Refresh în `JobMarketSources.pbip`. Modul implicit `snapshot` nu apelează API-urile; alege explicit `live` pentru date noi. Nu modifica schedule și nu șterge volumele.
