# Lot rezervat pentru evaluarea finala ML

Rezervare efectuata manual la 8 octombrie 2026, prin citirea API-ului public Himalayas. 336 anunturi distincte colectate; 142 eligibile dupa excluderea tuturor celor 672 texte/GUID-uri cunoscute si a titlurilor identice normalizate. Selectie aleatoare seed 45: 80 anunturi, fara stratificare dupa sugestiile regulilor.

Date locale: data/ml/final-evaluation/. reservation.json contine data, metoda si SHA256 pentru reserved_jobs.jsonl; source_snapshot.json pastreaza raspunsul colectat. Toate sunt ignorate de Git. Pagina review.html elimina complet sugestiile regulilor, inclusiv din JSON. Export: reviewed_final_labels.jsonl, de salvat in acelasi director. Originalul rezervat nu se modifica.

## Protocol stabilit inainte de etichetare

Candidatul ales este TF-IDF pe titlu (unigram/bigram, max_features 30000, sublinear_tf), Logistic Regression (class_weight balanced, max_iter 1000, seed 44). Se va antrena numai pe cele 203 exemple de dezvoltare validate; primul test de 42 ramane exclus. Regulile existente sunt comparatorul pe acelasi lot nou. Nu sunt folosite etichetele finale pentru alegerea variantei sau a parametrilor.

Citeste titlul si descrierea pentru a atribui responsabilitatea principala. Sari peste cazurile ambigue si pastreaza-le nerevizuite. Pentru evaluare se raporteaza explicit cate randuri au fost revizuite/excluse si suportul fiecarei categorii; nu se atribuie automat etichete lipsa. Lotul si etichetele finale nu se adauga ulterior la antrenare in aceasta evaluare.

Evaluarea finala a fost efectuata; rezultatele si decizia sunt la finalul acestui document. Evaluarea va fi efectuata o singura data dupa inghetarea modelului candidat. Orice ajustare ulterioara cere un alt lot final. Chiar daca performanta este buna, promovarea nu este automata.

## Limite si operare

Lot nou fata de datele cunoscute, dar aceeasi sursa si aceleasi cautari directionate; nu reprezinta intreaga piata si nu este o evaluare pe alta sursa/perioada. Titluri/text identice sunt excluse; texte aproape identice pot ramane. Daca unele categorii au putine exemple, rezultatele lor vor fi incerte.

Colectarea a folosit un container temporar cu retea, fara secrete sau conexiuni DB/Azure, montand numai codul, sablonul si data/ml. Serviciul ML normal ramane offline. Nu s-a pornit DAG-ul, nu s-a incarcat in Azure si nu s-au activat programari.


## Rezultat final — 8 octombrie 2026

Candidatul `title-only-final-20261008` a fost antrenat pe cele 203 exemple de dezvoltare, cu parametrii protocolului de mai sus. Artefactul si manifestul au fost salvate inaintea citirii etichetelor finale. Lotul rezervat are SHA256 verificat; textul fiecarui anunt a fost comparat cu originalul, iar GUID-urile, textele si titlurile au fost verificate ca distincte de dezvoltare. Exportul contine 80 etichete umane valide, fara randuri omise.

| Indicator | ML: titlu | Reguli |
| --- | ---: | ---: |
| Accuracy | 81.25% (65/80) | 90.00% (72/80) |
| Macro F1, cinci categorii | 0.4899 | 0.4483 |

Macro F1 acorda fiecarei categorii aceeasi pondere; accuracy numara toate clasificarile corecte. Scorurile pot favoriza metode diferite. Categoria Other domina lotul, iar suportul categoriilor rare este foarte mic.

| Categorie | Exemple finale | F1 ML | F1 reguli |
| --- | ---: | ---: | ---: |
| Data Engineer | 5 | 0.6667 | 0.5714 |
| Data Analyst | 1 | 0.2857 | 0.0000 |
| Data Scientist | 1 | 0.0000 | 0.0000 |
| Machine Learning Engineer | 4 | 0.6154 | 0.7273 |
| Other | 69 | 0.8819 | 0.9429 |

Decizie: **regulile raman in pipeline; ML ramane experimental**. Macro F1 usor mai mare nu este dovada suficienta pentru promovare: Data Analyst si Data Scientist au cate un singur exemplu, iar ML are mai multe erori totale. Nu revendicam superioritate generala sau semnificatie statistica. Testul final a fost inspectat; nu se reutilizeaza pentru ajustarea parametrilor sau etichetelor.

Artefacte locale ignorate: models/title-only-final-20261008/model.joblib, manifest.json, evaluation.json si final_predictions.jsonl. Candidatul contine feature_mode=title_only; CLI predict respecta modul, pastrand compatibilitatea cu primele modele bazate pe titlu + descriere. Nu au fost incarcate predictii in DB/Azure/Power BI si nu a fost adaugat task ML Airflow. Programarile raman oprite.
