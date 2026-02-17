"""
Templates HTML pour les emails transactionnels ServantAssist.

Design : chaleureux, professionnel, compatible avec tous les clients email.
Toutes les couleurs et styles sont en inline CSS pour la compatibilite maximale.
"""
from datetime import datetime

# ── Palette de couleurs ──────────────────────────────────────────────────
_PRIMARY = "#6C3FC5"  # Violet profond (marque ServantAssist)
_PRIMARY_LIGHT = "#F3EDFF"  # Fond violet tres clair
_ACCENT = "#E8A838"  # Or chaud (liturgique)
_TEXT = "#2D2D2D"  # Texte principal
_TEXT_LIGHT = "#6B7280"  # Texte secondaire
_BG = "#F9FAFB"  # Fond gris tres clair
_WHITE = "#FFFFFF"
_BORDER = "#E5E7EB"
_SUCCESS = "#059669"  # Vert confirmation
_SUCCESS_LIGHT = "#ECFDF5"  # Fond vert clair


def _base_layout(content: str, preview_text: str = "") -> str:
    """Enveloppe le contenu dans le layout de base ServantAssist."""
    year = datetime.now().year
    return f"""\
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light">
  <title>ServantAssist</title>
  <!--[if mso]>
  <noscript>
    <xml>
      <o:OfficeDocumentSettings>
        <o:PixelsPerInch>96</o:PixelsPerInch>
      </o:OfficeDocumentSettings>
    </xml>
  </noscript>
  <![endif]-->
</head>
<body style="margin:0; padding:0; background-color:{_BG}; font-family:'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif; -webkit-font-smoothing:antialiased;">
  <!-- Preview text (visible dans la boite de reception, masque dans le mail) -->
  <div style="display:none;font-size:1px;color:{_BG};line-height:1px;max-height:0px;max-width:0px;opacity:0;overflow:hidden;">
    {preview_text}
  </div>

  <!-- Container principal -->
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:{_BG};">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

          <!-- Header -->
          <tr>
            <td align="center" style="padding:0 0 24px 0;">
              <table role="presentation" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="background-color:{_PRIMARY};border-radius:12px;padding:6px 16px;">
                    <span style="font-size:14px;font-weight:700;color:{_WHITE};letter-spacing:0.5px;">&#9769;</span>
                  </td>
                  <td style="padding-left:12px;">
                    <span style="font-size:22px;font-weight:700;color:{_PRIMARY};letter-spacing:-0.3px;">Servant</span><span style="font-size:22px;font-weight:300;color:{_TEXT_LIGHT};">Assist</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Card -->
          <tr>
            <td style="background-color:{_WHITE};border-radius:16px;border:1px solid {_BORDER};box-shadow:0 1px 3px rgba(0,0,0,0.06);">
              {content}
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td align="center" style="padding:24px 0 0 0;">
              <p style="margin:0;font-size:13px;color:{_TEXT_LIGHT};line-height:1.6;">
                Cet email a ete envoye automatiquement par <strong style="color:{_PRIMARY};">ServantAssist</strong>.
              </p>
              <p style="margin:8px 0 0 0;font-size:12px;color:{_TEXT_LIGHT};">
                &copy; {year} ServantAssist &mdash; Gestion des servants d'autel
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════════
#  1. Mot de passe oublie — demande de reinitialisation
# ═══════════════════════════════════════════════════════════════════════════


def render_forgot_password(
    user_first_name: str,
    reset_link: str,
    expiry_minutes: int = 15,
) -> tuple[str, str]:
    """
    Retourne (subject, html_body) pour l'email de reinitialisation.
    """
    subject = "Reinitialisation de votre mot de passe — ServantAssist"
    preview = (
        f"{user_first_name}, voici votre lien de reinitialisation de mot de passe."
    )

    content = f"""\
              <!-- Icone + titre -->
              <td style="padding:40px 40px 0 40px;">
                <div style="text-align:center;margin-bottom:24px;">
                  <div style="display:inline-block;background-color:{_PRIMARY_LIGHT};border-radius:50%;width:64px;height:64px;line-height:64px;text-align:center;">
                    <span style="font-size:28px;">&#128274;</span>
                  </div>
                </div>
                <h1 style="margin:0 0 8px 0;font-size:24px;font-weight:700;color:{_TEXT};text-align:center;line-height:1.3;">
                  Reinitialisation de mot de passe
                </h1>
                <p style="margin:0 0 24px 0;font-size:15px;color:{_TEXT_LIGHT};text-align:center;line-height:1.5;">
                  Pas de panique, cela arrive a tout le monde !
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:0 40px;">
                <div style="height:1px;background-color:{_BORDER};"></div>
              </td>
            </tr>
            <tr>
              <!-- Corps du message -->
              <td style="padding:24px 40px 0 40px;">
                <p style="margin:0 0 16px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Bonjour <strong>{user_first_name}</strong>,
                </p>
                <p style="margin:0 0 16px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Nous avons recu une demande de reinitialisation de mot de passe pour votre compte
                  <strong>ServantAssist</strong>. Cliquez sur le bouton ci-dessous pour choisir
                  un nouveau mot de passe :
                </p>

                <!-- Bouton CTA -->
                <div style="text-align:center;margin:32px 0;">
                  <a href="{reset_link}"
                     target="_blank"
                     style="display:inline-block;
                            background-color:{_PRIMARY};
                            color:{_WHITE};
                            font-size:16px;
                            font-weight:600;
                            text-decoration:none;
                            padding:14px 40px;
                            border-radius:8px;
                            letter-spacing:0.3px;
                            box-shadow:0 2px 8px rgba(108,63,197,0.35);">
                    Reinitialiser mon mot de passe
                  </a>
                </div>

                <!-- Avertissement expiration -->
                <div style="background-color:{_PRIMARY_LIGHT};border-radius:8px;padding:16px;margin-bottom:24px;">
                  <p style="margin:0;font-size:13px;color:{_PRIMARY};line-height:1.5;">
                    &#9200; Ce lien expirera dans <strong>{expiry_minutes} minutes</strong> pour
                    des raisons de securite.
                  </p>
                </div>

                <!-- Lien alternatif -->
                <p style="margin:0 0 8px 0;font-size:13px;color:{_TEXT_LIGHT};line-height:1.5;">
                  Si le bouton ne fonctionne pas, copiez et collez ce lien dans votre navigateur :
                </p>
                <p style="margin:0 0 24px 0;font-size:12px;color:{_PRIMARY};word-break:break-all;line-height:1.5;">
                  {reset_link}
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:0 40px;">
                <div style="height:1px;background-color:{_BORDER};"></div>
              </td>
            </tr>
            <tr>
              <!-- Securite -->
              <td style="padding:24px 40px 40px 40px;">
                <p style="margin:0;font-size:13px;color:{_TEXT_LIGHT};line-height:1.6;">
                  &#128737; <strong>Vous n'avez pas fait cette demande ?</strong>
                  Ignorez simplement cet email. Votre mot de passe ne sera pas modifie.
                  Si vous pensez que votre compte est compromis, contactez votre administrateur.
                </p>
              </td>
            </tr>"""

    # Envelopper dans le layout de base
    card_content = f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0'><tr>{content}</table>"
    html = _base_layout(card_content, preview)
    return subject, html


# ═══════════════════════════════════════════════════════════════════════════
#  2. Confirmation de reinitialisation reussie
# ═══════════════════════════════════════════════════════════════════════════


def render_password_changed(
    user_first_name: str,
    login_link: str,
) -> tuple[str, str]:
    """
    Retourne (subject, html_body) pour l'email de confirmation de changement.
    """
    subject = "Votre mot de passe a ete modifie — ServantAssist"
    preview = f"{user_first_name}, votre mot de passe ServantAssist a ete modifie avec succes."

    now_str = datetime.now().strftime("%d/%m/%Y a %H:%M")

    content = f"""\
              <!-- Icone + titre -->
              <td style="padding:40px 40px 0 40px;">
                <div style="text-align:center;margin-bottom:24px;">
                  <div style="display:inline-block;background-color:{_SUCCESS_LIGHT};border-radius:50%;width:64px;height:64px;line-height:64px;text-align:center;">
                    <span style="font-size:28px;">&#9989;</span>
                  </div>
                </div>
                <h1 style="margin:0 0 8px 0;font-size:24px;font-weight:700;color:{_TEXT};text-align:center;line-height:1.3;">
                  Mot de passe modifie
                </h1>
                <p style="margin:0 0 24px 0;font-size:15px;color:{_SUCCESS};text-align:center;line-height:1.5;font-weight:500;">
                  Votre mot de passe a ete reinitialise avec succes !
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:0 40px;">
                <div style="height:1px;background-color:{_BORDER};"></div>
              </td>
            </tr>
            <tr>
              <!-- Corps du message -->
              <td style="padding:24px 40px 0 40px;">
                <p style="margin:0 0 16px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Bonjour <strong>{user_first_name}</strong>,
                </p>
                <p style="margin:0 0 16px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Nous vous confirmons que le mot de passe de votre compte <strong>ServantAssist</strong>
                  a ete modifie avec succes le <strong>{now_str}</strong>.
                </p>
                <p style="margin:0 0 24px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Vous pouvez desormais vous connecter avec votre nouveau mot de passe :
                </p>

                <!-- Bouton CTA -->
                <div style="text-align:center;margin:24px 0 32px 0;">
                  <a href="{login_link}"
                     target="_blank"
                     style="display:inline-block;
                            background-color:{_SUCCESS};
                            color:{_WHITE};
                            font-size:16px;
                            font-weight:600;
                            text-decoration:none;
                            padding:14px 40px;
                            border-radius:8px;
                            letter-spacing:0.3px;">
                    Me connecter
                  </a>
                </div>
              </td>
            </tr>
            <tr>
              <td style="padding:0 40px;">
                <div style="height:1px;background-color:{_BORDER};"></div>
              </td>
            </tr>
            <tr>
              <!-- Securite -->
              <td style="padding:24px 40px 40px 40px;">
                <div style="background-color:#FEF2F2;border-radius:8px;padding:16px;border-left:4px solid #EF4444;">
                  <p style="margin:0;font-size:13px;color:#991B1B;line-height:1.6;">
                    &#9888; <strong>Ce n'etait pas vous ?</strong>
                    Si vous n'avez pas effectue ce changement, votre compte a peut-etre ete compromis.
                    Contactez immediatement votre administrateur pour securiser votre compte.
                  </p>
                </div>
              </td>
            </tr>"""

    card_content = f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0'><tr>{content}</table>"
    html = _base_layout(card_content, preview)
    return subject, html


# ═══════════════════════════════════════════════════════════════════════════
#  3. Notification d'affectation a un evenement
# ═══════════════════════════════════════════════════════════════════════════


def render_assignment_notification(
    user_first_name: str,
    event_title: str,
    event_date: str,
    liturgical_role: str,
    event_location: str = "",
) -> tuple[str, str]:
    """Retourne (subject, html_body) pour une notification d'affectation."""
    subject = f"Nouvelle affectation — {event_title}"
    preview = f"{user_first_name}, vous etes affecte(e) a {event_title}."

    location_line = ""
    if event_location:
        location_line = f"""
                <tr>
                  <td style="padding:4px 16px;font-size:14px;color:{_TEXT};">
                    <strong>Lieu :</strong> {event_location}
                  </td>
                </tr>"""

    content = f"""\
              <td style="padding:40px 40px 0 40px;">
                <div style="text-align:center;margin-bottom:24px;">
                  <div style="display:inline-block;background-color:{_PRIMARY_LIGHT};border-radius:50%;width:64px;height:64px;line-height:64px;text-align:center;">
                    <span style="font-size:28px;">&#9769;</span>
                  </div>
                </div>
                <h1 style="margin:0 0 8px 0;font-size:24px;font-weight:700;color:{_TEXT};text-align:center;">
                  Nouvelle affectation
                </h1>
              </td>
            </tr>
            <tr>
              <td style="padding:24px 40px;">
                <p style="margin:0 0 16px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Bonjour <strong>{user_first_name}</strong>,
                </p>
                <p style="margin:0 0 16px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Vous avez ete affecte(e) a un evenement :
                </p>
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                       style="background-color:{_PRIMARY_LIGHT};border-radius:8px;padding:16px;margin-bottom:24px;">
                <tr>
                  <td style="padding:4px 16px;font-size:14px;color:{_TEXT};">
                    <strong>Evenement :</strong> {event_title}
                  </td>
                </tr>
                <tr>
                  <td style="padding:4px 16px;font-size:14px;color:{_TEXT};">
                    <strong>Date :</strong> {event_date}
                  </td>
                </tr>
                <tr>
                  <td style="padding:4px 16px;font-size:14px;color:{_TEXT};">
                    <strong>Role :</strong> {liturgical_role}
                  </td>
                </tr>{location_line}
                </table>
                <p style="margin:0;font-size:13px;color:{_TEXT_LIGHT};">
                  Connectez-vous a ServantAssist pour accepter ou decliner cette affectation.
                </p>
              </td>
            </tr>"""

    card_content = f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0'><tr>{content}</table>"
    return subject, _base_layout(card_content, preview)


# ═══════════════════════════════════════════════════════════════════════════
#  4. Rappel d'evenement (24h avant)
# ═══════════════════════════════════════════════════════════════════════════


def render_event_reminder(
    user_first_name: str,
    event_title: str,
    event_date: str,
    event_location: str = "",
    liturgical_role: str = "",
) -> tuple[str, str]:
    """Retourne (subject, html_body) pour un rappel d'evenement."""
    subject = f"Rappel — {event_title} demain"
    preview = f"{user_first_name}, rappel pour {event_title} demain."

    role_line = ""
    if liturgical_role:
        role_line = f"<br>Votre role : <strong>{liturgical_role}</strong>"

    content = f"""\
              <td style="padding:40px 40px 0 40px;">
                <div style="text-align:center;margin-bottom:24px;">
                  <div style="display:inline-block;background-color:{_PRIMARY_LIGHT};border-radius:50%;width:64px;height:64px;line-height:64px;text-align:center;">
                    <span style="font-size:28px;">&#128276;</span>
                  </div>
                </div>
                <h1 style="margin:0 0 8px 0;font-size:24px;font-weight:700;color:{_TEXT};text-align:center;">
                  Rappel : evenement demain
                </h1>
              </td>
            </tr>
            <tr>
              <td style="padding:24px 40px 40px 40px;">
                <p style="margin:0 0 16px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Bonjour <strong>{user_first_name}</strong>,
                </p>
                <p style="margin:0 0 16px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Ceci est un rappel pour l'evenement <strong>{event_title}</strong>
                  prevu le <strong>{event_date}</strong>.
                  {role_line}
                </p>
                <p style="margin:0;font-size:13px;color:{_TEXT_LIGHT};">
                  Merci de confirmer votre presence dans l'application.
                </p>
              </td>
            </tr>"""

    card_content = f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0'><tr>{content}</table>"
    return subject, _base_layout(card_content, preview)


# ═══════════════════════════════════════════════════════════════════════════
#  5. Notification d'absence au parent
# ═══════════════════════════════════════════════════════════════════════════


def render_absence_parent_notification(
    parent_first_name: str,
    child_first_name: str,
    child_last_name: str,
    event_title: str,
    event_date: str,
) -> tuple[str, str]:
    """Retourne (subject, html_body) pour informer un parent d'une absence."""
    subject = f"Absence de {child_first_name} — {event_title}"
    preview = f"{parent_first_name}, {child_first_name} a ete marque(e) absent(e)."

    content = f"""\
              <td style="padding:40px 40px 0 40px;">
                <div style="text-align:center;margin-bottom:24px;">
                  <div style="display:inline-block;background-color:#FEF2F2;border-radius:50%;width:64px;height:64px;line-height:64px;text-align:center;">
                    <span style="font-size:28px;">&#9888;</span>
                  </div>
                </div>
                <h1 style="margin:0 0 8px 0;font-size:24px;font-weight:700;color:{_TEXT};text-align:center;">
                  Notification d'absence
                </h1>
              </td>
            </tr>
            <tr>
              <td style="padding:24px 40px 40px 40px;">
                <p style="margin:0 0 16px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Bonjour <strong>{parent_first_name}</strong>,
                </p>
                <p style="margin:0 0 16px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Nous vous informons que <strong>{child_first_name} {child_last_name}</strong>
                  a ete marque(e) <strong style="color:#EF4444;">absent(e)</strong>
                  lors de l'evenement <strong>{event_title}</strong> du <strong>{event_date}</strong>.
                </p>
                <p style="margin:0;font-size:13px;color:{_TEXT_LIGHT};">
                  Si votre enfant avait un motif valable, veuillez le communiquer a l'aumonier.
                </p>
              </td>
            </tr>"""

    card_content = f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0'><tr>{content}</table>"
    return subject, _base_layout(card_content, preview)


# ═══════════════════════════════════════════════════════════════════════════
#  6. Notification generale (broadcast / message personnalise)
# ═══════════════════════════════════════════════════════════════════════════


def render_general_notification(
    user_first_name: str,
    title: str,
    body: str,
) -> tuple[str, str]:
    """Retourne (subject, html_body) pour une notification generale."""
    subject = f"{title} — ServantAssist"
    preview = f"{user_first_name}, {title}"

    content = f"""\
              <td style="padding:40px 40px 0 40px;">
                <div style="text-align:center;margin-bottom:24px;">
                  <div style="display:inline-block;background-color:{_PRIMARY_LIGHT};border-radius:50%;width:64px;height:64px;line-height:64px;text-align:center;">
                    <span style="font-size:28px;">&#128172;</span>
                  </div>
                </div>
                <h1 style="margin:0 0 8px 0;font-size:24px;font-weight:700;color:{_TEXT};text-align:center;">
                  {title}
                </h1>
              </td>
            </tr>
            <tr>
              <td style="padding:24px 40px 40px 40px;">
                <p style="margin:0 0 16px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Bonjour <strong>{user_first_name}</strong>,
                </p>
                <p style="margin:0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  {body}
                </p>
              </td>
            </tr>"""

    card_content = f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0'><tr>{content}</table>"
    return subject, _base_layout(card_content, preview)
