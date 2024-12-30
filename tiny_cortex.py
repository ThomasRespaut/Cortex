import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer, util
from database.database import Neo4jDatabase

# Chargement du modèle et du tokenizer fine-tunés
finetuned_model_path = "./tinyllama_cortex_finetuned"
tokenizer = AutoTokenizer.from_pretrained(finetuned_model_path)
model = AutoModelForCausalLM.from_pretrained(finetuned_model_path)
print("Modèle fine-tuné chargé avec succès.")

# Spécifiez le chemin où enregistrer localement le modèle
model_path = "./models/all-MiniLM-L6-v2"
embedder = SentenceTransformer('all-MiniLM-L6-v2', cache_folder=model_path)
print("Modèle d'embeddings téléchargé et chargé avec succès.")

def fetch_graph_with_relations(query, db, top_k=10):
    """
    Récupère les nœuds et relations pertinents de Neo4j en fonction de la requête.
    """
    cypher_query = """
    MATCH (n)-[r]->(m)
    RETURN n, r, m
    """
    results = db.execute_query(cypher_query)

    # Calcul de la similarité sémantique entre la requête et les noms des nœuds
    query_embedding = embedder.encode(query, convert_to_tensor=True)
    similarities = []

    for record in results:
        node = record["n"]
        related_node = record["m"]
        relation = record["r"]

        # Extraire les noms ou descriptions pour la similarité
        node_name = node.get("nom", "") + " " + node.get("prenom", "")
        related_node_name = related_node.get("nom", "") + " " + related_node.get("prenom", "")
        relation_type = relation.type if relation else "relation inconnue"
        combined_text = f"{node_name} {relation_type} {related_node_name}"

        # Calculer l'embedding et la similarité
        combined_embedding = embedder.encode(combined_text, convert_to_tensor=True)
        score = util.pytorch_cos_sim(query_embedding, combined_embedding)

        similarities.append((score.item(), node, relation, related_node))

    # Trier par pertinence et limiter les résultats
    top_results = sorted(similarities, key=lambda x: x[0], reverse=True)[:top_k]
    return top_results

def build_context(results):
    """
    Construit un contexte simplifié en listant les nœuds, leurs relations et les nœuds connectés.
    """
    context_parts = []

    for _, node, relation, related_node in results:
        # Extraire les informations principales des nœuds et de la relation
        node_label = next(iter(node.labels), "")  # Récupère un label du frozenset
        node_name = node.get("nom", "Inconnu")
        node_state = node.get("etat", "")

        if related_node:
            related_label = next(iter(related_node.labels), "")
            related_node_name = related_node.get("nom", "Inconnu")
            related_node_state = related_node.get("etat", "")
        else:
            related_label = "Nœud inconnu"
            related_node_name = "Inconnu"
            related_node_state = ""

        relation_type = relation.type if relation else "Relation inconnue"

        # Construire une description simplifiée
        context_parts.append(
            f"- **{node_label}: {node_name} ({node_state})**\n"
            f"  └── **Relation : {relation_type}** → **{related_label} : {related_node_name} ({related_node_state})**"
        )

    return "\n".join(context_parts)

def generate_response_with_graph(query, db):
    """
    Génère une réponse basée sur la requête utilisateur et les données du graphe.
    """
    # Étape 1 : Récupérer les relations pertinentes
    results = fetch_graph_with_relations(query, db)

    # Étape 2 : Construire le contexte
    context = build_context(results)

    # Étape 3 : Générer la réponse
    if context:
        response = f"Contexte :\n{context}\n\nQuestion : {query}\nRéponse : Je suis Thomas RESPAUT, un assistant vocal conçu pour fonctionner localement."
    else:
        response = "Aucune relation pertinente trouvée pour répondre à la requête."

    return response

# Exemple d'utilisation :
db = Neo4jDatabase()
user_query = "Qui est Thomas RESPAUT ?"
response = generate_response_with_graph(user_query, db)
print(response)
