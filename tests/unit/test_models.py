"""Tests unitaires pour les modèles Pydantic."""

import pytest
from datetime import date

from src.backend.models.auth import (
    Credentials,
    PasswordChange,
    UserCreate,
    UserEdit,
    UserOut,
    UserRole,
)
from src.backend.models.suppliers import SupplierBase, SupplierCreate, SupplierEdit
from src.backend.models.products import ProductBase, ProductCreate, LabelEgalim, Provenance, Gamme
from src.backend.models.orders import OrderBase, OrderCreate, OrderKind, OrderLineBase
from src.backend.models.meals import MealBase, MealCreate, MealItemBase
from src.backend.models.recipes import RecipeBase, RecipeCreate, RecipeItemBase
from src.backend.models.stocks import StockAdjustmentBase, StockAdjustmentCreate
from src.backend.models.commitments import CommitmentBase, CommitmentCreate


class TestAuthModels:
    """Tests pour les modèles d'authentification."""

    def test_credentials(self):
        """Test du modèle Credentials."""
        creds = Credentials(username="test", password="password123")
        assert creds.username == "test"
        assert creds.password == "password123"
        
        # Validation
        with pytest.raises(Exception):
            Credentials(username="ab", password="password123")  # Trop court
        with pytest.raises(Exception):
            Credentials(username="test", password="short")  # Trop court

    def test_user_role(self):
        """Test de l'énumération UserRole."""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.EDITOR.value == "editor"
        assert UserRole.READER.value == "reader"
        assert UserRole.STATS.value == "stats"

    def test_user_create(self):
        """Test du modèle UserCreate."""
        user = UserCreate(
            username="test",
            password="password123",
            role=UserRole.ADMIN
        )
        assert user.username == "test"
        assert user.password == "password123"
        assert user.role == UserRole.ADMIN

    def test_user_edit(self):
        """Test du modèle UserEdit."""
        edit = UserEdit(role=UserRole.EDITOR, password="newpassword123")
        assert edit.role == UserRole.EDITOR
        assert edit.password == "newpassword123"
        
        edit2 = UserEdit()
        assert edit2.role is None
        assert edit2.password is None


class TestSupplierModels:
    """Tests pour les modèles de fournisseurs."""

    def test_supplier_base(self):
        """Test du modèle SupplierBase."""
        supplier = SupplierBase(
            name="Test Supplier",
            contact="John Doe",
            email="contact@test.com",
            phone="0123456789",
            address="123 Test Street",
            siret="12345678901234",
            direct_producteur=True
        )
        assert supplier.name == "Test Supplier"
        assert supplier.contact == "John Doe"
        assert supplier.email == "contact@test.com"
        assert supplier.direct_producteur is True

    def test_supplier_create(self):
        """Test du modèle SupplierCreate."""
        supplier = SupplierCreate(
            name="New Supplier",
            categories='["Fruits", "Légumes"]'
        )
        assert supplier.name == "New Supplier"
        assert supplier.categories == '["Fruits", "Légumes"]'

    def test_supplier_edit(self):
        """Test du modèle SupplierEdit."""
        edit = SupplierEdit(name="Updated Supplier")
        assert edit.name == "Updated Supplier"
        assert edit.contact is None


class TestProductModels:
    """Tests pour les modèles de produits."""

    def test_label_egalim(self):
        """Test de l'énumération LabelEgalim."""
        assert LabelEgalim.BIO.value == "bio"
        assert LabelEgalim.AUTRE.value == "autre"
        assert LabelEgalim.SANS.value == "sans"

    def test_provenance(self):
        """Test de l'énumération Provenance."""
        assert Provenance.CC_NOZAY.value == "cc_nozay"
        assert Provenance.LOIRE_ATLANTIQUE.value == "loire_atlantique"
        assert Provenance.FRANCE.value == "france"

    def test_gamme(self):
        """Test de l'énumération Gamme."""
        assert Gamme.FRAIS_BRUT.value == "1"
        assert Gamme.SURGELES.value == "3"

    def test_product_base(self):
        """Test du modèle ProductBase."""
        product = ProductBase(
            ref="REF123",
            name="Test Product",
            category="Fruits: pommes, poires, kiwis",
            gamme=Gamme.FRAIS_BRUT,
            label_egalim=LabelEgalim.BIO,
            provenance=Provenance.FRANCE,
            unit="kg",
            unit_price=2.50
        )
        assert product.ref == "REF123"
        assert product.name == "Test Product"
        assert product.gamme == Gamme.FRAIS_BRUT
        assert product.unit_price == 2.50

    def test_product_create(self):
        """Test du modèle ProductCreate."""
        product = ProductCreate(
            name="New Product",
            unit_price=3.00
        )
        assert product.name == "New Product"
        assert product.unit_price == 3.00


class TestOrderModels:
    """Tests pour les modèles de commandes."""

    def test_order_kind(self):
        """Test de l'énumération OrderKind."""
        assert OrderKind.LIVRAISON.value == "livraison"
        assert OrderKind.FACTURE.value == "facture"

    def test_order_line_base(self):
        """Test du modèle OrderLineBase."""
        line = OrderLineBase(
            product_id=1,
            ref="REF123",
            label="Test Product",
            qty=10.0,
            unit="kg",
            unit_price=2.50,
            total_ht=25.00
        )
        assert line.product_id == 1
        assert line.qty == 10.0
        assert line.total_ht == 25.00

    def test_order_create(self):
        """Test du modèle OrderCreate."""
        order = OrderCreate(
            supplier_id=1,
            ref="ORDER123",
            kind=OrderKind.LIVRAISON,
            date="2026-10-28",
            total_ht=100.00,
            lines=[]
        )
        assert order.supplier_id == 1
        assert order.ref == "ORDER123"
        assert order.kind == OrderKind.LIVRAISON


class TestMealModels:
    """Tests pour les modèles de repas."""

    def test_meal_item_base(self):
        """Test du modèle MealItemBase."""
        item = MealItemBase(
            product_id=1,
            qty=5.0,
            unit="kg",
            prix_reel=10.00
        )
        assert item.product_id == 1
        assert item.qty == 5.0
        assert item.prix_reel == 10.00

    def test_meal_create(self):
        """Test du modèle MealCreate."""
        meal = MealCreate(
            date="2026-10-28",
            nb_maternelles=10,
            nb_elementaires=20,
            nb_adultes=5,
            entree="Salade",
            plat="Poulet rôti",
            items=[]
        )
        assert meal.date == "2026-10-28"
        assert meal.nb_maternelles == 10
        assert meal.nb_elementaires == 20


class TestRecipeModels:
    """Tests pour les modèles de recettes."""

    def test_recipe_item_base(self):
        """Test du modèle RecipeItemBase."""
        item = RecipeItemBase(
            product_id=1,
            label="Carottes",
            qty_maternelle=100.0,
            qty_elementaire=150.0,
            qty_adulte=200.0,
            unit="g",
            principal=True
        )
        assert item.product_id == 1
        assert item.qty_maternelle == 100.0
        assert item.principal is True

    def test_recipe_create(self):
        """Test du modèle RecipeCreate."""
        recipe = RecipeCreate(
            name="Poulet rôti",
            categorie="plat",
            description="Recette de poulet rôti",
            items=[]
        )
        assert recipe.name == "Poulet rôti"
        assert recipe.categorie == "plat"


class TestStockModels:
    """Tests pour les modèles de stocks."""

    def test_stock_adjustment_base(self):
        """Test du modèle StockAdjustmentBase."""
        adjustment = StockAdjustmentBase(
            product_id=1,
            date="2026-10-28",
            qty=5.0,
            unit="kg",
            reason="Réception",
            username="admin"
        )
        assert adjustment.product_id == 1
        assert adjustment.qty == 5.0
        assert adjustment.reason == "Réception"


class TestCommitmentModels:
    """Tests pour les modèles d'engagements."""

    def test_commitment_base(self):
        """Test du modèle CommitmentBase."""
        commitment = CommitmentBase(
            label="Bio 50%",
            metric="bio",
            target=50.0,
            level="marche",
            mode="min"
        )
        assert commitment.label == "Bio 50%"
        assert commitment.metric == "bio"
        assert commitment.target == 50.0

    def test_commitment_create(self):
        """Test du modèle CommitmentCreate."""
        commitment = CommitmentCreate(
            label="Local 30%",
            metric="local",
            target=30.0
        )
        assert commitment.label == "Local 30%"
        assert commitment.target == 30.0
