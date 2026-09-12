from app.models.identity import CaseReviewGrant


def test_case_review_grant_references_disease_report() -> None:
    targets = {
        foreign_key.target_fullname
        for foreign_key in CaseReviewGrant.__table__.c.disease_report_id.foreign_keys
    }

    assert targets == {"disease_reports.id"}
