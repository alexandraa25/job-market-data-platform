# Dashboard Job Market — Power BI

Din repository, deschide `JobMarket.pbip` în Power BI Desktop. Dacă ai fișierul local `JobMarket.pbix`, îl poți deschide direct; acesta este exclus din Git. Raportul este salvat cu date încărcate și trei pagini. `JobMarket.pbip` păstrează definițiile editabile ale modelului și raportului pentru Git. Nu separa fișierul PBIP de folderele JobMarket.Report și JobMarket.SemanticModel.

## Pagini

1. **Privire generală**: indicatori globali, distribuția rolurilor și companiile ordonate după numărul anunțurilor.
2. **Competențe**: filtrare pe rol, numărul joburilor și procentul din joburile rolurilor selectate. Totalul numărului reprezintă asocieri job–competență; nu este număr de joburi distincte. Totalul procentual este ascuns.
3. **Salarii**: filtre pentru rol, monedă și perioadă; grafic și tabel cu mărimea eșantionului. Graficul este gol când selecția include monede/perioade diferite. Tabelul arată fiecare grupă separat. Media globală într-o grupă compatibilă este ponderată după numărul salariilor, nu o medie a mediilor rolurilor.

Indicatorii de pe prima pagină sunt globali; filtrele din paginile competențe și salarii se aplică local paginii. Pentru selecții multiple poate fi necesară tasta Ctrl, în funcție de comportamentul slicer-ului. Folosește radiera slicer-ului pentru resetare. Dacă pagina se vede prea mică, apasă Fit to page în dreapta jos.

## Sursa actuală: snapshot

Implicit, parametrul Power Query `UsePostgreSQL` este false. Datele sunt agregările citite din PostgreSQL la 04.10.2026: 283 joburi, 166 companii, 101 anunțuri cu salariu. Snapshot-ul este inclus în interogările M și în snapshot.json. Refresh în acest mod reîncarcă aceleași date; nu preia joburi noi.

Nu sunt incluse parole în PBIX/PBIP. Modelul folosește tabele agregate distincte și o tabelă RoleFilter, cu relații unidirecționale spre Roles, Skills și Salaries. Companies și Overview nu sunt legate artificial de agregările pe rol.

## Activarea actualizării din PostgreSQL

1. Pornește serviciile proiectului și verifică existența celor cinci view-uri analytics.
2. În Power BI: **Transform data → Edit parameters**, setează **UsePostgreSQL = true**.
3. Aplică schimbarea și execută **Refresh → Schema and data**.
4. La dialogul de autentificare, introdu personal credențialele bazei. Server: **localhost:5433**; baza: **job_market_db**. Nu introduce parole în interogările M și nu le salva în README.
5. Verifică numărătorile față de `SELECT * FROM analytics.overview;`, apoi salvează raportul. Pentru date colectate ulterior, folosește Refresh din nou.

Interogările PostgreSQL sunt pregătite în fiecare partiție a modelului și citesc exclusiv view-uri analytics. Mod de stocare: Import. Importul direct din PostgreSQL nu a fost executat/verificat în Power BI în această intervenție; verificarea vizuală a folosit snapshot-ul. Autentificarea necesită intervenția utilizatoarei. Conexiunea nu este DirectQuery și nu se actualizează automat când DAG-ul se termină. Nu s-a publicat raportul în Power BI Service și nu s-a configurat gateway/refresh programat.

Într-un proiect redistribuit doar cu fișierele text, fără cache, folosește Refresh pentru prima încărcare. `.pbi/` conține cache și setări locale și este ignorat de Git. Power BI poate propune conversia TMSL → TMDL la salvarea PBIP; versiunea verificată a păstrat TMSL, alegând Don't upgrade. Documentația Microsoft: https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview

## Interpretare și verificare

Date istorice, inclusiv joburi expirate. Clasificarea rolurilor, detectarea competențelor și gruparea companiilor sunt euristice. Salariile sunt mediile limitelor publicate sau singura limită disponibilă; nu sunt salarii efectiv plătite. Monedele/perioadele nu se convertesc. Alte dimensiuni, mediane sau analiza evoluției salariilor nu sunt reprezentate în acest raport.

Verificări în Power BI Desktop: toate paginile se deschid, snapshot-ul se încarcă, KPI-urile corespund SQL; Data Engineer Python 17/89,5% și SQL 16/84,2%; USD anual are 81 salarii în total, Data Engineer 5 cu media 184.679,50. Eliminarea filtrului anual golește graficul când rămân perioade mixte. Totalul procentual de competențe este gol. 27 de definiții JSON au fost validate față de schemele oficiale Microsoft. Fișierul PBIX a fost salvat din aplicație cu datele incluse; nu s-a făcut o redeschidere separată a PBIX după salvare.
