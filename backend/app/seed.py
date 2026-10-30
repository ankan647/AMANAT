"""Deterministic seed data for AMANAT (spec section 7). Idempotent: drops and recreates all
tables, then rebuilds everything from scratch using `random.Random(2026)`.
"""

import random
from datetime import date, datetime, timezone

from app.core import audit
from app.core.clock import now as clock_now
from app.core.clock import reset as clock_reset
from app.core.clock import today as clock_today
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.enums import FieldGrade
from app.db.init_db import init_anchor_db, init_main_db
from app.db.models import (
    AnchorBase,
    AnomalyFlag,
    BankRequest,
    Document,
    Hold,
    Institution,
    Instrument,
    InstrumentAssignment,
    Notification,
    PlantedLabel,
    Rule,
    RuleVersion,
    User,
)
from app.db.session import get_anchor_engine, get_anchor_sessionmaker, get_engine, get_sessionmaker
from app.fixtures.synthetic_pdf import generate_affidavit_pdf, generate_fdr_pdf
from app.services import anomalies, confidence, ingestion, reminders

RNG = random.Random(2026)

GOOD_BENEFICIARY = "AICTE, Government of India"
GOOD_LIEN = "Lien marked in favour of AICTE, pledged against this security deposit"
STATES = [
    "Tamil Nadu", "Karnataka", "Maharashtra", "Uttar Pradesh", "West Bengal",
    "Gujarat", "Rajasthan", "Kerala", "Punjab", "Telangana",
]
COLLEGE_NOUNS = ["Institute of Technology", "College of Engineering", "Polytechnic", "School of Management", "Institute of Pharmacy"]
COLLEGE_ADJECTIVES = ["Nilgiri", "Sahyadri", "Ganga", "Vindhya", "Narmada", "Kaveri", "Satpura", "Aravalli", "Brahmaputra", "Godavari"]


def run_seed(reset: bool = True) -> None:
    engine = get_engine()
    anchor_engine = get_anchor_engine()

    if reset:
        Base.metadata.drop_all(engine)
        AnchorBase.metadata.drop_all(anchor_engine)
    init_main_db(engine)
    init_anchor_db(anchor_engine)

    clock_reset()

    db = get_sessionmaker()()
    anchor_db = get_anchor_sessionmaker()()

    users = _seed_users(db)
    rules = _seed_rules(db)
    _seed_scenarios(db, users, rules, clock_today())
    _seed_planted_and_clean(db, clock_today())
    _seed_vigilance_referrals(db, users)
    _seed_notifications_and_misc(db, users, clock_today())

    db.commit()
    audit.record(
        db, actor_id=None, actor_role="system", action="seed_completed", entity_type="system",
        entity_id=None, details={"institutions": db.query(Institution).count()},
    )
    db.close()
    anchor_db.close()


def _seed_users(db) -> dict[str, User]:
    pw = hash_password("Demo@123")
    fixed = [
        ("scrutiny1@aicte.demo", "Asha Verma", "scrutiny", None),
        ("scrutiny2@aicte.demo", "Rohit Nair", "scrutiny", None),
        ("approver1@aicte.demo", "Meera Iyer", "senior_approver", None),
        ("authority@aicte.demo", "Dr. K. Rao", "competent_authority", None),
        ("admin1@aicte.demo", "Admin One", "admin", None),
        ("admin2@aicte.demo", "Admin Two", "admin", None),
        ("auditor@aicte.demo", "Auditor Demo", "auditor", None),
        ("bank.sbi@bank.demo", "SBI Bank Officer", "bank_officer", "State Bank of India"),
        ("bank.hdfc@bank.demo", "HDFC Bank Officer", "bank_officer", "HDFC Bank"),
    ]
    out = {}
    for email, name, role, bank_name in fixed:
        user = User(email=email, name=name, role=role, password_hash=pw, bank_name=bank_name, active=True)
        db.add(user)
        out[email] = user
    db.commit()
    for email in out:
        db.refresh(out[email])
    return out


def _seed_rules(db) -> dict[str, RuleVersion]:
    required = Rule(key="required_deposit", title="Required security deposit")
    exemption = Rule(key="exemption", title="Exemption from security deposit")
    proof_window = Rule(key="proof_window", title="Proof submission window and penalty")
    release = Rule(key="release", title="Release eligibility")
    db.add_all([required, exemption, proof_window, release])
    db.commit()

    note = "Seed - pending AICTE legal validation"
    v1 = RuleVersion(
        rule_id=required.id, version=1, effective_from=date(2010, 1, 1), effective_to=date(2019, 12, 31),
        applicability_json={}, parameters_json={
            "amounts": {"Technology": 10_00_000_00, "Management": 5_00_000_00, "Pharmacy": 5_00_000_00, "Architecture": 5_00_000_00},
            "term_years": 10, "min_fdr_term_months": 12,
        }, status="active", note=note,
    )
    v2 = RuleVersion(
        rule_id=required.id, version=2, effective_from=date(2020, 1, 1), effective_to=None,
        applicability_json={}, parameters_json={
            "amounts": {"Technology": 15_00_000_00, "Management": 7_50_000_00, "Pharmacy": 7_50_000_00, "Architecture": 7_50_000_00},
            "term_years": 10, "min_fdr_term_months": 12,
        }, status="active", note=note,
    )
    exemption_v1 = RuleVersion(
        rule_id=exemption.id, version=1, effective_from=date(2000, 1, 1), effective_to=None,
        applicability_json={}, parameters_json={"min_years": 10, "government_exempt": False},
        status="active",
        note=note + "; years-based only — a separate government_exempt parameter exists but defaults to false",
    )
    proof_window_v1 = RuleVersion(
        rule_id=proof_window.id, version=1, effective_from=date(2000, 1, 1), effective_to=None,
        applicability_json={}, parameters_json={"grace_days": 7, "penalty_percent": 10},
        status="active", note=note,
    )
    release_v1 = RuleVersion(
        rule_id=release.id, version=1, effective_from=date(2000, 1, 1), effective_to=None,
        applicability_json={}, parameters_json={}, status="active",
        note=note + "; release allowed after term completion or documented closure",
    )
    db.add_all([v1, v2, exemption_v1, proof_window_v1, release_v1])
    db.commit()
    return {"v1": v1, "v2": v2, "exemption_v1": exemption_v1}


def _mk_institution(db, code, name, state, category, programme_type, deposit_request_date,
                     is_government=False, approval_year=2015, years_existing_elsewhere=0, closure_date=None) -> Institution:
    inst = Institution(
        code=code, name=name, state=state, category=category, programme_type=programme_type,
        is_government=is_government, approval_year=approval_year, years_existing_elsewhere=years_existing_elsewhere,
        deposit_request_date=deposit_request_date, closure_date=closure_date, status="active",
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    db.add(
        User(
            email=f"inst.{code.lower()}@inst.demo", name=f"{name} (Institution User)", role="institution",
            password_hash=hash_password("Demo@123"), institution_id=inst.id, active=True,
        )
    )
    db.commit()
    return inst


def _mk_instrument(db, institution_id, fdr_number, bank_name, branch, ifsc, amount_paise, issue_date,
                    maturity_date, status="active", beneficiary=GOOD_BENEFICIARY, lien_text=GOOD_LIEN,
                    intimation_date=None, proof_received_date=None, penalty_settled=False,
                    created_at=None) -> Instrument:
    instrument = Instrument(
        institution_id=institution_id, fdr_number=fdr_number, fdr_number_norm=anomalies.normalize_fdr_number(fdr_number),
        bank_name=bank_name, branch=branch, ifsc=ifsc, amount_paise=amount_paise, issue_date=issue_date,
        maturity_date=maturity_date, beneficiary=beneficiary, lien_text=lien_text,
        intimation_date=intimation_date, proof_received_date=proof_received_date, penalty_settled=penalty_settled,
        status=status, created_at=created_at or datetime(issue_date.year, issue_date.month, issue_date.day, tzinfo=timezone.utc),
    )
    db.add(instrument)
    db.commit()
    db.refresh(instrument)
    confidence.init_fields_for_instrument(db, instrument)
    if status == "active":
        reminders.create_reminders_for_instrument(db, instrument)
    return instrument


def _attach_document(db, instrument, kind="fdr_scan", suspicious_metadata=None, raw_bytes=None):
    data = raw_bytes if raw_bytes is not None else generate_fdr_pdf(instrument, suspicious_metadata)
    text, metadata = ingestion.extract_pdf_text_and_metadata(data)
    import os

    settings = get_settings()
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    path = os.path.join(settings.STORAGE_DIR, f"seed_{instrument.id}_{kind}.pdf")
    with open(path, "wb") as fh:
        fh.write(data)
    doc = Document(
        instrument_id=instrument.id, kind=kind, filename=f"{kind}.pdf", sha256=ingestion.compute_sha256(data),
        mime="application/pdf", size=len(data), ocr_text=text, pdf_metadata_json=metadata, scan_status="clean",
        storage_path=path, created_at=clock_now(),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    if kind == "fdr_scan":
        matches = ingestion.match_fields_against_text(instrument, text)
        for field_name, matched in matches.items():
            if matched:
                confidence.upgrade_field(db, instrument.id, field_name, FieldGrade.document_checked.value, f"document:{doc.id}")
    return doc


def _bank_confirm_all_fields(db, instrument, source):
    for field_name in ["fdr_number", "bank", "amount", "issue_date", "maturity", "beneficiary", "lien"]:
        confidence.upgrade_field(db, instrument.id, field_name, FieldGrade.bank_confirmed.value, source)


def _raise_flags_for(db, instrument, other_instruments, other_documents, min_fdr_term_months, required_paise, other_valid_amount_paise, planted_type=None):
    documents = db.query(Document).filter(Document.instrument_id == instrument.id).all()
    candidates = anomalies.run_lodge_checks(
        instrument=instrument, documents=documents, other_instruments=other_instruments,
        other_documents=other_documents, min_fdr_term_months=min_fdr_term_months,
        required_paise=required_paise, other_valid_amount_paise=other_valid_amount_paise,
    )
    for candidate in candidates:
        is_planted = planted_type is not None and candidate.type == planted_type
        flag = AnomalyFlag(
            instrument_id=instrument.id, type=candidate.type, title=candidate.title, reasons_json=candidate.reasons,
            evidence_json=candidate.evidence, severity=candidate.severity, status="open",
            created_at=clock_now(), is_planted_label=is_planted,
        )
        db.add(flag)
    db.commit()
    return candidates


def _seed_scenarios(db, users, rules, today: date) -> dict[str, Institution]:
    out = {}

    # --- A: shortfall ahead ---
    a = _mk_institution(db, "DEMO-A", "Nilgiri Institute of Technology", "Tamil Nadu", "Technology", "UG", date(2017, 2, 23))
    ia = _mk_instrument(db, a.id, "SBI/FDR/2017/100001", "State Bank of India", "Chennai Main", "SBIN0001234",
                         10_00_000_00, date(2017, 3, 10), date(2027, 1, 13))
    _attach_document(db, ia, "fdr_scan")
    out["A"] = a

    # --- B: covered but unverified ---
    b = _mk_institution(db, "DEMO-B", "Sahyadri College of Engineering", "Karnataka", "Technology", "UG", date(2023, 4, 1))
    ib = _mk_instrument(db, b.id, "SBI/FDR/2023/100002", "State Bank of India", "Bengaluru Main", "SBIN0001234",
                         15_00_000_00, date(2023, 4, 10), date(2033, 4, 10))
    _attach_document(db, ib, "fdr_scan")
    out["B"] = b

    # --- C: duplicate FDR number across two institutions ---
    c1 = _mk_institution(db, "DEMO-C1", "Ganga College of Engineering", "Uttar Pradesh", "Technology", "UG", date(2021, 1, 1))
    c2 = _mk_institution(db, "DEMO-C2", "Vindhya Institute of Technology", "Madhya Pradesh", "Technology", "UG", date(2021, 6, 1))
    ic1 = _mk_instrument(db, c1.id, "SBI/FDR/2024/778812", "State Bank of India", "Lucknow Main", "SBIN0001234",
                          15_00_000_00, date(2024, 1, 1), date(2034, 1, 1), created_at=datetime(2024, 1, 1, tzinfo=timezone.utc))
    ic2 = _mk_instrument(db, c2.id, "SBI/FDR/2024/778812", "State Bank of India", "Bhopal Main", "SBIN0001234",
                          15_00_000_00, date(2024, 2, 1), date(2034, 2, 1), created_at=datetime(2024, 2, 1, tzinfo=timezone.utc))
    for pair in [(ic1, [(ic2, c2.id)]), (ic2, [(ic1, c1.id)])]:
        inst, others = pair
        candidate = anomalies.check_duplicate_fdr_number(inst, others)
        if candidate:
            db.add(
                AnomalyFlag(
                    instrument_id=inst.id, type=candidate.type, title=candidate.title, reasons_json=candidate.reasons,
                    evidence_json=candidate.evidence, severity=candidate.severity, status="open",
                    created_at=clock_now(), is_planted_label=True,
                )
            )
    db.add(PlantedLabel(instrument_id=ic1.id, type="duplicate_fdr_number"))
    db.add(PlantedLabel(instrument_id=ic2.id, type="duplicate_fdr_number"))
    db.commit()
    out["C1"], out["C2"] = c1, c2

    # --- D: bank differs ---
    d = _mk_institution(db, "DEMO-D", "Narmada College of Engineering", "Gujarat", "Technology", "UG", date(2024, 2, 15))
    idd = _mk_instrument(db, d.id, "SBI/FDR/2024/200001", "State Bank of India", "Ahmedabad Main", "SBIN0001234",
                          15_00_000_00, date(2024, 2, 20), date(2034, 2, 15))
    _attach_document(db, idd, "fdr_scan")
    req = BankRequest(
        request_code="BR-2026-0001", instrument_id=idd.id, bank_name="State Bank of India", branch="Ahmedabad Main",
        sent_date=today, due_date=date(2026, 11, 10), aicte_officer_id=users["scrutiny1@aicte.demo"].id,
        outcome="pending", differing_values_json={},
    )
    db.add(req)
    db.commit()
    out["D"] = d

    # --- E1 / E2: different rule versions by obligation date ---
    e1 = _mk_institution(db, "DEMO-E1", "Kaveri Institute of Technology", "Tamil Nadu", "Technology", "UG", date(2018, 5, 1))
    e2 = _mk_institution(db, "DEMO-E2", "Satpura Institute of Technology", "Maharashtra", "Technology", "UG", date(2022, 5, 1))
    _mk_instrument(db, e1.id, "SBI/FDR/2018/300001", "State Bank of India", "Chennai South", "SBIN0001234",
                    10_00_000_00, date(2018, 5, 10), date(2028, 5, 10))
    _mk_instrument(db, e2.id, "SBI/FDR/2022/300002", "State Bank of India", "Mumbai Main", "SBIN0001234",
                    15_00_000_00, date(2022, 5, 10), date(2032, 5, 10))
    out["E1"], out["E2"] = e1, e2

    # --- F: release blocked by hold ---
    f = _mk_institution(db, "DEMO-F", "Aravalli College of Engineering", "Rajasthan", "Technology", "UG", date(2015, 6, 1))
    if_ = _mk_instrument(db, f.id, "SBI/FDR/2015/400001", "State Bank of India", "Jaipur Main", "SBIN0001234",
                         10_00_000_00, date(2015, 6, 10), date(2025, 6, 10))
    _attach_document(db, if_, "fdr_scan")
    _attach_document(db, if_, "affidavit", raw_bytes=generate_affidavit_pdf(if_))
    _attach_document(db, if_, "release_application", raw_bytes=generate_affidavit_pdf(if_))
    _bank_confirm_all_fields(db, if_, "bank_request:BR-2025-0099")
    db.add(InstrumentAssignment(instrument_id=if_.id, officer_id=users["scrutiny1@aicte.demo"].id, role="scrutiniser", assigned_at=datetime(2015, 6, 10, tzinfo=timezone.utc)))
    db.add(Hold(institution_id=None, instrument_id=if_.id, reason="Inquiry ref VIG/2026/114", source="vigilance",
                placed_by=users["authority@aicte.demo"].id, placed_on=today))
    db.commit()
    out["F"] = f

    # --- G1 / G2: signed orders (valid / revoked) ---
    g1 = _mk_institution(db, "DEMO-G1", "Brahmaputra Institute of Technology", "West Bengal", "Technology", "UG", date(2014, 1, 1))
    g2 = _mk_institution(db, "DEMO-G2", "Godavari College of Engineering", "Telangana", "Technology", "UG", date(2014, 6, 1))
    ig1 = _mk_instrument(db, g1.id, "SBI/FDR/2014/500001", "State Bank of India", "Kolkata Main", "SBIN0001234",
                          10_00_000_00, date(2014, 1, 10), date(2024, 1, 10), status="released")
    ig2 = _mk_instrument(db, g2.id, "SBI/FDR/2014/500002", "State Bank of India", "Hyderabad Main", "SBIN0001234",
                          10_00_000_00, date(2014, 6, 10), date(2024, 6, 10), status="released")
    from app.db.models import ReleaseRequest
    from app.services import orders as orders_service

    rr1 = ReleaseRequest(instrument_id=ig1.id, requested_by=users["scrutiny1@aicte.demo"].id, requested_on=date(2024, 1, 15),
                          reason="Term completed", status="approved", needs_second_approval=False)
    rr2 = ReleaseRequest(instrument_id=ig2.id, requested_by=users["scrutiny1@aicte.demo"].id, requested_on=date(2024, 6, 15),
                          reason="Term completed", status="approved", needs_second_approval=False)
    db.add_all([rr1, rr2])
    db.commit()
    db.refresh(rr1)
    db.refresh(rr2)
    orders_service.create_signed_order(db, institution=g1, instrument=ig1, release_request=rr1, issued_on=date(2024, 1, 20))
    order2 = orders_service.create_signed_order(db, institution=g2, instrument=ig2, release_request=rr2, issued_on=date(2024, 6, 20))
    order2.status = "revoked"
    order2.revoked_reason = "Superseded due to a clerical error in the original filing."
    db.add(order2)
    db.commit()
    out["G1"], out["G2"] = g1, g2

    # --- H: healthy, fully confirmed ---
    h = _mk_institution(db, "DEMO-H", "Godhuli Institute of Technology", "Kerala", "Technology", "UG", date(2023, 9, 1))
    ih = _mk_instrument(db, h.id, "SBI/FDR/2023/600001", "State Bank of India", "Kochi Main", "SBIN0001234",
                        15_00_000_00, date(2023, 9, 10), date(2033, 9, 10))
    _attach_document(db, ih, "fdr_scan")
    req_h = BankRequest(request_code="BR-2026-0002", instrument_id=ih.id, bank_name="State Bank of India", branch="Kochi Main",
                         sent_date=date(2026, 10, 1), due_date=date(2026, 10, 15), response_date=date(2026, 10, 10),
                         aicte_officer_id=users["scrutiny1@aicte.demo"].id, outcome="confirmed", differing_values_json={},
                         accepted_by_id=users["scrutiny1@aicte.demo"].id, accepted_at=datetime(2026, 10, 11, tzinfo=timezone.utc))
    db.add(req_h)
    db.commit()
    _bank_confirm_all_fields(db, ih, "bank_request:BR-2026-0002")
    out["H"] = h

    # --- I: exempt ---
    i_inst = _mk_institution(db, "DEMO-I", "Punjab Heritage Institute of Technology", "Punjab", "Technology", "UG",
                              date(2010, 1, 1), years_existing_elsewhere=14)
    out["I"] = i_inst

    # --- J: not covered, no instruments ---
    j = _mk_institution(db, "DEMO-J", "Telangana New College of Engineering", "Telangana", "Technology", "UG", date(2024, 8, 1))
    out["J"] = j

    # --- K: expiring soon ---
    k = _mk_institution(db, "DEMO-K", "Kerala Coastal Institute of Technology", "Kerala", "Technology", "UG", date(2017, 1, 20))
    ik = _mk_instrument(db, k.id, "SBI/FDR/2017/700001", "State Bank of India", "Thiruvananthapuram Main", "SBIN0001234",
                         10_00_000_00, date(2017, 2, 1), date(2026, 11, 24))
    _attach_document(db, ik, "fdr_scan")
    out["K"] = k

    # --- R1: single-approver release ---
    r1 = _mk_institution(db, "DEMO-R1", "Rajasthan Model Institute of Technology", "Rajasthan", "Technology", "UG", date(2015, 10, 1))
    ir1 = _mk_instrument(db, r1.id, "SBI/FDR/2015/800001", "State Bank of India", "Jodhpur Main", "SBIN0001234",
                          40_00_000_00, date(2015, 10, 10), date(2025, 10, 10))
    _attach_document(db, ir1, "fdr_scan")
    _attach_document(db, ir1, "affidavit", raw_bytes=generate_affidavit_pdf(ir1))
    _attach_document(db, ir1, "release_application", raw_bytes=generate_affidavit_pdf(ir1))
    _bank_confirm_all_fields(db, ir1, "bank_request:BR-2025-0100")
    db.add(InstrumentAssignment(instrument_id=ir1.id, officer_id=users["scrutiny1@aicte.demo"].id, role="scrutiniser", assigned_at=datetime(2015, 10, 10, tzinfo=timezone.utc)))
    db.commit()
    out["R1"] = r1

    # --- R2: two-approver release (above threshold) ---
    r2 = _mk_institution(db, "DEMO-R2", "Odisha Grand Institute of Technology", "Odisha", "Technology", "UG", date(2015, 11, 1))
    ir2 = _mk_instrument(db, r2.id, "SBI/FDR/2015/900001", "State Bank of India", "Bhubaneswar Main", "SBIN0001234",
                          60_00_000_00, date(2015, 11, 10), date(2025, 11, 10))
    _attach_document(db, ir2, "fdr_scan")
    _attach_document(db, ir2, "affidavit", raw_bytes=generate_affidavit_pdf(ir2))
    _attach_document(db, ir2, "release_application", raw_bytes=generate_affidavit_pdf(ir2))
    _bank_confirm_all_fields(db, ir2, "bank_request:BR-2025-0101")
    db.add(InstrumentAssignment(instrument_id=ir2.id, officer_id=users["scrutiny1@aicte.demo"].id, role="scrutiniser", assigned_at=datetime(2015, 11, 10, tzinfo=timezone.utc)))
    db.commit()
    out["R2"] = r2

    # --- R3: SOD demo — scrutiniser is approver1 ---
    r3 = _mk_institution(db, "DEMO-R3", "Bihar Central Institute of Technology", "Bihar", "Technology", "UG", date(2015, 12, 1))
    ir3 = _mk_instrument(db, r3.id, "SBI/FDR/2015/999001", "State Bank of India", "Patna Main", "SBIN0001234",
                          30_00_000_00, date(2015, 12, 10), date(2025, 12, 10))
    _attach_document(db, ir3, "fdr_scan")
    _attach_document(db, ir3, "affidavit", raw_bytes=generate_affidavit_pdf(ir3))
    _attach_document(db, ir3, "release_application", raw_bytes=generate_affidavit_pdf(ir3))
    _bank_confirm_all_fields(db, ir3, "bank_request:BR-2025-0102")
    db.add(InstrumentAssignment(instrument_id=ir3.id, officer_id=users["approver1@aicte.demo"].id, role="scrutiniser", assigned_at=datetime(2015, 12, 10, tzinfo=timezone.utc)))
    db.commit()
    out["R3"] = r3

    return out


def _random_college_name() -> str:
    return f"{RNG.choice(COLLEGE_ADJECTIVES)} {RNG.choice(COLLEGE_NOUNS)}"


def _seed_planted_and_clean(db, today: date) -> None:
    counter = [0]

    def next_institution(prefix: str) -> Institution:
        counter[0] += 1
        code = f"DEMO-{prefix}-{counter[0]:02d}"
        state = RNG.choice(STATES)
        return _mk_institution(db, code, _random_college_name(), state, "Technology", "UG", date(2022, 1, 1))

    def ifsc_for(bank: str) -> str:
        table = {"State Bank of India": "SBIN", "HDFC Bank": "HDFC", "ICICI Bank": "ICIC", "Punjab National Bank": "PUNB"}
        return f"{table.get(bank, 'SBIN')}0009876"

    required_paise = 15_00_000_00

    # duplicate_file_hash x2: two instruments (different institutions) sharing identical bytes
    same_bytes = generate_affidavit_pdf(
        type("Tmp", (), {"fdr_number": "SBI/FDR/2026/DUPHASH", "bank_name": "State Bank of India", "beneficiary": GOOD_BENEFICIARY, "lien_text": GOOD_LIEN})()
    )
    dup_hash_instruments = []
    for _ in range(2):
        inst = next_institution("PLANT")
        instrument = _mk_instrument(db, inst.id, f"SBI/FDR/2026/{RNG.randint(100000,999999)}", "State Bank of India", "Main",
                                     "SBIN0009876", required_paise, date(2023, 1, 1), date(2033, 1, 1))
        doc = Document(instrument_id=instrument.id, kind="fdr_scan", filename="dup.pdf", sha256=ingestion.compute_sha256(same_bytes),
                        mime="application/pdf", size=len(same_bytes), ocr_text="", pdf_metadata_json={}, scan_status="clean",
                        storage_path="(shared-hash-fixture)", created_at=clock_now())
        db.add(doc)
        db.commit()
        db.add(PlantedLabel(instrument_id=instrument.id, type="duplicate_file_hash"))
        db.commit()
        dup_hash_instruments.append(instrument)

    for instrument in dup_hash_instruments:
        other = [i for i in dup_hash_instruments if i.id != instrument.id][0]
        documents = db.query(Document).filter(Document.instrument_id == instrument.id).all()
        other_documents = db.query(Document).filter(Document.instrument_id == other.id).all()
        candidate = anomalies.check_duplicate_file_hash(documents, [(d, other.institution_id) for d in other_documents])
        if candidate is not None:
            db.add(
                AnomalyFlag(
                    instrument_id=instrument.id, type=candidate.type, title=candidate.title, reasons_json=candidate.reasons,
                    evidence_json=candidate.evidence, severity=candidate.severity, status="open",
                    created_at=clock_now(), is_planted_label=True,
                )
            )
    db.commit()

    # Each remaining type gets its own pair of fully-isolated institutions (1 instrument each)
    # so "other instruments under the same institution" never masks the planted problem.
    def plant(type_key: str, build) -> None:
        for _ in range(2):
            inst = next_institution("PLANT")
            instrument = build(inst)
            db.add(PlantedLabel(instrument_id=instrument.id, type=type_key))
            db.commit()
            other_instruments = [
                (i, i.institution_id) for i in db.query(Instrument).filter(Instrument.id != instrument.id).all()
            ]
            other_docs = [
                (d, None) for d in db.query(Document).filter(Document.instrument_id != instrument.id).all()
            ]
            _raise_flags_for(
                db, instrument, other_instruments, other_docs, min_fdr_term_months=12,
                required_paise=required_paise, other_valid_amount_paise=0, planted_type=type_key,
            )

    plant("maturity_before_issue", lambda inst: _mk_instrument(
        db, inst.id, f"SBI/FDR/2026/{RNG.randint(100000,999999)}", "State Bank of India", "Main", "SBIN0009876",
        required_paise, date(2026, 6, 1), date(2025, 6, 1)))

    plant("term_too_short", lambda inst: _mk_instrument(
        db, inst.id, f"SBI/FDR/2026/{RNG.randint(100000,999999)}", "State Bank of India", "Main", "SBIN0009876",
        required_paise, date(2026, 1, 1), date(2026, 6, 1)))

    plant("beneficiary_missing", lambda inst: _mk_instrument(
        db, inst.id, f"SBI/FDR/2026/{RNG.randint(100000,999999)}", "State Bank of India", "Main", "SBIN0009876",
        required_paise, date(2023, 1, 1), date(2033, 1, 1), beneficiary="Some Other College Trust"))

    plant("lien_missing", lambda inst: _mk_instrument(
        db, inst.id, f"SBI/FDR/2026/{RNG.randint(100000,999999)}", "State Bank of India", "Main", "SBIN0009876",
        required_paise, date(2023, 1, 1), date(2033, 1, 1), lien_text="No lien information recorded"))

    plant("ifsc_invalid", lambda inst: _mk_instrument(
        db, inst.id, f"SBI/FDR/2026/{RNG.randint(100000,999999)}", "State Bank of India", "Main", "BADIFSC1",
        required_paise, date(2023, 1, 1), date(2033, 1, 1)))

    plant("ifsc_bank_mismatch", lambda inst: _mk_instrument(
        db, inst.id, f"SBI/FDR/2026/{RNG.randint(100000,999999)}", "State Bank of India", "Main", "HDFC0001234",
        required_paise, date(2023, 1, 1), date(2033, 1, 1)))

    def _pdf_metadata_instrument(inst):
        instrument = _mk_instrument(db, inst.id, f"SBI/FDR/2026/{RNG.randint(100000,999999)}", "State Bank of India", "Main",
                                     "SBIN0009876", required_paise, date(2024, 6, 1), date(2034, 6, 1))
        _attach_document(db, instrument, "fdr_scan", suspicious_metadata={"producer": "Adobe Photoshop 2024"})
        return instrument

    plant("pdf_metadata_suspicious", _pdf_metadata_instrument)

    plant("amount_below_required", lambda inst: _mk_instrument(
        db, inst.id, f"SBI/FDR/2026/{RNG.randint(100000,999999)}", "State Bank of India", "Main", "SBIN0009876",
        5_00_000_00, date(2023, 1, 1), date(2033, 1, 1)))

    # Clean controls (~20), grouped under a handful of institutions
    for i in range(4):
        inst = next_institution("FILL")
        for j in range(5):
            _mk_instrument(
                db, inst.id, f"SBI/FDR/2026/{RNG.randint(100000,999999)}", "State Bank of India", "Main", "SBIN0009876",
                required_paise, date(2023, 1, 1), date(2033, 1, 1),
            )


def _seed_vigilance_referrals(db, users) -> None:
    """A few pre-decided flags for the Vigilance referrals list (spec 7.1)."""
    candidates = (
        db.query(AnomalyFlag)
        .filter(AnomalyFlag.status == "open", AnomalyFlag.severity == "medium")
        .limit(2)
        .all()
    )
    for flag in candidates:
        flag.status = "referred"
        flag.outcome_reason = "Referred to Vigilance for further inquiry."
        flag.reviewer_id = users["scrutiny1@aicte.demo"].id
        flag.decided_at = clock_now()
        db.add(flag)
    db.commit()


def _seed_notifications_and_misc(db, users, today: date) -> None:
    sample_user_ids = [u.id for u in users.values()][:5]
    for idx in range(25):
        user_id = sample_user_ids[idx % len(sample_user_ids)]
        db.add(
            Notification(
                user_id=user_id, kind="info", message=f"Demo notification #{idx + 1}: portfolio activity update.",
                entity_type="system", entity_id=0, created_at=clock_now(), read_at=None,
            )
        )

    # 3 overdue-ready bank requests (due within 10 days of today)
    instruments = db.query(Instrument).limit(3).all()
    for idx, instrument in enumerate(instruments):
        db.add(
            BankRequest(
                request_code=f"BR-2026-{900+idx:04d}", instrument_id=instrument.id, bank_name=instrument.bank_name,
                branch=instrument.branch, sent_date=today, due_date=today, aicte_officer_id=sample_user_ids[0],
                outcome="pending", differing_values_json={},
            )
        )
    db.commit()


if __name__ == "__main__":
    run_seed(reset=True)
    print("Seed complete.")
