import matplotlib.pyplot as plt
import networkx as nx
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
import math
import pygame
import networkx as nx
import pygame
import math
from pygame.locals import *

import tkinter as tk
from tkinter import simpledialog, messagebox

import threading

# Charger les variables d'environnement
load_dotenv()


class Neo4jDatabase:

    def __init__(self):
        # Connexion à la base de données Neo4j
        self.uri = os.getenv("DB_URI")
        self.username = os.getenv("DB_USERNAME")
        self.password = os.getenv("DB_PASSWORD")
        self.database = os.getenv("DB_DATABASE")

        # Définition de l'outil pour ajouter une entité et une relation
        self.tool = {
            "type": "function",
            "function": {
                "name": "ajouter_entite_et_relation",
                "description": "Ajoute une entité et, si spécifié, une relation avec une autre entité. "
                               "Si l'entité ou la relation cible n'existe pas, elles seront créées. "
                               "Si relation_inverse est True, on inverse la direction de la relation. "
                               "Exemple : entite='ActiviteSportive', proprietes={'nom': 'Natation', 'duree': '1h'}, "
                               "relation='PRATIQUE', cible_relation='Personne', "
                               "proprietes_relation={'prenom': 'Thomas', 'nom': 'Respaut'}, "
                               "relation_inverse=True",
                "parameters": {
                    "entite": {
                        "type": "string",
                        "description": "Le type d'entité à créer ou à vérifier (par exemple: ActiviteSportive, Lieu, etc.)."
                    },
                    "proprietes": {
                        "type": "object",
                        "description": "Un dictionnaire contenant les propriétés de l'entité à créer (par exemple: nom, description, duree)."
                    },
                    "relation": {
                        "type": "string",
                        "description": "Le type de relation à établir entre l'entité et l'entité cible (par exemple: PRATIQUE, VIT_A)."
                    },
                    "cible_relation": {
                        "type": "string",
                        "description": "Le type de l'entité cible avec laquelle la relation sera créée (par exemple: Personne, Projet)."
                    },
                    "proprietes_relation": {
                        "type": "object",
                        "description": "Un dictionnaire contenant les propriétés de l'entité cible pour établir une correspondance (par exemple: nom, prenom pour une Personne)."
                    },
                    "relation_inverse": {
                        "type": "boolean",
                        "description": "Indique si la relation doit être inversée. Si True, la relation ira de l'entité cible vers l'entité principale."
                    }
                }
            }
        }
        self.driver = None

        # Initialisation du driver
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            #print(f"Connexion réussie à la BDD Neo4j (base : {self.database})")
            self.ensure_main_person_exists()  # Vérifier ou créer la personne principale
        except Exception as e:
            print(f"Erreur de connexion à la base de données Neo4j : {e}")

    def execute_query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [record for record in result]

    def query(self, query, parameters=None):
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, parameters)
                return list(result)
        except Exception as e:
            print(f"Erreur lors de l'exécution de la requête : {e}")
            return []

    def ensure_main_person_exists(self):
        """
        Vérifie si la personne principale (Thomas Respaut) existe.
        Si elle n'existe pas, elle est créée avec les informations de base (Prénom, Nom).
        """
        try:
            with self.driver.session(database=self.database) as session:
                query = """
                MERGE (p:Personne {prenom: $prenom, nom: $nom})
                RETURN p
                """
                parameters = {
                    "prenom": "Thomas",
                    "nom": "Respaut"
                }

                result = session.run(query, parameters)
                person = result.single()
                #if person:
                    #print("La personne principale 'Thomas Respaut' existe ou vient d'être créée.")
        except Exception as e:
            print(f"Erreur lors de la vérification/création de la personne principale : {e}")

    def ajouter_entite_et_relation(self, entite, proprietes, relation=None, cible_relation=None,
                                   proprietes_relation=None, relation_inverse=False):
        """
        Ajoute une entité et, si spécifié, une relation avec une autre entité.
        Si l'entité ou la relation cible n'existe pas, elles seront créées.
        Si relation_inverse est True, on inverse la direction de la relation.
        """
        try:
            with self.driver.session(database=self.database) as session:
                # Vérification des nœuds pour éviter la duplication
                prop_string = ", ".join([f"{key}: ${key}" for key in proprietes.keys()])
                query = f"MERGE (e:{entite.replace(' ', '_')} {{{prop_string}}})"

                # Si une relation est définie, gérer la relation avec l'entité cible
                if relation and cible_relation and proprietes_relation:
                    cible_prop_string = ", ".join([f"{key}: ${key}_cible" for key in proprietes_relation.keys()])
                    query += f" MERGE (c:{cible_relation.replace(' ', '_')} {{{cible_prop_string}}})"

                    # Inverser la relation si nécessaire
                    if relation_inverse:
                        query += f" MERGE (c)-[:{relation}]->(e)"
                    else:
                        query += f" MERGE (e)-[:{relation}]->(c)"

                # Séparer les paramètres des nœuds
                params_entite = {**proprietes}
                params_cible = {f"{key}_cible": value for key, value in
                                proprietes_relation.items()} if proprietes_relation else {}

                # Exécution de la requête dans Neo4j
                session.run(query, {**params_entite, **params_cible})

                print(f"Entité '{entite}' et relation '{relation}' ajoutées avec succès.")
                return f"Entité '{entite}' et relation '{relation}' ajoutées avec succès."

        except Exception as e:
            print(f"Erreur lors de l'ajout de l'entité et de la relation : {e}")

    def ajouter_propriete_a_entite(self, entite, proprietes, nouvelle_propriete):
        """
        Ajoute ou met à jour une propriété d'une entité existante dans la base de données Neo4j.
        Si l'entité n'existe pas, elle est créée avec la nouvelle propriété.
        """
        try:
            with self.driver.session(database=self.database) as session:
                # Création ou mise à jour de l'entité avec la nouvelle propriété
                prop_string = ", ".join([f"{key}: ${key}" for key in proprietes.keys()])
                query = f"MERGE (e:{entite} {{{prop_string}}}) SET e.{nouvelle_propriete[0]} = $nouvelle_valeur"

                # Exécution de la requête dans Neo4j
                session.run(query, {**proprietes, "nouvelle_valeur": nouvelle_propriete[1]})
                return f"Propriété '{nouvelle_propriete[0]}' ajoutée ou mise à jour pour l'entité '{entite}'."
        except Exception as e:
            print(f"Erreur lors de l'ajout de la propriété à l'entité : {e}")

    def visualiser_graph(self):
        """
        Visualise le graphe des nœuds et relations avec les noms des nœuds et relations.
        """
        try:
            with self.driver.session(database=self.database) as session:
                query = """
                MATCH (n)-[r]->(m)
                RETURN n, r, m
                """
                result = session.run(query)

                # Création du graphe avec NetworkX
                graph = nx.DiGraph()

                for record in result:
                    noeud_1 = record["n"]
                    noeud_2 = record["m"]
                    relation = record["r"]

                    # Récupérer les informations de chaque nœud pour l'affichage correct
                    def get_node_label(node):
                        # On priorise certaines propriétés pour le label du nœud
                        if "prenom" in node and "nom" in node:
                            return f'{node["prenom"]} {node["nom"]}'
                        if "nom" in node:
                            return node["nom"]
                        if "description" in node:
                            return node["description"]
                        return "Unnamed Node"

                    # Ajouter les nœuds au graphe avec leur label
                    graph.add_node(noeud_1.id, label=get_node_label(noeud_1))
                    graph.add_node(noeud_2.id, label=get_node_label(noeud_2))

                    # Ajouter la relation avec son nom
                    graph.add_edge(noeud_1.id, noeud_2.id, label=relation.type)

                # Dessiner le graphe
                pos = nx.spring_layout(graph)  # Position des nœuds

                # Dessiner les nœuds avec leurs labels
                labels = nx.get_node_attributes(graph, "label")
                nx.draw(graph, pos, labels=labels, with_labels=True, node_color='lightblue', node_size=3000,
                        font_size=10)

                # Dessiner les relations avec leurs noms
                edge_labels = nx.get_edge_attributes(graph, 'label')
                nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels, font_color='red')

                plt.show()

        except Exception as e:
            print(f"Erreur lors de la visualisation du graphe : {e}")

    def recuperer_informations_graph(self):
        """
        Récupère toutes les informations du graphe (nœuds et relations) depuis la base de données Neo4j.
        Retourne un dictionnaire structuré avec les nœuds et les relations.
        """
        try:
            with self.driver.session(database=self.database) as session:
                # Requête pour récupérer tous les nœuds et relations
                query = """
                MATCH (n)-[r]->(m)
                RETURN n, r, m
                """
                result = session.run(query)

                # Initialiser des structures pour stocker les informations du graphe
                noeuds = {}
                relations = []

                for record in result:
                    noeud_1 = record["n"]
                    noeud_2 = record["m"]
                    relation = record["r"]

                    # Fonction pour récupérer les informations d'un nœud
                    def obtenir_info_noeud(noeud):
                        return {
                            "labels": list(noeud.labels),  # Liste des labels du nœud
                            "proprietes": dict(noeud)  # Propriétés du nœud
                        }

                    # Ajouter les nœuds au dictionnaire s'ils ne sont pas déjà présents
                    if noeud_1.id not in noeuds:
                        noeuds[noeud_1.id] = obtenir_info_noeud(noeud_1)
                    if noeud_2.id not in noeuds:
                        noeuds[noeud_2.id] = obtenir_info_noeud(noeud_2)

                    # Ajouter la relation sous forme structurée
                    relations.append({
                        "de": noeud_1.id,
                        "vers": noeud_2.id,
                        "type": relation.type,
                        "proprietes": dict(relation)  # Propriétés de la relation, s'il y en a
                    })

                # Retourner les informations structurées pour le graphe
                return {
                    "noeuds": noeuds,
                    "relations": relations
                }

        except Exception as e:
            print(f"Erreur lors de la récupération des informations du graphe : {e}")
            return None

    @staticmethod
    def afficher_formulaire(screen, titre, question):
        """
        Affiche un formulaire de saisie pour obtenir une réponse de l'utilisateur.
        :param screen: Surface pygame où afficher le formulaire
        :param titre: Titre du formulaire
        :param question: Question posée à l'utilisateur
        :return: Réponse de l'utilisateur
        """
        from app.screen_config import env_bool, pointer_down_position

        screen_width, screen_height = screen.get_size()
        diameter = min(screen_width, screen_height)
        center_x = screen_width / 2
        center_y = screen_height / 2

        font = pygame.font.Font(None, max(22, min(32, int(diameter * 0.07))))
        input_width = max(80, min(int(diameter * 0.72), max(80, screen_width - 32)))
        input_height = max(42, min(56, int(diameter * 0.11)))
        input_box = pygame.Rect(
            int(center_x - input_width / 2),
            int(center_y + diameter * 0.08),
            input_width,
            input_height,
        )
        color_inactive = pygame.Color('lightskyblue3')
        color_active = pygame.Color('dodgerblue2')
        color = color_inactive
        active = False
        text = ''
        done = False

        clock = pygame.time.Clock()

        while not done:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                pointer = pointer_down_position(event, screen_width, screen_height)
                if pointer:
                    # Si l'utilisateur clique sur la boîte, activez-la.
                    if input_box.collidepoint(pointer):
                        active = not active
                    else:
                        active = False
                    # Changez la couleur de la boîte d'entrée.
                    color = color_active if active else color_inactive
                if event.type == pygame.KEYDOWN:
                    if active:
                        if event.key == pygame.K_RETURN:
                            done = True
                        elif event.key == pygame.K_BACKSPACE:
                            text = text[:-1]
                        else:
                            text += event.unicode

            screen.fill((255, 255, 255))

            # Dessiner le titre
            titre_surface = font.render(titre, True, (0, 0, 0))
            screen.blit(
                titre_surface,
                titre_surface.get_rect(center=(center_x, center_y - diameter * 0.26)),
            )

            # Dessiner la question
            question_surface = font.render(question, True, (0, 0, 0))
            screen.blit(
                question_surface,
                question_surface.get_rect(center=(center_x, center_y - diameter * 0.08)),
            )

            # Dessiner la boîte d'entrée.
            txt_surface = font.render(text, True, (0, 0, 0))
            screen.blit(txt_surface, (input_box.x + 5, input_box.y + 5))
            pygame.draw.rect(screen, color, input_box, 2)

            pygame.display.flip()
            if env_bool("CORTEX_EXIT_AFTER_FRAME", False):
                return text or None
            clock.tick(30)

        return text

    def _initialiser_graphe(self):
        with self.driver.session(database=self.database) as session:
            query = """
            MATCH (n)-[r]->(m)
            RETURN n, r, m
            """
            result = session.run(query)

            # Création du graphe avec NetworkX
            graph = nx.DiGraph()

            # Stocker les nœuds et créer une correspondance
            noeuds = {}
            node_id_map = {}
            current_id = 0
            noeud_principal_id = None

            def get_node_label(node):
                """Récupérer les informations de chaque nœud pour l'affichage correct"""
                if "prenom" in node and "nom" in node:
                    return f'{node["prenom"]} {node["nom"]}'
                if "nom" in node:
                    return node["nom"]
                if "description" in node:
                    return node["description"]
                return "Unnamed Node"

            for record in result:
                noeud_1 = record["n"]
                noeud_2 = record["m"]
                relation = record["r"]

                label_1 = get_node_label(noeud_1)
                label_2 = get_node_label(noeud_2)

                # Créer des IDs uniques pour chaque noeud
                if noeud_1.element_id not in node_id_map:
                    node_id_map[noeud_1.element_id] = current_id
                    current_id += 1
                if noeud_2.element_id not in node_id_map:
                    node_id_map[noeud_2.element_id] = current_id
                    current_id += 1

                id_1 = node_id_map[noeud_1.element_id]
                id_2 = node_id_map[noeud_2.element_id]

                # Ajouter les nœuds au graphe avec leur label
                graph.add_node(id_1, label=label_1)
                graph.add_node(id_2, label=label_2)

                # Identifier le nœud principal
                if label_1 == "Thomas Respaut":
                    noeud_principal_id = id_1
                elif label_2 == "Thomas Respaut":
                    noeud_principal_id = id_2

                # Ajouter la relation avec son label
                graph.add_edge(id_1, id_2, label=relation.type)

                # Sauvegarder les nœuds
                noeuds[id_1] = noeud_1
                noeuds[id_2] = noeud_2

            # Calculer les voisins directs du nœud principal
            voisins_directs = set()
            if noeud_principal_id is not None:
                voisins_directs = set(graph.neighbors(noeud_principal_id))

            # Générer les positions des nœuds de manière concentrique
            positions = {}
            center = (0, 0)  # Centre du graphe, pour "Thomas RESPAUT"
            radius_step_direct = 300  # Distance pour les voisins directs
            radius_step_indirect = 150  # Distance pour les voisins indirects

            # Positionner le nœud principal
            if noeud_principal_id is not None:
                positions[noeud_principal_id] = center

                # Positionner les voisins directs
                angle_step = 360 / len(voisins_directs) if voisins_directs else 360
                angle = 0
                for voisin in voisins_directs:
                    x = center[0] + radius_step_direct * math.cos(math.radians(angle))
                    y = center[1] + radius_step_direct * math.sin(math.radians(angle))
                    positions[voisin] = (x, y)
                    angle += angle_step

                # Positionner les voisins indirects et les niveaux suivants
                def positionner_indirects(niveau, voisins_niveau_precedent):
                    if not voisins_niveau_precedent:
                        return

                    angle_step = 360 / len(voisins_niveau_precedent) if voisins_niveau_precedent else 360
                    angle = 0
                    nouveaux_voisins = set()
                    for voisin in voisins_niveau_precedent:
                        voisins_suivants = list(graph.successors(voisin)) + list(graph.predecessors(voisin))

                        # Positionner les nœuds de niveau suivant autour du voisin actuel
                        for voisin_suivant in voisins_suivants:
                            if voisin_suivant not in positions:
                                x = positions[voisin][0] + radius_step_indirect * math.cos(math.radians(angle))
                                y = positions[voisin][1] + radius_step_indirect * math.sin(math.radians(angle))
                                positions[voisin_suivant] = (x, y)
                                nouveaux_voisins.add(voisin_suivant)
                                angle += angle_step

                    # Appel récursif pour le niveau suivant
                    positionner_indirects(niveau + 1, nouveaux_voisins)

                # Appel initial pour les voisins directs
                positionner_indirects(1, voisins_directs)

        return graph, noeuds, node_id_map, noeud_principal_id, positions

    def visualiser_graph_interactif(self):
        """
        Visualise le graphe des nœuds et relations avec Pygame, permettant des interactions dynamiques,
        avec un zoom tactile, glissement, l'affichage des nœuds cliqués, et un système de couleurs.
        """
        try:
            from app.app_bdd import launch_bdd
            from app.screen_config import display_flags, env_bool, env_int, env_screen_size

            class CortexProxy:
                def __init__(self, db):
                    self.db = db

            pygame.init()
            pygame.display.set_caption("Visualisation interactive du graphe")
            fullscreen = env_bool("CORTEX_FULLSCREEN", False)
            if fullscreen:
                screen = pygame.display.set_mode((0, 0), display_flags(fullscreen))
            else:
                preview_size = env_int("CORTEX_PREVIEW_SIZE", 900)
                screen = pygame.display.set_mode(
                    env_screen_size("CORTEX_SCREEN_SIZE", (preview_size, preview_size)),
                    display_flags(fullscreen),
                )
            launch_bdd(screen, CortexProxy(self), *screen.get_size())

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Erreur lors de la visualisation interactive du graphe : {e}")
        finally:
            if pygame.get_init():
                pygame.quit()

    def close(self):
        # Fermeture du driver Neo4j
        if self.driver:
            self.driver.close()
            print("Connexion à la base de données Neo4j fermée.")


# Exemple d'utilisation
if __name__ == "__main__":
    # Connexion à la base de données
    db = Neo4jDatabase()

    '''

    # Ajouter une activité sportive (Natation) et la relier à Thomas (relation directe)
    db.ajouter_entite_et_relation(
        entite="ActiviteSportive",
        proprietes={"nom": "Natation", "duree": "1h"},
        relation="PRATIQUE",
        cible_relation="Personne",
        proprietes_relation={"prenom": "Thomas", "nom": "Respaut"},
        relation_inverse=True  # La relation va de Thomas vers l'activité
    )

    # Ajouter un lieu et connecter Thomas au lieu (relation inverse, Thomas vit à Courbevoie)
    db.ajouter_entite_et_relation(
        entite="Lieu",
        proprietes={"nom": "Courbevoie"},
        relation="VIT_A",
        cible_relation="Personne",
        proprietes_relation={"prenom": "Thomas", "nom": "Respaut"},
        relation_inverse=True  # La relation va de Thomas vers Courbevoie
    )
    
    '''

    #db.visualiser_graph_interactif()

    print(db.recuperer_informations_graph())


    # Fermeture de la connexion
    db.close()


