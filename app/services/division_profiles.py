from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.models import DivisionProfile, Organization

DIVISION_NAMES = {
    "FO": "DDC5I Front Office",
    "CCD": "Command & Control Capabilities Division",
    "JAD": "Joint Assessment Division",
    "DSD": "Data and Standards Division",
    "AID": "Architecture & Integration Division",
    "CID": "Coalition Interoperability Division",
    "JFID": "Joint Fires Integration Division",
    "C3OD2": "Cyber & C2 Operational Development Division",
}

PROFILE_SPECS: dict[str, dict[str, Any]] = {
    "FO": {
        "mission": "Provides executive leadership, strategic direction, and decision support to integrate C5I priorities across the Joint Force.",
        "vision": "Lead, align, and integrate Joint C5I to create decision advantage.",
        "focus_areas": ["Strategic Direction", "Decision Support", "Enterprise Integration", "Governance"],
        "responsibilities": [
            "Set enterprise direction for DDC5I mission priorities and outcomes.",
            "Synchronize cross-division priorities, dependencies, and leadership engagements.",
            "Enable timely, evidence-based senior-leader decisions.",
            "Integrate C5I priorities across the Joint Force and mission partners.",
            "Oversee governance, performance, communications, and organizational readiness.",
        ],
        "branches": [],
        "initiatives": ["Joint C5I Decision Advantage", "Enterprise Portfolio Governance", "Cross-Division Integration"],
        "relationships": [
            {"name": "Joint Staff J6 Leadership", "role": "Executive advice, direction, and decision support", "category": "Joint Staff"},
            {"name": "DDC5I Divisions", "role": "Synchronize priorities, commitments, dependencies, and outcomes", "category": "Internal"},
            {"name": "Services, CCMDs, Agencies, and Mission Partners", "role": "Align Joint C5I priorities and implementation", "category": "Enterprise"},
        ],
        "forums": [
            {"name": "DDC5I Leadership Governance", "role": "Lead", "purpose": "Set direction, synchronize priorities, and enable decisions."},
            {"name": "Joint C5I Executive Engagements", "role": "Lead / Support", "purpose": "Integrate enterprise priorities and decision support."},
        ],
        "doctrine": [],
        "banner_asset": "/static/division-banners/fo.webp",
        "banner_alt": "DDC5I Front Office banner showing Joint C5I decision advantage connecting space, air, land, maritime, and cyber operations.",
        "source_documents": ["Owner-provided Front Office banner"],
        "source_notes": "Initial profile uses the owner-provided banner; existing administrator-maintained fields are preserved.",
    },
    "CCD": {
        "mission": "Leads joint C2 requirements, CJADC2 priorities, capability sponsorship, and end-to-end traceability from operational need to fielded solution.",
        "vision": "Turn warfighter needs into integrated Joint C2 capability.",
        "focus_areas": ["CJADC2", "C2 Requirements", "Gap Analysis", "Capability Sponsorship"],
        "responsibilities": [
            "Identify and assess Joint C2 capability gaps in operational context.",
            "Develop, validate, and prioritize Joint C2 requirements.",
            "Sponsor material and non-material capability solutions.",
            "Maintain end-to-end traceability from warfighter need to fielded capability.",
            "Lead CJADC2 operational priorities, metrics analysis, and capability advocacy.",
            "Support posture reviews, readiness assessment, fielding, and feedback.",
        ],
        "branches": [],
        "initiatives": ["CJADC2 Capability Development", "Joint C2 Requirements", "Capability Gap Assessment", "End-to-End Traceability"],
        "relationships": [
            {"name": "Operational Warfighter Community", "role": "Identify needs, gaps, priorities, and operational feedback", "category": "Joint Force"},
            {"name": "Material and Non-Material Developers", "role": "Translate validated requirements into integrated solutions", "category": "Capability Development"},
            {"name": "Services, CCMDs, and Agencies", "role": "Coordinate Joint C2 requirements, sponsorship, and fielding", "category": "Enterprise"},
        ],
        "forums": [
            {"name": "CJADC2 Cross-Functional Team", "role": "Secretariat / Principal advocate", "purpose": "Synchronize operational priorities, metrics, and routine business operations."},
            {"name": "Joint C2 Requirements Governance", "role": "Lead / Sponsor", "purpose": "Validate requirements, prioritize gaps, and sponsor solutions."},
        ],
        "doctrine": [
            {"name": "Joint C2 Family of Programs", "role": "Functional manager / capability sponsor", "notes": "Requirements development and capability sponsorship."},
        ],
        "banner_asset": "/static/division-banners/ccd.webp",
        "banner_alt": "Command and Control Capabilities Division banner showing CJADC2 capability development from warfighter need through requirements, prioritization, development, assessment, and fielding.",
        "source_documents": ["Owner-provided CCD banner"],
        "source_notes": "Initial profile uses the owner-provided banner and mission description; existing administrator-maintained fields are preserved.",
    },
    "JFID": {
        "mission": "Connects fires integration, targeting, and operational effects with joint and coalition C2 so sensor-to-decision-to-effect can move faster.",
        "vision": "Modernize the Joint Targeting Cycle C2 for globally integrated operations and deliver outpacing, integrated all-domain fires and effects at speed and scale.",
        "focus_areas": ["Joint Fires", "Targeting", "Effects Chains", "C2 Integration"],
        "responsibilities": [
            "Integrate joint fires across air, land, maritime, space, and cyber domains.",
            "Align DOTMLPF-P changes that improve multinational combat effectiveness.",
            "Advance combat identification and friendly force tracking to reduce fratricide and collateral damage.",
            "Plan and execute demonstrations that validate fires and C2 interoperability.",
        ],
        "branches": [
            {"name": "Combined Joint Fires Branch", "focus": "All-domain joint fires integration and policy."},
            {"name": "Demonstration Branch (Bold Quest)", "focus": "Operational demonstrations and capability validation."},
            {"name": "Combat Identification – Friendly Force Tracking Branch", "focus": "Identification, tracking, and shared situational awareness."},
        ],
        "initiatives": ["Joint Fire Support Executive Steering Committee", "CID-FFT Executive Steering Committee", "Bold Quest", "NATO fires and targeting interoperability"],
        "relationships": [
            {"name": "Joint Staff J2/J3", "role": "Targeting, situational awareness, and operational integration", "category": "Joint Staff"},
            {"name": "NATO and Allied Partners", "role": "Doctrine, STANAG, and multinational capability alignment", "category": "Coalition"},
            {"name": "OSD(P) and DOT&E", "role": "Policy, test, and evaluation coordination", "category": "OSD"},
        ],
        "forums": [
            {"name": "JFS ESC", "role": "Lead / Support", "purpose": "Joint fire support capability integration."},
            {"name": "CID-FFT ESC", "role": "Lead / Support", "purpose": "Combat identification and friendly force tracking governance."},
            {"name": "Bold Quest SSG", "role": "Support", "purpose": "Coalition interoperability demonstration governance."},
        ],
        "doctrine": [
            {"name": "JP 3-03 Joint Interdiction", "role": "Doctrine sponsor", "notes": "Planning, execution, and assessment of joint interdiction."},
            {"name": "JP 3-09 Joint Fire Support", "role": "Lead agent / doctrine sponsor", "notes": "Integration and coordination of joint fire support."},
            {"name": "JP 3-09.3 Close Air Support", "role": "Doctrine sponsor", "notes": "Close air support doctrine and procedures."},
            {"name": "STANAG 7144", "role": "Contributor", "notes": "NATO CAS and air interdiction tactics, techniques, and procedures."},
        ],
        "banner_asset": "/static/division-banners/jfid.webp",
        "banner_alt": "Joint Fires Integration Division banner showing integrated air, land, maritime, space, cyber, targeting, and command-and-control effects.",
        "source_documents": ["JFID Division Outline.docx", "DDC5I Joint and Allied Authoritative Directives- Joint Doctrine Publications.docx"],
        "source_notes": "Profile distilled from the division outline, authoritative-directives summary, and owner-provided banner.",
    },
    "JAD": {
        "mission": "Conduct comprehensive laboratory and operational analyses of emerging, developmental, and fielded C2 information systems and procedures, producing decision-quality data that improves Coalition and Joint integration and interoperability.",
        "vision": "Validate mission capability before the fight and turn operational evidence into readiness decisions.",
        "focus_areas": ["Mission Assessment", "Interoperability", "Gap Analysis", "Readiness"],
        "responsibilities": [
            "Plan and conduct laboratory and operational C2 assessments.",
            "Produce decision-quality evidence for senior leader and portfolio decisions.",
            "Assess coalition interoperability, mission effectiveness, technical maturity, and operational relevance.",
            "Identify gaps, risks, and recommended actions before fielding or employment.",
        ],
        "branches": [
            {"name": "Technical Branch", "focus": "Technical measures, instrumentation, and analysis."},
            {"name": "Sustainment Branch", "focus": "Sustainment evidence and fielded-capability assessment."},
            {"name": "Joint Operational Assessment Branch", "focus": "Operational assessments and mission effectiveness."},
            {"name": "Coalition & Interagency Assessment Branch", "focus": "Partnered and interagency interoperability assessment."},
        ],
        "initiatives": ["CJADC2 Capability Portfolio Management Review", "CAPSTONE ICD", "CJADC2 Campaign Plan 2027/2035", "Coalition Interoperability Assurance and Validation", "Low-TRL demonstrations"],
        "relationships": [
            {"name": "Combatant Commands", "role": "Operational assessment sponsors and evidence consumers", "category": "CCMD"},
            {"name": "Coalition and Interagency Partners", "role": "Interoperability validation and shared assessment", "category": "Coalition"},
            {"name": "DoD Senior Leaders", "role": "Decision-quality assessment products", "category": "Leadership"},
        ],
        "forums": [
            {"name": "CJADC2 CPMR", "role": "Assessment support", "purpose": "Portfolio evidence and capability readiness review."},
            {"name": "CIAV", "role": "Lead / Support", "purpose": "Coalition interoperability assurance and validation."},
            {"name": "Joint Lessons Learned GOSC", "role": "Support", "purpose": "Capture and disseminate assessment lessons."},
        ],
        "doctrine": [],
        "banner_asset": "/static/division-banners/jad.webp",
        "banner_alt": "Joint Assessment Division banner showing mission assessment across space, air, land, maritime, and cyber with gap analysis, validation, and recommended actions.",
        "source_documents": ["JAD Division Outline.docx"],
        "source_notes": "Profile distilled from the Joint Assessment Division outline and owner-provided banner.",
    },
    "DSD": {
        "mission": "Improve joint and combined warfighter interoperability and readiness by developing data policy, standards, governance, and mission data services, then validating implementation through rapid prototyping, integration, and evaluation.",
        "vision": "Make data mission-ready, governed, discoverable, interoperable, and available for decision advantage across every operational domain.",
        "focus_areas": ["Data Fabric", "Standards", "Governance", "Mission Data"],
        "responsibilities": [
            "Lead CJADC2 data enterprise, data management, and conformance activities.",
            "Develop and maintain data policies, standards, and governance structures.",
            "Advance mission data services, catalogs, metadata, and data-fabric maturity.",
            "Coordinate U.S., NATO, and allied tactical data, message, symbology, and information-exchange standards.",
        ],
        "branches": [
            {"name": "Applied Technology Branch", "focus": "Rapid prototyping, integration, and emerging technology evaluation."},
            {"name": "Data Policy, Standards & Enterprise Interoperability Branch", "focus": "Policy, standards, governance, and enterprise interoperability."},
            {"name": "Mission Data Services Branch", "focus": "Operationally ready data services and subject-matter expertise."},
        ],
        "initiatives": ["CJADC2 Data Enterprise", "CJADC2 Data Interoperability Evaluation and Conformance", "Mission Data Catalog", "Data Fabric Maturity", "NATO Core Data Framework", "TDL, MTF, IER, and symbology governance"],
        "relationships": [
            {"name": "CDAO and DoD CIO", "role": "Enterprise data, architecture, and standards alignment", "category": "OSD"},
            {"name": "NATO & Allied Partners", "role": "Data governance and interoperability standards", "category": "Coalition"},
            {"name": "CCMDs and Joint Staff J6 Divisions", "role": "Mission priorities and operational implementation", "category": "Joint"},
        ],
        "forums": [
            {"name": "CJADC2 Data and Standards WG", "role": "Co-chair", "purpose": "Data and standards coordination for CJADC2."},
            {"name": "NIEM MilOps", "role": "Steward / Lead", "purpose": "Military operations information-exchange standardization."},
            {"name": "NATO Digital Policy Committee", "role": "Support", "purpose": "U.S. input to NATO digital policy and data alignment."},
        ],
        "doctrine": [
            {"name": "NCDF", "role": "Lead / Support", "notes": "NATO Core Data Framework interoperability standards."},
            {"name": "ACP-240", "role": "Standards coordination", "notes": "Allied communications and information-exchange alignment."},
            {"name": "TDL / MTF / Symbology Governance", "role": "Governance", "notes": "U.S. and NATO tactical data and message standards."},
        ],
        "banner_asset": "/static/division-banners/dsd.webp",
        "banner_alt": "Data and Standards Division banner showing a data fabric connecting space, air, land, maritime, and cyber with metadata, APIs, governance, and standards.",
        "source_documents": ["DSD Division Outline.docx"],
        "source_notes": "Profile distilled from the Data and Standards Division outline and owner-provided banner.",
    },
    "CID": {
        "mission": "Enable coalition-ready C2, mission-partner information sharing, and interoperability across networks, nations, and operational communities.",
        "vision": "Connect mission partners at operational speed through trusted, resilient, standards-based coalition C2 environments.",
        "focus_areas": ["MPE", "FMN", "NATO", "Partner Interoperability"],
        "responsibilities": [
            "Coordinate coalition and multinational C2 interoperability across operational communities.",
            "Advance Mission Partner Environment and Federated Mission Networking alignment.",
            "Support bilateral, multilateral, and NATO digital interoperability engagements.",
            "Connect coalition architecture, standards, policy, and operational implementation activities.",
        ],
        "branches": [],
        "initiatives": ["Mission Partner Environment", "Federated Mission Networking", "NATO interoperability", "FNC3 and bilateral engagements", "Coalition mission threads"],
        "relationships": [
            {"name": "NATO", "role": "Digital policy, FMN, and interoperability alignment", "category": "Coalition"},
            {"name": "FVEY and Bilateral Partners", "role": "Mission-partner information sharing and C2 integration", "category": "Coalition"},
            {"name": "CDAO, CIO, R&E, A&S, and CAPE", "role": "Architecture, policy, acquisition, and portfolio coordination", "category": "OSD"},
        ],
        "forums": [
            {"name": "MPE ESC", "role": "Lead / Support", "purpose": "Mission Partner Environment integration and governance."},
            {"name": "NATO DPC", "role": "Support", "purpose": "NATO digital policy direction and U.S. coordination."},
            {"name": "FMN Management Group", "role": "Support", "purpose": "Federated Mission Networking management and standards alignment."},
        ],
        "doctrine": [
            {"name": "FMN Spiral Specifications", "role": "Alignment and implementation support", "notes": "Federated mission-networking interoperability."},
            {"name": "MPE Implementation Guidance", "role": "Integration support", "notes": "Mission-partner environment policy and technical alignment."},
        ],
        "banner_asset": "/static/division-banners/cid.webp",
        "banner_alt": "Coalition Interoperability Division banner showing connected allied mission partners across air, land, maritime, space, and cyber domains.",
        "source_documents": ["OSD Key Relationships Cross-Cutting.docx", "DDC5I -Functional Engagements – C2 Integration and Interoperability.docx", "Overview of Key Defense Leadership Forums DDC5I Leads or Support.docx"],
        "source_notes": "Conservative profile based on cross-cutting relationship and forum summaries plus the owner-provided banner; branch structure remains for content-owner confirmation.",
    },
    "C3OD2": {
        "mission": "Accelerate cyber, C2, laboratory, experimentation, and prototyping work that turns emerging concepts into resilient operational capability.",
        "vision": "Prototype, experiment, and operationalize secure C2 capabilities across every operational domain.",
        "focus_areas": ["Cyber C2", "Labs", "Prototyping", "Tech Enablement"],
        "responsibilities": [
            "Prototype and experiment with emerging cyber and C2 capabilities.",
            "Bridge concepts, laboratory evidence, and fielded operational capability.",
            "Coordinate C2 policy and issue resolution across technical and operational stakeholders.",
            "Advance secure, resilient networks and mission-partner connectivity.",
        ],
        "branches": [],
        "initiatives": ["Cyber labs", "C2 experimentation", "Operational prototyping", "Mission Partner Environment support", "Joint communications doctrine"],
        "relationships": [
            {"name": "CDAO, CIO, R&E, and A&S", "role": "Technology, policy, architecture, and acquisition coordination", "category": "OSD"},
            {"name": "USD(I&S)", "role": "Cyber and operational policy coordination", "category": "OSD"},
            {"name": "Service laboratories and research organizations", "role": "Experimentation, prototyping, and transition", "category": "R&D"},
        ],
        "forums": [
            {"name": "DECRE SSG", "role": "Support", "purpose": "DoD enterprise cyber range oversight."},
            {"name": "C2 ESC / JC2 SAG", "role": "Lead / Support", "purpose": "C2 policy, capability, and issue governance."},
            {"name": "Software Modernization ESC", "role": "Support", "purpose": "Modern software delivery and DevSecOps alignment."},
        ],
        "doctrine": [
            {"name": "JP 6-0 Joint Communications System", "role": "Lead agent / doctrine sponsor", "notes": "Joint communications systems and information exchange."},
        ],
        "banner_asset": "/static/division-banners/c3od2.webp",
        "banner_alt": "Cyber and C2 Operational Development Division banner showing cyber operations, command and control, labs, experimentation, prototyping, and operational development across domains.",
        "source_documents": ["DDC5I Joint and Allied Authoritative Directives- Joint Doctrine Publications.docx", "OSD Key Relationships Cross-Cutting.docx", "Overview of Key Defense Leadership Forums DDC5I Leads or Support.docx"],
        "source_notes": "Initial profile based on cross-cutting material and the owner-provided banner; branch structure remains for content-owner confirmation.",
    },
    "AID": {
        "mission": "Analyze, develop, and validate joint C5 architectures, Mission Based Analyses, common system functions, and Mission Threads to ensure integration and interoperability and identify opportunities for capability improvement.",
        "vision": "Architect the mission integration layer that turns concepts, systems, and mission threads into integrated C2 capability across domains, Services, and partners.",
        "focus_areas": ["C5 Architecture", "Mission Threads", "Mission Analysis", "System Integration"],
        "responsibilities": [
            "Develop and validate CJADC2 reference architectures and designs.",
            "Lead Mission Based Analysis, Mission Enabled Solution Assessment, and Mission Threads.",
            "Maintain Warfighting Mission Area architecture standards, repository, and governance products.",
            "Coordinate enterprise, reference, multinational, and mission-network architectures.",
        ],
        "branches": [],
        "initiatives": ["CJADC2 Chief Architect", "Golden Dome", "JFN", "Digital Fusion CONEMP", "Multinational Architectures", "Warfighting Mission Area Architecture", "JCSFL", "Mission Network as a Service"],
        "relationships": [
            {"name": "DoD CIO and CDAO", "role": "Enterprise and reference architecture coordination", "category": "OSD"},
            {"name": "JROC and JCIDS Communities", "role": "Conformance assessment and capability review", "category": "Joint"},
            {"name": "MPE, CCEB, NATO, and FMN Partners", "role": "Multinational architecture alignment", "category": "Coalition"},
        ],
        "forums": [
            {"name": "EASB", "role": "Support / Advise", "purpose": "Enterprise architecture and services governance."},
            {"name": "JMTWG", "role": "Lead / Support", "purpose": "Joint mission-thread development and validation."},
            {"name": "Mission Engineering ESC", "role": "Support", "purpose": "Integrated mission-engineering oversight."},
        ],
        "doctrine": [
            {"name": "Warfighting Mission Area Architecture Standards", "role": "Chief architect", "notes": "Develop, maintain, and govern architecture standards."},
            {"name": "Joint Common System Function List", "role": "Maintainer", "notes": "Maintain and update common system functions."},
        ],
        "banner_asset": "/static/division-banners/aid.webp",
        "banner_alt": "Architecture and Integration Division banner showing an integrated C2 capability connected to space, air, land, and maritime mission threads and architecture layers.",
        "source_documents": ["AID Division Outline.docx"],
        "source_notes": "Profile distilled from the Architecture and Integration Division outline and owner-provided banner.",
    },
}


def ensure_division_profiles(db: Session, updated_by_id: str | None = None) -> None:
    """Idempotently reconcile profiles while preserving administrator-maintained content."""
    for code, name in DIVISION_NAMES.items():
        org = db.query(Organization).filter(Organization.code == code).first()
        if not org:
            continue
        org.name = name
        spec = PROFILE_SPECS[code]
        if spec.get("mission") and not (org.narrative or "").strip():
            org.narrative = spec["mission"]
        profile = db.query(DivisionProfile).filter(DivisionProfile.org_id == org.id).first()
        if profile:
            # Repair only blank fields. The corrected JFID banner is replaced at the same stable path.
            for field in ("mission", "vision", "banner_asset", "banner_alt", "source_notes"):
                if not getattr(profile, field, None) and spec.get(field):
                    setattr(profile, field, spec[field])
            for field in ("focus_areas", "responsibilities", "branches", "initiatives", "relationships", "forums", "doctrine", "source_documents"):
                if not getattr(profile, field, None) and spec.get(field):
                    setattr(profile, field, spec[field])
            continue
        profile = DivisionProfile(
            org_id=org.id,
            updated_by_id=updated_by_id,
            last_reviewed_at=datetime.now(timezone.utc),
            **spec,
        )
        db.add(profile)


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                value = json.loads(text)
            except json.JSONDecodeError:
                value = text
        if isinstance(value, str):
            separator = "\n" if "\n" in value else "|"
            return [part.strip(" -\t") for part in value.split(separator) if part.strip(" -\t")]
    if isinstance(value, Iterable) and not isinstance(value, (dict, bytes)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _record_list(value: Any, keys: tuple[str, ...]) -> list[dict[str, str]]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                value = json.loads(text)
            except json.JSONDecodeError:
                value = text
        if isinstance(value, str):
            rows = [row.strip() for row in value.splitlines() if row.strip()]
            records: list[dict[str, str]] = []
            for row in rows:
                parts = [part.strip() for part in row.split("|")]
                records.append({key: (parts[index] if index < len(parts) else "") for index, key in enumerate(keys)})
            return records
    if isinstance(value, dict):
        value = [value]
    if isinstance(value, list):
        return [{key: str(item.get(key, "")).strip() for key in keys} for item in value if isinstance(item, dict)]
    return []


def normalize_profile_data(data: dict[str, Any], existing: DivisionProfile | None = None) -> dict[str, Any]:
    current = profile_to_dict(existing, include_identity=False) if existing else {}
    normalized = {
        "mission": str(data.get("mission", current.get("mission", ""))).strip(),
        "vision": str(data.get("vision", current.get("vision", ""))).strip(),
        "focus_areas": _string_list(data.get("focus_areas", current.get("focus_areas", []))),
        "responsibilities": _string_list(data.get("responsibilities", current.get("responsibilities", []))),
        "branches": _record_list(data.get("branches", current.get("branches", [])), ("name", "focus")),
        "initiatives": _string_list(data.get("initiatives", current.get("initiatives", []))),
        "relationships": _record_list(data.get("relationships", current.get("relationships", [])), ("name", "role", "category")),
        "forums": _record_list(data.get("forums", current.get("forums", [])), ("name", "role", "purpose")),
        "doctrine": _record_list(data.get("doctrine", current.get("doctrine", [])), ("name", "role", "notes")),
        "banner_asset": str(data.get("banner_asset", current.get("banner_asset", ""))).strip(),
        "banner_alt": str(data.get("banner_alt", current.get("banner_alt", ""))).strip(),
        "focal_x": max(0, min(100, int(data.get("focal_x", current.get("focal_x", 50)) or 50))),
        "focal_y": max(0, min(100, int(data.get("focal_y", current.get("focal_y", 50)) or 50))),
        "status": str(data.get("status", current.get("status", "Published"))).strip() or "Published",
        "source_documents": _string_list(data.get("source_documents", current.get("source_documents", []))),
        "source_notes": str(data.get("source_notes", current.get("source_notes", ""))).strip(),
    }
    return normalized


def apply_profile_data(profile: DivisionProfile, data: dict[str, Any], updated_by_id: str | None = None) -> DivisionProfile:
    normalized = normalize_profile_data(data, profile)
    for key, value in normalized.items():
        setattr(profile, key, value)
    profile.updated_by_id = updated_by_id
    profile.updated_at = datetime.now(timezone.utc)
    profile.last_reviewed_at = datetime.now(timezone.utc)
    return profile


def profile_to_dict(profile: DivisionProfile | None, org: Organization | None = None, include_identity: bool = True) -> dict[str, Any]:
    if not profile:
        return {}
    data = {
        "mission": profile.mission,
        "vision": profile.vision,
        "focus_areas": profile.focus_areas or [],
        "responsibilities": profile.responsibilities or [],
        "branches": profile.branches or [],
        "initiatives": profile.initiatives or [],
        "relationships": profile.relationships or [],
        "forums": profile.forums or [],
        "doctrine": profile.doctrine or [],
        "banner_asset": profile.banner_asset,
        "banner_alt": profile.banner_alt,
        "focal_x": profile.focal_x,
        "focal_y": profile.focal_y,
        "status": profile.status,
        "source_documents": profile.source_documents or [],
        "source_notes": profile.source_notes,
        "last_reviewed_at": profile.last_reviewed_at.isoformat() if profile.last_reviewed_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }
    if include_identity and org:
        return {
            "schema_version": "0.7.5",
            "division_code": org.code,
            "official_name": org.name,
            "narrative": org.narrative,
            **data,
        }
    return data


def profile_form_values(profile: DivisionProfile) -> dict[str, str]:
    def lines(items: list[str]) -> str:
        return "\n".join(items or [])

    def record_lines(items: list[dict[str, Any]], keys: tuple[str, ...]) -> str:
        return "\n".join(" | ".join(str(item.get(key, "")) for key in keys) for item in (items or []))

    return {
        "mission": profile.mission,
        "vision": profile.vision,
        "focus_areas": lines(profile.focus_areas),
        "responsibilities": lines(profile.responsibilities),
        "branches": record_lines(profile.branches, ("name", "focus")),
        "initiatives": lines(profile.initiatives),
        "relationships": record_lines(profile.relationships, ("name", "role", "category")),
        "forums": record_lines(profile.forums, ("name", "role", "purpose")),
        "doctrine": record_lines(profile.doctrine, ("name", "role", "notes")),
        "banner_asset": profile.banner_asset,
        "banner_alt": profile.banner_alt,
        "focal_x": str(profile.focal_x),
        "focal_y": str(profile.focal_y),
        "status": profile.status,
        "source_documents": lines(profile.source_documents),
        "source_notes": profile.source_notes,
    }
