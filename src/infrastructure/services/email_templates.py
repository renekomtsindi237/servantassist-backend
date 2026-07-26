"""
Templates HTML pour les emails transactionnels ServantAssist.

Design : chaleureux, professionnel, compatible avec tous les clients email.
Toutes les couleurs et styles sont en inline CSS pour la compatibilité maximale.
"""

from datetime import datetime

from src.infrastructure.config.settings import get_settings

# ── Palette de couleurs ──────────────────────────────────────────────────
_PRIMARY = "#1A4A7A"  # Navy BMRA (Basilique Marie Reine des Apôtres)
_PRIMARY_LIGHT = "#EEF3F9"  # Fond navy très clair
_ACCENT = "#C9A84C"  # Or liturgique BMRA
_TEXT = "#2D2D2D"  # Texte principal
_TEXT_LIGHT = "#6B7280"  # Texte secondaire
_BG = "#F9FAFB"  # Fond gris très clair
_WHITE = "#FFFFFF"
_BORDER = "#E5E7EB"
_SUCCESS = "#059669"  # Vert confirmation
_SUCCESS_LIGHT = "#ECFDF5"  # Fond vert clair


def _logo_url() -> str:
    """URL absolue vers le logo ServantAssist (utilisé dans les emails).

    Réutilise `static/images/logo_servant.jpeg` (même fichier que le
    filigrane PDF et l'icône mobile) — `logo_servant_mail.png` n'a jamais
    existé sur disque, d'où les icônes d'image cassée dans les emails.
    """
    settings = get_settings()
    return f"{settings.APP_URL}/static/images/logo_servant.jpeg"


def _base_layout(content: str, preview_text: str = "") -> str:
    """Enveloppe le contenu dans le layout de base ServantAssist."""
    year = datetime.now().year
    logo = _logo_url()
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
  <!-- Texte d'aperçu (visible dans la boîte de réception, masqué dans le mail) -->
  <div style="display:none;font-size:1px;color:{_BG};line-height:1px;max-height:0px;max-width:0px;opacity:0;overflow:hidden;">
    {preview_text}
  </div>

  <!-- Container principal -->
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:{_BG};">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

          <!-- En-tête : logo centré + branding -->
          <tr>
            <td align="center" style="padding:0 0 28px 0;">
              <img src="{logo}"
                   alt="ServantAssist — BMRA Mvolyé"
                   width="80" height="80"
                   style="display:block;border-radius:50%;border:3px solid {_ACCENT};width:80px;height:80px;object-fit:cover;margin:0 auto 12px auto;box-shadow:0 4px 12px rgba(26,74,122,0.18);">
              <div style="margin-top:4px;">
                <span style="font-size:24px;font-weight:700;color:{_PRIMARY};letter-spacing:-0.3px;">Servant</span><span style="font-size:24px;font-weight:300;color:{_TEXT_LIGHT};">Assist</span>
              </div>
              <div style="margin-top:2px;font-size:11px;color:{_ACCENT};font-weight:600;letter-spacing:1px;text-transform:uppercase;">
                BMRA Mvolyé · Yaoundé
              </div>
            </td>
          </tr>

          <!-- Carte principale avec filigrane logo -->
          <tr>
            <td style="background-color:{_WHITE};border-radius:16px;border:1px solid {_BORDER};box-shadow:0 2px 8px rgba(0,0,0,0.07);position:relative;overflow:hidden;">
              <!-- Filigrane centré dans la carte -->
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding:0;position:relative;">
                    <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);pointer-events:none;z-index:0;">
                      <img src="{logo}"
                           alt=""
                           width="220" height="220"
                           style="display:block;border-radius:50%;opacity:0.045;width:220px;height:220px;object-fit:cover;filter:grayscale(30%);">
                    </div>
                    <div style="position:relative;z-index:1;">
                      {content}
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Séparateur décoratif -->
          <tr>
            <td align="center" style="padding:16px 0 0 0;">
              <table role="presentation" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="width:40px;height:1px;background-color:{_BORDER};"></td>
                  <td style="width:8px;height:8px;background-color:{_ACCENT};border-radius:50%;margin:0 6px;"></td>
                  <td style="width:40px;height:1px;background-color:{_BORDER};"></td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Pied de page -->
          <tr>
            <td align="center" style="padding:12px 0 0 0;">
              <p style="margin:0;font-size:12px;color:{_TEXT_LIGHT};line-height:1.6;">
                Cet email a été envoyé automatiquement par <strong style="color:{_PRIMARY};">ServantAssist</strong>.
              </p>
              <p style="margin:6px 0 0 0;font-size:11px;color:{_TEXT_LIGHT};">
                &copy; {year} &mdash; Basilique Marie Reine des Apôtres &mdash; Mvolyé, Yaoundé &mdash; Cameroun
              </p>
              <p style="margin:4px 0 0 0;font-size:11px;color:{_ACCENT};font-style:italic;">
                Aimer · Unir · Servir
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
#  0. Email de bienvenue — après inscription
# ═══════════════════════════════════════════════════════════════════════════


def render_welcome_email(
    user_first_name: str,
    role: str = "SERVANT",
    login_link: str = "",
) -> tuple[str, str]:
    """Retourne (subject, html_body) pour l'email de bienvenue post-inscription."""
    _ROLE_LABELS = {
        "SERVANT": "Servant d'autel",
        "PARENT": "Parent / Tuteur",
        "SECRETAIRE": "Secrétaire",
        "CENSEUR": "Censeur",
        "AUMONIER": "Aumônier",
        "ADMIN": "Administrateur",
    }
    role_label = _ROLE_LABELS.get(role.upper(), role)

    subject = f"Bienvenue dans ServantAssist, {user_first_name} !"
    preview = f"Bienvenue {user_first_name} ! Votre compte {role_label} est prêt. " f"Connectez-vous dès maintenant."
    logo = _logo_url()

    content = f"""\
              <!-- Bandeau de bienvenue -->
              <td style="background-color:{_PRIMARY};border-radius:16px 16px 0 0;padding:32px 40px;text-align:center;">
                <div style="margin-bottom:16px;">
                  <img src="{logo}"
                       alt="ServantAssist"
                       width="64" height="64"
                       style="display:inline-block;border-radius:16px;border:3px solid rgba(255,255,255,0.3);width:64px;height:64px;object-fit:cover;">
                </div>
                <h1 style="margin:0;font-size:26px;font-weight:700;color:#FFFFFF;letter-spacing:-0.3px;">
                  Bienvenue, {user_first_name} !
                </h1>
                <p style="margin:8px 0 0 0;font-size:14px;color:rgba(255,255,255,0.85);">
                  Votre compte <strong style="color:{_ACCENT};">{role_label}</strong> est prêt
                </p>
              </td>
            </tr>
            <tr>
              <!-- Corps du message -->
              <td style="padding:40px 40px 32px 40px;">
                <p style="margin:0 0 16px 0;font-size:15px;color:{_TEXT};line-height:1.7;">
                  Cher(e) <strong>{user_first_name}</strong>,
                </p>
                <p style="margin:0 0 16px 0;font-size:15px;color:{_TEXT};line-height:1.7;">
                  Nous sommes vraiment heureux de vous accueillir au sein de <strong style="color:{_PRIMARY};">ServantAssist</strong>,
                  la plateforme officielle des <strong>Enfants de Chœur</strong> de la
                  <strong>Basilique Marie Reine des Apôtres de Mvolyé (BMRA)</strong>, Yaoundé.
                </p>

                <!-- Encadré de rôle -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:24px 0;">
                  <tr>
                    <td style="background-color:{_PRIMARY_LIGHT};border-left:4px solid {_ACCENT};border-radius:0 8px 8px 0;padding:16px 20px;">
                      <p style="margin:0;font-size:12px;font-weight:600;color:{_PRIMARY};text-transform:uppercase;letter-spacing:0.8px;">
                        Votre rôle dans la communauté
                      </p>
                      <p style="margin:6px 0 0 0;font-size:17px;font-weight:700;color:{_TEXT};">
                        {role_label}
                      </p>
                    </td>
                  </tr>
                </table>

                <p style="margin:0 0 20px 0;font-size:15px;color:{_TEXT};line-height:1.7;">
                  Avec ServantAssist, vous pouvez consulter vos plannings, suivre vos présences,
                  accéder aux formations, gérer les événements liturgiques et rester connecté
                  à toute votre communauté de servants.
                </p>

                <!-- Bouton de connexion -->
                <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto;">
                  <tr>
                    <td style="background-color:{_ACCENT};border-radius:10px;text-align:center;">
                      <a href="{login_link}"
                         style="display:inline-block;padding:14px 40px;font-size:15px;font-weight:700;color:#1A1A1A;text-decoration:none;letter-spacing:0.2px;">
                        Accéder à mon espace &#8594;
                      </a>
                    </td>
                  </tr>
                </table>

                <!-- Devise -->
                <p style="margin:32px 0 0 0;font-size:13px;color:{_TEXT_LIGHT};text-align:center;font-style:italic;letter-spacing:0.8px;">
                  Aimer &nbsp;&mdash;&nbsp; Unir &nbsp;&mdash;&nbsp; Servir
                </p>
              </td>
            </tr>
            <tr>
              <!-- Note de sécurité -->
              <td style="background-color:{_PRIMARY_LIGHT};border-radius:0 0 16px 16px;padding:20px 40px;border-top:1px solid {_BORDER};">
                <p style="margin:0;font-size:12px;color:{_TEXT_LIGHT};line-height:1.6;">
                  Si vous n'êtes pas à l'origine de la création de ce compte, ignorez simplement cet email
                  ou contactez un responsable de la BMRA Mvolyé.
                </p>
              </td>"""

    return subject, _base_layout(content, preview)


# ═══════════════════════════════════════════════════════════════════════════
#  1. Mot de passe oublié — demande de réinitialisation
# ═══════════════════════════════════════════════════════════════════════════


def render_forgot_password(
    user_first_name: str,
    reset_link: str,
    expiry_minutes: int = 15,
) -> tuple[str, str]:
    """Retourne (subject, html_body) pour l'email de réinitialisation."""
    subject = "Réinitialisation de votre mot de passe — ServantAssist"
    preview = f"{user_first_name}, voici votre lien de réinitialisation de mot de passe (valable {expiry_minutes} min)."

    content = f"""\
              <!-- Icône + titre -->
              <td style="padding:40px 40px 0 40px;">
                <div style="text-align:center;margin-bottom:24px;">
                  <div style="display:inline-block;background-color:{_PRIMARY_LIGHT};border-radius:50%;width:64px;height:64px;line-height:64px;text-align:center;">
                    <span style="font-size:28px;">&#128274;</span>
                  </div>
                </div>
                <h1 style="margin:0 0 8px 0;font-size:24px;font-weight:700;color:{_TEXT};text-align:center;line-height:1.3;">
                  Réinitialisation de mot de passe
                </h1>
                <p style="margin:0 0 24px 0;font-size:15px;color:{_TEXT_LIGHT};text-align:center;line-height:1.5;">
                  Pas de panique, ça arrive à tout le monde !
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
                  Nous avons bien reçu une demande de réinitialisation de mot de passe pour votre compte
                  <strong>ServantAssist</strong>. Cliquez sur le bouton ci-dessous pour définir
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
                            letter-spacing:0.3px;">
                    Réinitialiser mon mot de passe
                  </a>
                </div>

                <!-- Avertissement expiration -->
                <div style="background-color:{_PRIMARY_LIGHT};border-radius:8px;padding:16px;margin-bottom:24px;">
                  <p style="margin:0;font-size:13px;color:{_PRIMARY};line-height:1.5;">
                    &#9200; Ce lien est valable <strong>{expiry_minutes} minutes</strong> uniquement,
                    pour des raisons de sécurité.
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
              <!-- Sécurité -->
              <td style="padding:24px 40px 40px 40px;">
                <p style="margin:0;font-size:13px;color:{_TEXT_LIGHT};line-height:1.6;">
                  &#128737; <strong>Vous n'avez pas fait cette demande ?</strong>
                  Ignorez simplement cet email — votre mot de passe ne sera pas modifié.
                  Si vous pensez que votre compte est compromis, contactez votre administrateur.
                </p>
              </td>
            </tr>"""

    card_content = f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0'><tr>{content}</table>"
    html = _base_layout(card_content, preview)
    return subject, html


# ═══════════════════════════════════════════════════════════════════════════
#  2. Confirmation de réinitialisation réussie
# ═══════════════════════════════════════════════════════════════════════════


def render_password_changed(
    user_first_name: str,
    login_link: str,
) -> tuple[str, str]:
    """Retourne (subject, html_body) pour l'email de confirmation de changement."""
    subject = "Votre mot de passe a été modifié — ServantAssist"
    preview = f"{user_first_name}, votre mot de passe ServantAssist a été modifié avec succès."

    now_str = datetime.now().strftime("%d/%m/%Y à %H:%M")

    content = f"""\
              <!-- Icône + titre -->
              <td style="padding:40px 40px 0 40px;">
                <div style="text-align:center;margin-bottom:24px;">
                  <div style="display:inline-block;background-color:{_SUCCESS_LIGHT};border-radius:50%;width:64px;height:64px;line-height:64px;text-align:center;">
                    <span style="font-size:28px;">&#9989;</span>
                  </div>
                </div>
                <h1 style="margin:0 0 8px 0;font-size:24px;font-weight:700;color:{_TEXT};text-align:center;line-height:1.3;">
                  Mot de passe modifié avec succès
                </h1>
                <p style="margin:0 0 24px 0;font-size:15px;color:{_SUCCESS};text-align:center;line-height:1.5;font-weight:500;">
                  Votre compte est sécurisé.
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
                  a bien été modifié le <strong>{now_str}</strong>.
                </p>
                <p style="margin:0 0 24px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Vous pouvez désormais vous connecter avec votre nouveau mot de passe :
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
              <!-- Sécurité -->
              <td style="padding:24px 40px 40px 40px;">
                <div style="background-color:#FEF2F2;border-radius:8px;padding:16px;border-left:4px solid #EF4444;">
                  <p style="margin:0;font-size:13px;color:#991B1B;line-height:1.6;">
                    &#9888; <strong>Ce n'était pas vous ?</strong>
                    Si vous n'avez pas effectué ce changement, votre compte est peut-être compromis.
                    Contactez immédiatement votre administrateur pour sécuriser votre compte.
                  </p>
                </div>
              </td>
            </tr>"""

    card_content = f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0'><tr>{content}</table>"
    html = _base_layout(card_content, preview)
    return subject, html


# ═══════════════════════════════════════════════════════════════════════════
#  3. Notification d'affectation à un événement
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
    preview = f"{user_first_name}, vous êtes affecté(e) à {event_title} en tant que {liturgical_role}."

    location_line = ""
    if event_location:
        location_line = f"""
                <tr>
                  <td style="padding:4px 16px 8px;font-size:14px;color:{_TEXT};">
                    <strong>Lieu :</strong> {event_location}
                  </td>
                </tr>"""

    content = f"""\
              <td style="padding:40px 40px 0 40px;">
                <div style="text-align:center;margin-bottom:24px;">
                  <div style="display:inline-block;background-color:{_PRIMARY_LIGHT};border-radius:50%;width:64px;height:64px;line-height:64px;text-align:center;">
                    <span style="font-size:28px;">&#9989;</span>
                  </div>
                </div>
                <h1 style="margin:0 0 8px 0;font-size:24px;font-weight:700;color:{_TEXT};text-align:center;">
                  Vous avez été affecté(e) !
                </h1>
                <p style="margin:0 0 4px 0;font-size:14px;color:{_TEXT_LIGHT};text-align:center;">
                  Votre présence est attendue à la célébration suivante
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:24px 40px 40px 40px;">
                <p style="margin:0 0 16px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Bonjour <strong>{user_first_name}</strong>,
                </p>
                <p style="margin:0 0 20px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Vous avez été assigné(e) à un événement liturgique. Voici les détails :
                </p>
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                       style="background-color:{_PRIMARY_LIGHT};border-radius:10px;margin-bottom:24px;overflow:hidden;">
                <tr>
                  <td style="padding:12px 16px 4px;font-size:14px;color:{_TEXT};">
                    <strong>Événement :</strong> {event_title}
                  </td>
                </tr>
                <tr>
                  <td style="padding:4px 16px;font-size:14px;color:{_TEXT};">
                    <strong>Date :</strong> {event_date}
                  </td>
                </tr>
                <tr>
                  <td style="padding:4px 16px;font-size:14px;color:{_TEXT};">
                    <strong>Votre rôle :</strong> <span style="color:{_PRIMARY};font-weight:600;">{liturgical_role}</span>
                  </td>
                </tr>{location_line}
                <tr><td style="padding:8px;"></td></tr>
                </table>
                <p style="margin:0;font-size:13px;color:{_TEXT_LIGHT};line-height:1.6;">
                  Connectez-vous à <strong>ServantAssist</strong> pour confirmer votre présence
                  ou signaler un empêchement à votre responsable.
                </p>
              </td>
            </tr>"""

    card_content = f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0'><tr>{content}</table>"
    return subject, _base_layout(card_content, preview)


# ═══════════════════════════════════════════════════════════════════════════
#  4. Rappel d'événement (24h avant)
# ═══════════════════════════════════════════════════════════════════════════


def render_event_reminder(
    user_first_name: str,
    event_title: str,
    event_date: str,
    event_location: str = "",
    liturgical_role: str = "",
) -> tuple[str, str]:
    """Retourne (subject, html_body) pour un rappel d'événement."""
    subject = f"Rappel — {event_title} demain"
    preview = f"{user_first_name}, n'oubliez pas : {event_title} a lieu demain !"

    role_line = ""
    if liturgical_role:
        role_line = f"<br>Votre rôle : <strong style='color:{_PRIMARY};'>{liturgical_role}</strong>"

    location_line = ""
    if event_location:
        location_line = f"<br>Lieu : <strong>{event_location}</strong>"

    content = f"""\
              <td style="padding:40px 40px 0 40px;">
                <div style="text-align:center;margin-bottom:24px;">
                  <div style="display:inline-block;background-color:{_PRIMARY_LIGHT};border-radius:50%;width:64px;height:64px;line-height:64px;text-align:center;">
                    <span style="font-size:28px;">&#128276;</span>
                  </div>
                </div>
                <h1 style="margin:0 0 8px 0;font-size:24px;font-weight:700;color:{_TEXT};text-align:center;">
                  Rappel : événement demain !
                </h1>
              </td>
            </tr>
            <tr>
              <td style="padding:24px 40px 40px 40px;">
                <p style="margin:0 0 16px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Bonjour <strong>{user_first_name}</strong>,
                </p>
                <p style="margin:0 0 20px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Ce message est un rappel amical : vous participez à <strong>{event_title}</strong>
                  prévu le <strong>{event_date}</strong>.
                  {role_line}{location_line}
                </p>
                <div style="background-color:{_PRIMARY_LIGHT};border-left:4px solid {_ACCENT};border-radius:0 8px 8px 0;padding:14px 18px;margin-bottom:20px;">
                  <p style="margin:0;font-size:13px;color:{_PRIMARY};font-weight:600;">
                    &#128337; Pensez à préparer vos affaires et à arriver à l'heure !
                  </p>
                </div>
                <p style="margin:0;font-size:13px;color:{_TEXT_LIGHT};line-height:1.6;">
                  En cas d'empêchement, signalez-vous dès maintenant via l'application.
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
    preview = f"{parent_first_name}, {child_first_name} a été marqué(e) absent(e) lors de {event_title}."

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
                  a été marqué(e) <strong style="color:#EF4444;">absent(e)</strong>
                  lors de <strong>{event_title}</strong> du <strong>{event_date}</strong>.
                </p>
                <p style="margin:0 0 16px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Si votre enfant avait un motif valable (maladie, voyage, urgence familiale…),
                  nous vous invitons à le communiquer à l'aumônier dès que possible afin
                  que l'absence soit justifiée.
                </p>
                <p style="margin:0;font-size:13px;color:{_TEXT_LIGHT};line-height:1.6;font-style:italic;">
                  Pour toute question, n'hésitez pas à contacter l'aumônier de la BMRA Mvolyé.
                </p>
              </td>
            </tr>"""

    card_content = f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0'><tr>{content}</table>"
    return subject, _base_layout(card_content, preview)


# ═══════════════════════════════════════════════════════════════════════════
#  6b. Code d'invitation — envoyé par l'admin au parent / servant
# ═══════════════════════════════════════════════════════════════════════════


def render_invitation_code(
    parent_name: str,
    code: str,
    role: str = "PARENT",
) -> tuple[str, str]:
    """Retourne (subject, html_body) pour l'email d'envoi du code d'invitation."""
    _ROLE_LABELS = {
        "PARENT": "Parent / Tuteur",
        "AUMONIER": "Aumônier",
        "SERVANT": "Servant d'autel",
    }
    role_label = _ROLE_LABELS.get(role.upper(), role)
    logo = _logo_url()

    subject = f"Votre code d'invitation ServantAssist — {code}"
    preview = f"Bonjour {parent_name}, voici votre code d'invitation pour rejoindre ServantAssist."

    content = f"""\
              <!-- Bandeau d'en-tête -->
              <td style="background-color:{_PRIMARY};border-radius:16px 16px 0 0;padding:32px 40px;text-align:center;">
                <div style="margin-bottom:16px;">
                  <img src="{logo}"
                       alt="ServantAssist"
                       width="64" height="64"
                       style="display:inline-block;border-radius:16px;border:3px solid rgba(255,255,255,0.3);width:64px;height:64px;object-fit:cover;">
                </div>
                <h1 style="margin:0;font-size:24px;font-weight:700;color:#FFFFFF;letter-spacing:-0.3px;">
                  Invitation à rejoindre ServantAssist
                </h1>
                <p style="margin:8px 0 0 0;font-size:14px;color:rgba(255,255,255,0.85);">
                  Basilique Marie Reine des Apôtres &mdash; BMRA Mvolyé
                </p>
              </td>
            </tr>
            <tr>
              <!-- Corps du message -->
              <td style="padding:40px 40px 32px 40px;">
                <p style="margin:0 0 16px 0;font-size:15px;color:{_TEXT};line-height:1.7;">
                  Cher(e) <strong>{parent_name}</strong>,
                </p>
                <p style="margin:0 0 20px 0;font-size:15px;color:{_TEXT};line-height:1.7;">
                  L'administration des <strong>Enfants de Chœur de la BMRA</strong> vous invite
                  à rejoindre <strong style="color:{_PRIMARY};">ServantAssist</strong>
                  en tant que <strong style="color:{_ACCENT};">{role_label}</strong>.
                  Nous sommes ravis de vous compter parmi nous !
                </p>
                <p style="margin:0 0 8px 0;font-size:14px;color:{_TEXT_LIGHT};">
                  Votre code d'invitation personnel :
                </p>

                <!-- Code mis en valeur -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:8px 0 28px 0;">
                  <tr>
                    <td style="background-color:{_PRIMARY_LIGHT};border:2px dashed {_PRIMARY};border-radius:12px;padding:20px;text-align:center;">
                      <p style="margin:0;font-size:30px;font-weight:800;color:{_PRIMARY};letter-spacing:6px;font-family:'Courier New',Courier,monospace;">
                        {code}
                      </p>
                    </td>
                  </tr>
                </table>

                <!-- Instructions -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                       style="background-color:{_PRIMARY_LIGHT};border-radius:8px;padding:16px;margin-bottom:24px;">
                  <tr>
                    <td style="padding:8px 16px;">
                      <p style="margin:0 0 10px 0;font-size:13px;font-weight:700;color:{_PRIMARY};text-transform:uppercase;letter-spacing:0.5px;">
                        Comment utiliser ce code ?
                      </p>
                      <p style="margin:0 0 6px 0;font-size:13px;color:{_TEXT};line-height:1.6;">
                        1&#46; Téléchargez l'application <strong>ServantAssist</strong> sur votre téléphone
                      </p>
                      <p style="margin:0 0 6px 0;font-size:13px;color:{_TEXT};line-height:1.6;">
                        2&#46; Cliquez sur <strong>« Créer un compte »</strong>
                      </p>
                      <p style="margin:0;font-size:13px;color:{_TEXT};line-height:1.6;">
                        3&#46; Saisissez ce code pour valider votre inscription
                      </p>
                    </td>
                  </tr>
                </table>

                <!-- Devise -->
                <p style="margin:0;font-size:13px;color:{_TEXT_LIGHT};text-align:center;font-style:italic;letter-spacing:0.8px;">
                  Aimer &nbsp;&mdash;&nbsp; Unir &nbsp;&mdash;&nbsp; Servir
                </p>
              </td>
            </tr>
            <tr>
              <!-- Note de sécurité -->
              <td style="background-color:{_PRIMARY_LIGHT};border-radius:0 0 16px 16px;padding:20px 40px;border-top:1px solid {_BORDER};">
                <p style="margin:0;font-size:12px;color:{_TEXT_LIGHT};line-height:1.6;">
                  Ce code est strictement personnel et ne doit pas être partagé. Si vous pensez avoir reçu
                  cet email par erreur, contactez l'administration de la BMRA Mvolyé.
                </p>
              </td>"""

    card_content = f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0'><tr>{content}</table>"
    return subject, _base_layout(card_content, preview)


def render_general_notification(
    user_first_name: str,
    title: str,
    body: str,
) -> tuple[str, str]:
    """Retourne (subject, html_body) pour une notification générale."""
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
                <p style="margin:0;font-size:15px;color:{_TEXT};line-height:1.7;">
                  {body}
                </p>
              </td>
            </tr>"""

    card_content = f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0'><tr>{content}</table>"
    return subject, _base_layout(card_content, preview)


def render_absence_warning(
    *,
    servant_first_name: str,
    servant_last_name: str,
    absent_count: int,
    session_date: str,
) -> tuple[str, str]:
    """Email d'avertissement au servant après 3 absences."""
    subject = f"Avertissement — {absent_count} absences enregistrées — ServantAssist"
    preview = f"{servant_first_name}, vous avez atteint {absent_count} absences non justifiées."
    _W = "#B45309"
    _WL = "#FFFBEB"

    content = f"""
              <td style="padding:40px 40px 0 40px;">
                <div style="text-align:center;margin-bottom:20px;">
                  <div style="display:inline-block;background-color:{_WL};border-radius:50%;width:64px;height:64px;line-height:64px;text-align:center;">
                    <span style="font-size:28px;">&#9888;</span>
                  </div>
                </div>
                <h1 style="margin:0 0 6px 0;font-size:22px;font-weight:700;color:{_W};text-align:center;">
                  Avertissement d'absence
                </h1>
                <p style="margin:0 0 4px 0;font-size:13px;color:{_TEXT_LIGHT};text-align:center;">Session du {session_date}</p>
              </td>
            </tr><tr>
              <td style="padding:24px 40px 0 40px;">
                <p style="margin:0 0 14px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Bonjour <strong>{servant_first_name} {servant_last_name}</strong>,
                </p>
                <p style="margin:0 0 14px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Nous avons noté que vous avez cumulé <strong>{absent_count} absences</strong> non justifiées.
                  Conformément au règlement intérieur de la BMRA, ceci constitue un <strong>avertissement officiel</strong>.
                </p>
                <div style="background-color:{_WL};border-left:4px solid #F59E0B;border-radius:0 8px 8px 0;padding:14px 18px;margin:0 0 14px 0;">
                  <p style="margin:0;font-size:14px;color:{_W};font-weight:600;">
                    &#9888; Attention : 5 absences entraîneront la convocation de vos parents ou tuteurs.
                  </p>
                </div>
                <p style="margin:0 0 14px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Si vos absences étaient justifiées, nous vous invitons à contacter le Censeur
                  dès maintenant pour régulariser votre situation.
                </p>
              </td>
            </tr><tr>
              <td style="padding:16px 40px 40px 40px;">
                <p style="margin:0;font-size:13px;color:{_TEXT_LIGHT};font-style:italic;">
                  Message automatique généré par ServantAssist — contactez le Censeur pour toute question.
                </p>
              </td>"""

    return subject, _base_layout(
        f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0'><tr>{content}</table>",
        preview,
    )


def render_parent_convocation(
    *,
    parent_first_name: str,
    servant_first_name: str,
    servant_last_name: str,
    absent_count: int,
) -> tuple[str, str]:
    """Email de convocation envoyé au parent après 5 absences du servant."""
    subject = f"Convocation — Absences de {servant_first_name} {servant_last_name} — ServantAssist"
    preview = f"Convocation concernant {servant_first_name} {servant_last_name} ({absent_count} absences enregistrées)."
    _D = "#B91C1C"
    _DL = "#FEF2F2"
    logo = _logo_url()

    content = f"""
              <td style="background-color:{_D};border-radius:16px 16px 0 0;padding:28px 40px;text-align:center;">
                <div style="margin-bottom:14px;">
                  <img src="{logo}"
                       alt="ServantAssist"
                       width="48" height="48"
                       style="display:inline-block;border-radius:12px;border:2px solid rgba(255,255,255,0.3);width:48px;height:48px;object-fit:cover;">
                </div>
                <h1 style="margin:0 0 6px 0;font-size:22px;font-weight:700;color:#FFFFFF;">
                  Convocation des Parents
                </h1>
                <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.85);">Basilique Marie Reine des Apôtres — Mvolyé</p>
              </td>
            </tr><tr>
              <td style="padding:28px 40px 0 40px;">
                <p style="margin:0 0 14px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Cher(e) <strong>{parent_first_name}</strong>,
                </p>
                <p style="margin:0 0 14px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Nous vous contactons au sujet de votre enfant <strong>{servant_first_name} {servant_last_name}</strong>,
                  servant d'autel à la Basilique Marie Reine des Apôtres de Mvolyé.
                </p>
                <div style="background-color:{_DL};border-left:4px solid #EF4444;border-radius:0 8px 8px 0;padding:16px 18px;margin:0 0 16px 0;">
                  <p style="margin:0 0 4px 0;font-size:15px;color:{_D};font-weight:700;">{absent_count} absences enregistrées</p>
                  <p style="margin:0;font-size:13px;color:{_D};">Le seuil de convocation a été atteint (5 absences)</p>
                </div>
                <p style="margin:0 0 14px 0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Conformément au règlement intérieur, vous êtes <strong>convoqué(e)</strong> à rencontrer
                  l'Aumônier et le Censeur lors de la prochaine session d'appel, en Sacristie.
                </p>
                <p style="margin:0;font-size:15px;color:{_TEXT};line-height:1.6;">
                  Nous comptons sur votre compréhension et restons disponibles pour en discuter avec vous.
                </p>
              </td>
            </tr><tr>
              <td style="padding:20px 40px 40px 40px;border-top:1px solid {_BORDER};margin-top:20px;">
                <p style="margin:0;font-size:13px;color:{_TEXT_LIGHT};font-style:italic;line-height:1.6;">
                  Pour fixer un rendez-vous ou pour toute question, contactez directement l'Aumônier de la Basilique.
                </p>
              </td>"""

    return subject, _base_layout(
        f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0'><tr>{content}</table>",
        preview,
    )


# ═══════════════════════════════════════════════════════════════════════════
#  10. Code OTP de réinitialisation — envoi sur mobile
# ═══════════════════════════════════════════════════════════════════════════


def render_reset_code_email(
    user_first_name: str,
    code: str,
) -> tuple[str, str]:
    subject = "Votre code de réinitialisation ServantAssist"
    preview = f"Votre code de réinitialisation est {code}. Il expire dans 15 minutes."

    digits = "".join(
        f"<td style='padding:0 6px;'>"
        f"<span style='display:inline-block;width:44px;height:56px;line-height:56px;"
        f"text-align:center;background-color:{_PRIMARY_LIGHT};border:2px solid {_PRIMARY};"
        f"border-radius:10px;font-size:28px;font-weight:700;color:{_PRIMARY};'>"
        f"{d}</span></td>"
        for d in code
    )

    content = f"""
      <td style="padding:40px 40px 32px;">
        <h1 style="margin:0 0 6px;font-size:22px;font-weight:700;color:{_PRIMARY};">
          Code de réinitialisation
        </h1>
        <p style="margin:0 0 28px;font-size:14px;color:{_TEXT_LIGHT};line-height:1.6;">
          Bonjour <strong style="color:{_TEXT};">{user_first_name}</strong>,<br>
          Voici votre code de réinitialisation de mot de passe.
          Saisissez-le rapidement dans l'application :
        </p>
        <table role="presentation" cellpadding="0" cellspacing="0"
               style="margin:0 auto 28px;">
          <tr>{digits}</tr>
        </table>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
               style="margin-bottom:28px;">
          <tr>
            <td style="background-color:#FFF7ED;border:1px solid #FED7AA;border-radius:10px;
                       padding:14px 18px;">
              <p style="margin:0;font-size:13px;color:#92400E;line-height:1.6;">
                &#9200; Ce code <strong>expire dans 15 minutes</strong>.
                Ne le partagez avec personne, même un membre de l'équipe.
              </p>
            </td>
          </tr>
        </table>
        <p style="margin:0;font-size:13px;color:{_TEXT_LIGHT};line-height:1.6;">
          Si vous n'avez pas demandé cette réinitialisation, ignorez simplement cet email.
          Votre compte reste sécurisé.
        </p>
      </td>
    """

    return subject, _base_layout(
        f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0'><tr>{content}</table>",
        preview,
    )
