"""
KAVALI ERP — Seeds d'initialisation de la base de données.
Import: from app.core.seeds import init_db
Usage: init_db()
"""

from werkzeug.security import generate_password_hash
from app import db
from app.core.models import Permission, Role, Company, User

ALL_PERMISSIONS = [
    ("AUT001", "Consulter les indicateurs et objectifs"),
    ("AUT002", "Créer / modifier les objectifs"),
    ("AUT003", "Consulter le suivi des commandes"),
    ("AUT004", "Créer et transmettre une commande"),
    ("AUT005", "Modifier une commande autorisée avec justification"),
    ("AUT006", "Annuler une commande non payée"),
    ("AUT007", "Appliquer une remise"),
    ("AUT008", "Consulter les investissements marketing"),
    ("AUT009", "Initier une action commerciale gratuite"),
    ("AUT010", "Modifier sa demande en attente"),
    ("AUT011", "Annuler sa demande en attente"),
    ("AUT012", "Valider l'investissement"),
    ("AUT013", "Refuser l'investissement"),
    ("AUT014", "Confirmer la sortie du stock"),
    ("AUT015", "Consulter la demande et le bon d'enlèvement"),
    ("AUT016", "Enregistrer les tarifs marketing manquants"),
    ("AUT017", "Aperçu / téléchargement du bon de commande"),
    ("AUT018", "Aperçu / téléchargement de la proforma"),
    ("AUT019", "Aperçu / téléchargement du bon de livraison"),
    ("AUT020", "Aperçu / téléchargement du bon d'enlèvement"),
    ("AUT021", "Aperçu / téléchargement de la facture"),
    ("AUT022", "Consulter les clients et prospects"),
    ("AUT023", "Ajouter un client / prospect"),
    ("AUT024", "Modifier les clients autorisés"),
    ("AUT025", "Consulter les références et disponibilités"),
    ("AUT026", "Enregistrer une réception fournisseur"),
    ("AUT027", "Modifier le stock initial et ses paramètres"),
    ("AUT028", "Modifier le stock physique"),
    ("AUT029", "Consulter les paiements et montants"),
    ("AUT030", "Confirmer la réception d'un paiement"),
    ("AUT031", "Consulter les livraisons"),
    ("AUT032", "Confirmer l'enlèvement / départ"),
    ("AUT033", "Valider la livraison et émettre la facture"),
    ("AUT034", "Consulter les événements autorisés"),
    ("AUT035", "Créer / modifier un rendez-vous"),
    ("AUT036", "Créer / modifier un créneau de livraison"),
    ("AUT037", "Créer / modifier une réunion"),
    ("AUT038", "Annuler les événements autorisés"),
    ("AUT039", "Exporter le calendrier avec les rappels"),
    ("AUT040", "Marquer une alerte comme lue"),
    ("AUT041", "Consulter les demandes et affectations (véhicules)"),
    ("AUT042", "Approuver une demande de véhicule"),
    ("AUT043", "Refuser une demande de véhicule"),
    ("AUT044", "Affecter un véhicule et un chauffeur"),
    ("AUT045", "Consulter la flotte et les chauffeurs"),
    ("AUT046", "Créer / modifier les véhicules"),
    ("AUT047", "Créer / modifier les chauffeurs"),
    ("AUT048", "Consulter les pleins et tarifs"),
    ("AUT049", "Enregistrer un plein"),
    ("AUT050", "Mettre à jour le prix des carburants"),
    ("AUT051", "Consulter les missions"),
    ("AUT052", "Enregistrer une mission"),
    ("AUT053", "Consulter les entretiens et échéances"),
    ("AUT054", "Enregistrer un entretien"),
    ("AUT055", "Consulter les pannes et récurrences"),
    ("AUT056", "Signaler une panne"),
    ("AUT057", "Consulter les fournisseurs / prestations"),
    ("AUT058", "Créer / modifier un fournisseur"),
    ("AUT059", "Consulter les préparations d'approvisionnement"),
    ("AUT060", "Modifier un mail de préparation"),
    ("AUT061", "Valider une préparation fournisseur"),
    ("AUT062", "Renouveler une préparation expirée"),
    ("AUT063", "Consulter les dossiers des travailleurs"),
    ("AUT064", "Enregistrer un travailleur"),
    ("AUT065", "Modifier un dossier / demander un accès"),
    ("AUT066", "Autoriser la création d'un accès"),
    ("AUT067", "Réinitialiser les mots de passe autorisés"),
    ("AUT068", "Forcer / renouveler la validation d'un dossier incomplet"),
    ("AUT069", "Clore un contrat et archiver le travailleur"),
    ("AUT070", "Consulter les contrats et échéances"),
    ("AUT071", "Consulter les pièces du dossier"),
    ("AUT072", "Ajouter contrats et pièces"),
    ("AUT073", "Modifier les éléments d'un contrat"),
    ("AUT074", "Ouvrir / télécharger les pièces RH"),
    ("AUT075", "Consulter le pointage autorisé"),
    ("AUT076", "Enregistrer / corriger le pointage autorisé"),
    ("AUT077", "Créer une attestation / un certificat de travail"),
    ("AUT078", "Consulter et télécharger les documents de travail"),
    ("AUT079", "Consulter le listing, les salaires et variables"),
    ("AUT080", "Préparer les variables et primes mensuelles"),
    ("AUT081", "Valider le listing des salaires / primes"),
    ("AUT082", "Valider les bulletins sélectionnés"),
    ("AUT083", "Annuler un bulletin validé"),
    ("AUT084", "Ouvrir / télécharger un bulletin"),
    ("AUT085", "Télécharger le dossier PDF complet d'un mois"),
    ("AUT086", "Consulter le listing mensuel des congés"),
    ("AUT087", "Enregistrer l'acquisition mensuelle des congés"),
    ("AUT088", "Consulter catégories / échelons / minima"),
    ("AUT089", "Créer / modifier les catégories"),
    ("AUT090", "Consulter les paramètres de cotisations"),
    ("AUT091", "Modifier et confirmer les paramètres de paie"),
    ("AUT092", "Consulter la synthèse et les ristournes autorisées"),
    ("AUT093", "Proposer un taux de ristourne"),
    ("AUT094", "Valider les ristournes"),
    ("AUT095", "Consulter les informations de l'entreprise"),
    ("AUT096", "Modifier les informations de l'entreprise"),
    ("AUT097", "Consulter les documents administratifs"),
    ("AUT098", "Ajouter des documents administratifs"),
    ("AUT099", "Archiver des documents administratifs"),
    ("AUT100", "Ouvrir / télécharger un document administratif"),
    ("AUT101", "Consulter la liste des validations attendues"),
    ("AUT102", "Consulter les profils et accès"),
    ("AUT103", "Créer / modifier / autoriser les profils"),
    ("AUT104", "Modifier le profil lié au poste"),
    ("AUT105", "Supprimer un accès individuel"),
    ("AUT106", "Rétablir un accès individuel"),
    ("AUT107", "Consulter et trier l'historique"),
    ("AUT108", "Consulter et trier les archives"),
    ("AUT109", "Consulter les conversations autorisées"),
    ("AUT110", "Démarrer un échange individuel"),
    ("AUT111", "Envoyer un message individuel"),
    ("AUT112", "Créer / gérer un groupe de diffusion"),
    ("AUT113", "Diffuser dans ses groupes"),
    ("AUT114", "Superviser les conversations"),
    ("AUT115", "Consulter mon profil"),
    ("AUT116", "Changer mon mot de passe"),
]


def _expand_refs(ref_patterns):
    """
    Convertit des patterns comme 'AUT002-AUT004' en liste ['AUT002', 'AUT003', 'AUT004'].
    Accepte aussi des refs simples comme 'AUT007'.
    """
    result = []
    for pattern in ref_patterns:
        if "-" in pattern:
            parts = pattern.split("-")
            prefix = parts[0][:3]  # "AUT"
            start_num = int(parts[0][3:])
            end_num = int(parts[1][3:])
            for num in range(start_num, end_num + 1):
                result.append(f"{prefix}{num:03d}")
        else:
            result.append(pattern)
    return result


# Définition des rôles et leurs permissions (en format compact avec plages)
ROLE_DEFINITIONS = {
    "DG": {
        "description": "Direction Générale — accès complet",
        "permission_refs": [f"AUT{i:03d}" for i in range(1, 117)],  # AUT001-AUT116
    },
    "Chef": {
        "description": "Chef de service — vue activité, réunions, véhicules, validation, marketing",
        "permission_refs": _expand_refs([
            "AUT002-AUT004", "AUT008-AUT011", "AUT017-AUT024",
            "AUT031-AUT044", "AUT092-AUT093", "AUT109-AUT113",
        ]),
    },
    "Commercial": {
        "description": "Commercial — clients, commandes, suivi",
        "permission_refs": _expand_refs([
            "AUT003-AUT006", "AUT017-AUT024", "AUT025",
            "AUT031", "AUT034-AUT036",
        ]),
    },
    "RH": {
        "description": "Ressources Humaines — dossiers, contrats, pointage, paie (sauf validation finale)",
        "permission_refs": _expand_refs([
            "AUT063-AUT091", "AUT092-AUT094",
        ]),
    },
    "Compta": {
        "description": "Comptabilité — paiements, consultation commerciale, remises",
        "permission_refs": _expand_refs([
            "AUT007", "AUT008", "AUT017-AUT022", "AUT029-AUT030",
        ]),
    },
    "Logistique": {
        "description": "Logistique — stock, livraisons, flotte, chauffeurs",
        "permission_refs": _expand_refs([
            "AUT008", "AUT014", "AUT019-AUT020",
            "AUT025-AUT026", "AUT031-AUT056",
        ]),
    },
    "Admin": {
        "description": "Administration — infos entreprise, documents admin",
        "permission_refs": _expand_refs([
            "AUT095-AUT100",
        ]),
    },
}


def init_db():
    """Initialise les données de base KAVALI ERP (permissions, rôles, company, admin DG)."""
    print("[seeds] Initialisation de la base de données KAVALI ERP...")

    # --- 1. Permissions ---
    try:
        existing_count = Permission.query.count()
        if existing_count >= 116:
            print(f"[seeds] OK — {existing_count} permissions déjà présentes, skip.")
        else:
            permissions = []
            for ref, name in ALL_PERMISSIONS:
                if not Permission.query.filter_by(ref=ref).first():
                    permissions.append(Permission(ref=ref, name=name, description=name))
            if permissions:
                db.session.add_all(permissions)
                db.session.commit()
                print(f"[seeds] ✓ {len(permissions)} permissions créées.")
            else:
                print(f"[seeds] OK — toutes les permissions existent déjà.")
    except Exception as e:
        db.session.rollback()
        print(f"[seeds] ⚠ Erreur permissions (ignorée) : {e}")

    # Recharger les permissions depuis la DB pour les liaisons rôles
    perm_map = {}
    try:
        for p in Permission.query.all():
            perm_map[p.ref] = p
    except Exception as e:
        print(f"[seeds] ⚠ Erreur chargement permissions : {e}")
        return

    # --- 2. Rôles ---
    try:
        roles_created = 0
        for role_name, role_def in ROLE_DEFINITIONS.items():
            role = Role.query.filter_by(name=role_name).first()
            if role:
                # S'assurer que les permissions sont à jour
                role.permissions = [perm_map[ref] for ref in role_def["permission_refs"] if ref in perm_map]
            else:
                role = Role(
                    name=role_name,
                    description=role_def["description"],
                )
                role.permissions = [perm_map[ref] for ref in role_def["permission_refs"] if ref in perm_map]
                db.session.add(role)
                roles_created += 1
        db.session.commit()
        print(f"[seeds] ✓ {roles_created} rôles créés, existants mis à jour.")
    except Exception as e:
        db.session.rollback()
        print(f"[seeds] ⚠ Erreur rôles (ignorée) : {e}")

    # --- 3. Company KAVALI ---
    try:
        company = Company.query.filter_by(name="KAVALI").first()
        if not company:
            company = Company(
                name="KAVALI",
                legal_form="SARL",
                activity="Commerce général et prestations de services",
                email="contact@kavali.ci",
                address="Abidjan, Côte d'Ivoire",
            )
            db.session.add(company)
            db.session.commit()
            print("[seeds] ✓ Company KAVALI créée.")
        else:
            print("[seeds] OK — Company KAVALI existe déjà.")
    except Exception as e:
        db.session.rollback()
        print(f"[seeds] ⚠ Erreur company (ignorée) : {e}")

    # --- 4. Admin DG ---
    try:
        user = User.query.filter_by(email="admin@kavali.ci").first()
        if not user:
            dg_role = Role.query.filter_by(name="DG").first()
            company = Company.query.filter_by(name="KAVALI").first()
            if dg_role and company:
                user = User(
                    username="admin",
                    email="admin@kavali.ci",
                    password_hash=generate_password_hash("Admin123!"),
                    full_name="Administrateur DG",
                    role_id=dg_role.id,
                    company_id=company.id,
                    service="DG",
                    position="Directeur Général",
                    is_active=True,
                )
                db.session.add(user)
                db.session.commit()
                print("[seeds] ✓ Admin DG créé (email: admin@kavali.ci).")
                print("[seeds]   ⚠ PASSWORD PAR DÉFAUT — à changer en production !")
            else:
                print(f"[seeds] ⚠ Impossible de créer l'admin : rôle DG={dg_role is not None}, company={company is not None}")
        else:
            print("[seeds] OK — Admin DG existe déjà.")
    except Exception as e:
        db.session.rollback()
        print(f"[seeds] ⚠ Erreur admin DG (ignorée) : {e}")

    print("[seeds] ✓ Initialisation terminée.")