from app.schemas.user import UserBase, UserCreate, UserUpdate, UserResponse
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
from app.schemas.structure import (
    CampusBase, CampusCreate, CampusUpdate, CampusResponse,
    DepartementBase, DepartementCreate, DepartementUpdate, DepartementResponse,
    FiliereBase, FiliereCreate, FiliereUpdate, FiliereResponse,
    UEBase, UECreate, UEUpdate, UEResponse,
    MatiereBase, MatiereCreate, MatiereUpdate, MatiereResponse,
)
from app.schemas.etudiant import (
    EtudiantBase, EtudiantCreate, EtudiantUpdate, EtudiantInscriptionRequest, EtudiantResponse,
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

__all__ = [
    "UserBase", "UserCreate", "UserUpdate", "UserResponse",
    "LoginRequest", "TokenResponse", "TokenPayload",
    "SetupStatusResponse", "SetupInitRequest", "SetupInitResponse",
    "EtablissementSetupInput", "AdminSetupInput", "DatabaseSetupInput",
    "PeriodePaiementBase", "PeriodePaiementCreate", "PeriodePaiementResponse",
    "SessionAcademiqueBase", "SessionAcademiqueCreate", "SessionAcademiqueUpdate", "SessionAcademiqueResponse",
    "CampusBase", "CampusCreate", "CampusUpdate", "CampusResponse",
    "DepartementBase", "DepartementCreate", "DepartementUpdate", "DepartementResponse",
    "FiliereBase", "FiliereCreate", "FiliereUpdate", "FiliereResponse",
    "UEBase", "UECreate", "UEUpdate", "UEResponse",
    "MatiereBase", "MatiereCreate", "MatiereUpdate", "MatiereResponse",
    "EtudiantBase", "EtudiantCreate", "EtudiantUpdate", "EtudiantInscriptionRequest", "EtudiantResponse",
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
]
