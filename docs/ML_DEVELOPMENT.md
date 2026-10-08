# Doua foldere pentru prezentare si dezvoltare

## Varianta stabila

Folder: D:\Proiecte\job-market-data-platform. Branch main, versiunea prezentata v1.0. Nu schimba acest folder pe branch-ul ML si nu copia peste el fisierele in dezvoltare.

## Dezvoltare ML

Folder: D:\Proiecte\job-market-data-platform-ml. Branch feature/ml-classification, pornit din tagul v1.0. Acesta este un Git worktree, nu un repository independent. Istoricul Git, tagurile si remote-ul sunt comune; fisierele de lucru sunt separate.

Modelul ML nu este inca implementat. Folderul este pregatit pentru lucrul ulterior, fara antrenari sau colectari automate.

## Izolare

Compose project: job-market-data-platform-ml, stabilit atat in compose.yaml cat si in .env.example. Volumele PostgreSQL si reteaua Docker primesc acest prefix si nu sunt cele ale stivei stabile. Porturile ML sunt 15434 pentru PostgreSQL si 18081 pentru Airflow, legate la 127.0.0.1.

.env local are secrete noi, fara credentialele Azure ale versiunii stabile, AZURE_UPLOAD_ENABLED=false. Datele si logurile sunt locale acestui folder; nu au fost copiate. Programarile raman schedule=None si template-ul Databricks PAUSED. Nu folosi -p cu numele stivei stabile si nu copia .env-ul stabil peste cel ML.

## Lucru in VS Code

Deschide folderul stabil pentru demonstratie si folderul ML pentru dezvoltare. Verifica terminalul inainte de comenzi: git branch --show-current. In folderul ML trebuie sa afiseze feature/ml-classification.

Pentru verificarea configuratiei fara pornire: docker compose config --services. Pentru pornire, cand este necesara:

```powershell
cd D:\Proiecte\job-market-data-platform-ml
docker compose build airflow-init airflow-api-server airflow-scheduler airflow-dag-processor
docker compose up -d airflow-api-server airflow-scheduler airflow-dag-processor
```

Airflow: http://localhost:18081. Procedura de autentificare si rulare manuala este in OPERATIONS.md. Oprire in acelasi folder: docker compose stop. Pornirea stivei nu executa ETL-ul independent, deoarece serviciul etl are profil manual.

## Versionare

Commiturile ML raman pe feature/ml-classification. Nu folosim git merge in main pana cand functionalitatea este verificata si dorim integrarea. v1.0 ramane un reper fix. O viitoare v2.0 va fi marcata numai dupa implementare si validare; existenta folderului ML nu inseamna ca v2.0 este finalizata.

Un merge viitor trebuie sa pastreze configuratia pentru prezentare si sa trateze deliberat diferentele de porturi si nume ale stivei ML. Git nu versioneaza bazele de date, .env sau datele generate. Nu sterge folderul worktree manual; gestioneaza-l ulterior prin git worktree.
