from app.schemas.user import UserBase, UserCreate, UserUpdate, UserResponse
from app.schemas.audit import AuditEventResponse
from app.schemas.auth import LoginRequest, TokenResponse, TokenPayload
from app.schemas.setup import (
    SetupStatusResponse,
    SetupInitRequest,
    SetupInitResponse,
    EtablissementSetupInput,
    AdminSetupInput,
    DatabaseSetupInput,
)
from app.schemas.session import (
    PeriodePaiementBase,
    PeriodePaiementCreate,
    PeriodePaiementResponse,
    SessionAcademiqueBase,
    SessionAcademiqueCreate,
    SessionAcademiqueUpdate,
    SessionAcademiqueResponse,
)
from app.schemas.academic import (
    CycleBase, CycleCreate, CycleUpdate, CycleSummary, CycleResponse,
    NiveauBase, NiveauCreate, NiveauUpdate, NiveauSummary, NiveauResponse,
    FiliereSummary, FiliereResume, NiveauResume, CycleResume,
    ClasseBase, ClasseCreate, ClasseUpdate, ClasseResponse,
    EtudiantInscriptionSummary, InscriptionSummary, InscriptionBase,
    InscriptionCreate, InscriptionUpdate, InscriptionResponse,
    ModeleLMDChargeRequest, ModeleLMDChargeResponse,
)
from app.schemas.structure import (
    CampusBase, CampusCreate, CampusUpdate, CampusResponse,
    DepartementBase, DepartementCreate, DepartementUpdate, DepartementResponse,
    FiliereBase, FiliereCreate, FiliereUpdate, FiliereResponse,
    UEBase, UECreate, UEUpdate, UEResponse,
    MatiereBase, MatiereCreate, MatiereUpdate, MatiereResponse,
)
from app.schemas.etudiant import (
    EtudiantBase, EtudiantCreate, EtudiantUpdate, EtudiantInscriptionRequest,
    EtudiantSummaryResponse, EtudiantResponse,
)
from app.schemas.pedagogie import (
    CoursBase, CoursCreate, CoursResponse,
    ExamenBase, ExamenCreate, ExamenResponse,
    NoteBase, NoteCreate, NoteBulkCreate, NoteBulkItem, NoteResponse,
    AbsenceBase, AbsenceCreate, AbsenceResponse,
    DeliberationConfig, DeliberationSingleRequest, DeliberationPromotionRequest,
    EtudiantDeliberationResult, PromotionDeliberationStats, PromotionDeliberationResult,
)
from app.schemas.finance import (
    FactureBase, FactureCreate, FactureResponse,
    PaiementCreate, PaiementResponse,
    RecuResponse, BalanceAgeeItem, BalanceAgeeResponse,
)
from app.schemas.portals import PortalEtudiantResponse, PortalEnseignantResponse
from app.schemas.admissions import (
    StatutCandidature, StatutPiece, TypeDecision,
    CandidatureCreate, CandidatureUpdate, CandidatureResponse, CandidaturePage,
    CandidatureStatusUpdate, CandidatureConversionResponse,
    PieceCandidatureCreate, PieceCandidatureUpdate, PieceCandidatureResponse,
    DecisionAdmissionCreate, DecisionAdmissionResponse,
    VueAdmissionsFiltres, VueAdmissionsCreate, VueAdmissionsUpdate, VueAdmissionsResponse,
    ActionGroupee, BulkCandidatureAction, BulkActionError, BulkCandidatureActionResponse,
)
from app.schemas.context import AcademicContextUpdate, AcademicContextResponse
from app.schemas.rbac import (
    CurrentUserResponse,
    EffectivePermissionsResponse,
    PermissionCreate, PermissionResponse, PermissionUpdate,
    RbacUserResponse,
    RoleCreate, RolePermissionAdd, RolePermissionsSet, RoleResponse, RoleUpdate,
    RoleUsersAssign, RoleUsersResponse, UserRoleAssignmentResponse,
)

__all__ = [
    "UserBase", "UserCreate", "UserUpdate", "UserResponse",
    "AuditEventResponse",
    "LoginRequest", "TokenResponse", "TokenPayload",
    "SetupStatusResponse", "SetupInitRequest", "SetupInitResponse",
    "EtablissementSetupInput", "AdminSetupInput", "DatabaseSetupInput",
    "PeriodePaiementBase", "PeriodePaiementCreate", "PeriodePaiementResponse",
    "SessionAcademiqueBase", "SessionAcademiqueCreate", "SessionAcademiqueUpdate", "SessionAcademiqueResponse",
    "CycleBase", "CycleCreate", "CycleUpdate", "CycleSummary", "CycleResponse",
    "NiveauBase", "NiveauCreate", "NiveauUpdate", "NiveauSummary", "NiveauResponse",
    "FiliereSummary", "FiliereResume", "NiveauResume", "CycleResume",
    "ClasseBase", "ClasseCreate", "ClasseUpdate", "ClasseResponse",
    "EtudiantInscriptionSummary", "InscriptionSummary", "InscriptionBase",
    "InscriptionCreate", "InscriptionUpdate", "InscriptionResponse",
    "ModeleLMDChargeRequest", "ModeleLMDChargeResponse",
    "CampusBase", "CampusCreate", "CampusUpdate", "CampusResponse",
    "DepartementBase", "DepartementCreate", "DepartementUpdate", "DepartementResponse",
    "FiliereBase", "FiliereCreate", "FiliereUpdate", "FiliereResponse",
    "UEBase", "UECreate", "UEUpdate", "UEResponse",
    "MatiereBase", "MatiereCreate", "MatiereUpdate", "MatiereResponse",
    "EtudiantBase", "EtudiantCreate", "EtudiantUpdate", "EtudiantInscriptionRequest",
    "EtudiantSummaryResponse", "EtudiantResponse",
    "CoursBase", "CoursCreate", "CoursResponse",
    "ExamenBase", "ExamenCreate", "ExamenResponse",
    "NoteBase", "NoteCreate", "NoteBulkCreate", "NoteBulkItem", "NoteResponse",
    "AbsenceBase", "AbsenceCreate", "AbsenceResponse",
    "DeliberationConfig", "DeliberationSingleRequest", "DeliberationPromotionRequest",
    "EtudiantDeliberationResult", "PromotionDeliberationStats", "PromotionDeliberationResult",
    "FactureBase", "FactureCreate", "FactureResponse",
    "PaiementCreate", "PaiementResponse",
    "RecuResponse", "BalanceAgeeItem", "BalanceAgeeResponse",
    "PortalEtudiantResponse", "PortalEnseignantResponse",
    "StatutCandidature", "StatutPiece", "TypeDecision",
    "CandidatureCreate", "CandidatureUpdate", "CandidatureResponse", "CandidaturePage",
    "CandidatureStatusUpdate", "CandidatureConversionResponse",
    "PieceCandidatureCreate", "PieceCandidatureUpdate", "PieceCandidatureResponse",
    "DecisionAdmissionCreate", "DecisionAdmissionResponse",
    "VueAdmissionsFiltres", "VueAdmissionsCreate", "VueAdmissionsUpdate", "VueAdmissionsResponse",
    "ActionGroupee", "BulkCandidatureAction", "BulkActionError", "BulkCandidatureActionResponse",
    "AcademicContextUpdate", "AcademicContextResponse",
    "CurrentUserResponse", "EffectivePermissionsResponse",
    "PermissionCreate", "PermissionResponse", "PermissionUpdate",
    "RbacUserResponse",
    "RoleCreate", "RolePermissionAdd", "RolePermissionsSet", "RoleResponse", "RoleUpdate",
    "RoleUsersAssign", "RoleUsersResponse", "UserRoleAssignmentResponse",
]
