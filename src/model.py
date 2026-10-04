"""Maintain dimensions and current skill associations in the jobs transaction."""

from sqlalchemy import text


def sync_dimensions(connection, records):
    for record in records:
        name = (record.get("company_name") or "").strip()
        company_id = None
        if name:
            company_id = connection.execute(
                text("""INSERT INTO companies(name,name_key)
                VALUES (:name,lower(:name)) ON CONFLICT(name_key) DO UPDATE SET name_key=EXCLUDED.name_key
                RETURNING company_id"""),
                {"name": name},
            ).scalar_one()
        connection.execute(
            text("UPDATE jobs SET company_id=:company WHERE guid=:guid"),
            {"company": company_id, "guid": record["guid"]},
        )
        connection.execute(
            text("DELETE FROM job_skills WHERE job_guid=:guid"),
            {"guid": record["guid"]},
        )
        for column, value in record.items():
            if column.startswith("has_") and value == 1:
                skill_id = connection.execute(
                    text(
                        """INSERT INTO skills(name) VALUES (:name)
                    ON CONFLICT(name) DO UPDATE SET name=EXCLUDED.name RETURNING skill_id"""
                    ),
                    {"name": column[4:]},
                ).scalar_one()
                connection.execute(
                    text(
                        "INSERT INTO job_skills(job_guid,skill_id) VALUES (:guid,:skill)"
                    ),
                    {"guid": record["guid"], "skill": skill_id},
                )
