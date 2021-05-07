from flask import Flask, render_template, request, session
from github import Github
import re

app = Flask(__name__)
app.secret_key = 'unamur_pws_3'  # Clef secrète nécessaire pour activer la session


# ================================================================================================================

################ [[ ROUTES ]] ################


# Fonction login()
@app.route('/login', methods=["GET", "POST"])
def login():
    # Redirection, avec argument "alerte", si présent.
    return connexion(request.args.get('alerte'))


# Fonction logout()
@app.route('/logout', methods=["GET"])
def logout():
    return exit()


# Fonction index()
@app.route('/index', methods=["GET", "POST"])
@app.route('/', methods=["GET", "POST"])
def index():
    # Redirection vers login si aucun compte connecté.
    if not session.get('user'):
        return connexion()
    # Appel de la méthode de création de repo si POST.
    elif request.method == 'POST' and request.form["reponom"]:
        return create()
    # Par défaut : simple affichage.
    else:
        return onyva()


# Fonction gestion()
@app.route('/gestion', methods=["GET", "POST"])
def gestion():
    # Redirection vers login si aucun compte connecté.
    if not session.get('user'):
        return connexion()
    # Par défaut : simple affichage.
    else:
        return gerer()


# ================================================================================================================

################ [[ GITHUB ]] ################


# Connexion par le biais d'un token :
def coGithub(token):
    g = Github(token)
    return g


# Vérifie la validité du Token et fournit le nom du compte Github si existe.
def getGitName(g):
    # Tentative de connexion :
    try:
        nom = g.get_user().login

    # En cas d'erreur :
    except Exception:
        nom = None

    return nom


# Récuparation de l'Access Token :
def geToken():
    return session['user']["token"]


# Détermination du statut d'un repo :
def statutRepo(private, archived):
    if archived:
        return "Archivé"
    elif private:
        return "Privé"
    else:
        return "Public"


# ================================================================================================================

################ [[ CONTROLLERS ]] ################


# --> FONCTION DE LOGIN

def connexion(alerte=None):
    if request.method == 'POST' and request.form["token"]:

        g = coGithub(request.form["token"])
        n = getGitName(g)

        if n:
            data = {
                "nom": n,
                "token": request.form["token"]
            }
            session['user'] = data
            return onyva()  # render_template('index.html')

        else:
            alerte = "Token non-reconnu ou quota de requêtes API dépassé pour le moment."
            return render_template('login.html', alerte=alerte)

    else:
        return render_template('login.html')


# --> FONCTION DE LOGOUT

def exit():
    session.clear()
    alerte = "Déconnexion effectuée."
    return render_template('login.html', alerte=alerte)


# --> FONCTION D'AFFICHAGE

def onyva(rapport=None):
    # Prise en compte du paramètre optionnel (rapport de création ou suppression) :
    report = ""
    if rapport is not None:
        report = rapport

    # Variables :
    liste = []
    lstnoms = []
    message = ""

    # Tentative de connexion :
    try:
        g = Github(geToken())
        user = g.get_user()

        # Récupération des données Github :
        repo = user.get_repos()
        for r in repo:
            # Uniquement garder les repos locaux (where 'organization' => None)
            if not r.organization:
                data = {
                    "nom": r.name,
                    "url": r.html_url,
                    "private": r.private
                }
                lstnoms.append(r.name)  # Mémorisation en session des noms de repos seulement

                # Mémorisation des noms de repos non-archivés seulement dans la liste à afficher
                if not r.archived:
                    liste.append(data)

        session['listeCourante'] = lstnoms  # Ajout des noms dans une liste session

        return render_template('index.html', liste=liste, message=message, rapport=report)

    # En cas d'erreur :
    except Exception:
        message = 'Un problème de connexion à l\'API est survenu ...'
        return render_template('index.html', liste=False, message=message)


# --> FONCTION DE CREATION

def create():
    # Récupération des données du formulaire :
    reponom = request.form["reponom"]
    reponbr = int(request.form["reponbr"])
    nmadmin = request.form["nmadmin"]

    # Suppression des caractères spéciaux dans le nom :
    reponom = re.sub('[^a-zA-Z0-9\n.]', '-', reponom)

    # Tentative de connexion :
    try:
        g = Github(geToken())
        user = g.get_user()

        # Boucle de création des repos :
        rebours = 1
        redondances = 0
        doublons = ""
        rapport = ""
        while reponbr >= rebours:

            # Prise en compte du nombre de créations (série ou unique ?)
            if reponbr > 1:
                zero = ""
                if rebours < 10:
                    zero = "0"
                nmcompl = reponom + zero + str(rebours)
            else:
                nmcompl = reponom

            # Création du repo s'il n'existe pas déjà :
            if nmcompl not in session['listeCourante']:
                user.create_repo(
                    nmcompl,  # Nom du repo
                    description="",  # Description du repo
                    private=True,  # Repo private
                    auto_init=True,  # Init ReadMe ON
                )
            # Si le repo existe déjà :
            else:
                if redondances > 0:
                    doublons += " , "
                doublons += nmcompl
                redondances += 1
            rebours += 1

            # + ajout de l'admin supplémentaire :
            if nmadmin:
                user.get_repo(nmcompl).add_to_collaborators(nmadmin, "admin")

        # Adaptation du rapport puis terminé :
        if redondances == 0:
            rapport += "Création réussie !"
        elif 0 < redondances < reponbr:
            rapport += "Création partiellement effectuée, car ces repos existente déjà : " + doublons
        else:
            rapport += "Le ou les repos que vous tentez de créer existent déjà."
        return onyva(rapport)

    # Si erreur :
    except Exception:

        message = 'Un problème est survenu ...'
        return render_template('index.html', liste=False, message=message)


# --> FONCTION DE GESTION (archivage et suppression)

def gerer():
    # Variables :
    liste = []
    message = ""
    rapport = ""
    if not session.get('affichage'):
        session['affichage'] = 0

    # [ Traitement d'un POST : ]

    if request.method == 'POST':

        # Récupération des données du formulaire :
        checkboxes = request.form.getlist('checkbox')
        option = request.form['option']
        session['affichage'] = int(request.form['memoireAffichage'])

        # Vérification : post non-vide
        if checkboxes:
            try:
                # Connexion :
                g = Github(geToken())

                for repo in checkboxes:
                    cible = g.get_user().get_repo(repo)
                    # CAS D'ARCHIVAGE :
                    if option == "archiver":
                        # Avant archivage, vérifier que le repo n'est pas déjà sous ce statut (sinon ça plante)
                        # S'assurer également que le mode d'affichage a permis le cochage du repos traité
                        if not cible.archived and session['affichage'] != 1:
                            # Archivage :
                            cible.edit(archived=True)
                            rapport = "Archivage effectué."
                    # CAS DE SUPPRESSION :
                    elif option == "supprimer":
                        # S'assurer également que le mode d'affichage a permis le cochage du repos traité
                        caroule = True
                        if session['affichage'] == 1 and not cible.archived: caroule = False
                        if session['affichage'] != 1 and cible.archived:     caroule = False
                        if caroule:
                            # Suppression :
                            cible.delete()
                            rapport = "Suppression effectuée."

            except Exception:
                message = "Un problème est survenu ..."
                return render_template('gestion.html', liste=False, message=message)

        else:
            message = 'Aucun repository sélectionné.'

    # [ Traitement de l'affichage : ]

    # Tentative de connexion :
    try:
        g = Github(geToken())
        user = g.get_user()

        # Récupération des données Github :
        repo = user.get_repos()
        for r in repo:
            # Uniquement garder les repos locaux (where 'organization' => None)
            # + try sans gestion d'exception pour compenser le conflit suppression repo en cours vs rechargement index.
            try:
                if not r.organization:
                    data = {
                        "nom": r.name,
                        "url": r.html_url,
                        "statut": statutRepo(r.private, r.archived),
                        "creation": r.created_at.strftime("%d/%m/%Y")
                    }
                    liste.append(data)
                else:
                    break
            except Exception:
                pass

        return render_template('gestion.html', liste=liste, message=message, rapport=rapport)

    # En cas d'erreur :
    except:
        message = 'Un problème de connexion à l\'API est survenu ...'
        return render_template('gestion.html', message=message)
