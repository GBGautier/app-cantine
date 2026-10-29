"""Modèles d'authentification."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    """Rôles des utilisateurs."""

    ADMIN = "admin"
    EDITOR = "editor"
    READER = "reader"
    STATS = "stats"


class Credentials(BaseModel):
    """Identifiants de connexion."""

    username: str = Field(..., min_length=3, max_length=40, description="Nom d'utilisateur")
    password: str = Field(..., min_length=8, description="Mot de passe")


class PasswordChange(BaseModel):
    """Changement de mot de passe."""

    current: str = Field(..., description="Mot de passe actuel")
    new: str = Field(..., min_length=8, description="Nouveau mot de passe")


class UserBase(BaseModel):
    """Base pour les modèles utilisateur."""

    username: str = Field(..., description="Nom d'utilisateur")
    role: UserRole = Field(default=UserRole.READER, description="Rôle de l'utilisateur")


class UserCreate(UserBase):
    """Création d'un nouvel utilisateur."""

    password: str = Field(..., min_length=8, description="Mot de passe")


class UserEdit(BaseModel):
    """Édition d'un utilisateur."""

    role: Optional[UserRole] = Field(default=None, description="Nouveau rôle")
    password: Optional[str] = Field(default=None, min_length=8, description="Nouveau mot de passe")


class UserOut(UserBase):
    """Utilisateur en sortie."""

    id: int = Field(..., description="ID de l'utilisateur")
    created: str = Field(..., description="Date de création")

    class Config:
        from_attributes = True


class AuthStatus(BaseModel):
    """Statut d'authentification."""

    setup_needed: bool = Field(..., description="Un compte admin doit-il être créé ?")
    user: Optional[UserOut] = Field(default=None, description="Utilisateur connecté")


class LoginResponse(BaseModel):
    """Réponse de connexion."""

    user: UserOut = Field(..., description="Utilisateur connecté")
