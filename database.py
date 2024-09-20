from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
import json
from datetime import datetime

# Charger les variables d'environnement
load_dotenv()

class Neo4jDatabase:

    def __init__(self):
        # Connexion à la base de données Neo4j
        self.uri = os.getenv("DB_URI")
        self.username = os.getenv("DB_USERNAME")
        self.password = os.getenv("DB_PASSWORD")
        self.database = os.getenv("DB_DATABASE")
        self.driver = None

        # Initialisation du driver
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            print(f"Connexion réussie à la BDD Neo4j (base : {self.database})")
        except Exception as e:
            print(f"Erreur de connexion à la base de données Neo4j : {e}")

    def query(self, query):
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query)
                return list(result)
        except Exception as e:
            print(f"Erreur lors de l'exécution de la requête : {e}")
            return []

    def daily_activity(self):
        try:
            with self.driver.session(database=self.database) as session:
                query = """
                MATCH (t:Personne {prenom: "Thomas", nom: "Respaut"})-[:A_SANTE]->(s:Sante)
                RETURN s
                """

                result = session.run(query)
                noeud = result.single()["s"]

                #Récupéprer les activités depuis la proprité du noeud "Santé"
                activites_json = noeud["activites"]

                #Décoder chaque activité JSON en un dictionnaire Python
                activites = [json.loads(activite) for activite in activites_json]

                #Obtenir la date actuelle au format YYYY-MM-DD
                date_actuelle = datetime.now().strftime("%Y-%m-%d")

                #Filtrer les activités pour ne garder que celle du jour
                activites_du_jour = [activite for activite in activites if activite["date"] == date_actuelle]

                # Afficher les activités du jour
                if activites_du_jour:
                    for activite in activites_du_jour:
                        print(f"Date : {activite['date']}")
                        print(f"Type : {activite['type']}")
                        print(f"Nombre de pas : {activite['nombre_de_pas']}")
                        print(f"Distance : {activite['distance']} km")
                        print(f"Durée : {activite['duree']}")
                        print(f"Calories brûlées : {activite['calories_brulees']} kcal")
                        print("-" * 40)
                else:
                    print("Aucune activité pour aujourd'hui.")

        except Exception as e:
            print(f"Erreur lors de la récupération des activites : {e}")



    def close(self):
        # Fermeture du driver Neo4j
        if self.driver:
            self.driver.close()
            print("Connexion à la base de données Neo4j fermée.")


# Connexion à la base de données
db = Neo4jDatabase()

db.daily_activity()

# Fermeture de la connexion
db.close()
