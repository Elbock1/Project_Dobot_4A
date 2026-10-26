"""
app/api/routes.py
Ensemble des routes HTTP Flask (Vues web et API REST) en français.
Point d'entrée unique pour la commande structurée (/api/commande) et le pilotage manuel.
Garantit la rétrocompatibilité complète avec les anciennes routes et paramètres en anglais.
"""

from flask import Blueprint, render_template, Response, request, jsonify
from app.vision.camera import generer_flux_mjpeg
from app.core import commandes
from app.core.securite import VerificateurSecurite


def serialiser_commande(cmd) -> dict:
    """Sérialise une commande en combinant les clés en français et en anglais."""
    dump_fr = cmd.model_dump(by_alias=False)
    dump_en = cmd.model_dump(by_alias=True)
    return {**dump_fr, **dump_en}


def creer_routes(controleur, executeur, securite: VerificateurSecurite) -> Blueprint:
    """Factory de création du Blueprint des routes Flask."""
    bp = Blueprint('principal', __name__)

    # --- Vues HTML (Français + redirection/alias anglais) ---

    @bp.route('/')
    def index():
        return render_template('index.html')

    @bp.route('/manuel')
    @bp.route('/manual')
    def vue_manuel():
        return render_template('manuel.html')

    @bp.route('/texte')
    @bp.route('/text')
    def vue_texte():
        return render_template('texte.html')

    @bp.route('/voix')
    @bp.route('/voice')
    def vue_voix():
        return render_template('voix.html')

    @bp.route('/gestes')
    @bp.route('/gesture')
    def vue_gestes():
        return render_template('gestes.html')

    @bp.route('/image')
    def vue_image():
        return render_template('image.html')

    # --- Flux Vidéo (Singleton partagé) ---

    @bp.route('/flux_video')
    @bp.route('/video_feed')
    def flux_video():
        return Response(generer_flux_mjpeg(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')

    # --- API Pilotage Manuel (JOG, Vitesse, Effecteurs, Urgence) ---

    @bp.route('/api/statut')
    @bp.route('/api/status')
    def api_statut():
        return jsonify(controleur.obtenir_statut())

    @bp.route('/api/jog/demarrer', methods=['POST'])
    @bp.route('/api/jog/start', methods=['POST'])
    def api_jog_demarrer():
        donnees = request.get_json(silent=True) or {}
        axe = donnees.get('axe') or donnees.get('axis', 'X')
        sens = donnees.get('direction') if 'direction' in donnees else donnees.get('dir', 1)
        return jsonify(controleur.demarrer_jog(axe, sens))

    @bp.route('/api/jog/battement', methods=['POST'])
    @bp.route('/api/jog/beat', methods=['POST'])
    def api_jog_battement():
        return jsonify(controleur.battement_jog())

    @bp.route('/api/jog/arreter', methods=['POST'])
    @bp.route('/api/jog/stop', methods=['POST'])
    def api_jog_arreter():
        return jsonify(controleur.arreter_jog())

    @bp.route('/api/vitesse', methods=['POST'])
    @bp.route('/api/speed', methods=['POST'])
    def api_vitesse():
        donnees = request.get_json(silent=True) or {}
        ratio = donnees.get('ratio') if 'ratio' in donnees else donnees.get('pourcentage', 100)
        return jsonify(controleur.regler_ratio_vitesse(ratio))

    @bp.route('/api/effecteur', methods=['POST'])
    @bp.route('/api/effector', methods=['POST'])
    def api_effecteur():
        donnees = request.get_json(silent=True) or {}
        outil = donnees.get('outil') or donnees.get('tool', 'ventouse')
        actif = donnees.get('actif') if 'actif' in donnees else donnees.get('on', False)
        return jsonify(controleur.regler_effecteur(outil, actif))

    @bp.route('/api/recalage', methods=['POST'])
    @bp.route('/api/home', methods=['POST'])
    def api_recalage():
        return jsonify(controleur.demarrer_recalage_asynchrone())

    @bp.route('/api/arret', methods=['POST'])
    @bp.route('/api/stop', methods=['POST'])
    def api_arret():
        # L'arrêt d'urgence vide la file de tâches et coupe le JOG
        if executeur:
            return jsonify(executeur.soumettre(commandes.CommandeArret()))
        return jsonify(controleur.arret_urgence())

    # --- API REST Commande Structurée (Chemin Unifié) ---

    @bp.route('/api/commande', methods=['POST'])
    @bp.route('/api/command', methods=['POST'])
    def api_commande():
        """
        Contrat commun : reçoit un JSON conforme au schéma,
        valide les règles de sécurité et transmet à l'exécuteur.
        """
        charge_utile = request.get_json(silent=True) or {}
        try:
            cmd = commandes.analyser_dictionnaire_commande(charge_utile)
        except Exception as e:
            return jsonify({"ok": False, "message": f"Erreur de validation de schéma JSON : {e}"}), 400

        resultat = executeur.soumettre(cmd)
        dict_cmd = serialiser_commande(cmd)
        return jsonify({
            **resultat,
            "command_json": dict_cmd,
            "commande_json": dict_cmd
        })

    # --- Commande Textuelle (NLU Règles -> JSON -> Validation -> Robot) ---

    @bp.route('/api/texte', methods=['POST'])
    @bp.route('/api/text', methods=['POST'])
    def api_texte():
        """
        Applique le pipeline complet :
        Texte -> NLU à règles -> Schéma JSON -> Validation Sécurité -> Exécution.
        """
        donnees = request.get_json(silent=True) or {}
        texte_brut = (
            donnees.get('texte') or
            donnees.get('consigne') or
            donnees.get('command') or
            donnees.get('commande', '')
        ).strip()

        if not texte_brut:
            return jsonify({"ok": False, "message": "Aucun texte fourni."}), 400

        # Interprétation par règles NLU
        cmd = commandes.analyser_regles_texte(texte_brut)
        if cmd is None:
            return jsonify({
                "ok": False,
                "message": f"Consigne non comprise par le parser à règles : '{texte_brut}'. Reformulez ou utilisez les commandes standard.",
                "command_json": None,
                "commande_json": None
            }), 422

        # Soumission au chemin commun
        resultat = executeur.soumettre(cmd)
        dict_cmd = serialiser_commande(cmd)
        return jsonify({
            **resultat,
            "raw_text": texte_brut,
            "texte_brut": texte_brut,
            "command_json": dict_cmd,
            "commande_json": dict_cmd
        })

    return bp


# Alias rétrocompatible
create_routes = creer_routes
