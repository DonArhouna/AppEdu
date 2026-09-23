"""
Script de peuplement de données réelles pour EduManagePro (EMP)
Insère des données cohérentes dans PostgreSQL (Structure, Étudiants, Inscriptions, Factures, Paiements)
Usage: python seed_demo_data.py
"""

import asyncio
from datetime import date, datetime, timezone
import uuid
from sqlalchemy import select

from app.core.database import async_session_factory, get_engine_for_tenant
from app.core.security import get_password_hash
from app.models.base import Base
from app.models.etablissement import Etablissement
from app.models.utilisateur import Utilisateur, UserRole
from app.models.session_academique import SessionAcademique, PeriodePaiement
from app.models.structure import Campus, Departement, Filiere, UniteEnseignement, Matiere
from app.models.etudiant import Etudiant
from app.models.finance import Facture, Paiement, Recu
from app.models.pedagogie import Cours, Examen, Note, Absence


async def seed():
    engine = get_engine_for_tenant("default")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        # 1. Vérifier / Créer l'établissement
        etab = (await db.execute(select(Etablissement))).scalar_one_or_none()
        if not etab:
            etab = Etablissement(
                nom="Institut de Management & d'Informatique Appliquée",
                sigle="IMIA",
                adresse="Boulevard de France, Cocody",
                telephone="+225 27 22 00 00",
                email="contact@imia-edu.com",
                devise="FCFA",
                licence_cle="EMP-PRO-DEV-2026",
                is_configured=True,
                date_configuration=datetime.now(timezone.utc),
            )
            db.add(etab)

        # 2. Vérifier / Créer SuperAdmin
        admin = (await db.execute(select(Utilisateur).where(Utilisateur.email == "admin@edumanagepro.com"))).scalar_one_or_none()
        if not admin:
            admin = Utilisateur(
                email="admin@edumanagepro.com",
                hashed_password=get_password_hash("Admin@2026!"),
                nom="Directeur",
                prenom="Principal",
                telephone="+225 07 00 00 01",
                role=UserRole.ADMIN.value,
                is_active=True,
                is_superuser=True,
                last_login=datetime.now(timezone.utc),
            )
            db.add(admin)

        # 3. Session Académique
        session = (await db.execute(select(SessionAcademique).where(
            (SessionAcademique.id == "session-2025-2026") | (SessionAcademique.code == "2025-2026")
        ))).scalar_one_or_none()
        
        if not session:
            session_id = "session-2025-2026"
            session = SessionAcademique(
                id=session_id,
                nom="Année Académique 2025-2026",
                code="2025-2026",
                annee_academique="2025-2026",
                date_debut=date(2025, 9, 1),
                date_fin=date(2026, 7, 31),
                statut="active",
                description="Session académique principale de rentrée de septembre."
            )
            db.add(session)
            await db.flush()
        else:
            session_id = session.id

            # Périodes
            periodes = [
                ("Tranche 1 - Octobre", "Octobre", date(2025, 10, 15), 1),
                ("Tranche 2 - Janvier", "Janvier", date(2026, 1, 15), 2),
                ("Tranche 3 - Avril", "Avril", date(2026, 4, 15), 3),
            ]
            for nom_p, mois_p, ech, ordr in periodes:
                pid_per = f"PER-{ordr}"
                per_exist = (await db.execute(select(PeriodePaiement).where(PeriodePaiement.id == pid_per))).scalar_one_or_none()
                if not per_exist:
                    db.add(PeriodePaiement(
                        id=pid_per,
                        session_id=session_id,
                        nom=nom_p,
                        mois=mois_p,
                        date_echeance=ech,
                        montant_estime=60000.0,
                        ordre=ordr
                    ))

        await db.flush()

        # 4. Campus
        campuses_data = [
            ("CAMP-01", "Campus Principal", "CAMP-PRI", "Campus central de l'université", "Cocody Riviera", "Abidjan", "Dr. Emmanuel Koné"),
            ("CAMP-02", "Campus Nord", "CAMP-NOR", "Campus dédié aux sciences et technologies", "Plateau", "Abidjan", "Prof. Aya N'Guessan"),
            ("CAMP-03", "Campus Sud", "CAMP-SUD", "Campus des sciences de gestion", "Marcory Zone 4", "Abidjan", "Dr. Ibrahim Touré"),
        ]
        for cid, nom, code, desc, adr, ville, resp in campuses_data:
            existing = (await db.execute(select(Campus).where(Campus.id == cid))).scalar_one_or_none()
            if not existing:
                db.add(Campus(id=cid, nom=nom, code=code, description=desc, adresse=adr, ville=ville, responsable=resp))

        await db.flush()

        # 5. Départements
        depts_data = [
            ("DEP-01", "Génie Informatique & Télécoms", "GIT", "Formations en ingénierie logicielle et réseaux", "CAMP-01", "Dr. Marc Kouassi"),
            ("DEP-02", "Sciences de Gestion & Finance", "SGF", "Management, comptabilité et audit financier", "CAMP-03", "Dr. Mariam Coulibaly"),
        ]
        for did, nom, code, desc, cid, resp in depts_data:
            existing = (await db.execute(select(Departement).where(Departement.id == did))).scalar_one_or_none()
            if not existing:
                db.add(Departement(id=did, nom=nom, code=code, description=desc, campus_id=cid, responsable=resp))

        await db.flush()

        # 6. Filières
        filieres_data = [
            ("FIL-01", "Génie Logiciel", "GL", "DEP-01", "Licence", 3, "Licence professionnelle en conception logicielle"),
            ("FIL-02", "Cybersécurité & Réseaux", "CR", "DEP-01", "Licence", 3, "Protection des systèmes d'information"),
            ("FIL-03", "Finance d'Entreprise", "FE", "DEP-02", "Master", 2, "Expertise en analyse et gestion financière"),
        ]
        for fid, nom, code, did, diplome, dur, desc in filieres_data:
            existing = (await db.execute(select(Filiere).where(Filiere.id == fid))).scalar_one_or_none()
            if not existing:
                db.add(Filiere(id=fid, nom=nom, code=code, departement_id=did, diplome=diplome, duree=dur, description=desc))

        await db.flush()

        # 7. Unités d'Enseignement (UEs)
        ues_data = [
            ("UE-01", "Architecture Logicielle & DevOps", "UE-GL-01", "FIL-01", "S5", 6, 3.0, 45, "Licence 3", "Dr. Kouassi"),
            ("UE-02", "Bases de Données Avancées", "UE-GL-02", "FIL-01", "S5", 6, 2.5, 45, "Licence 3", "Dr. Diallo"),
            ("UE-03", "Sécurité des Applications Web", "UE-CR-01", "FIL-02", "S5", 6, 3.0, 45, "Licence 3", "Ing. Yao"),
        ]
        for uid_p, nom, code, fid, sem, cr, coef, hrs, niv, resp in ues_data:
            existing = (await db.execute(select(UniteEnseignement).where(UniteEnseignement.id == uid_p))).scalar_one_or_none()
            if not existing:
                db.add(UniteEnseignement(
                    id=uid_p,
                    nom=nom,
                    code=code,
                    filiere_id=fid,
                    semestre=sem,
                    credits=cr,
                    coefficient=coef,
                    heures=hrs,
                    niveau=niv,
                    responsable=resp
                ))

        await db.flush()

        # 8. Matières (ECUE)
        matieres_data = [
            ("MAT-01", "FastAPI & Microservices", "INF301", "UE-01", 3, 1.5, 20, 15, 10, "Dr. Diallo"),
            ("MAT-02", "Conteneurisation Docker & Kubernetes", "INF302", "UE-01", 3, 1.5, 15, 15, 15, "Ing. Yao"),
            ("MAT-03", "PostgreSQL & Modélisation Avancée", "INF303", "UE-02", 3, 1.5, 20, 15, 10, "Dr. Traoré"),
        ]
        for mid, nom, code, ue_id, cr, coef, cm, td, tp, ens in matieres_data:
            existing = (await db.execute(select(Matiere).where(Matiere.id == mid))).scalar_one_or_none()
            if not existing:
                db.add(Matiere(id=mid, nom=nom, code=code, ue_id=ue_id, credits=cr, coefficient=coef, heures_cm=cm, heures_td=td, heures_tp=tp, enseignant_nom=ens))

        await db.flush()

        # 9. Étudiants réels
        etudiants_data = [
            ("ETU-001", "2026-GL-0001", "Dupont", "Marie", "marie.dupont@email.com", "+225 07 11 22 33", "Génie Logiciel", "FIL-01", "Licence 3", session_id, "actif", 60),
            ("ETU-002", "2026-CR-0002", "Konan", "Kouassi Jean", "k.konan@email.com", "+225 05 22 33 44", "Cybersécurité & Réseaux", "FIL-02", "Licence 3", session_id, "actif", 48),
            ("ETU-003", "2026-GL-0003", "Sarr", "Awa", "awa.sarr@email.com", "+225 01 33 44 55", "Génie Logiciel", "FIL-01", "Licence 2", session_id, "actif", 35),
            ("ETU-004", "2026-FE-0004", "Dubois", "Pierre", "pierre.dubois@email.com", "+225 07 44 55 66", "Finance d'Entreprise", "FIL-03", "Master 2", session_id, "actif", 60),
        ]
        for eid, mat, nom, pre, em, tel, fil, fid, niv, ses, st, _ in etudiants_data:
            existing = (await db.execute(select(Etudiant).where(Etudiant.id == eid))).scalar_one_or_none()
            if not existing:
                db.add(Etudiant(
                    id=eid,
                    matricule=mat,
                    nom=nom,
                    prenom=pre,
                    email=em,
                    telephone=tel,
                    filiere=fil,
                    filiere_id=fid,
                    niveau=niv,
                    session_id=ses,
                    statut=st,
                    date_naissance=date(2002, 5, 14),
                    adresse="Abidjan Cocody",
                    date_inscription=date(2025, 9, 10),
                ))

        await db.flush()

        # 10. Factures & Paiements
        factures_data = [
            ("FAC-2026-0001", "ETU-001", session_id, 375000.0, 375000.0, "payee", date(2025, 9, 15), date(2025, 10, 15), "Scolarité Annuelle L3 GL"),
            ("FAC-2026-0002", "ETU-002", session_id, 450000.0, 250000.0, "partielle", date(2025, 9, 15), date(2025, 10, 15), "Scolarité Annuelle L3 Cybersécurité"),
            ("FAC-2026-0003", "ETU-003", session_id, 350000.0, 0.0, "emise", date(2025, 9, 15), date(2025, 10, 15), "Scolarité Annuelle L2 GL"),
        ]
        for fid, eid, ses, tot, paye, st, emis, ech, desc in factures_data:
            existing = (await db.execute(select(Facture).where(Facture.id == fid))).scalar_one_or_none()
            if not existing:
                db.add(Facture(
                    id=fid,
                    numero_facture=fid,
                    etudiant_id=eid,
                    session_id=ses,
                    montant_total=tot,
                    montant_paye=paye,
                    date_emission=emis,
                    date_echeance=ech,
                    statut=st,
                    description=desc,
                ))

        await db.flush()

        # Paiements
        paiements_data = [
            ("PAI-2026-0001", "FAC-2026-0001", "ETU-001", session_id, 375000.0, date(2025, 10, 5), "Espèces", "ESP-2025-001"),
            ("PAI-2026-0002", "FAC-2026-0002", "ETU-002", session_id, 250000.0, date(2025, 10, 12), "Wave", "WAV-2025-042"),
        ]
        for pid, fac_id, eid, ses, mnt, dt, mode, ref in paiements_data:
            existing = (await db.execute(select(Paiement).where(Paiement.id == pid))).scalar_one_or_none()
            if not existing:
                p = Paiement(
                    id=pid,
                    facture_id=fac_id,
                    etudiant_id=eid,
                    session_id=ses,
                    montant=mnt,
                    date_paiement=dt,
                    mode_paiement=mode,
                    reference=ref,
                    statut="valide",
                    encaisse_par_id=admin.id,
                )
                db.add(p)
                await db.flush()

                # Reçu
                recu_num = f"REC-{pid[-4:]}"
                db.add(Recu(
                    id=f"rec-{pid}",
                    numero_recu=recu_num,
                    paiement_id=pid,
                    date_emission=dt,
                    donnees_json={
                        "numero_recu": recu_num,
                        "etudiant_id": eid,
                        "montant": mnt,
                        "etablissement": "IMIA",
                    }
                ))

        await db.flush()

        # 11. Pédagogie (Cours, Examens, Notes, Absences)
        cours_data = [
            ("CRS-01", "MAT-01", "Amphi A", "Lundi", "08:00", "10:00", "CM", "Dr. Diallo"),
            ("CRS-02", "MAT-01", "Salle TP 3", "Mardi", "10:00", "12:00", "TP", "Dr. Diallo"),
            ("CRS-03", "MAT-02", "Salle B2", "Mercredi", "14:00", "16:00", "TD", "Ing. Yao"),
            ("CRS-04", "MAT-03", "Labo Info", "Jeudi", "09:00", "12:00", "TP", "Dr. Traoré"),
        ]
        for cid, mid, salle, jour, hdeb, hfin, tc, ens in cours_data:
            existing = (await db.execute(select(Cours).where(Cours.id == cid))).scalar_one_or_none()
            if not existing:
                db.add(Cours(
                    id=cid,
                    matiere_id=mid,
                    salle=salle,
                    jour_semaine=jour,
                    heure_debut=hdeb,
                    heure_fin=hfin,
                    type_cours=tc,
                    enseignant_nom=ens
                ))

        await db.flush()

        # Examens
        examens_data = [
            ("EXAM-01", "Contrôle Continu 1 - FastAPI", session_id, "MAT-01", "CC", date(2025, 11, 20), 120, 1.0),
            ("EXAM-02", "Examen Partiel - Docker & Kubernetes", session_id, "MAT-02", "Partiel", date(2026, 1, 10), 180, 2.0),
        ]
        for xid, nom, ses, mid, t_ex, dt, dur, coef in examens_data:
            existing = (await db.execute(select(Examen).where(Examen.id == xid))).scalar_one_or_none()
            if not existing:
                db.add(Examen(
                    id=xid,
                    nom=nom,
                    session_id=ses,
                    matiere_id=mid,
                    type_examen=t_ex,
                    date_examen=dt,
                    duree_minutes=dur,
                    coefficient=coef
                ))

        await db.flush()

        # Notes
        notes_data = [
            ("NOTE-01", "ETU-001", "MAT-01", "EXAM-01", session_id, 16.5, 1.0, "Très bon travail", "Validé"),
            ("NOTE-02", "ETU-002", "MAT-01", "EXAM-01", session_id, 14.0, 1.0, "Bien", "Validé"),
            ("NOTE-03", "ETU-003", "MAT-01", "EXAM-01", session_id, 11.5, 1.0, "Passable", "Validé"),
            ("NOTE-04", "ETU-001", "MAT-02", "EXAM-02", session_id, 18.0, 2.0, "Excellent", "Validé"),
            ("NOTE-05", "ETU-002", "MAT-02", "EXAM-02", session_id, 12.0, 2.0, "Moyen", "Validé"),
        ]
        for nid, eid, mid, xid, ses, val, coef, app, st in notes_data:
            existing = (await db.execute(select(Note).where(Note.id == nid))).scalar_one_or_none()
            if not existing:
                db.add(Note(
                    id=nid,
                    etudiant_id=eid,
                    matiere_id=mid,
                    examen_id=xid,
                    session_id=ses,
                    valeur=val,
                    coefficient=coef,
                    appreciation=app,
                    statut=st,
                    saisi_par_id=admin.id
                ))

        # Absences
        absences_data = [
            ("ABS-01", "ETU-002", "CRS-01", "MAT-01", date(2025, 10, 13), 2.0, False, "Non justifiée"),
            ("ABS-02", "ETU-003", "CRS-03", "MAT-02", date(2025, 10, 20), 2.0, True, "Certificat médical"),
        ]
        for aid, eid, crs_id, mid, dt, dur, just, motif in absences_data:
            existing = (await db.execute(select(Absence).where(Absence.id == aid))).scalar_one_or_none()
            if not existing:
                db.add(Absence(
                    id=aid,
                    etudiant_id=eid,
                    cours_id=crs_id,
                    matiere_id=mid,
                    date_absence=dt,
                    duree_heures=dur,
                    justifiee=just,
                    motif=motif
                ))

        await db.commit()
        print("[SEED] Données réelles insérées avec succès dans PostgreSQL !")


if __name__ == "__main__":
    asyncio.run(seed())
