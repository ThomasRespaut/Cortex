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
        font = pygame.font.Font(None, 32)
        input_box = pygame.Rect(200, 300, 400, 50)
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
                    pygame.quit()
                    exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    # Si l'utilisateur clique sur la boîte, activez-la.
                    if input_box.collidepoint(event.pos):
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
            screen.blit(titre_surface, (200, 150))

            # Dessiner la question
            question_surface = font.render(question, True, (0, 0, 0))
            screen.blit(question_surface, (200, 250))

            # Dessiner la boîte d'entrée.
            txt_surface = font.render(text, True, (0, 0, 0))
            width = max(400, txt_surface.get_width() + 10)
            input_box.w = width
            screen.blit(txt_surface, (input_box.x + 5, input_box.y + 5))
            pygame.draw.rect(screen, color, input_box, 2)

            pygame.display.flip()
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
            # Initialisation du graphe
            graph, noeuds, node_id_map, noeud_principal_id, positions = self._initialiser_graphe()

            # Initialiser Pygame
            pygame.init()
            screen = pygame.display.set_mode((800, 600))
            pygame.display.set_caption("Visualisation interactive du graphe")

            # Variables de zoom et de glissement
            zoom = 1.0
            zoom_min = 0.2
            zoom_max = 5.0
            offset_x, offset_y = 0, 0
            finger_positions = {}
            dragging = False
            last_distance = None

            # Boucle principale pour l'interaction
            running = True
            while running:
                screen.fill((255, 255, 255))

                # Dessiner les arêtes (relations)
                for edge in graph.edges:
                    if edge[0] in positions and edge[1] in positions:
                        start_pos = (int(positions[edge[0]][0] * zoom + 400 + offset_x),
                                     int(positions[edge[0]][1] * zoom + 300 + offset_y))
                        end_pos = (int(positions[edge[1]][0] * zoom + 400 + offset_x),
                                   int(positions[edge[1]][1] * zoom + 300 + offset_y))
                        pygame.draw.line(screen, (0, 0, 0), start_pos, end_pos, 2)

                        # Ajouter un texte pour représenter la relation
                        relation_label = graph.edges[edge].get('label', 'Relation')
                        mid_pos = ((start_pos[0] + end_pos[0]) // 2,
                                   (start_pos[1] + end_pos[1]) // 2)
                        font = pygame.font.Font(None, max(int(18 * zoom), 12))
                        text = font.render(relation_label, True, (255, 0, 0))  # Texte en rouge
                        screen.blit(text, mid_pos)

                # Dessiner les nœuds
                for node_id, pos in positions.items():
                    if node_id in graph.nodes:
                        x, y = int(pos[0] * zoom + 400 + offset_x), int(pos[1] * zoom + 300 + offset_y)
                        # Déterminer la couleur du nœud
                        if node_id == noeud_principal_id:
                            color = (0, 255, 0)  # Vert pour "Thomas RESPAUT"
                        elif node_id in graph.neighbors(noeud_principal_id):
                            color = (0, 0, 255)  # Bleu pour les voisins directs
                        else:
                            color = (255, 255, 0)  # Jaune pour les autres nœuds

                        # Dessiner le nœud
                        pygame.draw.circle(screen, color, (x, y), int(20 * zoom))

                        # Ajouter le label du nœud
                        label = graph.nodes[node_id]['label']
                        font = pygame.font.Font(None, max(int(24 * zoom), 12))
                        text = font.render(label, True, (0, 0, 0))
                        screen.blit(text, (x - 20, y - 35))

                # Gérer les événements
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.FINGERDOWN:
                        finger_positions[event.finger_id] = (event.x * 800, event.y * 600)
                        if len(finger_positions) == 1:
                            dragging = True
                    elif event.type == pygame.FINGERUP:
                        if event.finger_id in finger_positions:
                            del finger_positions[event.finger_id]
                        if len(finger_positions) < 2:
                            last_distance = None
                        dragging = False
                    elif event.type == pygame.FINGERMOTION:
                        finger_positions[event.finger_id] = (event.x * 800, event.y * 600)
                        if len(finger_positions) == 2:
                            fingers = list(finger_positions.values())
                            dist_current = math.sqrt((fingers[0][0] - fingers[1][0]) ** 2 +
                                                     (fingers[0][1] - fingers[1][1]) ** 2)

                            if last_distance is not None:
                                zoom_change = (dist_current - last_distance) * 0.002
                                zoom = max(zoom_min, min(zoom + zoom_change, zoom_max))

                            last_distance = dist_current

                        elif dragging and len(finger_positions) == 1:
                            dx = event.dx * 800
                            dy = event.dy * 600
                            offset_x += dx
                            offset_y += dy

                    # Gérer le clic sur un nœud
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_pos = event.pos
                        for node_id, pos in positions.items():
                            x, y = int(pos[0] * zoom + 400 + offset_x), int(pos[1] * zoom + 300 + offset_y)
                            if (mouse_pos[0] - x) ** 2 + (mouse_pos[1] - y) ** 2 <= int(20 * zoom) ** 2:
                                # Ajouter les boutons et gérer les actions
                                buttons = {
                                    "Ajouter": pygame.Rect(50, 500, 150, 50),
                                    "Modifier": pygame.Rect(250, 500, 150, 50),
                                    "Supprimer": pygame.Rect(450, 500, 150, 50),
                                }

                                for button_name, button_rect in buttons.items():
                                    pygame.draw.rect(screen, (0, 0, 255), button_rect)
                                    text = font.render(button_name, True, (255, 255, 255))
                                    screen.blit(text, (button_rect.x + 20, button_rect.y + 10))

                                pygame.display.flip()

                                waiting_for_action = True
                                while waiting_for_action:
                                    for sub_event in pygame.event.get():
                                        if sub_event.type == pygame.QUIT:
                                            pygame.quit()
                                            exit()
                                        elif sub_event.type == pygame.MOUSEBUTTONDOWN:
                                            click_pos = sub_event.pos
                                            for button_name, button_rect in buttons.items():
                                                if button_rect.collidepoint(click_pos):
                                                    if button_name == "Ajouter":
                                                        # Ajouter une relation
                                                        cible_relation = Neo4jDatabase.afficher_formulaire(
                                                            screen, "Ajouter une Relation",
                                                            "Entrez le nom de l'entité cible :"
                                                        )
                                                        relation_type = Neo4jDatabase.afficher_formulaire(
                                                            screen, "Ajouter une Relation",
                                                            "Entrez le type de relation :"
                                                        )

                                                        # Ajouter la relation dans la base Neo4j
                                                        with self.driver.session(database=self.database) as session:
                                                            query = f"""
                                                            MATCH (n)
                                                            WHERE elementId(n) = $node_id
                                                            MERGE (c:Cible {{nom: $cible_relation}})
                                                            CREATE (n)-[r:{relation_type}]->(c)
                                                            RETURN n, r, c
                                                            """
                                                            result = session.run(query,
                                                                                 node_id=noeuds[node_id].element_id,
                                                                                 cible_relation=cible_relation)

                                                            for record in result:
                                                                noeud_1 = record["n"]
                                                                noeud_2 = record["c"]

                                                                if noeud_1.element_id not in node_id_map:
                                                                    node_id_map[noeud_1.element_id] = len(node_id_map)
                                                                    graph.add_node(node_id_map[noeud_1.element_id],
                                                                                   label=noeud_1.get("nom",
                                                                                                     "Unnamed Node"))
                                                                if noeud_2.element_id not in node_id_map:
                                                                    node_id_map[noeud_2.element_id] = len(node_id_map)
                                                                    graph.add_node(node_id_map[noeud_2.element_id],
                                                                                   label=cible_relation)

                                                                graph.add_edge(
                                                                    node_id_map[noeud_1.element_id],
                                                                    node_id_map[noeud_2.element_id], label=relation_type
                                                                )

                                                        print(
                                                            f"Relation ajoutée entre {graph.nodes[node_id]['label']} et '{cible_relation}' de type '{relation_type}'")

                                                        # Réinitialiser le graphe après modification
                                                        graph, noeuds, node_id_map, noeud_principal_id, positions = self._initialiser_graphe()

                                                    elif button_name == "Modifier":
                                                        propriete = Neo4jDatabase.afficher_formulaire(screen,
                                                                                                      "Modifier Nœud",
                                                                                                      "Entrez la propriété à modifier :")
                                                        nouvelle_valeur = Neo4jDatabase.afficher_formulaire(screen,
                                                                                                            "Modifier Nœud",
                                                                                                            "Entrez la nouvelle valeur :")

                                                        if propriete and nouvelle_valeur:
                                                            with self.driver.session(database=self.database) as session:
                                                                query = f"""
                                                                MATCH (n)
                                                                WHERE elementId(n) = $node_id
                                                                SET n.`{propriete}` = $nouvelle_valeur
                                                                """
                                                                try:
                                                                    session.run(query,
                                                                                node_id=noeuds[node_id].element_id,
                                                                                nouvelle_valeur=nouvelle_valeur)
                                                                    print(
                                                                        f"Nœud {graph.nodes[node_id]['label']} modifié : {propriete} = {nouvelle_valeur}")
                                                                except Exception as e:
                                                                    print(f"Erreur lors de la modification : {e}")

                                                            graph, noeuds, node_id_map, noeud_principal_id, positions = self._initialiser_graphe()

                                                    elif button_name == "Supprimer":
                                                        with self.driver.session(database=self.database) as session:
                                                            delete_query = """
                                                            MATCH (n)
                                                            WHERE elementId(n) = $node_id
                                                            DETACH DELETE n
                                                            """
                                                            session.run(delete_query,
                                                                        node_id=noeuds[node_id].element_id)
                                                            print(f"Nœud {graph.nodes[node_id]['label']} supprimé.")

                                                        graph, noeuds, node_id_map, noeud_principal_id, positions = self._initialiser_graphe()

                                                    waiting_for_action = False
                                                    break

                pygame.display.flip()

            pygame.quit()

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Erreur lors de la visualisation interactive du graphe : {e}")

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


