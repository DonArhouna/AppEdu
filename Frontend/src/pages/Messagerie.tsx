import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Send, Search, User, Mail } from "lucide-react";

const Messagerie = () => {
  const [selectedConversation, setSelectedConversation] = useState(0);
  const [message, setMessage] = useState("");

  const conversations = [
    {
      id: 1,
      name: "Prof. Dubois",
      role: "Enseignant - Bases de Données",
      lastMessage: "Bonjour, concernant le projet de fin de semestre...",
      time: "Il y a 2h",
      unread: 2,
      avatar: "PD"
    },
    {
      id: 2,
      name: "Administration",
      role: "Service Scolarité",
      lastMessage: "Votre demande de certificat a été traitée",
      time: "Il y a 5h",
      unread: 0,
      avatar: "AD"
    },
    {
      id: 3,
      name: "Prof. Martin",
      role: "Enseignant - Programmation Web",
      lastMessage: "Le TP de la semaine prochaine est reporté",
      time: "Hier",
      unread: 1,
      avatar: "PM"
    },
    {
      id: 4,
      name: "Prof. Bernard",
      role: "Enseignant - Réseaux",
      lastMessage: "Les notes du dernier examen sont disponibles",
      time: "Il y a 2 jours",
      unread: 0,
      avatar: "PB"
    },
  ];

  const messages = [
    {
      id: 1,
      sender: "Prof. Dubois",
      content: "Bonjour Sophie, j'ai consulté votre projet de base de données. C'est un bon travail !",
      time: "10:30",
      isOwn: false
    },
    {
      id: 2,
      sender: "Vous",
      content: "Merci beaucoup professeur ! J'ai quelques questions sur la normalisation.",
      time: "10:35",
      isOwn: true
    },
    {
      id: 3,
      sender: "Prof. Dubois",
      content: "Bien sûr, je suis disponible demain après-midi pour en discuter. Passez me voir à mon bureau.",
      time: "10:40",
      isOwn: false
    },
    {
      id: 4,
      sender: "Vous",
      content: "Parfait, je viendrai vers 14h. Merci !",
      time: "10:42",
      isOwn: true
    },
    {
      id: 5,
      sender: "Prof. Dubois",
      content: "Bonjour, concernant le projet de fin de semestre, n'oubliez pas la date limite du 15 mars.",
      time: "14:20",
      isOwn: false
    },
  ];

  const handleSendMessage = () => {
    if (message.trim()) {
      console.log("Envoi du message:", message);
      setMessage("");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Messagerie</h1>
        <p className="text-muted-foreground mt-2">
          Communiquez avec vos enseignants et l'administration
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-6 h-[calc(100vh-200px)]">
        {/* Liste des conversations */}
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg">Conversations</CardTitle>
            <div className="relative mt-2">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Rechercher..." className="pl-8" />
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[calc(100vh-340px)]">
              {conversations.map((conv, index) => (
                <div
                  key={conv.id}
                  onClick={() => setSelectedConversation(index)}
                  className={`p-4 border-b border-border cursor-pointer hover:bg-muted/50 transition-colors ${
                    selectedConversation === index ? "bg-muted" : ""
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <Avatar>
                      <AvatarFallback className="bg-primary text-primary-foreground">
                        {conv.avatar}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <p className="font-medium text-foreground truncate">
                          {conv.name}
                        </p>
                        {conv.unread > 0 && (
                          <Badge variant="default" className="ml-2">
                            {conv.unread}
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground mb-1">
                        {conv.role}
                      </p>
                      <p className="text-sm text-muted-foreground truncate">
                        {conv.lastMessage}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {conv.time}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Fenêtre de conversation */}
        <Card className="md:col-span-2 flex flex-col">
          <CardHeader className="border-b border-border">
            <div className="flex items-center gap-3">
              <Avatar>
                <AvatarFallback className="bg-primary text-primary-foreground">
                  {conversations[selectedConversation].avatar}
                </AvatarFallback>
              </Avatar>
              <div>
                <CardTitle className="text-lg">
                  {conversations[selectedConversation].name}
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  {conversations[selectedConversation].role}
                </p>
              </div>
            </div>
          </CardHeader>

          <CardContent className="flex-1 p-0">
            <ScrollArea className="h-[calc(100vh-440px)] p-4">
              <div className="space-y-4">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.isOwn ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[70%] rounded-lg p-3 ${
                        msg.isOwn
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-foreground"
                      }`}
                    >
                      {!msg.isOwn && (
                        <p className="font-medium text-sm mb-1">{msg.sender}</p>
                      )}
                      <p className="text-sm">{msg.content}</p>
                      <p
                        className={`text-xs mt-1 ${
                          msg.isOwn ? "text-primary-foreground/70" : "text-muted-foreground"
                        }`}
                      >
                        {msg.time}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>

          <div className="p-4 border-t border-border">
            <div className="flex gap-2">
              <Textarea
                placeholder="Écrivez votre message..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="min-h-[60px] resize-none"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
              />
              <Button
                onClick={handleSendMessage}
                className="self-end"
                disabled={!message.trim()}
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Appuyez sur Entrée pour envoyer, Shift+Entrée pour une nouvelle ligne
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Messagerie;
