import pygame
import os

def launch_bdd(screen, cortex, screen_width, screen_height):
    """Fonction principale pour l'application Jeux."""
    clock = pygame.time.Clock()
    running = True

    #background_path = os.path.join("app","images", "backgrounds", "jeu.png")
    try:
        #background = pygame.image.load(background_path)
        #background = pygame.transform.scale(background, (screen_width, screen_height))
        background = pygame.Surface((screen.get_width(), screen.get_height()))
        background.fill((0, 0, 0))  # Black color
    except pygame.error as e:
        print(f"Erreur lors du chargement de l'image de fond : {e}")
        running = False

    # Initialisation du graphe
    graph, noeuds, node_id_map, noeud_principal_id, positions = cortex.db._initialiser_graphe()

    # Variables de zoom et de glissement
    zoom = 1.0
    zoom_min = 0.2
    zoom_max = 5.0
    offset_x, offset_y = 0, 0
    finger_positions = {}
    dragging = False
    last_distance = None


    #Bouton Quitter
    boutton_quitter = pygame.Rect(screen_width/2-75, 0, 150, 50)
    border_color = (0, 200, 0)
    border_width = 3
    pygame.draw.rect(screen, border_color, boutton_quitter, width=border_width)
    screen.fill((255, 255, 255))
    while running:
        screen.fill((255, 255, 255))
        boutton_quitter = pygame.Rect(screen_width / 2 - 75, 0, 150, 50)
        border_color = (0, 200, 0)
        border_width = 3
        pygame.draw.rect(screen, border_color, boutton_quitter, width=border_width)


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
                finger_positions[event.finger_id] = (event.x * screen.get_width(), event.y * screen.get_height())
                if len(finger_positions) == 1:
                    dragging = True
            elif event.type == pygame.FINGERUP:
                if event.finger_id in finger_positions:
                    del finger_positions[event.finger_id]
                if len(finger_positions) < 2:
                    last_distance = None
                dragging = False

                touch_x, touch_y = int(event.x * screen.get_width()), int(event.y * screen.get_height())
                if boutton_quitter.collidepoint((touch_x, touch_y)):
                    running = False
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
                                                with cortex.db.driver.session(database=cortex.db.database) as session:
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
                                                graph, noeuds, node_id_map, noeud_principal_id, positions = cortex.db._initialiser_graphe()

                                            elif button_name == "Modifier":
                                                propriete = Neo4jDatabase.afficher_formulaire(screen,
                                                                                              "Modifier Nœud",
                                                                                              "Entrez la propriété à modifier :")
                                                nouvelle_valeur = Neo4jDatabase.afficher_formulaire(screen,
                                                                                                    "Modifier Nœud",
                                                                                                    "Entrez la nouvelle valeur :")

                                                if propriete and nouvelle_valeur:
                                                    with cortex.db.driver.session(database=cortex.db.database) as session:
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

                                                    graph, noeuds, node_id_map, noeud_principal_id, positions = cortex.db._initialiser_graphe()

                                            elif button_name == "Supprimer":
                                                with cortex.db.driver.session(database=cortex.db.database) as session:
                                                    delete_query = """
                                                    MATCH (n)
                                                    WHERE elementId(n) = $node_id
                                                    DETACH DELETE n
                                                    """
                                                    session.run(delete_query,
                                                                node_id=noeuds[node_id].element_id)
                                                    print(f"Nœud {graph.nodes[node_id]['label']} supprimé.")

                                                graph, noeuds, node_id_map, noeud_principal_id, positions = cortex.db._initialiser_graphe()

                                            waiting_for_action = False
                                            break
        pygame.display.flip()