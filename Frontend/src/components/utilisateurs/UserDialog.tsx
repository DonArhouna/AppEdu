import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { etudiantsApi } from "@/services/apiClient";
import type { Student, User } from "@/services/apiTypes";

export interface UserFormData {
  nom: string;
  prenom: string;
  email: string;
  telephone: string;
  role: string;
  is_active: boolean;
  etudiant_id: string;
  password?: string;
}

type EditableUser = Pick<User, "id" | "email" | "nom" | "prenom" | "telephone" | "role" | "is_active"> & Partial<User>;

interface UserDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  userToEdit?: EditableUser;
  protectAdminAccess?: boolean;
  onSave: (data: UserFormData) => Promise<void> | void;
}

const emptyForm: UserFormData = {
  nom: "",
  prenom: "",
  email: "",
  telephone: "",
  role: "ENSEIGNANT",
  is_active: true,
  etudiant_id: "",
  password: "",
};

export const UserDialog = ({ open, onOpenChange, userToEdit, protectAdminAccess = false, onSave }: UserDialogProps) => {
  const [formData, setFormData] = useState<UserFormData>(emptyForm);
  const [students, setStudents] = useState<Student[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setFormData(
      userToEdit
        ? {
            nom: userToEdit.nom || "",
            prenom: userToEdit.prenom || "",
            email: userToEdit.email || "",
            telephone: userToEdit.telephone || "",
            role: userToEdit.role || "ENSEIGNANT",
            is_active: Boolean(userToEdit.is_active),
            etudiant_id: userToEdit.etudiant_id || "",
            password: "",
          }
        : emptyForm
    );
  }, [open, userToEdit]);

  useEffect(() => {
    if (!open) return;
    let active = true;
    const loadStudents = async () => {
      const result = await etudiantsApi.getAll();
      if (active) setStudents(result.data || []);
    };
    void loadStudents();
    return () => {
      active = false;
    };
  }, [open]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!userToEdit && (!formData.password || formData.password.length < 8)) {
      return;
    }
    setSaving(true);
    try {
      await onSave(formData);
      onOpenChange(false);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[550px]">
        <DialogHeader>
          <DialogTitle>{userToEdit ? "Modifier l'utilisateur" : "Créer un utilisateur"}</DialogTitle>
          <DialogDescription>
            L'identité, le rôle statique et le statut sont enregistrés par le backend.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2"><Label htmlFor="user-prenom">Prénom *</Label><Input id="user-prenom" required value={formData.prenom} onChange={(event) => setFormData({ ...formData, prenom: event.target.value })} /></div>
            <div className="space-y-2"><Label htmlFor="user-nom">Nom *</Label><Input id="user-nom" required value={formData.nom} onChange={(event) => setFormData({ ...formData, nom: event.target.value })} /></div>
          </div>
          <div className="space-y-2"><Label htmlFor="user-email">Email *</Label><Input id="user-email" type="email" required value={formData.email} onChange={(event) => setFormData({ ...formData, email: event.target.value })} disabled={Boolean(userToEdit)} /></div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2"><Label htmlFor="user-telephone">Téléphone</Label><Input id="user-telephone" value={formData.telephone} onChange={(event) => setFormData({ ...formData, telephone: event.target.value })} /></div>
            <div className="space-y-2"><Label htmlFor="user-role">Rôle *</Label><Select value={formData.role} onValueChange={(value) => setFormData({ ...formData, role: value })}><SelectTrigger id="user-role" disabled={protectAdminAccess}><SelectValue /></SelectTrigger><SelectContent>
              <SelectItem value="ADMIN">Administrateur</SelectItem><SelectItem value="DIRECTEUR_ETUDES">Directeur des études</SelectItem><SelectItem value="SECRETARIAT">Secrétariat</SelectItem><SelectItem value="COMPTABILITE">Comptabilité</SelectItem><SelectItem value="ENSEIGNANT">Enseignant</SelectItem><SelectItem value="ETUDIANT">Étudiant</SelectItem>
            </SelectContent></Select></div>
          </div>
          {formData.role === "ETUDIANT" && (
             <div className="space-y-2">
               <Label htmlFor="user-etudiant">Dossier étudiant lié</Label>
               <Select
                 value={formData.etudiant_id || "none"}
                 onValueChange={(value) => setFormData({ ...formData, etudiant_id: value === "none" ? "" : value })}
               >
                 <SelectTrigger id="user-etudiant">
                   <SelectValue placeholder="Sélectionner un dossier" />
                 </SelectTrigger>
                 <SelectContent>
                   <SelectItem value="none">Aucun dossier lié</SelectItem>
                   {students.map((student) => (
                     <SelectItem key={student.id} value={student.id}>
                       {student.matricule} — {student.prenom} {student.nom}
                     </SelectItem>
                   ))}
                 </SelectContent>
               </Select>
               <p className="text-xs text-muted-foreground">
                 Un lien explicite est recommandé pour le portail auto-service étudiant.
               </p>
             </div>
           )}
           <div className="space-y-2"><Label htmlFor="user-status">Statut</Label><Select value={formData.is_active ? "active" : "inactive"} onValueChange={(value) => setFormData({ ...formData, is_active: value === "active" })}><SelectTrigger id="user-status" disabled={protectAdminAccess}><SelectValue /></SelectTrigger><SelectContent><SelectItem value="active">Actif</SelectItem><SelectItem value="inactive">Inactif</SelectItem></SelectContent></Select>{protectAdminAccess && <p className="text-xs text-amber-600 dark:text-amber-400">Le dernier administrateur actif doit conserver son rôle et son accès.</p>}</div>
          <div className="space-y-2"><Label htmlFor="user-password">{userToEdit ? "Nouveau mot de passe (optionnel)" : "Mot de passe *"}</Label><Input id="user-password" type="password" minLength={userToEdit ? 0 : 8} required={!userToEdit} value={formData.password} onChange={(event) => setFormData({ ...formData, password: event.target.value })} /></div>
          <div className="flex justify-end gap-3 border-t pt-4"><Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Annuler</Button><Button type="submit" disabled={saving}>{saving ? "Enregistrement..." : userToEdit ? "Enregistrer" : "Créer"}</Button></div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default UserDialog;
