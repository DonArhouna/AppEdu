import { lazy, Suspense } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { PageLoader } from "@/components/ui/page-loader";

// 🚀 Performance Code-Splitting: Lazy loading all page views for lightning fast initial load
const Dashboard = lazy(() => import("./pages/Dashboard"));
const PreInscription = lazy(() => import("./pages/PreInscription"));
const Etudiants = lazy(() => import("./pages/Etudiants"));
const StudentDetail = lazy(() => import("./pages/StudentDetail"));
const Validation = lazy(() => import("./pages/Validation"));
const Promotions = lazy(() => import("./pages/Promotions"));
const PromotionDetail = lazy(() => import("./pages/PromotionDetail"));
const SessionsConfig = lazy(() => import("./pages/SessionsConfig"));
const Departements = lazy(() => import("./pages/Departements"));
const DepartementDetail = lazy(() => import("./pages/DepartementDetail"));
const Filieres = lazy(() => import("./pages/Filieres"));
const FiliereDetail = lazy(() => import("./pages/FiliereDetail"));
const Campus = lazy(() => import("./pages/Campus"));
const CampusDetail = lazy(() => import("./pages/CampusDetail"));
const Sites = lazy(() => import("./pages/Sites"));
const SiteDetail = lazy(() => import("./pages/SiteDetail"));
const Personnel = lazy(() => import("./pages/Personnel"));
const Enseignants = lazy(() => import("./pages/Enseignants")); // <-- NEW!
const PersonnelDetail = lazy(() => import("./pages/PersonnelDetail"));
const Matieres = lazy(() => import("./pages/MatieresECUE"));
const UnitesEnseignement = lazy(() => import("./pages/UnitesEnseignement"));
const MatiereDetail = lazy(() => import("./pages/MatiereDetail"));
const UEDetail = lazy(() => import("./pages/UEDetail"));
const PortailEnseignant = lazy(() => import("./pages/PortailEnseignant"));
const EmploisDuTemps = lazy(() => import("./pages/EmploisDuTemps"));
const Notes = lazy(() => import("./pages/Notes"));
const Ressources = lazy(() => import("./pages/Ressources"));
const Absences = lazy(() => import("./pages/Absences"));
const FraisScolarite = lazy(() => import("./pages/FraisScolarite"));
const Factures = lazy(() => import("./pages/Factures"));
const FactureDetail = lazy(() => import("./pages/FactureDetail"));
const Paiements = lazy(() => import("./pages/Paiements"));
const PaiementDetail = lazy(() => import("./pages/PaiementDetail"));
const ReportingFinancier = lazy(() => import("./pages/ReportingFinancier"));
const EspaceEtudiant = lazy(() => import("./pages/EspaceEtudiant"));
const Messagerie = lazy(() => import("./pages/Messagerie"));
const Analytics = lazy(() => import("./pages/Analytics"));
const RolesPermissions = lazy(() => import("./pages/RolesPermissions"));
const Parametrage = lazy(() => import("./pages/Parametrage"));
const Salles = lazy(() => import("./pages/Salles"));
const SalleDetail = lazy(() => import("./pages/SalleDetail"));
const Utilisateurs = lazy(() => import("./pages/Utilisateurs"));
const JournalAudit = lazy(() => import("./pages/JournalAudit"));
const VerificationDocument = lazy(() => import("./pages/VerificationDocument"));
const Profil = lazy(() => import("./pages/Profil"));
const ParametresCompte = lazy(() => import("./pages/ParametresCompte"));
const Login = lazy(() => import("./pages/Login"));
const SetupWizard = lazy(() => import("./pages/SetupWizard"));
const Deconnexion = lazy(() => import("./pages/Deconnexion"));
const NotFound = lazy(() => import("./pages/NotFound"));

import { RBACProvider } from "@/contexts/RBACContext";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <RBACProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            {/* Standalone Authentication & Public Verification Routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/setup" element={<SetupWizard />} />
            <Route path="/verifier-document" element={<VerificationDocument />} />
            <Route path="/verifier-document/:id" element={<VerificationDocument />} />

            {/* Main SaaS Application Routes */}
            <Route
              path="/*"
              element={
                <MainLayout>
                  <Routes>
                    {/* Dashboard Global */}
                    <Route path="/" element={<Dashboard />} />

                    {/* Module 1: Scolarité & Admissions */}
                    <Route
                      path="/pre-inscription"
                      element={
                        <ProtectedRoute allowedRoles={["ADMIN", "SECRETARIAT", "DIRECTEUR_ETUDES"]}>
                          <PreInscription />
                        </ProtectedRoute>
                      }
                    />
                    <Route path="/etudiants" element={<Etudiants />} />
                    <Route path="/etudiants/:id" element={<StudentDetail />} />
                    <Route
                      path="/validation"
                      element={
                        <ProtectedRoute allowedRoles={["ADMIN", "SECRETARIAT", "DIRECTEUR_ETUDES"]}>
                          <Validation />
                        </ProtectedRoute>
                      }
                    />

                    {/* Module 2: Gestion Pédagogique */}
                    <Route path="/filieres" element={<Filieres />} />
                    <Route path="/filieres/:id" element={<FiliereDetail />} />
                    <Route path="/matieres" element={<Matieres />} />
                    <Route path="/matieres/:id" element={<MatiereDetail />} />
                    <Route path="/ue" element={<UnitesEnseignement />} />
                    <Route path="/ue/:id" element={<UEDetail />} />
                    <Route path="/emplois-du-temps" element={<EmploisDuTemps />} />
                    <Route
                      path="/notes"
                      element={
                        <ProtectedRoute allowedRoles={["ADMIN", "DIRECTEUR_ETUDES", "ENSEIGNANT"]}>
                          <Notes />
                        </ProtectedRoute>
                      }
                    />
                    <Route path="/ressources" element={<Ressources />} />
                    <Route path="/absences" element={<Absences />} />

                    {/* Module 3: RH & Enseignants */}
                    <Route path="/enseignants" element={<Enseignants />} />
                    <Route path="/personnel" element={<Personnel />} />
                    <Route path="/personnel/:id" element={<PersonnelDetail />} />
                    <Route path="/portail-enseignant" element={<PortailEnseignant />} />

                    {/* Module 4: Gestion Financière */}
                    <Route
                      path="/frais-scolarite"
                      element={
                        <ProtectedRoute allowedRoles={["ADMIN", "COMPTABILITE"]}>
                          <FraisScolarite />
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/factures"
                      element={
                        <ProtectedRoute allowedRoles={["ADMIN", "COMPTABILITE"]}>
                          <Factures />
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/factures/:id"
                      element={
                        <ProtectedRoute allowedRoles={["ADMIN", "COMPTABILITE"]}>
                          <FactureDetail />
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/paiements"
                      element={
                        <ProtectedRoute allowedRoles={["ADMIN", "COMPTABILITE"]}>
                          <Paiements />
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/paiements/:id"
                      element={
                        <ProtectedRoute allowedRoles={["ADMIN", "COMPTABILITE"]}>
                          <PaiementDetail />
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/reporting-financier"
                      element={
                        <ProtectedRoute allowedRoles={["ADMIN", "COMPTABILITE"]}>
                          <ReportingFinancier />
                        </ProtectedRoute>
                      }
                    />

                    {/* Module 5: Espace Étudiant & Messagerie */}
                    <Route path="/espace-etudiant" element={<EspaceEtudiant />} />
                    <Route path="/messagerie" element={<Messagerie />} />

                    {/* Module 6: Analytics & BI */}
                    <Route path="/analytics" element={<Analytics />} />

                    {/* Module 7: Paramètres & Structure (Administration) */}
                    <Route
                      path="/utilisateurs"
                      element={
                        <ProtectedRoute allowedRoles={["ADMIN"]}>
                          <Utilisateurs />
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/journal-audit"
                      element={
                        <ProtectedRoute allowedRoles={["ADMIN"]}>
                          <JournalAudit />
                        </ProtectedRoute>
                      }
                    />
                    <Route path="/campus" element={<Campus />} />
                    <Route path="/campus/:id" element={<CampusDetail />} />
                    <Route path="/sites" element={<Sites />} />
                    <Route path="/sites/:id" element={<SiteDetail />} />
                    <Route path="/salles" element={<Salles />} />
                    <Route path="/salles/:id" element={<SalleDetail />} />
                    <Route path="/departements" element={<Departements />} />
                    <Route path="/departements/:id" element={<DepartementDetail />} />
                    <Route path="/promotions" element={<Promotions />} />
                    <Route path="/promotions/:id" element={<PromotionDetail />} />
                    <Route
                      path="/sessions"
                      element={
                        <ProtectedRoute allowedRoles={["ADMIN", "DIRECTEUR_ETUDES", "COMPTABILITE"]}>
                          <SessionsConfig />
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/roles-permissions"
                      element={
                        <ProtectedRoute allowedRoles={["ADMIN"]}>
                          <RolesPermissions />
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/parametrage"
                      element={
                        <ProtectedRoute allowedRoles={["ADMIN"]}>
                          <Parametrage />
                        </ProtectedRoute>
                      }
                    />

                    {/* Profil Utilisateur & Compte */}
                    <Route path="/profil" element={<Profil />} />
                    <Route path="/parametres-compte" element={<ParametresCompte />} />
                    <Route path="/deconnexion" element={<Deconnexion />} />

                    {/* 404 */}
                    <Route path="*" element={<NotFound />} />
                  </Routes>
                </MainLayout>
              }
            />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </RBACProvider>
  </TooltipProvider>
</QueryClientProvider>
);

export default App;
