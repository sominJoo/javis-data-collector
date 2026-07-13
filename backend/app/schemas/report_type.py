from datetime import datetime

from app.schemas.base import CamelModel


class ReportSkillSchema(CamelModel):
    skill_type: str = ""  # WORKFLOW | CONCEPT_EXTRACTION | EVALUATION_POLICY
    name: str
    description: str = ""
    status: str = "none"  # none | gen | uploaded
    content: str = ""


class ReportTypeIn(CamelModel):
    code: str
    name: str
    description: str = ""
    classification_types: list[str] = []
    skills: list[ReportSkillSchema] = []
    active: bool = True


class ReportTypeOut(CamelModel):
    code: str
    name: str
    description: str = ""
    classification_types: list[str] = []
    skills: list[ReportSkillSchema] = []
    updated_at: datetime | None = None
    active: bool = True


class SkillGenerateRequest(CamelModel):
    skill_type: str  # WORKFLOW | CONCEPT_EXTRACTION | EVALUATION_POLICY
    report_type_code: str
    report_type_name: str
    report_type_description: str = ""
