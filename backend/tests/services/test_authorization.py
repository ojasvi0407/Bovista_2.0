from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.auth import CurrentPrincipal
from app.services.authorization import ForbiddenError, authorize


def test_vet_is_denied_outside_assignment() -> None:
    principal = CurrentPrincipal(
        user_id=uuid4(),
        roles=("VETERINARIAN",),
        location_path="/IN/STATE-1/DISTRICT-1/",
    )
    report = SimpleNamespace(
        reporter_id=uuid4(),
        location_path="/IN/STATE-1/DISTRICT-2/BLOCK-4/",
    )

    with pytest.raises(ForbiddenError):
        authorize(principal, "report.read_identifiable", report)


def test_farmer_reads_owned_report_only() -> None:
    farmer_id = uuid4()
    principal = CurrentPrincipal(farmer_id, ("FARMER",), None)
    own_report = SimpleNamespace(reporter_id=farmer_id, location_path="/IN/STATE-1/")
    other_report = SimpleNamespace(reporter_id=uuid4(), location_path="/IN/STATE-1/")

    authorize(principal, "report.read", own_report)
    with pytest.raises(ForbiddenError):
        authorize(principal, "report.read", other_report)


def test_district_officer_gets_aggregates_but_not_identifiable_rows() -> None:
    principal = CurrentPrincipal(uuid4(), ("DISTRICT_OFFICER",), "/IN/STATE-1/DISTRICT-1/")
    report = SimpleNamespace(reporter_id=uuid4(), location_path=principal.location_path)

    authorize(principal, "report.read_aggregate", report)
    with pytest.raises(ForbiddenError):
        authorize(principal, "report.read_identifiable", report)
