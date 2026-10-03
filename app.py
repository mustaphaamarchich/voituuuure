"""Tomobil - application Streamlit pour conducteurs, techniciens et experts auto."""
import base64
import hashlib
import secrets
import sqlite3
import urllib.request
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

BASE = Path(__file__).parent
DB_PATH = BASE / "mycar.db"
ASSETS = BASE  # images locales optionnelles, placées à côté de app.py
SEED_DEMO = True  # crée 3 comptes de démonstration si la base est vide

def unsplash(photo_id, w=900):
    return f"https://unsplash.com/photos/{photo_id}/download?force=true&w={w}"


def pexels(photo_id, w=900):
    return f"https://images.pexels.com/photos/{photo_id}/pexels-photo-{photo_id}.jpeg?auto=compress&cs=tinysrgb&w={w}"


# Photos professionnelles libres de droits (Unsplash / Pexels)
HERO_1 = unsplash("OWWnwU0cVnI", 1400)   # voiture électrique en recharge
HERO_2 = pexels(3807329, 1400)           # mécanicien sous le capot
HERO_3 = unsplash("azfu97JYrsw", 1400)   # voiture électrique et borne
HERO_BRAKE = unsplash("evobURW3hE4", 1400)
HERO_WHEEL = unsplash("5r7qgI2FHWs", 1400)
HERO_OIL = pexels(10490609, 1400)
HERO_CHARGE = unsplash("4uIHG_JKbmY", 1400)
FALLBACK = "https://loremflickr.com/900/500/car,driving?lock=21"

ROLES = ["Conducteur", "Technicien / Mécanicien", "Expert automobile"]
PRO_ROLES = ROLES[1:]
RAPPEL_TYPES = ["Visite technique", "Vidange", "Assurance", "Pneus", "Freins",
                "Batterie", "Révision", "Autre"]
CATEGORIES = ["Moteur", "Freins", "Pneus", "Batterie", "Climatisation",
              "Voiture électrique", "Suspension", "Carrosserie", "Documents", "Diagnostic"]

st.set_page_config(page_title="Tomobil", layout="wide")


# ------------------------------------------------------------------ base de données
def run(sql, params=(), fetch=False, one=False):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.execute(sql, params)
    result = None
    if fetch:
        result = cur.fetchone() if one else cur.fetchall()
    con.commit()
    last = cur.lastrowid
    con.close()
    return result if fetch else last


def init_db():
    run("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY, nom TEXT, email TEXT UNIQUE, salt TEXT, pwd TEXT,
        role TEXT, ville TEXT, specialite TEXT, created TEXT)""")
    run("""CREATE TABLE IF NOT EXISTS cars(
        id INTEGER PRIMARY KEY, user_id INTEGER, marque TEXT, modele TEXT,
        annee INTEGER, immat TEXT, km INTEGER)""")
    run("""CREATE TABLE IF NOT EXISTS reminders(
        id INTEGER PRIMARY KEY, user_id INTEGER, car_id INTEGER, type TEXT,
        date TEXT, note TEXT, done INTEGER DEFAULT 0)""")
    run("""CREATE TABLE IF NOT EXISTS requests(
        id INTEGER PRIMARY KEY, user_id INTEGER, car_id INTEGER, titre TEXT,
        description TEXT, categorie TEXT, budget REAL, statut TEXT DEFAULT 'ouverte',
        offer_id INTEGER, created TEXT)""")
    run("""CREATE TABLE IF NOT EXISTS offers(
        id INTEGER PRIMARY KEY, request_id INTEGER, tech_id INTEGER,
        prix REAL, message TEXT, created TEXT)""")
    run("""CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY, room TEXT, sender_id INTEGER, text TEXT, created TEXT)""")
    if SEED_DEMO:
        seed_demo()


def create_user(nom, email, pwd, role, ville="", spec=""):
    salt = secrets.token_hex(16)
    return run("INSERT INTO users(nom,email,salt,pwd,role,ville,specialite,created)"
               " VALUES(?,?,?,?,?,?,?,?)",
               (nom.strip(), email.strip().lower(), salt, hash_pwd(pwd, salt),
                role, ville.strip(), spec, now()))


def seed_demo():
    if run("SELECT 1 FROM users LIMIT 1", fetch=True, one=True):
        return
    uid = create_user("Conducteur Démo", "conducteur@demo.com", "demo1234", ROLES[0], "Ville démo")
    create_user("Technicien Démo", "technicien@demo.com", "demo1234", ROLES[1], "Ville démo", "Moteur")
    create_user("Expert Démo", "expert@demo.com", "demo1234", ROLES[2], "Ville démo", "Diagnostic")
    cid = run("INSERT INTO cars(user_id,marque,modele,annee,immat,km) VALUES(?,?,?,?,?,?)",
              (uid, "Dacia", "Logan", 2019, "12345-A-1", 78000))
    run("INSERT INTO requests(user_id,car_id,titre,description,categorie,budget,created)"
        " VALUES(?,?,?,?,?,?,?)",
        (uid, cid, "Bruit au freinage", "Grincement à l'avant quand je freine.", "Freins", 300, now()))


def hash_pwd(pwd, salt):
    return hashlib.pbkdf2_hmac("sha256", pwd.encode(), bytes.fromhex(salt), 100_000).hex()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


@st.cache_data
def load_dataset():
    return pd.read_csv(BASE / "dataset.csv", encoding="utf-8").fillna("")


# ------------------------------------------------------------------ images
@st.cache_data(show_spinner=False, ttl=86400)
def _download(url):
    """Télécharge l'image (suit les redirections). Lève une erreur si échec (non mis en cache)."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = r.read()
        if not r.headers.get_content_type().startswith("image") or len(data) < 500:
            raise ValueError("pas une image")
        return data


def fetch_image(url):
    try:
        return _download(url)
    except Exception:
        return None


def show_image(source, caption=None):
    """Affiche une photo : fichier local (à côté de app.py) ou URL, avec photo de secours."""
    if not source:
        return
    source = str(source)
    local = ASSETS / source
    if local.is_file():
        st.image(str(local), caption=caption, use_container_width=True)
        return
    data = fetch_image(source) or fetch_image(FALLBACK)
    if data:
        st.image(data, caption=caption, use_container_width=True)
    else:
        st.info("🖼️ Image indisponible (vérifiez la connexion internet).")


def bg_uri(url):
    data = fetch_image(url)
    if not data:
        return ""
    mime = "image/png" if data[:4] == b"\x89PNG" else "image/webp" if data[:4] == b"RIFF" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


CSS_AUTH = """
<style>
.stApp{background:__BG__;background-size:cover;background-position:center;background-attachment:fixed}
header[data-testid="stHeader"]{background:transparent}
.block-container{max-width:820px;margin-top:4vh;background:rgba(255,255,255,.94);
  border-radius:20px;padding:2.2rem 2.6rem !important;box-shadow:0 20px 60px rgba(0,0,0,.4)}
.block-container h1,.block-container h2,.block-container h3,
.block-container p,.block-container label{color:#111827 !important}
</style>
"""

CSS_APP = """
<style>
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0b1220,#1f2a44)}
[data-testid="stSidebar"] *{color:#e5e7eb !important}
[data-testid="stSidebar"] .stButton>button{background:transparent;border:1px solid #64748b}
.hero{background-size:cover;background-position:center;border-radius:18px;padding:3.2rem 2.6rem;
  min-height:230px;display:flex;flex-direction:column;justify-content:center;margin-bottom:1.4rem}
.hero h1{color:#fff !important;font-size:2.6rem;margin:0;padding:0}
.hero p{color:#e5e7eb !important;font-size:1.1rem;margin:.4rem 0 0}
</style>
"""


def style_auth(url):
    uri = bg_uri(url)
    bg = (f"linear-gradient(rgba(8,12,20,.62),rgba(8,12,20,.62)),url('{uri}')" if uri
          else "linear-gradient(135deg,#0f172a,#334155)")
    st.markdown(CSS_AUTH.replace("__BG__", bg), unsafe_allow_html=True)


def hero(title, subtitle, url):
    """Bandeau d'en-tête avec photo en arrière-plan."""
    uri = bg_uri(url)
    bg = (f"linear-gradient(90deg,rgba(8,12,20,.88),rgba(8,12,20,.3)),url('{uri}')" if uri
          else "linear-gradient(135deg,#0f172a,#334155)")
    css = f"<style>.hero{{background-image:{bg}}}</style>"
    st.markdown(css + f"<div class='hero'><h1>{title}</h1><p>{subtitle}</p></div>",
                unsafe_allow_html=True)


PAGE_HEROES = {
    "Mes voitures": ("Mes voitures", "Gardez le suivi de votre véhicule et de son kilométrage.", HERO_WHEEL),
    "Rappels & dates": ("Rappels & dates", "Visite technique, vidange, assurance : ne ratez plus aucune échéance.", HERO_OIL),
    "Conseils": ("Conseils d'entretien", "Des conseils clairs pour chaque partie de votre voiture.", HERO_2),
    "Vidéos": ("Vidéos pratiques", "Suivez des tutoriels pour traiter le problème de votre voiture.", HERO_3),
    "Mes demandes": ("Mes demandes de service", "Publiez votre problème et recevez des offres de techniciens.", HERO_BRAKE),
    "Demandes clients": ("Demandes clients", "Proposez votre prix et décrochez de nouvelles missions.", HERO_2),
    "Discussions": ("Discussions", "Échangez avec les experts, les techniciens et la communauté.", HERO_CHARGE),
    "Profil": ("Mon profil", "Vos informations personnelles.", HERO_1),
}


# ------------------------------------------------------------------ authentification
def page_auth():
    style_auth(HERO_2)
    st.markdown("<h1 style='margin:0;font-size:2.8rem;letter-spacing:.5px'>Tomobil</h1>"
                "<p style='font-size:1.1rem'>Votre voiture, vos rappels, vos experts, au même endroit.</p>",
                unsafe_allow_html=True)
    tab_in, tab_up = st.tabs(["Se connecter", "Créer mon compte"])

    with tab_in:
        email = st.text_input("Email", key="li_email")
        pwd = st.text_input("Mot de passe", type="password", key="li_pwd")
        if st.button("Connexion", type="primary"):
            u = run("SELECT * FROM users WHERE email=?", (email.strip().lower(),),
                    fetch=True, one=True)
            if not u:
                st.error("Aucun compte avec cet email. Si vous l'avez déjà créé, la base a peut-être "
                         "été réinitialisée (hébergement Streamlit Cloud) : recréez le compte.")
            elif secrets.compare_digest(u["pwd"], hash_pwd(pwd, u["salt"])):
                st.session_state.user = dict(u)
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")
        if SEED_DEMO:
            st.caption("Comptes de démonstration : conducteur@demo.com, technicien@demo.com, "
                       "expert@demo.com — mot de passe : demo1234")

    with tab_up:
        nom = st.text_input("Nom complet")
        email = st.text_input("Email", key="su_email")
        pwd = st.text_input("Mot de passe (6 caractères min.)", type="password", key="su_pwd")
        role = st.selectbox("Votre métier / profil", ROLES)
        ville = st.text_input("Ville")
        spec = ""
        if role in PRO_ROLES:
            spec = st.selectbox("Spécialité", CATEGORIES)
        if st.button("Créer mon compte", type="primary"):
            if not nom or "@" not in email or len(pwd) < 6:
                st.error("Vérifiez le nom, l'email et le mot de passe.")
            else:
                try:
                    create_user(nom, email, pwd, role, ville, spec)
                    st.success("Compte créé, vous pouvez vous connecter.")
                except sqlite3.IntegrityError:
                    st.error("Cet email est déjà utilisé.")


# ------------------------------------------------------------------ pages
def my_cars(uid):
    return run("SELECT * FROM cars WHERE user_id=?", (uid,), fetch=True)


def page_accueil(user):
    uid = user["id"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Mes voitures", len(my_cars(uid)))
    rem = run("SELECT * FROM reminders WHERE user_id=? AND done=0 ORDER BY date",
              (uid,), fetch=True)
    c2.metric("Rappels à venir", len(rem))
    if user["role"] == "Conducteur":
        n = run("SELECT COUNT(*) n FROM requests WHERE user_id=? AND statut='ouverte'",
                (uid,), fetch=True, one=True)["n"]
        c3.metric("Demandes ouvertes", n)
    else:
        n = run("SELECT COUNT(*) n FROM requests WHERE statut='ouverte'", fetch=True, one=True)["n"]
        c3.metric("Demandes disponibles", n)

    st.subheader("Prochaines échéances")
    if not rem:
        st.info("Aucun rappel. Ajoutez-en dans « Rappels & dates ».")
    for r in rem[:5]:
        d = (date.fromisoformat(r["date"]) - date.today()).days
        icon = "🔴" if d < 0 else "🟠" if d <= 30 else "🟢"
        st.write(f"{icon} **{r['type']}** le {r['date']} "
                 f"({'en retard de ' + str(-d) if d < 0 else 'dans ' + str(d)} jours)")



def page_voitures(user):
    with st.form("car"):
        c1, c2, c3 = st.columns(3)
        marque = c1.text_input("Marque")
        modele = c2.text_input("Modèle")
        annee = c3.number_input("Année", 1980, date.today().year, 2018)
        c4, c5 = st.columns(2)
        immat = c4.text_input("Immatriculation")
        km = c5.number_input("Kilométrage", 0, 1_000_000, 50_000, step=500)
        if st.form_submit_button("Ajouter") and marque and modele:
            run("INSERT INTO cars(user_id,marque,modele,annee,immat,km) VALUES(?,?,?,?,?,?)",
                (user["id"], marque, modele, int(annee), immat, int(km)))
            st.rerun()
    cars = my_cars(user["id"])
    if cars:
        df = pd.DataFrame([dict(c) for c in cars]).drop(columns=["user_id"])
        st.dataframe(df, use_container_width=True, hide_index=True)
        with st.expander("Mettre à jour le kilométrage"):
            car = st.selectbox("Voiture", cars, format_func=lambda c: f"{c['marque']} {c['modele']}")
            new_km = st.number_input("Nouveau km", 0, 1_000_000, int(car["km"]), step=100)
            if st.button("Enregistrer le km"):
                run("UPDATE cars SET km=? WHERE id=?", (int(new_km), car["id"]))
                st.rerun()


def page_conseils():
    df = load_dataset()
    df = df[df["type"] == "conseil"]
    c1, c2 = st.columns([1, 2])
    cat = c1.selectbox("Catégorie", ["Toutes"] + sorted(df["categorie"].unique()))
    txt = c2.text_input("Rechercher")
    if cat != "Toutes":
        df = df[df["categorie"] == cat]
    if txt:
        df = df[df["titre"].str.contains(txt, case=False) | df["contenu"].str.contains(txt, case=False)]
    cols = st.columns(3)
    for i, (_, r) in enumerate(df.iterrows()):
        with cols[i % 3].container(border=True):
            show_image(r["image"])
            st.caption(r["categorie"])
            st.subheader(r["titre"])
            st.write(r["contenu"])


def page_rappels(user):
    cars = my_cars(user["id"])
    if not cars:
        st.warning("Ajoutez d'abord une voiture.")
        return
    with st.form("rem"):
        car = st.selectbox("Voiture", cars, format_func=lambda c: f"{c['marque']} {c['modele']}")
        c1, c2 = st.columns(2)
        typ = c1.selectbox("Type", RAPPEL_TYPES)
        d = c2.date_input("Date d'échéance", date.today())
        note = st.text_input("Note (garage, prix...)")
        if st.form_submit_button("Enregistrer"):
            run("INSERT INTO reminders(user_id,car_id,type,date,note) VALUES(?,?,?,?,?)",
                (user["id"], car["id"], typ, d.isoformat(), note))
            st.rerun()
    rows = run("""SELECT r.*, c.marque, c.modele FROM reminders r
                  JOIN cars c ON c.id=r.car_id WHERE r.user_id=? ORDER BY r.done, r.date""",
               (user["id"],), fetch=True)
    for r in rows:
        d = (date.fromisoformat(r["date"]) - date.today()).days
        icon = "✅" if r["done"] else "🔴" if d < 0 else "🟠" if d <= 30 else "🟢"
        c1, c2, c3 = st.columns([5, 1, 1])
        c1.write(f"{icon} **{r['type']}** · {r['marque']} {r['modele']} · {r['date']} · {r['note'] or ''}")
        if not r["done"] and c2.button("Fait", key=f"d{r['id']}"):
            run("UPDATE reminders SET done=1 WHERE id=?", (r["id"],))
            st.rerun()
        if c3.button("Suppr.", key=f"x{r['id']}"):
            run("DELETE FROM reminders WHERE id=?", (r["id"],))
            st.rerun()


def page_demandes_client(user):
    st.caption("Décrivez le problème et proposez un budget : les techniciens vous envoient leurs offres.")
    cars = my_cars(user["id"])
    with st.form("req"):
        titre = st.text_input("Problème (ex : bruit au freinage)")
        c1, c2, c3 = st.columns(3)
        cat = c1.selectbox("Catégorie", CATEGORIES)
        budget = c2.number_input("Votre budget (MAD / €)", 0, 100_000, 300, step=10)
        car = c3.selectbox("Voiture", cars or [None],
                           format_func=lambda c: f"{c['marque']} {c['modele']}" if c else "—")
        desc = st.text_area("Détails")
        if st.form_submit_button("Publier la demande") and titre:
            run("INSERT INTO requests(user_id,car_id,titre,description,categorie,budget,created)"
                " VALUES(?,?,?,?,?,?,?)",
                (user["id"], car["id"] if car else None, titre, desc, cat, budget, now()))
            st.rerun()

    for r in run("SELECT * FROM requests WHERE user_id=? ORDER BY id DESC", (user["id"],), fetch=True):
        with st.container(border=True):
            st.subheader(f"{r['titre']}  ·  {r['statut']}")
            st.write(f"{r['categorie']} · budget {r['budget']:.0f} · {r['created']}")
            st.write(r["description"])
            offers = run("""SELECT o.*, u.nom, u.specialite, u.ville FROM offers o
                            JOIN users u ON u.id=o.tech_id WHERE request_id=?""",
                         (r["id"],), fetch=True)
            for o in offers:
                c1, c2 = st.columns([4, 1])
                c1.write(f"**{o['nom']}** ({o['specialite'] or 'général'}, {o['ville']}) "
                         f"→ **{o['prix']:.0f}** · {o['message']}")
                if r["statut"] == "ouverte" and c2.button("Accepter", key=f"acc{o['id']}"):
                    run("UPDATE requests SET statut='acceptée', offer_id=? WHERE id=?",
                        (o["id"], r["id"]))
                    st.rerun()
            if r["statut"] == "acceptée":
                st.success("Offre acceptée : discutez dans l'onglet « Discussions ».")
                if st.button("Marquer terminée", key=f"fin{r['id']}"):
                    run("UPDATE requests SET statut='terminée' WHERE id=?", (r["id"],))
                    st.rerun()


def page_missions_pro(user):
    st.caption("Façon inDrive : proposez votre prix, le client choisit.")
    reqs = run("""SELECT r.*, u.nom, u.ville FROM requests r JOIN users u ON u.id=r.user_id
                  WHERE r.statut='ouverte' ORDER BY r.id DESC""", fetch=True)
    if not reqs:
        st.info("Aucune demande ouverte pour le moment.")
    for r in reqs:
        with st.container(border=True):
            st.subheader(r["titre"])
            st.write(f"{r['categorie']} · {r['nom']} ({r['ville']}) · budget client : **{r['budget']:.0f}**")
            st.write(r["description"])
            mine = run("SELECT * FROM offers WHERE request_id=? AND tech_id=?",
                       (r["id"], user["id"]), fetch=True, one=True)
            if mine:
                st.info(f"Votre offre : {mine['prix']:.0f}")
            else:
                c1, c2 = st.columns([1, 3])
                prix = c1.number_input("Votre prix", 0, 100_000, int(r["budget"]), key=f"p{r['id']}")
                msg = c2.text_input("Message", key=f"m{r['id']}")
                if st.button("Envoyer l'offre", key=f"o{r['id']}", type="primary"):
                    run("INSERT INTO offers(request_id,tech_id,prix,message,created) VALUES(?,?,?,?,?)",
                        (r["id"], user["id"], prix, msg, now()))
                    st.rerun()

    st.subheader("Mes missions acceptées")
    won = run("""SELECT r.* FROM requests r JOIN offers o ON o.id=r.offer_id
                 WHERE o.tech_id=? ORDER BY r.id DESC""", (user["id"],), fetch=True)
    for r in won:
        st.write(f"✅ **{r['titre']}** · {r['statut']}")


def rooms_for(user):
    rooms = {"Communauté Tomobil": "general", "Experts & techniciens": "pros"}
    if user["role"] == "Conducteur":
        q = "SELECT * FROM requests WHERE user_id=? AND statut IN ('acceptée','terminée')"
        params = (user["id"],)
    else:
        q = """SELECT r.* FROM requests r JOIN offers o ON o.id=r.offer_id
               WHERE o.tech_id=?"""
        params = (user["id"],)
    for r in run(q, params, fetch=True):
        rooms[f"Mission : {r['titre']}"] = f"req-{r['id']}"
    if user["role"] == "Conducteur":
        rooms.pop("Experts & techniciens")
    return rooms


def page_chat(user):
    rooms = rooms_for(user)
    label = st.selectbox("Salon", list(rooms))
    room = rooms[label]
    if st.button("Actualiser"):
        st.rerun()
    msgs = run("""SELECT m.*, u.nom, u.role FROM messages m JOIN users u ON u.id=m.sender_id
                  WHERE room=? ORDER BY m.id DESC LIMIT 60""", (room,), fetch=True)[::-1]
    box = st.container(height=420)
    for m in msgs:
        mine = m["sender_id"] == user["id"]
        with box.chat_message("user" if mine else "assistant"):
            st.markdown(f"**{m['nom']}** · _{m['role']}_ · {m['created']}")
            st.write(m["text"])
    text = st.chat_input("Écrire un message...")
    if text:
        run("INSERT INTO messages(room,sender_id,text,created) VALUES(?,?,?,?)",
            (room, user["id"], text, now()))
        st.rerun()


def page_videos():
    df = load_dataset()
    df = df[df["type"] == "video"]
    cat = st.selectbox("Catégorie", ["Toutes"] + sorted(df["categorie"].unique()))
    if cat != "Toutes":
        df = df[df["categorie"] == cat]
    cols = st.columns(3)
    for i, (_, r) in enumerate(df.iterrows()):
        with cols[i % 3].container(border=True):
            if "watch?v=" in r["lien"] or "youtu.be" in r["lien"]:
                st.video(r["lien"])
            else:
                show_image(r["image"])
                st.link_button("▶ Voir la vidéo", r["lien"], use_container_width=True)
            st.subheader(r["titre"])
            st.caption(f"{r['categorie']} · {r['contenu']}")


def page_profil(user):
    st.write(f"**Nom** : {user['nom']}")
    st.write(f"**Email** : {user['email']}")
    st.write(f"**Métier** : {user['role']}")
    st.write(f"**Ville** : {user['ville']}")
    if user["specialite"]:
        st.write(f"**Spécialité** : {user['specialite']}")


# ------------------------------------------------------------------ main
def main():
    init_db()
    user = st.session_state.get("user")
    if not user:
        page_auth()
        return

    with st.sidebar:
        st.markdown(f"<h2 style='margin-bottom:0'>TOMOBIL</h2>"
                    f"<p style='margin-top:0'><b>{user['nom']}</b><br>{user['role']}</p>",
                    unsafe_allow_html=True)
        pages = ["Accueil", "Conseils", "Vidéos", "Discussions"]
        if user["role"] == "Conducteur":
            pages[1:1] = ["Mes voitures", "Rappels & dates"]
            pages.insert(-1, "Mes demandes")
        else:
            pages.insert(1, "Demandes clients")
        pages.append("Profil")
        page = st.radio("Navigation", pages, label_visibility="collapsed")
        if st.button("Se déconnecter"):
            st.session_state.clear()
            st.rerun()

    st.markdown(CSS_APP, unsafe_allow_html=True)
    if page == "Accueil":
        hero(f"Bonjour {user['nom'].split()[0]}", user["role"], HERO_1)
    elif page in PAGE_HEROES:
        hero(*PAGE_HEROES[page])

    if page == "Accueil":
        page_accueil(user)
    elif page == "Mes voitures":
        page_voitures(user)
    elif page == "Rappels & dates":
        page_rappels(user)
    elif page == "Conseils":
        page_conseils()
    elif page == "Vidéos":
        page_videos()
    elif page == "Mes demandes":
        page_demandes_client(user)
    elif page == "Demandes clients":
        page_missions_pro(user)
    elif page == "Discussions":
        page_chat(user)
    else:
        page_profil(user)


main()
