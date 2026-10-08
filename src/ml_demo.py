"""Generate an offline comparison page using a trusted local experimental model."""

import argparse
import hashlib
from html import escape
import json
from pathlib import Path

from src.ml import predict_rows, read_rows


def render(rows, predictions, version):
    table = ""
    for row, prediction in zip(rows, predictions):
        cells = [
            row["title"],
            prediction["rule_role"],
            prediction["ml_role"],
            f"{prediction['ml_score']:.1%}",
            "Revizuire" if prediction["needs_review"] else "â€”",
        ]
        table += (
            "<tr>"
            + "".join("<td>" + escape(cell) + "</td>" for cell in cells)
            + "</tr>"
        )
    return (
        """<!doctype html><html lang="ro"><meta charset="utf-8">
<title>Demonstratie ML â€” Job Market Data Platform</title>
<style>body{font:16px Segoe UI,Arial;background:#f4f7fa;color:#183044;max-width:1100px;margin:40px auto;padding:24px}h1{font-size:30px}table{border-collapse:collapse;width:100%;background:white}td,th{padding:14px;text-align:left;border-bottom:1px solid #dbe4ed}th{background:#173f57;color:white}.note{padding:18px;background:#fff2d7;border-radius:8px;line-height:1.6}p{line-height:1.6}</style>
<h1>Clasificarea rolurilor: reguli si ML</h1>
<p>Exemple sintetice, inclusiv titluri ambigue. Aceasta pagina arata comportamentul modelului; nu masoara performanta lui.</p>
<div class="note"><strong>ML experimental; regulile raman in pipeline.</strong><br>
Test final, 80 anunturi noi: ML 65/80 corecte (81,25%), reguli 72/80 (90%). Macro F1: ML 0,4899, reguli 0,4483. Doua categorii au cate un singur exemplu; rezultatul nu justifica promovarea.<br>
Scorul ML nu este o probabilitate calibrata. Revizuire = scor sub pragul demonstrativ 0,55; un scor mare nu garanteaza corectitudinea.</div>
<p>Model local: """
        + escape(version)
        + """. Intrare ML: doar titlul. Fara scriere in baza de date sau Azure.</p>
<table><thead><tr><th>Titlu</th><th>Reguli</th><th>ML</th><th>Scor ML</th><th>Semnal</th></tr></thead><tbody>"""
        + table
        + "</tbody></table><p>Pentru alte exemple, modifica ml/demo_jobs.jsonl si regenereaza pagina. Datele generate raman locale.</p></html>"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--input", default="ml/demo_jobs.jsonl")
    parser.add_argument("--output", default="data/ml/demo")
    args = parser.parse_args()
    model = Path(args.model)
    manifest = json.loads((model.parent / "manifest.json").read_text())
    if hashlib.sha256(model.read_bytes()).hexdigest() != manifest["model_sha256"]:
        raise ValueError("Model hash does not match its manifest")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    rows = read_rows(args.input)
    prediction_path = output / "predictions.jsonl"
    predict_rows(rows, model, prediction_path)
    predictions = read_rows(prediction_path)
    (output / "index.html").write_text(
        render(rows, predictions, manifest["model_version"]), encoding="utf-8"
    )
    print(json.dumps({"rows": len(rows), "page": str(output / "index.html")}))


if __name__ == "__main__":
    main()
