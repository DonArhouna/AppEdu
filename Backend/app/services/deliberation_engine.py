"""
Moteur de Délibération ECTS / LMD pour EduManagePro (EMP).
Calcule les moyennes d'UEs, applique la compensation, détermine les statuts
(Admis, Rattrapage, Ajourné) et les mentions académiques.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ECUEResult(BaseModel):
    code: str
    nom: str
    note: float  # /20
    coef: float = 1.0


class UEResult(BaseModel):
    code: str
    nom: str
    ects: int
    ecues: List[ECUEResult]
    moyenne_ue: float
    validee: bool
    validee_par_compensation: bool
    has_note_eliminatoire: bool


class EtudiantDeliberationResult(BaseModel):
    id: Optional[str] = None
    matricule: str
    nom: str
    prenom: str
    filiere: str
    semestre: str
    ues: List[UEResult]
    moyenne_generale: float
    total_ects_acquis: int
    total_ects_max: int
    statut_session: str  # "Admis" | "Rattrapage" | "Ajourné"
    mention: str         # "Très Bien" | "Bien" | "Assez Bien" | "Passable" | "Rattrapage" | "Ajourné"
    has_note_eliminatoire: bool
    notes_eliminatoires_details: List[str]


class DeliberationConfig(BaseModel):
    seuil_validation_moyenne: float = 10.0
    seuil_eliminatoire: float = 7.0
    seuil_passage_conditionnel_ects: int = 18
    compensation_autorisee: bool = True


class PromotionDeliberationStats(BaseModel):
    total: int
    admis: int
    rattrapage: int
    ajournes: int
    taux_reussite: str
    moyenne_promo: str


class PromotionDeliberationResult(BaseModel):
    resultats: List[EtudiantDeliberationResult]
    stats: PromotionDeliberationStats


class DeliberationEngine:
    @staticmethod
    def calculer_etudiant(
        etudiant_data: Dict[str, Any],
        config: DeliberationConfig = DeliberationConfig()
    ) -> EtudiantDeliberationResult:
        """
        Calcule les résultats individuels de délibération pour un étudiant.
        """
        sum_ects_valides = 0
        sum_ects_weighted = 0.0
        sum_ects_total = 0
        global_has_eliminatoire = False
        all_eliminatoires: List[str] = []

        ues_calculees: List[UEResult] = []

        # 1. Calcul par UE
        ues_raw = etudiant_data.get("ues_raw", [])
        for ue in ues_raw:
            ecues_raw = ue.get("ecues", [])
            total_note_coef = sum(e["note"] * e.get("coef", 1.0) for e in ecues_raw)
            total_coef = sum(e.get("coef", 1.0) for e in ecues_raw)
            moyenne_ue = round(total_note_coef / total_coef, 2) if total_coef > 0 else 0.0

            # Vérification des notes éliminatoires dans l'UE
            ue_eliminatoires = [e for e in ecues_raw if e["note"] < config.seuil_eliminatoire]
            has_ue_eliminatoire = len(ue_eliminatoires) > 0

            if has_ue_eliminatoire:
                global_has_eliminatoire = True
                for e in ue_eliminatoires:
                    all_eliminatoires.append(f"{e.get('code', 'EC')} ({e['note']}/20)")

            ects = ue.get("ects", 0)
            sum_ects_total += ects
            sum_ects_weighted += moyenne_ue * ects

            is_validee = (moyenne_ue >= config.seuil_validation_moyenne) and (not has_ue_eliminatoire)

            ues_calculees.append(
                UEResult(
                    code=ue.get("code", ""),
                    nom=ue.get("nom", ""),
                    ects=ects,
                    ecues=[ECUEResult(**e) for e in ecues_raw],
                    moyenne_ue=moyenne_ue,
                    validee=is_validee,
                    validee_par_compensation=False,
                    has_note_eliminatoire=has_ue_eliminatoire,
                )
            )

        # 2. Moyenne générale
        moyenne_generale = (
            round(sum_ects_weighted / sum_ects_total, 2) if sum_ects_total > 0 else 0.0
        )

        # 3. Règles de compensation
        can_compensate = (
            config.compensation_autorisee
            and moyenne_generale >= config.seuil_validation_moyenne
            and not global_has_eliminatoire
        )

        for ue_calc in ues_calculees:
            if ue_calc.validee:
                sum_ects_valides += ue_calc.ects
            elif can_compensate and not ue_calc.has_note_eliminatoire:
                ue_calc.validee = True
                ue_calc.validee_par_compensation = True
                sum_ects_valides += ue_calc.ects

        # 4. Décision du Jury & Mention
        if moyenne_generale >= config.seuil_validation_moyenne and sum_ects_valides == sum_ects_total:
            statut_session = "Admis"
            if moyenne_generale >= 16.0:
                mention = "Très Bien"
            elif moyenne_generale >= 14.0:
                mention = "Bien"
            elif moyenne_generale >= 12.0:
                mention = "Assez Bien"
            else:
                mention = "Passable"
        elif (
            sum_ects_valides >= config.seuil_passage_conditionnel_ects
            or global_has_eliminatoire
            or (8.5 <= moyenne_generale < config.seuil_validation_moyenne)
        ):
            statut_session = "Rattrapage"
            mention = "Rattrapage"
        else:
            statut_session = "Ajourné"
            mention = "Ajourné"

        return EtudiantDeliberationResult(
            id=etudiant_data.get("id"),
            matricule=etudiant_data.get("matricule", ""),
            nom=etudiant_data.get("nom", ""),
            prenom=etudiant_data.get("prenom", ""),
            filiere=etudiant_data.get("filiere", ""),
            semestre=etudiant_data.get("semestre", "Semestre 1"),
            ues=ues_calculees,
            moyenne_generale=moyenne_generale,
            total_ects_acquis=sum_ects_valides,
            total_ects_max=sum_ects_total,
            statut_session=statut_session,
            mention=mention,
            has_note_eliminatoire=global_has_eliminatoire,
            notes_eliminatoires_details=all_eliminatoires,
        )

    @classmethod
    def calculer_promotion(
        cls,
        etudiants: List[Dict[str, Any]],
        config: DeliberationConfig = DeliberationConfig()
    ) -> PromotionDeliberationResult:
        """
        Calcule les résultats pour l'ensemble d'une promotion/cohorte.
        """
        resultats = [cls.calculer_etudiant(e, config) for e in etudiants]
        total = len(resultats)
        admis = sum(1 for r in resultats if r.statut_session == "Admis")
        rattrapage = sum(1 for r in resultats if r.statut_session == "Rattrapage")
        ajournes = sum(1 for r in resultats if r.statut_session == "Ajourné")

        sum_moyennes = sum(r.moyenne_generale for r in resultats)
        moyenne_promo = f"{(sum_moyennes / total):.2f}" if total > 0 else "0.00"
        taux_reussite = f"{((admis / total) * 100):.1f}%" if total > 0 else "0.0%"

        return PromotionDeliberationResult(
            resultats=resultats,
            stats=PromotionDeliberationStats(
                total=total,
                admis=admis,
                rattrapage=rattrapage,
                ajournes=ajournes,
                taux_reussite=taux_reussite,
                moyenne_promo=moyenne_promo,
            )
        )
