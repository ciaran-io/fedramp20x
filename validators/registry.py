"""Maps KSI IDs to their automated validation methods.

To add coverage for another KSI: write two methods in methods.py (ideally one
static, one live), then register them here. KSIs with no entry are reported as
`not_implemented` rather than silently passing.
"""
from . import methods as m
from . import methods_tech as t
from . import methods_ops as o
from . import methods_grc as g

KSI_METHODS = {
    "KSI-CNA-RNT": [m.rnt_static, m.rnt_live],
    "KSI-CNA-EIS": [m.eis_static, m.eis_live],
    "KSI-IAM-APM": [m.apm_static, m.apm_live],
    "KSI-IAM-ELP": [m.elp_static, m.elp_live],
    "KSI-SVC-SIN": [m.sin_static, m.sin_live],
    "KSI-SVC-ASM": [m.asm_static, m.asm_live],
    "KSI-MLA-LET": [m.let_static, m.let_live],
    "KSI-RPL-ABO": [m.abo_static, m.abo_live, m.abo_alert],
    "KSI-SVC-VCM": [m.vcm_static, m.vcm_live],
    "KSI-CMT-LMC": [t.lmc_static, t.lmc_live, t.lmc_change_types],
    "KSI-CMT-RMV": [t.rmv_static, t.rmv_live],
    "KSI-CMT-VTD": [t.vtd_static, t.vtd_live],
    "KSI-CNA-DFP": [t.dfp_static, t.dfp_live],
    "KSI-CNA-IBP": [t.ibp_static, t.ibp_live],
    "KSI-CNA-MAT": [t.mat_static, t.mat_live],
    "KSI-CNA-OFA": [t.ofa_static, t.ofa_live],
    "KSI-CNA-ULN": [t.uln_static, t.uln_live],
    "KSI-IAM-AAM": [t.aam_static, t.aam_live],
    "KSI-IAM-JIT": [t.jit_static, t.jit_live],
    "KSI-IAM-SNU": [t.snu_static, t.snu_live],
    "KSI-IAM-SUS": [t.sus_static, t.sus_live],
    "KSI-SVC-ACM": [t.acm_static, t.acm_live],
    "KSI-SVC-EIS": [t.eis_svc_static, t.eis_svc_live],
    "KSI-SVC-PRR": [t.prr_static, t.prr_live],
    "KSI-SVC-RUD": [t.rud_static, t.rud_live],
    "KSI-SVC-VRI": [t.vri_static, t.vri_live],
    "KSI-MLA-ALA": [o.ala_static, o.ala_live],
    "KSI-MLA-EVC": [o.evc_static, o.evc_live],
    "KSI-MLA-OSM": [o.osm_static, o.osm_live],
    "KSI-MLA-RVL": [o.rvl_static, o.rvl_live],
    "KSI-PIY-GIV": [o.giv_static, o.giv_live],
    "KSI-PIY-RSD": [o.rsd_static, o.rsd_live],
    "KSI-RPL-ARP": [o.arp_static, o.arp_live],
    "KSI-RPL-TRC": [o.trc_static, o.trc_live],
    "KSI-SCR-MIT": [o.mit_static, o.mit_live],
    "KSI-SCR-MON": [o.mon_static, o.mon_live],
    "KSI-RPL-RRO": [g.rpl_rro_static, g.rpl_rro_live],
    "KSI-INR-RIR": [g.inr_rir_static, g.inr_rir_live],
    "KSI-CNA-RVP": [g.cna_rvp_static, g.cna_rvp_live, g.cna_rvp_change],
    "KSI-CMT-RVP": [g.cmt_rvp_static, g.cmt_rvp_live, g.cmt_rvp_change],
}

# Known gaps between what the methods check and the OFFICIAL Class C KSI statement
# (frmr/fedramp-consolidated-rules.json). A KSI with a gap cannot roll up to a clean
# "pass" even when every method passes. Remove an entry only when the gap is closed.
KSI_NOTES = {
    "KSI-MLA-ALA": "Official statement bases access on data sensitivity classes; methods check roles and grants, not a per-class sensitivity map.",
    "KSI-MLA-EVC": "Official statement covers all machine-based resources; methods check IaC scans and merge checks, not configuration tests of SaaS tools.",
    "KSI-MLA-OSM": "Official statement requires the SIEM itself to be persistently reviewed; methods check health and tamper protection, not a review record.",
    "KSI-MLA-RVL": "Official statement requires logs to be audited; methods check review recency and triage, not audit quality.",
    "KSI-PIY-GIV": "Official statement covers all information resources; the live method checks cloud resources against the scope record, not people and process resources.",
    "KSI-PIY-RSD": "Official statement covers CISA Secure by Design principles; methods check four named principles, not the full pledge.",
    "KSI-RPL-ARP": "Official statement is about a persistent review; methods compare the plan record to the objectives and check review age.",
    "KSI-RPL-TRC": "One restore test result is recorded; methods do not prove the result by running a restore.",
    "KSI-SCR-MIT": "Official statement covers identifying risks; methods check review recency, stale risks and contract clauses, not risk quality.",
    "KSI-SCR-MON": "Official statement covers contractual or active monitoring; methods check advisory check age and the SBOM, not that each advisory was acted on.",
    "KSI-CMT-LMC": "Official statement also requires changes to be monitored; methods check that changes are logged and manual changes alert, not that logs are reviewed.",
    "KSI-CNA-DFP": "Official statement says functionality and privileges are strictly defined for infrastructure and services; methods check roles only, not network or data-store privileges.",
    "KSI-CNA-IBP": "Official statement covers all third-party machine-based resources; methods compare the AWS account to one benchmark and not the SaaS tools (E1, E7, E9).",
    "KSI-CNA-MAT": "Official statement covers a persistent review of lateral movement; methods count known paths and do not run a path analysis.",
    "KSI-CNA-OFA": "Official statement covers rapid recovery; recovery is only tested by KSI-RPL-TRC, which records one restore test.",
    "KSI-CNA-ULN": "Official statement covers a persistent review of traffic flow controls; methods check configuration and telemetry, not a review record.",
    "KSI-IAM-AAM": "Official statement covers all accounts, roles and groups; methods check workforce leavers and provisioning, not role and group lifecycle.",
    "KSI-IAM-JIT": "Official statement covers user and non-user accounts and a persistent review; methods check privileged human access only.",
    "KSI-IAM-SNU": "Official statement covers a persistent review of non-user authentication; methods check key age and declared key use, not a review record.",
    "KSI-IAM-SUS": "Official statement covers disabling or securing accounts; methods check response time for sampled events, not every account type.",
    "KSI-SVC-EIS": "Official statement requires improvements to be made; methods check that open items are not stale, not that each improvement was effective.",
    "KSI-SVC-PRR": "Official statement covers plans, procedures and state; methods check state only.",
    "KSI-SVC-RUD": "Official statement depends on customer agreements; methods check the 30 day target the demo author chose, not each agreement.",
    "KSI-SVC-VRI": "Official statement covers all machine-based information resources; methods check container images only.",
    "KSI-CNA-EIS": "Official statement requires automatically ENFORCING intended state; methods only detect drift, no auto-remediation check.",
    "KSI-MLA-LET": "Official statement is about a maintained, reviewed LIST of resources and event types that are logged; methods only check that the audit trail is on and fresh.",
    "KSI-RPL-ABO": "Objectives are read from environment/recovery-objectives.json, but the methods do not prove a backup can be restored or that a restore meets the RTO (see KSI-RPL-TRC).",
    "KSI-SVC-ASM": "Official statement covers keys, certificates and other secrets; methods check secret rotation only, not key rotation or certificate expiry.",
    "KSI-SVC-VCM": "Observed TLS version and certificate validity are checked for every data flow in the scope record, but not mutual authentication or workload identity between machine-based resources.",
    "KSI-SVC-SIN": "Official statement also covers securing information from unwanted modification; methods check encryption at rest only.",
}

# A gap blocks a pass. None is open today: the notes above record where a check is narrower than the
# official statement. Add an entry here to hold a KSI at partial until the check is widened.
KSI_GAPS: dict[str, str] = {}
