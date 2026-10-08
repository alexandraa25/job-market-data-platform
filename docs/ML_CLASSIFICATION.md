# Clasificarea rolurilor prin ML

## Stare

Primul pas al extensiei v2: pregatire date, etichetare umana, antrenare/evaluare si predictie offline. Nu exista inca un model antrenat pe etichete reale, task ML Airflow sau tabele de predictii PostgreSQL. Regulile si v1.0 nu sunt inlocuite.

Export read-only din baza stabila la 8 octombrie 2026: 681 joburi. Dupa eliminarea duplicatelor de text normalizat: 672. Coada pentru revizuire: 174, cu maxim 40 din fiecare categorie sugerata de reguli (33 Data Engineer, 30 Data Analyst, 40 Data Scientist, 31 Machine Learning Engineer, 40 Other). Acest esantion este echilibrat intentionat, nu o estimare a distributiei pietei. Numerele descriu snapshotul local, nu sunt date incluse in Git.

## Etichetare

Deschide data/ml/review.html cu un browser sau http://localhost:18082/review.html cand serverul local este pornit. Fisierul local contine coada; pagina generica ml/review.html permite incarcarea unui JSONL. Citeste titlul si descrierea, apoi alege responsabilitatea principala. Sugestia regulilor este ascunsa implicit pentru a reduce influenta ei asupra alegerii.

Data Engineer: pipeline-uri si platforme de date; Data Analyst: analiza si rapoarte; Data Scientist: statistica/modelare predictiva; Machine Learning Engineer: inginerie si operationalizare ML; Other: celelalte roluri. Pentru cazuri ambigue sari peste rand, nu inventa o eticheta. Clasificarile regulilor NU sunt folosite automat ca adevar de referinta.

Apasarea categoriei marcheaza randul reviewed=true, label_source=human, human_label=<categoria>. Progresul este in memorie: Descarca progresul inainte de inchidere, apoi muta reviewed_labels.jsonl in data/ml/. Poti reincarca acest fisier pentru a continua; randurile neverificate nu intra in antrenare.

## Comenzi offline

```powershell
docker compose --profile ml build ml
docker compose --profile ml run --rm ml prepare --input data/ml/source_jobs.jsonl --output data/ml/prepared --per-role 40
```

prepare refuza un director existent pentru a nu suprascrie etichetele. Foloseste alt director pentru un nou snapshot. Datele sursa se exporta numai prin citire din PostgreSQL; exportul nu porneste ETL sau upload Azure.

Dupa verificarea umana a minimum 10 texte distincte din FIECARE categorie:

```powershell
docker compose --profile ml run --rm ml train --labels data/ml/reviewed_labels.jsonl --output models
```

10 pe categorie este un prag minim tehnic, nu dovada ca setul este suficient pentru un model bun. Este preferabil sa revizuiesti toata coada. Etichetele sunt autodeclarate in fisier; codul verifica schema/provenienta declarata, nu poate demonstra cine le-a atribuit.

Antrenarea foloseste TF-IDF unigram/bigram + LogisticRegression cu class_weight=balanced. Se elimina duplicatele de GUID/text si se resping etichetele contradictorii. Separare stratificata 75% train / 25% test, seed 42; TF-IDF este invatat numai pe train. Splitul evita duplicatele exacte normalizate, nu garanteaza eliminarea tuturor anunturilor aproape identice.

Rezultatul este models/<version>/model.joblib, evaluation.json, holdout_predictions.jsonl si manifest.json. Raportul compara precision/recall/F1 per categorie, macro F1 si matricea de confuzie cu regulile pe ACELASI holdout. Toate modelele raman experimental: un rezultat mai bun pe acest esantion nu promoveaza automat modelul. Nu ajusta hiperparametrii folosind acelasi holdout in mod repetat; pentru iteratii ulterioare foloseste validare separata.

Pentru predictii, inlocuieste VERSION cu identificatorul real afisat dupa train:

```powershell
docker compose --profile ml run --rm ml predict --input data/ml/prepared/all_jobs.jsonl --model models/VERSION/model.joblib --output data/ml/predictions.jsonl
```

Predictiile pastreaza rule_role separat de ml_role, scorul si versiunea modelului. Scorul predict_proba nu este o probabilitate calibrata; needs_review foloseste pragul demonstrativ 0.55. Incarca numai modele joblib create local si de incredere: deserializarea unui model strain poate executa cod.

## Izolare si teste

Serviciul ml are profil optional, network_mode: none, fara variabile Azure sau DB. Nu pornesc serviciile Airflow/DB pentru aceste comenzi. Datele, etichetele si modelele sunt ignorate de Git si excluse din contextul Docker. Testele folosesc date sintetice, deci NU masoara performanta reala pe joburile colectate.

```powershell
docker compose --profile ml run --rm --entrypoint python ml -m pytest tests/test_ml.py -q
```

Urmatorii pasi: etichete reale, evaluare fata de reguli, inspectia greselilor si apoi decizia de integrare in Airflow/PostgreSQL/Power BI. Programarile raman oprite.

Referinte: [TF-IDF](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html), [train/test split](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.train_test_split.html), [persistenta modelelor](https://scikit-learn.org/stable/model_persistence.html).
