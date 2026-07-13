"""
Script utilitaire pour générer un modèle de classement hebdomadaire vierge.

Ce script génère automatiquement tous les créneaux de messe pour une semaine :
- Lundi à Samedi : Matin (6h15)
- Lundi à Vendredi : Midi (12h00)
- Lundi à Vendredi : Soir (18h00)

Usage:
    python scripts/generate_weekly_template.py --start-date "2026-02-10" --title "Semaine du 10/02 au 16/02/2026"
"""
import argparse
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.entities.weekly_schedule import MassTime, WeekDay


def generate_weekly_slots():
    """
    Génère tous les créneaux de messe pour une semaine.
    
    Returns:
        List[dict]: Liste des créneaux avec jour et horaire
    """
    slots = []
    
    # Définir les jours et horaires disponibles
    days_with_morning = [
        WeekDay.LUNDI, WeekDay.MARDI, WeekDay.MERCREDI,
        WeekDay.JEUDI, WeekDay.VENDREDI, WeekDay.SAMEDI
    ]
    days_with_noon_evening = [
        WeekDay.LUNDI, WeekDay.MARDI, WeekDay.MERCREDI,
        WeekDay.JEUDI, WeekDay.VENDREDI
    ]
    
    # Matin (6h15) : Lundi à Samedi
    for day in days_with_morning:
        slots.append({
            "day": day,
            "mass_time": MassTime.MATIN,
            "servant_id": None,
            "servant_name": None,
            "notes": None
        })
    
    # Midi (12h00) : Lundi à Vendredi
    for day in days_with_noon_evening:
        slots.append({
            "day": day,
            "mass_time": MassTime.MIDI,
            "servant_id": None,
            "servant_name": None,
            "notes": None
        })
    
    # Soir (18h00) : Lundi à Vendredi
    for day in days_with_noon_evening:
        slots.append({
            "day": day,
            "mass_time": MassTime.SOIR,
            "servant_id": None,
            "servant_name": None,
            "notes": None
        })
    
    return slots


def generate_template_json(start_date: str, title: str = None):
    """
    Génère un template JSON pour créer un modèle de classement.
    
    Args:
        start_date: Date de début au format YYYY-MM-DD
        title: Titre du classement (optionnel)
    
    Returns:
        dict: Template JSON prêt à être envoyé à l'API
    """
    # Parser la date de début
    start = datetime.strptime(start_date, "%Y-%m-%d")
    # Calculer la date de fin (6 jours plus tard pour une semaine complète)
    end = start + timedelta(days=6)
    
    # Générer le titre si non fourni
    if not title:
        title = f"Classement hebdomadaire du {start.strftime('%d/%m/%Y')} au {end.strftime('%d/%m/%Y')}"
    
    # Générer tous les créneaux
    slots = generate_weekly_slots()
    
    template = {
        "title": title,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "notes": "Modèle généré automatiquement avec tous les créneaux de messe de la semaine",
        "slots": slots
    }
    
    return template


def print_template_summary(template: dict):
    """Affiche un résumé du template généré."""
    print("\n" + "="*70)
    print("MODÈLE DE CLASSEMENT HEBDOMADAIRE GÉNÉRÉ")
    print("="*70)
    print(f"\nTitre: {template['title']}")
    print(f"Période: {template['start_date']} → {template['end_date']}")
    print(f"Nombre de créneaux: {len(template['slots'])}")
    print("\nRépartition des créneaux:")
    
    # Compter par horaire
    matin_count = sum(1 for s in template['slots'] if s['mass_time'] == MassTime.MATIN)
    midi_count = sum(1 for s in template['slots'] if s['mass_time'] == MassTime.MIDI)
    soir_count = sum(1 for s in template['slots'] if s['mass_time'] == MassTime.SOIR)
    
    print(f"  - Matin (6h15):  {matin_count} créneaux (Lundi-Samedi)")
    print(f"  - Midi (12h00):  {midi_count} créneaux (Lundi-Vendredi)")
    print(f"  - Soir (18h00):  {soir_count} créneaux (Lundi-Vendredi)")
    print(f"  - TOTAL:         {matin_count + midi_count + soir_count} créneaux")
    print("\n" + "="*70)


def main():
    parser = argparse.ArgumentParser(
        description="Génère un modèle de classement hebdomadaire vierge"
    )
    parser.add_argument(
        "--start-date",
        required=True,
        help="Date de début de la semaine (format: YYYY-MM-DD)"
    )
    parser.add_argument(
        "--title",
        help="Titre du classement (optionnel)"
    )
    parser.add_argument(
        "--output",
        help="Fichier de sortie JSON (optionnel, affiche sur stdout par défaut)"
    )
    
    args = parser.parse_args()
    
    try:
        # Générer le template
        template = generate_template_json(args.start_date, args.title)
        
        # Afficher le résumé
        print_template_summary(template)
        
        # Sauvegarder ou afficher le JSON
        import json
        json_output = json.dumps(template, indent=2, ensure_ascii=False)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"\n✓ Template sauvegardé dans: {args.output}")
            print("\nPour créer ce modèle via l'API, utilisez:")
            print(f"  POST /api/v1/weekly-schedule/")
            print(f"  Body: @{args.output}")
        else:
            print("\nJSON du template:")
            print(json_output)
            print("\nPour créer ce modèle via l'API, copiez le JSON ci-dessus et envoyez-le à:")
            print("  POST /api/v1/weekly-schedule/")
        
    except ValueError as e:
        print(f"Erreur: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
