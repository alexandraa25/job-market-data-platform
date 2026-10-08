# Prima evaluare ML — 8 octombrie 2026

Modelul ramane **experimental**. Regulile existente sunt pastrate: modelul nu le depaseste pe acest set de test.

## Date si metoda

Din 174 de anunturi propuse pentru revizuire, 165 au etichete umane valide; 9 nu sunt revizuite si sunt excluse. Distributia etichetelor: 34 Data Engineer, 35 Data Analyst, 39 Data Scientist, 31 Machine Learning Engineer, 26 Other.

Separare stratificata cu seed 42: 123 exemple pentru antrenare si 42 pentru test. TF-IDF unigram/bigram este invatat numai pe antrenare, urmat de Logistic Regression. GUID-urile si hashurile textelor normalizate sunt distincte intre cele doua seturi. Regulile sunt evaluate pe aceleasi 42 de exemple.

## Rezultate

| Indicator | Model ML | Reguli existente |
| --- | ---: | ---: |
| Macro F1 | 0.7351 | 0.8982 |
| Accuracy | 78.57% (33/42) | 90.48% (38/42) |

Macro F1 acorda aceeasi importanta fiecarei categorii si combina precizia cu capacitatea de a identifica exemplele acelei categorii. Nu reprezinta procentul total de anunturi clasificate corect; acesta este accuracy.

| Categorie | Exemple test | F1 ML | F1 reguli |
| --- | ---: | ---: | ---: |
| Data Engineer | 9 | 0.8750 | 0.9412 |
| Data Analyst | 9 | 0.9474 | 0.8000 |
| Data Scientist | 10 | 0.6923 | 1.0000 |
| Machine Learning Engineer | 8 | 0.8750 | 1.0000 |
| Other | 6 | 0.2857 | 0.7500 |

Categoria Other are cel mai slab rezultat ML si doar 6 exemple de test. Unele roluri din aceasta categorie sunt confundate cu Data Scientist. Rezultatul mai bun pentru Data Analyst nu compenseaza scaderea globala.

## Artefacte si decizie

Versiune locala: `20261008T083022Z-644c623f`. Modelul, manifestul, evaluarea detaliata si predictiile de test sunt salvate in `models/`, exclus din Git. Hashul modelului a fost verificat fata de manifest.

Au fost generate si 672 de predictii experimentale locale, cu scoruri valide si versiune de model. Acestea includ exemple folosite la antrenare/test si NU constituie o evaluare independenta. Nu s-au incarcat predictii in PostgreSQL, Azure sau Power BI; nu s-a adaugat task ML in Airflow. Programarile raman oprite.

## Limite si pasul urmator

Esantionul initial a fost selectat intentionat dupa categoriile regulilor, nu aleator din intreaga piata. Setul este mic, etichetele provin dintr-o singura revizuire, iar separarea elimina duplicatele exacte, fara garantie pentru texte aproape identice. Rezultatele nu demonstreaza generalizare la alte surse sau perioade.

Urmatoarea iteratie necesita mai multe exemple variate, in special Other, si revizuirea cazurilor ambigue. Pentru alegerea parametrilor se foloseste validare separata; acest holdout deja inspectat nu trebuie reutilizat repetat pentru optimizare. Integrarea este amanata pana la o evaluare convingatoare pe date independente.


## A doua iteratie — 8 octombrie 2026

Runda a doua: toate cele 80 de anunturi revizuite. Total combinat: 245 etichete umane valide. Cele 42 de exemple din primul test sunt excluse prin GUID si hash de text din intreaga noua iteratie, inclusiv validare.

Date de dezvoltare: 203 exemple (Other 77, Data Scientist 51, Data Engineer 25, Machine Learning Engineer 23, Data Analyst 27). Algoritmul si parametrii raman aceiasi; split stratificat seed 43, 152 pentru antrenare si 51 pentru validare.

| Indicator pe noua validare | ML | Reguli |
| --- | ---: | ---: |
| Macro F1 | 0.6624 | 0.9127 |
| Accuracy | 66.67% | 92.16% |

Versiune locala: `20261008T085112Z-2d6deff2`. Hashul modelului si excluderea primului test au fost verificate. Modelul ramane experimental si nu inlocuieste regulile. Scorurile nu sunt direct comparabile cu primul experiment: validarea si distributia categoriilor sunt diferite. Aceasta validare serveste dezvoltarii, nu demonstreaza performanta pe un test final independent.

Mai multe etichete nu au fost suficiente pentru a depasi regulile. Urmatoarea analiza poate compara reprezentarea titlului cu titlu + descriere, folosind validare incrucisata numai pe datele de dezvoltare si un nou test final rezervat inaintea selectiei modelului. Nu se ajusteaza etichetele doar pentru a imbunatati scorul. Integrarea si colectarile automate raman amanate.


## Comparatie titlu versus titlu + descriere — 8 octombrie 2026

203 exemple de dezvoltare, primul test de 42 exclus. Validare incrucisata cu 5 folduri comune, StratifiedGroupKFold, seed 44. Titlurile identice dupa normalizare sunt grupate pentru a nu aparea in train si validare in acelasi fold. Fiecare fold contine toate cele cinci categorii; fiecare anunt este validat o singura data. TF-IDF este invatat separat numai pe train in fiecare fold. Parametrii modelului sunt fixati, reprezentarea textului este singura diferenta intre variante.

| Metoda | Macro F1 pe predictiile reunite de validare | Accuracy |
| --- | ---: | ---: |
| ML: titlu | 0.8781 | 86.70% (176/203) |
| ML: titlu + descriere | 0.5792 | 63.55% (129/203) |
| Reguli | 0.9437 | 94.58% (192/203) |

Media macro F1 calculata separat pe folduri este 0.8381 pentru titlu si 0.5705 pentru titlu + descriere; abaterea standard intre folduri este 0.0566, respectiv 0.0504. Media scorurilor pe folduri difera de scorul calculat pe toate predictiile reunite, deoarece F1 nu este o medie liniara.

Titlul singur este candidatul ML preferat pe aceste date. Descrierea integrala reduce performanta pentru acest algoritm si aceasta reprezentare; nu rezulta ca descrierile sunt inutile pentru orice model. Regulile raman mai bune. Nu se antreneaza sau promoveaza automat un nou model si nu se modifica predictiile existente.

Raport detaliat local: data/ml/comparisons/20261008T085405Z-1cd0a4f3/comparison.json, exclus din Git. Aceste rezultate sunt pentru selectia variantei pe date de dezvoltare, nu un test final independent. Esantionul este mic si selectat dupa reguli; gruparea titlurilor nu garanteaza eliminarea tuturor textelor aproape identice. Pasul urmator, daca extindem ML: rezervarea unor anunturi noi pentru evaluare finala, etichetarea lor fara sugestii si evaluarea candidatului ales o singura data.


## Evaluare finala pe lotul rezervat

80 etichete umane: ML titlu 65/80 corecte (81.25%), reguli 72/80 (90%). Macro F1 ML 0.4899, reguli 0.4483, cu suport foarte mic pentru unele categorii. Regulile raman in pipeline. Vezi [raportul final si suportul per categorie](ML_FINAL_EVALUATION.md).
