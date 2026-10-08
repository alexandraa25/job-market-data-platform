# Demonstratie locala a extensiei ML

Folder: D:\Proiecte\job-market-data-platform-ml. Branch: feature/ml-classification. main/v1.0 ramane separat; nu exista merge, push sau lansare v2.

## Generarea paginii

Docker Desktop trebuie sa fie activ. Din folderul ML:

```powershell
docker compose --profile ml run --rm --entrypoint python ml -m src.ml_demo --model models/title-only-final-20261008/model.joblib
```

Deschide data/ml/demo/index.html in browser, direct de pe disc. Pagina nu necesita un server, Azure, PostgreSQL sau Airflow. Daca serverul local de etichetare este inca activ, poate fi accesata si la http://localhost:18082/demo/index.html.

Pagina afiseaza opt titluri sintetice, categoria regulilor, predictia ML, scorul si semnalul de revizuire. Include cazuri ambigue; exemplele nu sunt un test de performanta. Modifica ml/demo_jobs.jsonl pentru alte titluri si regenereaza pagina. Descrierea nu este folosita de candidatul cu titlul singur.

Scorul este predict_proba necalibrat; un scor mare nu garanteaza o eticheta corecta. Semnalul de revizuire foloseste pragul demonstrativ 0.55. Modelul local este incarcat numai dupa verificarea SHA256 fata de manifest; foloseste numai artefacte locale de incredere.

## Cum prezinti in 2–3 minute

1. Prezinta proiectul stabil: ingestie, validare, UPSERT, audit, Airflow si Power BI.
2. Explica extensia: ai verificat daca invatarea din exemple depaseste regulile de clasificare.
3. Arata pagina demonstrativa si cateva rezultate, inclusiv un titlu ambiguu. Nu interpreta scorul ca garantie.
4. Prezinta testul final: 65/80 corecte pentru ML, 72/80 pentru reguli. Macro F1 favorizeaza usor ML, dar unele categorii au un singur exemplu.
5. Explica decizia: ai pastrat regulile, pentru ca rezultatele nu sustin promovarea modelului.

Formulare posibila: „Am construit o extensie NLP cu etichete umane, am comparat reprezentari text si am evaluat candidatul pe anunturi noi rezervate. Am pastrat solutia bazata pe reguli dupa analiza rezultatelor si am documentat limitele modelului.”

## Reproductibilitate si stare

Codul, testele, instructiunile, exemplul sintetic si rapoartele agregate sunt versionate. Modelele, dataseturile, etichetele si jurnalul personal sunt ignorate. Un clone Git nu contine modelul evaluat: pagina poate fi regenerata numai daca artefactul local este disponibil; nu pretindem reproducerea exacta doar din fisierele publice.

Programarile raman oprite; demonstrarea modelului nu colecteaza date si nu scrie in DB/Azure. Nu repeta evaluarea finala pentru ajustarea modelului. Dezvoltarea ML ramane pe branch separat pana la o decizie ulterioara explicita privind integrarea.
