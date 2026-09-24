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

import { AuthProvider } from "@/contexts/AuthContext";
import { RBACProvider, type UserRole } from "@/contexts/RBACContext";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";

const queryClient = new QueryClient();

const academicStructureRoles: UserRole[] = ["ADMIN", "DIRECTEUR_ETUDES"];
const pedagogyRoles: UserRole[] = ["ADMIN", "DIRECTEUR_ETUDES", "ENSEIGNANT"];

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <AuthProvider>
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
                <ProtectedRoute>
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
                    <Route
                       path="/etudiants"
                       element={
                         <ProtectedRoute allowedRoles={["ADMIN", "DIRECTEUR_ETUDES", "SECRETARIAT", "COMPTABILITE", "ENSEIGNANT"]}>
                           <Etudiants />
                         </ProtectedRoute>
                       }
                     />
                    <Route
                       path="/etudiants/:id"
                       element={
                         <ProtectedRoute allowedRoles={["ADMIN", "DIRECTEUR_ETUDES", "SECRETARIAT", "COMPTABILITE", "ENSEIGNANT"]}>
                           <StudentDetail />
                         </ProtectedRoute>
                       }
                     />
                    <Route
                      path="/validation"
                      element={
                        <ProtectedRoute allowedRoles={["ADMIN", "SECRETARIAT", "DIRECTEUR_ETUDES"]}>
                          <Validation />
                        </ProtectedRoute>
                      }
                    />

                    {/* Module 2: Gestion Pédagogique */}
                    <Route path="/filieres" element={<ProtectedRoute allowedRoles={academicStructureRoles}><Filieres /></ProtectedRoute>} />
                    <Route path="/filieres/:id" element={<ProtectedRoute allowedRoles={academicStructureRoles}><FiliereDetail /></ProtectedRoute>} />
                    <Route path="/matieres" element={<ProtectedRoute allowedRoles={academicStructureRoles}><Matieres /></ProtectedRoute>} />
                    <Route path="/matieres/:id" element={<ProtectedRoute allowedRoles={academicStructureRoles}><MatiereDetail /></ProtectedRoute>} />
                    <Route path="/ue" element={<ProtectedRoute allowedRoles={academicStructureRoles}><UnitesEnseignement /></ProtectedRoute>} />
                    <Route path="/ue/:id" element={<ProtectedRoute allowedRoles={academicStructureRoles}><UEDetail /></ProtectedRoute>} />
                    <Route path="/emplois-du-temps" element={<ProtectedRoute allowedRoles={pedagogyRoles}><EmploisDuTemps /></ProtectedRoute>} />
                    <Route
                      path="/notes"
                      element={
                        <ProtectedRoute allowedRoles={["ADMIN", "DIRECTEUR_ETUDES", "ENSEIGNANT"]}>
                          <Notes />
                        </ProtectedRoute>
                      }
                    />
                    <Route path="/ressources" element={<ProtectedRoute allowedRoles={pedagogyRoles}><Ressources /></ProtectedRoute>} />
                    <Route path="/absences" element={<ProtectedRoute allowedRoles={pedagogyRoles}><Absences /></ProtectedRoute>} />

                    {/* Module 3: RH & Enseignants */}
                    <Route path="/enseignants" element={<ProtectedRoute allowedRoles={["ADMIN", "SECRETARIAT"]}><Enseignants /></ProtectedRoute>} />
                    <Route path="/personnel" element={<ProtectedRoute allowedRoles={["ADMIN", "SECRETARIAT"]}><Personnel /></ProtectedRoute>} />
                    <Route path="/personnel/:id" element={<ProtectedRoute allowedRoles={["ADMIN", "SECRETARIAT"]}><PersonnelDetail /></ProtectedRoute>} />
                    <Route
                       path="/portail-enseignant"
                       element={
                         <ProtectedRoute allowedRoles={["ENSEIGNANT"]} allowSuperuser={false}>
                           <PortailEnseignant />
                         </ProtectedRoute>
                       }
                     />

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
                    <Route
                       path="/espace-etudiant"
                       element={
                         <ProtectedRoute allowedRoles={["ETUDIANT"]} allowSuperuser={false}>
                           <EspaceEtudiant />
                         </ProtectedRoute>
                       }
                     />
                    <Route path="/messagerie" element={<Messagerie />} />

                    {/* Module 6: Analytics & BI */}
                    <Route path="/analytics" element={<ProtectedRoute allowedRoles={["ADMIN", "DIRECTEUR_ETUDES", "COMPTABILITE"]}><Analytics /></ProtectedRoute>} />

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
                    <Route path="/campus" element={<ProtectedRoute allowedRoles={academicStructureRoles}><Campus /></ProtectedRoute>} />
                    <Route path="/campus/:id" element={<ProtectedRoute allowedRoles={academicStructureRoles}><CampusDetail /></ProtectedRoute>} />
                    <Route path="/sites" element={<ProtectedRoute allowedRoles={academicStructureRoles}><Sites /></ProtectedRoute>} />
                    <Route path="/sites/:id" element={<ProtectedRoute allowedRoles={academicStructureRoles}><SiteDetail /></ProtectedRoute>} />
                    <Route path="/salles" element={<ProtectedRoute allowedRoles={academicStructureRoles}><Salles /></ProtectedRoute>} />
                    <Route path="/salles/:id" element={<ProtectedRoute allowedRoles={academicStructureRoles}><SalleDetail /></ProtectedRoute>} />
                    <Route path="/departements" element={<ProtectedRoute allowedRoles={academicStructureRoles}><Departements /></ProtectedRoute>} />
                    <Route path="/departements/:id" element={<ProtectedRoute allowedRoles={academicStructureRoles}><DepartementDetail /></ProtectedRoute>} />
                    <Route path="/promotions" element={<ProtectedRoute allowedRoles={academicStructureRoles}><Promotions /></ProtectedRoute>} />
                    <Route path="/promotions/:id" element={<ProtectedRoute allowedRoles={academicStructureRoles}><PromotionDetail /></ProtectedRoute>} />
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
                </ProtectedRoute>
              }
            />
          </Routes>
        </Suspense>
      </BrowserRouter>
        </RBACProvider>
      </AuthProvider>
    </TooltipProvider>
</QueryClientProvider>
);

export default App;
