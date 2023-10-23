import os, re, datetime, sqlite3, sys 
from collections import Counter

"""
Auteur: Alexandra LI COMBEAU LONGUET 21700177
Utilisation du programme en ligne de dommande:
    [python projet.py C bdd.db repertoire lang1 lang2],  ou  [python projet.py CS bdd.db repertoire lang1 lang2]

1. Pour construire une base de donnée à partir de sous-titres anglais et francais:
    [python projet.py C bdd.db repertoire lang1 lang2]
    Les options sont:
        C : pour construire une base de donnée
        repertoire : le nom du repertoire où se trouve les paires fichiers sous-titre au format nomfichier_eng.srt et nomfichier_fr.srt
        bdd.db : le nom du fichier base de donnée à créer, au format .db
        lang1 : la langue du fichier sous-titre 1
        lang2: la langue du fichier sous-titre 2
2. Pour faire une recherche dans la base de donnée:
    [python projet.py S bdd.db]
        S : pour faire une recherche
        bdd.db : le fichier la base de donnée précédément crée, au format .db. 
            Si l'argument n'est pas entrée, la recherche se fait par défaut dans 'Dictionnaire_FR-ENG.db'

Pour faire le 1. et le 2. à la suite:
    [python projet.py CS bdd.db lang1 lang2]
"""

# fonction de lecture de paire de sous titres: anglais et français
# entrée : le chemin du répertoire où son placé les fichiers sous-titre au format .srt
# retour: un tuple de deux listes dont chaque élément est uen lsite contenant le temps de début et de fin dans un tuple, puis les sous-titres associés
# renvoie en premier la structure de donnée du fichier en anglais, plus du fichier en français
# note: les fichiers sous-titres doivent être de la forme 'nomdufichier_eng.srt' ou 'nomdufichier_fr.srt'
def lecture(dir):
    eng=[] # la liste contenant le fichier de soustitre str anglais
    fr=[] # la liste contenant le fichier de soustitre str français
    # si le chemin entére est un répertoir
    if os.path.isdir(dir):
        # pour chaque fichier du répertoire
        for f in os.listdir(dir):
            # ouvrir le fichier
            path= dir + os.path.sep + f
            file = open(path, "r", encoding="utf-8")
            tampon=[] # une liste contenant un tuple de timecode (timecode début, timecode fin) et le texte associé
            tamponline="" # le texte entier associé à un timecode
            #pour chaque ligne du fichier
            for line in file:
                # s'il y a un numéro, alors les lignes d'après sont : les timcodes et le texte de dialogue
                if re.match("^\d+?$",line):
                        pass
                # s'il y aune flèche, alors la ligne est de type timecode de début --> timecode de fin
                elif re.search("-->", line):
                    t = line.strip().split(" --> ")
                    tdebut = datetime.datetime.strptime(t[0], '%H:%M:%S,%f').time()
                    tfin= datetime.datetime.strptime(t[1], '%H:%M:%S,%f').time()
                    time = tdebut, tfin
                    tampon.append(time)
                # s'il y a une ligne vide, on enregistre le contenu reccupée dans la liste associée
                elif re.match("^$",line):
                    tampon.append(tamponline)
                    tamponline=""
                    if f.split("_")[-1] == "eng.srt":
                        eng.append(tampon)
                        tampon=[]
                    if f.split("_")[-1] == "fr.srt":
                        fr.append(tampon)
                        tampon=[]
                # s'il ya du texte, on réccupère la ligne de dialogue
                elif re.match("^.+?$",line):
                    line= re.sub("<i>(.+?)</i>", "\\1", line)
                    tamponline+= " "+ line.strip()
            file.close()
    # si le nom d'un fichier est rentrée
    elif os.path.isfile(dir):
        return "Vous devez entrer le nom d'un répertoire."
    # dans les auters cas
    else:
        return "Vous devez entrer le nom d'un répertoire de sous-titres."
    return eng, fr

# une fonction d'alignement
# entére: eng, une liste de référence dont chaque élément est une liste avec un tuple de timecode et une string de texte
#         fr, une liste à aligner avec eng dont chaque élément est une liste avec un tuple de timecode et une string de texte
# retour : alignement, une liste de tuple avec les textes alignés
# Note: les éléments de eng n'ayant pas d'équivalent en fr ne sont pas alignés, donc pas ajouté à la liste 'alignement'
def alignement(eng, fr):
    alignement=[]
    for elem_eng in eng:
        engtime_start, engtime_end = elem_eng[0]
        eng_sent = elem_eng[-1]
        tampon=""
        for elem_fr in fr:
            frtime_start, frtime_end = elem_fr[0]
            fr_sent = elem_fr[-1]
            # quand le phrase eng et fr ont le même timecode
            if frtime_start == engtime_start:
                if frtime_end == engtime_end:
                    tampon = fr_sent
                    break
                elif frtime_end < engtime_end:
                    tampon+= fr_sent
                elif frtime_end > engtime_end:
                    tampon+=fr_sent
                    break
            # quand le timecode de la phrase fr commence avant le timecode de la phrase eng mais continue durant le timecode de la phrase eng
            elif frtime_start < engtime_start and frtime_end > engtime_start:
                tampon+=fr_sent
            # quand le timecode de la phrase fr commence durant le timecode de la phrase eng
            elif frtime_start > engtime_start and frtime_start < engtime_end:
                tampon+=fr_sent
            
        if tampon != "":
            alignement.append((eng_sent, tampon))
                        
    return alignement

# Une fonction qui enregistre dans une base de donnée son mot et sa traduction.
# Création de la table si elle n'existe pas dans la base de donnée
# Entrée: table, une chaine de caractère, le nom de la table où il faut enregistrer les deux mots
#         mot,  une chaine de caractère, le mot de référence
#         traduction, une chaine de caractère, la traduction en langue cible du mot de référence
def connexionBD(table, mot, traduction, bdd):
    conn= sqlite3.connect(bdd)
    curs = conn.cursor()
    curs.execute(f'''
          CREATE TABLE IF NOT EXISTS {table}
          (id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, mot TEXT, traduction TEXT)
          ''')
    conn.commit()      
 
    sql = f"INSERT INTO {table} (mot, traduction) values (?, ?)"
    curs.execute(sql, (mot, traduction))
    conn.commit()

    conn.close()

# une fonction calculant la correspondance de deux mots entre deux langues
# entrée:  lang1_lang2, une liste de deux éléments: élément 1: la langue de rééfrence, élément 2: la langue alignée
#          nomtable, une chaine de caractère, le nom de la table dans laquelle enregistrer la correspondance
#          bdd, une chaine de caractère, le nom du fichier base de donnée au format .db 
def correspondance(lang1_lang2, nomtable, bdd='Dictionnaire_FR-ENG.db'):
    dico1_contexte={}
    dico2_contexte={}
    dico1_freq={}

    # Pour chaque paire (e1, e2) de sous-titre
    for e1, e2 in lang1_lang2:
        # espace entre les mots
        e1 = re.sub('([^\w\d\-])',' \\1 ', e1.lower())
        e2 = re.sub('([^\w\d\-])',' \\1 ', e2.lower())
        
        # normalisation des apostrophes
        e1 = re.sub("’|\'|ʼ", " ’ ", e1)
        #e1 = re.sub('d ’ hui','d\'hui', e1)
        e2 = re.sub("’|\'|ʼ", " ’ ", e2)
        #e2 = re.sub('d ’ hui','d\'hui', e2)

        # suppression des ponctuations
        e1 = re.sub("[,!?\.\"’]", "", e1)
        e2 = re.sub("[,!?\.\"’]", "", e2)

        # transformation des suites d'espace en 1 seul espace
        e2 = re.sub('\s+', ' ', e2)
        e1 = re.sub('\s+', ' ', e1)
        
        # tokénisation
        lang1 = e1.strip().split(" ")
        lang2 = e2.strip().split(" ")

        # pour chaque mot de référence, calcul de sa fréquence et 
        # enregistrement des contextes dans les deux langues dans un dictionnaire
        for mot in lang1:
            if mot not in dico1_freq:
                dico1_freq[mot] = 1
                dico1_contexte[mot] =[(lang1, lang2)]
            else:
                dico1_freq[mot] += 1
                dico1_contexte[mot].append((lang1,lang2))
    
    # Pour chaque mot dans le dictionnaire des contextes
    # réccupérer les phrases de contextes
    for word, sents in dico1_contexte.items():
        d4=Counter()
        # compter le nombre de fois que chaque mot apparait dans la langue cible
        # enregister le résultat dans un dictionnaire Counter d4
        for sent1, sent2 in sents:
            for w in sent2:
                d4[w]+=1
        # Si la fréquence du mot en langue de référence n'est pas trouvable dans le dictionnaire d4:
        if dico1_freq[word] not in d4.values():
            word_max=[]
            # la traduction en langue cible est celui avec la fréquence la plus élevé
            # enregister dans la base de donnée le mot et ses traductions
            for i in d4:
                if d4[i] == max({i:j for i, j in d4.items()}.values()):
                    word_max.append(i)
            if word_max != None:
                for e in word_max:
                    connexionBD(nomtable, word, e, bdd)
        # si la férquence du mot en langue de référence est trouvavble dans le dictionnaire d4
        # la traduction du mot en langue cible sont les mots de d4 qui ont la même férquence
        # enregistrement dans la abse de donnée le mot et ses traductions
        else:
            for mot in d4:
                if d4[mot] == dico1_freq[word]:
                    connexionBD(nomtable, word, mot, bdd)

# fonction qui pour un mot donné, en donne sa traduction
# Entrée : nomtable, une chaine de caractère, le nom de la table de la abse de donnée où chercher la traduction
#          mot, chaine de caractère, le mot dont il faut trouver la traduction
#          bdd, chaine de caractère, la base de donnée où se trouve la table au format .db
# Sortie: le ou les traductions s'il y en a, un message d'erreur...
def interrogerBD(nomtable, mot, bdd='Dictionnaire_FR-ENG.db'):

    # connection à la base de donnée
    conn = sqlite3.connect(bdd)
    curs = conn.cursor()

    # on vérifie que la table entrée existe bien
    tableslistes = curs.execute("SELECT name FROM sqlite_master WHERE type='table';")
    res = [e[0] for e in tableslistes.fetchall() if e[0] != 'sqlite_sequence']
    if nomtable not in res:
        print(f"ERREUR: tableau {nomtable} introuvable.\nVoici la liste des tableaux:")
        for table in res:
            print("\t"+table)
        for i in range(3):
            nomtable = input("Entrez le nom du tableau dans lequel chercher (langReference_langCible): ")
            if nomtable in res:
                break
            if i==3:
                return "ERREUR DANS LE NOM DU TABLEAU: fin du programme"
                
                
    # on cherche la traduction
    sql = f'SELECT mot, traduction FROM {nomtable} WHERE mot = ?'
    curs.execute(sql, (mot,))
    row = curs.fetchone()
    if row == None:
        print(f"Pas de traduction trouvé pour le mot: {mot}")
    else:
        print(f"La traduction de '{mot}' est:")
        while row != None:
            mot, traduction = row
            print(f"\t {traduction}")
            row = curs.fetchone()
    
    curs.close()



if len(sys.argv) == 1:
    print("ERREUR: Vous devez entrer des arguments sous la forme:\n\t[python projet.py C bdd.db repertoire lang1 lang2], [python projet.py S (bdd.db)] ou  [python projet.py CS bdd.db repertoire lang1 lang2]")
    quit()
if "C" not in sys.argv[1] and "S" not in sys.argv[1]:
    print("ERREUR: Le premier argument doit être C, S, ou les deux.")
    quit()
if "C" in sys.argv[1]:
    if len(sys.argv) < 6:
        print("ERREUR: Vous devez entrer 4 arguments dans cet ordre: C bdd.db lang1 lang2")
        quit()
    else:
        repertoire = sys.argv[3]
        bdd = sys.argv[2]
        lang1 = sys.argv[4]
        lang2 = sys.argv[5]

        if bdd[-3:] != ".db":
            print("Vous devez entrer le nom d'un fichier avec l'extention .db")
            quit()
        else:
            print("Lecture du répertoire...")
            eng, fr = lecture(repertoire)

            print("Alignement des phrases...")
            #alignement de l'anglais vers le français
            eng_fr = alignement(eng, fr)
            #alignement du français vers l'anglais
            fr_eng = alignement(fr, eng)

            print("Correspondance mot à mot et enregistrement dans la base de donnés...")
            correspondance(eng_fr, f"{lang1}_{lang2}", bdd)
            correspondance(fr_eng, f"{lang2}_{lang1}", bdd)

if "S" in sys.argv[1]:
    if sys.argv[2] == None:
        bdd = 'Dictionnaire_FR-ENG.db'
    else:
        bdd = sys.argv[2]
    p = True
    while p == True:
        mot = input("\nQuel mot voulez-vous traduire ? ")
        lang1 = input("Dans quel langue est ce mot ? ")
        lang2 = input("Dans quelle langue voulez-vous traduire ce mot ? ")
        interrogerBD(f"{lang1}_{lang2}", mot.lower(), bdd)

        for i in range(3):
            yes_no = input("Voulez-vous chercher une autre traduction ? Y/N\n")
            if yes_no.lower() == "n":
                p = False
                break
            elif yes_no.lower() == "y":
                p= True
                break
            else:
                yes_no = input("ERREUR: caractère non valide, recommencez.\n Voulez-vous chercher une autre traduction ? Y/N")
                if i==3:
                    p = False
                    break
print("Fin du programme")
    




