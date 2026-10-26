/**
 * app/web/static/js/manuel.js
 * Gestion client du pilotage manuel en français (manette JOG, effecteurs, retour de télémétrie)
 */

let maintenu = false;
let minuteurBattement = null;
let battementEnAttente = false;
let chaineRequetes = Promise.resolve();
const etatEffecteur = { ventouse: false, suction: false, pince: false, gripper: false };

function mettreAJourPose(donnees) {
    if (donnees.x === undefined) return;
    const elPose = document.getElementById('poseDisplay');
    if (elPose) {
        elPose.innerText = `X: ${donnees.x.toFixed(2)} | Y: ${donnees.y.toFixed(2)} | Z: ${donnees.z.toFixed(2)} | R: ${donnees.r.toFixed(2)}`;
    }
    const elJoint = document.getElementById('jointDisplay');
    if (elJoint && donnees.j1 !== undefined) {
        elJoint.innerText = `J1: ${donnees.j1.toFixed(2)} | J2: ${donnees.j2.toFixed(2)} | J3: ${donnees.j3.toFixed(2)} | J4: ${donnees.j4.toFixed(2)}`;
    }
}

function mettreAJourStatut(texte) {
    const elStatut = document.getElementById('actionStatus');
    if (elStatut) elStatut.innerText = texte;
}

function traiterReponse(donnees) {
    mettreAJourPose(donnees);
    const msg = donnees.dernier_message || donnees.message;
    if (msg) mettreAJourStatut(msg);
}

function envoyerJSON(url, corps) {
    return fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corps || {})
    }).then(res => res.json());
}

function enfilerRequete(url, corps) {
    chaineRequetes = chaineRequetes.then(() => envoyerJSON(url, corps))
        .then(traiterReponse)
        .catch(() => mettreAJourStatut('Erreur de communication réseau avec le serveur.'));
    return chaineRequetes;
}

// Battement léger (aucun appel série sur le serveur, simple rafraîchissement d'horodatage)
function battement() {
    if (battementEnAttente) return;
    battementEnAttente = true;
    enfilerRequete('/api/jog/battement').finally(() => { battementEnAttente = false; });
}

function demarrerMouvement(evenement, axe, pas) {
    if (maintenu) return;
    maintenu = true;
    try {
        evenement.currentTarget.setPointerCapture(evenement.pointerId);
    } catch (e) {}

    enfilerRequete('/api/jog/demarrer', { axe: axe, direction: pas > 0 ? 1 : -1 });
    minuteurBattement = setInterval(battement, 100);
}

function arreterMouvement() {
    if (!maintenu) return;
    maintenu = false;
    clearInterval(minuteurBattement);
    minuteurBattement = null;
    enfilerRequete('/api/jog/arreter');
}

window.addEventListener('pointerup', arreterMouvement);
window.addEventListener('blur', arreterMouvement);
document.addEventListener('visibilitychange', () => { if (document.hidden) arreterMouvement(); });

function changerMode(mode) {
    arreterMouvement();
    const cartPad = document.getElementById('cartPad');
    const jointPad = document.getElementById('jointPad');
    const modeCart = document.getElementById('modeCart');
    const modeJoint = document.getElementById('modeJoint');

    if (cartPad) cartPad.hidden = (mode !== 'cart');
    if (jointPad) jointPad.hidden = (mode !== 'joint');
    if (modeCart) modeCart.classList.toggle('active', mode === 'cart');
    if (modeJoint) modeJoint.classList.toggle('active', mode === 'joint');
}

function modifierAffichageVitesse(valeur) {
    const el = document.getElementById('speedVal');
    if (el) el.innerText = `${valeur} %`;
}

function changerVitesse(valeur) {
    envoyerJSON('/api/vitesse', { ratio: valeur }).then(traiterReponse);
}

function basculerEffecteur(outil) {
    const cleOutil = (outil === 'suction' || outil === 'ventouse') ? 'ventouse' : 'pince';
    const etatSuivant = !etatEffecteur[cleOutil];
    envoyerJSON('/api/effecteur', { outil: cleOutil, actif: etatSuivant }).then(d => {
        traiterReponse(d);
        if (d.ok === false) return;
        etatEffecteur[cleOutil] = etatSuivant;
        etatEffecteur[outil] = etatSuivant;
        const btn = document.getElementById((cleOutil === 'ventouse') ? 'btnSuction' : 'btnGripper');
        if (btn) {
            btn.classList.toggle('active', etatSuivant);
            const icone = btn.querySelector('i') ? btn.querySelector('i').outerHTML : '';
            btn.innerHTML = icone + (cleOutil === 'ventouse'
                ? (etatSuivant ? ' Ventouse : ACTIVE' : ' Ventouse : OFF')
                : (etatSuivant ? ' Pince : FERMÉE' : ' Pince : OUVERTE'));
        }
    });
}

function arretUrgence() {
    maintenu = false;
    clearInterval(minuteurBattement);
    minuteurBattement = null;
    envoyerJSON('/api/arret').then(traiterReponse);
}

function interrogerStatut() {
    fetch('/api/statut')
        .then(res => res.json())
        .then(d => {
            mettreAJourPose(d);
            const msg = d.dernier_message || d.message;
            if (msg) mettreAJourStatut(msg);
            if (d.occupe || d.busy) setTimeout(interrogerStatut, 400);
        })
        .catch(() => setTimeout(interrogerStatut, 1000));
}

function lancerRecalage() {
    arreterMouvement();
    mettreAJourStatut('Lancement de la procédure HOME (recalage)...');
    envoyerJSON('/api/recalage').then(d => {
        traiterReponse(d);
        interrogerStatut();
    });
}

// Surveillance périodique de pose hors JOG actif
setInterval(() => {
    if (maintenu) return;
    fetch('/api/statut')
        .then(res => res.json())
        .then(d => {
            mettreAJourPose(d);
            const msg = d.dernier_message || d.message;
            if ((d.occupe || d.busy) && msg) mettreAJourStatut(msg);
        })
        .catch(() => {});
}, 500);

document.addEventListener('contextmenu', e => e.preventDefault());
interrogerStatut();

// --- Alias rétrocompatibilité anglais pour handlers onclick existants ---
window.setPose = mettreAJourPose;
window.setStatus = mettreAJourStatut;
window.handleResponse = traiterReponse;
window.postJSON = envoyerJSON;
window.enqueueRequest = enfilerRequete;
window.beat = battement;
window.startMove = demarrerMouvement;
window.stopMove = arreterMouvement;
window.setMode = changerMode;
window.speedInput = modifierAffichageVitesse;
window.speedChange = changerVitesse;
window.toggleEffector = basculerEffecteur;
window.emergencyStop = arretUrgence;
window.pollStatus = interrogerStatut;
window.goHome = lancerRecalage;

