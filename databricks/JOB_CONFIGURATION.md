# ConfiguraÈ›ia Job-ului Free Edition

## FiÈ™iere

- `job.template.json`: definiÈ›ie reproductibilÄƒ pentru Jobs API, reconstruitÄƒ din informaÈ›iile confirmate. Setările sunt identice cu exportul furnizat de utilizatoare; doar calea personală a notebookului este înlocuită cu `<NOTEBOOK_PATH>`.
- `job.observed.json`: Job ID, rulare manualÄƒ verificatÄƒ È™i programarea raportatÄƒ; marcheazÄƒ setÄƒrile Ã®ncÄƒ necunoscute.
- `job.export.json`: exportul exact solicitat din meniul Job â†’ View as code / View JSON. Va fi verificat cÃ¢nd este disponibil.

È˜ablonul foloseÈ™te task Notebook, source WORKSPACE. Nu include cluster clasic: pentru taskuri Notebook aceasta permite compute Serverless. Nu introducem un environment/version presupus. [Exemple oficiale Serverless](https://docs.databricks.com/aws/en/dev-tools/bundles/examples).

Programarea doritÄƒ este zilnic 19:15 Europe/Bucharest, Quartz `47 15 19 * * ?` (19:15:47), UNPAUSED. Prima execuÈ›ie programatÄƒ nu este Ã®ncÄƒ verificatÄƒ. `max_concurrent_runs=1` È™i parametrii expliciÈ›i sunt setÄƒri propuse pentru reproducere, nu setÄƒri constatate din exportul existent. [Jobs API](https://docs.databricks.com/api/jobs/v2/job).

## Reproducere

1. CreeazÄƒ volumele managed workspace.default.raw È™i workspace.default.processed È™i Ã®ncarcÄƒ raw.json Ã®n primul.
2. ImportÄƒ Job_Market_PySpark_FreeEdition.py Ã®n workspace, cu numele Job_Market_PySpark_Complet.
3. ÃŽntr-o copie a È™ablonului, Ã®nlocuieÈ™te `<NOTEBOOK_PATH>` cu calea realÄƒ copiatÄƒ din Databricks. Nu publica datele de autentificare. È˜ablonul nu poate fi trimis API-ului pÃ¢nÄƒ cÃ¢nd placeholderul nu este Ã®nlocuit.
4. CreeazÄƒ Job-ul prin UI sau instrumentul Databricks autentificat, folosind setÄƒrile È™ablonului. Nu crea duplicate dacÄƒ Job-ul existÄƒ deja; comparÄƒ Ã®ntÃ¢i exportul È™i foloseÈ™te Job-ul existent.
5. RuleazÄƒ Run now, verificÄƒ Succeeded È™i manifestul, apoi activeazÄƒ programarea dacÄƒ doreÈ™ti. Crearea/deploy-ul acestei configuraÈ›ii nu au fost executate de asistent.

Template-ul are programarea activÄƒ; pentru o copie de test schimbÄƒ pause_status Ã®n PAUSED Ã®nainte de creare. Nu este necesarÄƒ trecerea Azure la Pay-As-You-Go. Sursa rÄƒmÃ¢ne fiÈ™ierul Ã®ncÄƒrcat manual; aceastÄƒ configuraÈ›ie nu sincronizeazÄƒ Azure/Airflow cu Free Edition.

## Exportul exact

ÃŽn Job-ul existent foloseÈ™te View as code / View JSON È™i salveazÄƒ job.export.json. Nu include tokenuri Ã®n fiÈ™ier. Exportul poate conÈ›ine numele utilizatorului È™i calea notebookului; originalul rÄƒmÃ¢ne local, iar pentru Git se pregÄƒteÈ™te o variantÄƒ portabilÄƒ verificatÄƒ. Un rezultat Jobs API get conÈ›ine settings; definiÈ›ia pentru create foloseÈ™te doar setÄƒrile, fÄƒrÄƒ job_id/creator/run metadata.

Exportul exact a fost furnizat în chat la 5 octombrie 2026. Nu au fost modificate setările remote. Pentru reproducere, păstrează notebookul cu valorile implicite ale volumelor sau configurează deliberat parametrii în Job. Versiunea mediului Serverless nu este prezentă în acest export și nu este presupusă.
