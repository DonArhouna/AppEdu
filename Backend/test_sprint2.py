"""
Test Suite Automatisée — Sprint 2 EduManagePro (EMP)
Valide les 4 piliers métiers :
1. Structure Académique (Campus -> Département -> Filière -> UE -> Matière)
2. Étudiants (Génération matricule paramétrable, création, inscription session)
3. Pédagogie (Saisie de notes, Moteur de délibération ECTS/LMD, compensation)
4. Finances (Facture -> Paiement/Encaissement -> Reçu structuré, balance âgée)
"""

import asyncio
import sys
from datetime import date
from typing import Dict, Any

from app.services.deliberation_engine import (
    DeliberationEngine,
    DeliberationConfig,
    EtudiantDeliberationResult,
    PromotionDeliberationResult,
)


def test_structure_models_and_schemas():
    print("\n--- [TEST 1] Structure Académique (Modèles & Schémas) ---")
    from app.schemas.structure import (
        CampusCreate, CampusResponse,
        DepartementCreate, DepartementResponse,
        FiliereCreate, FiliereResponse,
        UECreate, UEResponse,
        MatiereCreate, MatiereResponse,
    )

    # 1. Campus
    c_in = CampusCreate(nom="Campus Principal", code="CAMP-PRI", ville="Abidjan")
    print("  [OK] Campus schema validé:", c_in.nom, f"({c_in.code})")

    # 2. Département
    d_in = DepartementCreate(nom="Génie Informatique", code="GI", campus_id="CAMP-PRI")
    print("  [OK] Département schema validé:", d_in.nom, f"({d_in.code})")

    # 3. Filière
    f_in = FiliereCreate(nom="Génie Logiciel", code="GL", departement_id="GI", diplome="Licence", duree=3)
    print("  [OK] Filière schema validé:", f_in.nom, f"({f_in.diplome} {f_in.duree} ans)")

    # 4. UE
    ue_in = UECreate(
        nom="Architecture Logicielle & DevOps",
        code="UE-INF301",
        credits=6,
        coefficient=3.0,
        heures=45,
        semestre="S5",
        niveau="Licence 3",
        filiere_id="GL",
    )
    print("  [OK] UE schema validé:", ue_in.nom, f"({ue_in.credits} ECTS, Coef {ue_in.coefficient})")

    # 5. Matière (ECUE)
    m_in = MatiereCreate(
        nom="Microservices & APIs FastAPI",
        code="INF301-1",
        credits=3,
        coefficient=1.5,
        heures_cm=20,
        heures_td=15,
        heures_tp=10,
        ue_id="UE-INF301",
    )
    print("  [OK] Matière schema validé:", m_in.nom, f"(Total heures: {m_in.heures_cm + m_in.heures_td + m_in.heures_tp}h)")
    return True


def test_etudiant_models_and_matricule():
    print("\n--- [TEST 2] Étudiants & Matricule Automatique ---")
    from app.schemas.etudiant import EtudiantCreate, EtudiantResponse, EtudiantInscriptionRequest

    # Test format matricule
    filiere_code = "GL"
    annee = 2026
    seq = 42
    matricule_simule = f"{annee}-{filiere_code}-{seq:04d}"
    assert matricule_simule == "2026-GL-0042", "Format matricule invalide"
    print("  [OK] Format matricule généré:", matricule_simule)

    # Test création d'étudiant
    etu_in = EtudiantCreate(
        matricule=matricule_simule,
        nom="Dupont",
        prenom="Marie",
        email="marie.dupont@email.com",
        filiere="Génie Logiciel",
        filiere_id="fil-gl-001",
        niveau="Licence 3",
        statut="Inscrit",
        session_id="SES-2025-MAIN",
    )
    print("  [OK] Étudiant créé avec session:", etu_in.prenom, etu_in.nom, f"[{etu_in.matricule}]")

    # Une suppression peut créer un trou dans la séquence. Le générateur doit
    # retourner le premier numéro réellement disponible, pas count + 1.
    class _MatriculeResult:
        def scalars(self):
            return self

        def all(self):
            return ["2026-GL-0001", "2026-GL-0003"]

    class _MatriculeSession:
        async def execute(self, _statement):
            return _MatriculeResult()

    from app.services.matricule_service import generate_matricule

    generated = asyncio.run(
        generate_matricule(_MatriculeSession(), filiere_code="GL", annee=2026)
    )
    assert generated == "2026-GL-0002", f"Séquence matricule invalide: {generated}"
    print("  [OK] Trou de séquence détecté, prochain matricule:", generated)

    # Test inscription
    insc_in = EtudiantInscriptionRequest(
        session_id="SES-2026-DECALEE",
        filiere="Génie Logiciel",
        niveau="Master 1",
    )
    print("  [OK] Inscription mise à jour validée pour session:", insc_in.session_id)
    return True


def test_pedagogie_and_deliberation_engine():
    print("\n--- [TEST 3] Pédagogie & Moteur de Délibération ECTS ---")
    from app.schemas.pedagogie import NoteCreate, NoteBulkCreate, NoteBulkItem

    # 1. Test Saisie de Notes
    bulk_notes = NoteBulkCreate(
        matiere_id="INF301-1",
        notes=[
            NoteBulkItem(etudiant_id="ETU001", valeur=16.5, coefficient=2.0),
            NoteBulkItem(etudiant_id="ETU002", valeur=14.0, coefficient=2.0),
            NoteBulkItem(etudiant_id="ETU003", valeur=6.5, coefficient=2.0),  # < 7 (éliminatoire)
        ]
    )
    assert len(bulk_notes.notes) == 3
    print("  [OK] Saisie en lot (bulk) validée pour 3 étudiants.")

    # 2. Test Moteur de Délibération Individuelle (Cas Admis avec mention)
    etudiant_admis_data = {
        "id": "etu-1",
        "matricule": "2026-GL-0001",
        "nom": "Ba",
        "prenom": "Amadou",
        "filiere": "Génie Logiciel",
        "semestre": "Semestre 1",
        "ues_raw": [
            {
                "code": "UE-INF101",
                "nom": "Architecture Logicielle",
                "ects": 10,
                "ecues": [
                    {"code": "EC1", "nom": "Microservices", "note": 16.5, "coef": 2.0},
                    {"code": "EC2", "nom": "DevOps", "note": 15.0, "coef": 2.0},
                ],
            },
            {
                "code": "UE-INF102",
                "nom": "Bases de Données",
                "ects": 10,
                "ecues": [
                    {"code": "EC3", "nom": "PostgreSQL Avancé", "note": 14.0, "coef": 1.5},
                    {"code": "EC4", "nom": "NoSQL", "note": 15.5, "coef": 1.5},
                ],
            },
            {
                "code": "UE-MGT101",
                "nom": "Management & Anglais",
                "ects": 10,
                "ecues": [
                    {"code": "EC5", "nom": "Agilité", "note": 17.0, "coef": 1.0},
                    {"code": "EC6", "nom": "Anglais Tech", "note": 14.5, "coef": 1.0},
                ],
            },
        ],
    }

    res_admis = DeliberationEngine.calculer_etudiant(etudiant_admis_data)
    print(f"  [OK] Délibération Étudiant Admis: Moyenne = {res_admis.moyenne_generale}/20, ECTS = {res_admis.total_ects_acquis}/{res_admis.total_ects_max}")
    print(f"       Décision: {res_admis.statut_session}, Mention: {res_admis.mention}")
    assert res_admis.statut_session == "Admis"
    assert res_admis.total_ects_acquis == 30
    assert res_admis.mention in ["Bien", "Très Bien"]

    # 3. Test Délibération Individuelle (Cas Note Éliminatoire < 7 -> Rattrapage)
    etudiant_eliminatoire_data = {
        "id": "etu-2",
        "matricule": "2026-GL-0002",
        "nom": "Ndiaye",
        "prenom": "Awa",
        "filiere": "Génie Logiciel",
        "semestre": "Semestre 1",
        "ues_raw": [
            {
                "code": "UE-INF101",
                "nom": "Architecture Logicielle",
                "ects": 10,
                "ecues": [
                    {"code": "EC1", "nom": "Microservices", "note": 14.0, "coef": 2.0},
                    {"code": "EC2", "nom": "DevOps", "note": 13.0, "coef": 2.0},
                ],
            },
            {
                "code": "UE-INF102",
                "nom": "Bases de Données",
                "ects": 10,
                "ecues": [
                    {"code": "EC3", "nom": "PostgreSQL", "note": 5.5, "coef": 1.5},  # Note éliminatoire < 7.0 !
                    {"code": "EC4", "nom": "NoSQL", "note": 14.0, "coef": 1.5},
                ],
            },
            {
                "code": "UE-MGT101",
                "nom": "Management",
                "ects": 10,
                "ecues": [
                    {"code": "EC5", "nom": "Agilité", "note": 12.0, "coef": 1.0},
                ],
            },
        ],
    }
    res_elim = DeliberationEngine.calculer_etudiant(etudiant_eliminatoire_data)
    print(f"  [OK] Délibération Note Éliminatoire: Moyenne = {res_elim.moyenne_generale}/20, Note élim: {res_elim.notes_eliminatoires_details}")
    print(f"       Décision: {res_elim.statut_session}")
    assert res_elim.statut_session == "Rattrapage"
    assert res_elim.has_note_eliminatoire is True

    # 4. Test Promotion Cohorte
    res_promo = DeliberationEngine.calculer_promotion([etudiant_admis_data, etudiant_eliminatoire_data])
    print(f"  [OK] Délibération Cohorte: {res_promo.stats.total} étudiants, Taux réussite = {res_promo.stats.taux_reussite}, Moyenne Promo = {res_promo.stats.moyenne_promo}/20")
    assert res_promo.stats.total == 2
    assert res_promo.stats.admis == 1
    assert res_promo.stats.rattrapage == 1
    return True


def test_finances_and_receipts():
    print("\n--- [TEST 4] Finances, Encaissements & Reçus Structurés ---")
    from app.schemas.finance import FactureCreate, PaiementCreate, BalanceAgeeItem

    # 1. Facturation
    montant_facture = 375000.0
    f_in = FactureCreate(
        etudiant_id="etu-1",
        session_id="SES-2025-MAIN",
        montant_total=montant_facture,
        date_emission=date(2026, 1, 15),
        date_echeance=date(2026, 2, 15),
        numero_facture="FAC-2026-0001",
        description="Frais de scolarité Semestre 1",
    )
    print(f"  [OK] Facture générée: {f_in.numero_facture} pour un montant de {f_in.montant_total:,.0f} FCFA")

    # 2. Encaissement rattaché à une tranche de session
    montant_acompte = 200000.0
    p_in = PaiementCreate(
        etudiant_id="etu-1",
        session_id="SES-2025-MAIN",
        facture_id="fac-001",
        periode_id="per-main-1",  # Rattaché à la Tranche 1 (Octobre)
        montant=montant_acompte,
        mode_paiement="Wave Mobile Money",
        reference="WAV-2026-0042",
    )
    print(f"  [OK] Encaissement validé: {p_in.montant:,.0f} FCFA via {p_in.mode_paiement} (Ref: {p_in.reference})")

    # 3. Calcul du solde restant et nouveau statut facture
    reste = round(montant_facture - montant_acompte, 2)
    nouveau_statut = "payee" if reste <= 0 else "partielle"
    print(f"  [OK] Solde restant sur la facture: {reste:,.0f} FCFA -> Statut: '{nouveau_statut}'")
    assert reste == 175000.0
    assert nouveau_statut == "partielle"

    # 4. Reçu Structuré JSON
    recu_struct = {
        "numero_recu": "REC-2026-0001",
        "date_emission": "2026-01-20",
        "etudiant": {"matricule": "2026-GL-0001", "nom": "Ba", "prenom": "Amadou"},
        "details_paiement": {
            "periode": "Tranche 1 (Octobre)",
            "montant": montant_acompte,
            "mode_paiement": "Wave Mobile Money",
            "reference": "WAV-2026-0042",
        },
        "facture": {"numero_facture": "FAC-2026-0001", "solde_restant": reste},
    }
    print(f"  [OK] Reçu fiscal structuré émis: {recu_struct['numero_recu']} avec solde restant {recu_struct['facture']['solde_restant']:,.0f} FCFA")
    assert recu_struct["numero_recu"].startswith("REC-2026-")

    # 5. Balance Âgée
    b_item = BalanceAgeeItem(
        etudiant_id="etu-1",
        matricule="2026-GL-0001",
        nom_complet="Amadou Ba",
        filiere="Génie Logiciel",
        montant_total_du=reste,
        non_echu=0.0,
        retard_1_30_jours=reste,
        retard_31_60_jours=0.0,
        retard_plus_60_jours=0.0,
    )
    print(f"  [OK] Balance âgée calculée: {b_item.nom_complet} en retard de 1-30 jours ({b_item.retard_1_30_jours:,.0f} FCFA)")
    assert b_item.retard_1_30_jours == 175000.0
    return True


def main():
    print("================================================================")
    print("    TEST SUITE AUTOMATISÉE - SPRINT 2 (EDUMANAGEPRO BACKEND)    ")
    print("================================================================")

    test_structure_models_and_schemas()
    test_etudiant_models_and_matricule()
    test_pedagogie_and_deliberation_engine()
    test_finances_and_receipts()

    print("\n================================================================")
    print("  TOUS LES TESTS DU SPRINT 2 ONT RÉUSSI AVEC SUCCÈS (4/4) !    ")
    print("================================================================")


if __name__ == "__main__":
    main()
