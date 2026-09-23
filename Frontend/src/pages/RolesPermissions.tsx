import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Shield, Plus, Edit, Trash2 } from "lucide-react";

const RolesPermissions = () => {
  const [selectedRole, setSelectedRole] = useState<string | null>(null);

  const roles = [
    {
      id: 1,
      name: "Administrateur",
      description: "Accès complet à toutes les fonctionnalités",
      users: 3,
      color: "destructive",
    },
    {
      id: 2,
      name: "Secrétariat",
      description: "Gestion de la scolarité et des inscriptions",
      users: 8,
      color: "default",
    },
    {
      id: 3,
      name: "Enseignant",
      description: "Accès au portail enseignant et saisie des notes",
      users: 44,
      color: "secondary",
    },
    {
      id: 4,
      name: "Étudiant",
      description: "Accès à l'espace étudiant et consultation",
      users: 1234,
      color: "outline",
    },
  ];

  const permissions = {
    scolarite: [
      { id: "scol_read", label: "Consulter les étudiants", admin: true, secretariat: true, enseignant: false, etudiant: false },
      { id: "scol_write", label: "Modifier les étudiants", admin: true, secretariat: true, enseignant: false, etudiant: false },
      { id: "scol_validate", label: "Valider les dossiers", admin: true, secretariat: true, enseignant: false, etudiant: false },
      { id: "scol_delete", label: "Supprimer des étudiants", admin: true, secretariat: false, enseignant: false, etudiant: false },
    ],
    pedagogie: [
      { id: "ped_read", label: "Consulter les notes", admin: true, secretariat: true, enseignant: true, etudiant: true },
      { id: "ped_write", label: "Saisir les notes", admin: true, secretariat: false, enseignant: true, etudiant: false },
      { id: "ped_resources", label: "Gérer les ressources", admin: true, secretariat: false, enseignant: true, etudiant: false },
      { id: "ped_schedule", label: "Modifier emploi du temps", admin: true, secretariat: true, enseignant: false, etudiant: false },
    ],
    financier: [
      { id: "fin_read", label: "Consulter les paiements", admin: true, secretariat: true, enseignant: false, etudiant: true },
      { id: "fin_write", label: "Enregistrer paiements", admin: true, secretariat: true, enseignant: false, etudiant: false },
      { id: "fin_config", label: "Configurer les frais", admin: true, secretariat: false, enseignant: false, etudiant: false },
      { id: "fin_reports", label: "Accès reporting financier", admin: true, secretariat: false, enseignant: false, etudiant: false },
    ],
    administration: [
      { id: "admin_users", label: "Gérer les utilisateurs", admin: true, secretariat: false, enseignant: false, etudiant: false },
      { id: "admin_roles", label: "Gérer les rôles", admin: true, secretariat: false, enseignant: false, etudiant: false },
      { id: "admin_config", label: "Paramétrage général", admin: true, secretariat: false, enseignant: false, etudiant: false },
      { id: "admin_analytics", label: "Accès analytics", admin: true, secretariat: false, enseignant: false, etudiant: false },
    ],
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Rôles & Permissions</h1>
          <p className="text-muted-foreground mt-2">
            Gérez les rôles utilisateurs et leurs permissions d'accès
          </p>
        </div>
        <Dialog>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Nouveau Rôle
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Créer un nouveau rôle</DialogTitle>
              <DialogDescription>
                Définissez le nom et les permissions du nouveau rôle
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="role-name">Nom du rôle</Label>
                <Input id="role-name" placeholder="Ex: Directeur des études" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="role-description">Description</Label>
                <Input id="role-description" placeholder="Description du rôle" />
              </div>
              <Button className="w-full">Créer le rôle</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {roles.map((role) => (
          <Card
            key={role.id}
            className={`cursor-pointer transition-all ${
              selectedRole === role.name ? "ring-2 ring-primary" : ""
            }`}
            onClick={() => setSelectedRole(role.name)}
          >
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <Shield className="h-5 w-5 text-primary" />
              <Badge variant={role.color as any}>{role.users} utilisateurs</Badge>
            </CardHeader>
            <CardContent>
              <h3 className="font-bold text-foreground mb-1">{role.name}</h3>
              <p className="text-sm text-muted-foreground">{role.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Matrice des Permissions</CardTitle>
          <p className="text-sm text-muted-foreground">
            Définissez les permissions pour chaque rôle et module
          </p>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {/* Scolarité */}
            <div>
              <h3 className="font-semibold text-foreground mb-4">Module 1: Scolarité</h3>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Permission</TableHead>
                    <TableHead className="text-center">Admin</TableHead>
                    <TableHead className="text-center">Secrétariat</TableHead>
                    <TableHead className="text-center">Enseignant</TableHead>
                    <TableHead className="text-center">Étudiant</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {permissions.scolarite.map((perm) => (
                    <TableRow key={perm.id}>
                      <TableCell className="font-medium">{perm.label}</TableCell>
                      <TableCell className="text-center">
                        <Switch checked={perm.admin} />
                      </TableCell>
                      <TableCell className="text-center">
                        <Switch checked={perm.secretariat} />
                      </TableCell>
                      <TableCell className="text-center">
                        <Switch checked={perm.enseignant} />
                      </TableCell>
                      <TableCell className="text-center">
                        <Switch checked={perm.etudiant} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Pédagogie */}
            <div>
              <h3 className="font-semibold text-foreground mb-4">Module 2: Pédagogie</h3>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Permission</TableHead>
                    <TableHead className="text-center">Admin</TableHead>
                    <TableHead className="text-center">Secrétariat</TableHead>
                    <TableHead className="text-center">Enseignant</TableHead>
                    <TableHead className="text-center">Étudiant</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {permissions.pedagogie.map((perm) => (
                    <TableRow key={perm.id}>
                      <TableCell className="font-medium">{perm.label}</TableCell>
                      <TableCell className="text-center">
                        <Switch checked={perm.admin} />
                      </TableCell>
                      <TableCell className="text-center">
                        <Switch checked={perm.secretariat} />
                      </TableCell>
                      <TableCell className="text-center">
                        <Switch checked={perm.enseignant} />
                      </TableCell>
                      <TableCell className="text-center">
                        <Switch checked={perm.etudiant} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Financier */}
            <div>
              <h3 className="font-semibold text-foreground mb-4">Module 4: Financier</h3>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Permission</TableHead>
                    <TableHead className="text-center">Admin</TableHead>
                    <TableHead className="text-center">Secrétariat</TableHead>
                    <TableHead className="text-center">Enseignant</TableHead>
                    <TableHead className="text-center">Étudiant</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {permissions.financier.map((perm) => (
                    <TableRow key={perm.id}>
                      <TableCell className="font-medium">{perm.label}</TableCell>
                      <TableCell className="text-center">
                        <Switch checked={perm.admin} />
                      </TableCell>
                      <TableCell className="text-center">
                        <Switch checked={perm.secretariat} />
                      </TableCell>
                      <TableCell className="text-center">
                        <Switch checked={perm.enseignant} />
                      </TableCell>
                      <TableCell className="text-center">
                        <Switch checked={perm.etudiant} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Administration */}
            <div>
              <h3 className="font-semibold text-foreground mb-4">Module 7: Administration</h3>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Permission</TableHead>
                    <TableHead className="text-center">Admin</TableHead>
                    <TableHead className="text-center">Secrétariat</TableHead>
                    <TableHead className="text-center">Enseignant</TableHead>
                    <TableHead className="text-center">Étudiant</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {permissions.administration.map((perm) => (
                    <TableRow key={perm.id}>
                      <TableCell className="font-medium">{perm.label}</TableCell>
                      <TableCell className="text-center">
                        <Switch checked={perm.admin} />
                      </TableCell>
                      <TableCell className="text-center">
                        <Switch checked={perm.secretariat} />
                      </TableCell>
                      <TableCell className="text-center">
                        <Switch checked={perm.enseignant} />
                      </TableCell>
                      <TableCell className="text-center">
                        <Switch checked={perm.etudiant} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default RolesPermissions;
