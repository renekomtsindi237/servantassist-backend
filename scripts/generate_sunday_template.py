"""
Script utilitaire pour générer un modèle de classement dominical.

Ce script génère automatiquement un modèle avec les horaires ordinaires ou exceptionnels.

Usage:
    # Horaires ordinaires
    python scripts/generate_sunday_template.py --date "2026-02-16" --title "Dimanche du temps ordinaire"
    
    # Horaires exceptionnels
    python scripts/generate_sunday_template.py --date "2026-02-16" --title "Dimanche spécial" --exceptional
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))


ORDINARY_MASS_TIMES = [
    {"time": "06h30", "language": "EWONDO"},
    {"time": "08h30", "language": "FRANCAIS"},
    {"time": "10h00", "language": "EWONDO"},
    {"time": "11h30", "language": "ANGLAIS"},
    {"time": "17h00", "language": "FRANCAIS"},
]

EXCEPTIONAL_MASS_TIMES = [
    {"time": "06h30", "language": "EWONDO"},
    {"time": "09h00", "language": "BILINGUE"},
    {"time": "11h30", "language": "ANGLAIS"},
    {"time": "17h00", "language": "FRANCAIS"},
]

LITURGICAL_POSITIONS = [
    "CEREMONIAIRE_1",
    "CEREMONIAIRE_2",
    "CEREMONIAIRE_3",
    "CEREMONIAIRE_4",
    "RESPONSABLE",
    "CRUCIFERE",
    "ACOLYTE_1",
    "ACOLYTE_2",
    "ACOLYTE_3",
    "ACOLYTE_4",
    "ACOLYTE_5",
    "ACOLYTE_6",
    "THURIFERAIRE",
    "PORTE_INSIGNES",
    "CEROFERERAIRE",
    "MARMITIER_GARCON_1",
    "MARMITIER_GARCON_2",
    "MARMITIER_GARCON_3",
    "MARMITIER_GARCON_4",
    "MARMITIER_FILLE_1",
    "MARMITIER_FILLE_2",
]


def generate_template_json(
    schedule_date: str,
    title: str,
    is_exceptional: bool = False,
    mass_type: str = "ORDINAIRE"
):
    """
    Génère un template JSON pour créer un modèle de classement dominical.
    
    Args:
        schedule_date: Date du dimanche au format YYYY-MM-DD
        title: Titre du classement
        is_exceptional: Si True, utilise les horaires exceptionnels
        mass_type: Type de messe (ORDINAIRE, SOLENNELLE, PONTIFICALE)
    
    Returns:
        dict: Template JSON prêt à être envoyé à l'API
    """
    # Parser la date
    date = datetime.strptime(schedule_date, "%Y-%m-%d")
    
    # Choisir les horaires
    mass_times = EXCEPTIONAL_MASS_TIMES if is_exceptional else ORDINARY_MASS_TIMES
    
    # Générer les messes avec postes vides
    masses = []
    for mass_time in mass_times:
        mass = {
            "mass_time": mass_time["time"],
            "language": mass_time["language"],
            "notes": None,
            "assignments": [
                {
                    "position": position,
                    "servant_name": None,
                    "notes": None
                }
                for position in LITURGICAL_POSITIONS
            ]
        }
        masses.append(mass)
    
    template = {
        "title": title,
        "schedule_date": date.isoformat(),
        "mass_type": mass_type,
        "is_exceptional": is_exceptional,
        "notes": f"Modèle généré automatiquement - {'Horaires exceptionnels' if is_exceptional else 'Horaires ordinaires'}",
        "masses": masses
    }
    
    return template


def print_template_summary(template: dict):
    """Affiche un résumé du template généré."""
    print("\n" + "="*70)
    print("MODÈLE DE CLASSEMENT DOMINICAL GÉNÉRÉ")
    print("="*70)
    print(f"\nTitre: {template['title']}")
    print(f"Date: {template['schedule_date']}")
    print(f"Type: {template['mass_type']}")
    print(f"Horaires: {'Exceptionnels' if template['is_exceptional'] else 'Ordinaires'}")
    print(f"Nombre de messes: {len(template['masses'])}")
    
    print("\nMesses:")
    for mass in template['masses']:
        print(f"  - {mass['mass_time']} ({mass['language']}) - {len(mass['assignments'])} postes")
    
    total_positions = sum(len(m['assignments']) for m in template['masses'])
    print(f"\nTotal de postes à remplir: {total_positions}")
    print("\n" + "="*70)


def main():
    parser = argparse.ArgumentParser(
        description="Génère un modèle de classement dominical"
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Date du dimanche (format: YYYY-MM-DD)"
    )
    parser.add_argument(
        "--title",
        required=True,
        help="Titre du classement"
    )
    parser.add_argument(
        "--exceptional",
        action="store_true",
        help="Utiliser les horaires exceptionnels"
    )
    parser.add_argument(
        "--mass-type",
        default="ORDINAIRE",
        choices=["ORDINAIRE", "SOLENNELLE", "PONTIFICALE"],
        help="Type de messe"
    )
    parser.add_argument(
        "--output",
        help="Fichier de sortie JSON (optionnel, affiche sur stdout par défaut)"
    )
    
    args = parser.parse_args()
    
    try:
        # Générer le template
        template = generate_template_json(
            args.date,
            args.title,
            args.exceptional,
            args.mass_type
        )
        
        # Afficher le résumé
        print_template_summary(template)
        
        # Sauvegarder ou afficher le JSON
        json_output = json.dumps(template, indent=2, ensure_ascii=False)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"\n✓ Template sauvegardé dans: {args.output}")
            print("\nPour créer ce modèle via l'API, utilisez:")
            print(f"  POST /api/v1/sunday-schedule/")
            print(f"  Body: @{args.output}")
        else:
            print("\nJSON du template:")
            print(json_output)
            print("\nPour créer ce modèle via l'API, copiez le JSON ci-dessus et envoyez-le à:")
            print("  POST /api/v1/sunday-schedule/")
        
        print("\nOu utilisez l'endpoint de génération automatique:")
        if args.exceptional:
            print("  POST /api/v1/sunday-schedule/generate/exceptional")
        else:
            print("  POST /api/v1/sunday-schedule/generate/ordinary")
        
    except ValueError as e:
        print(f"Erreur: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
