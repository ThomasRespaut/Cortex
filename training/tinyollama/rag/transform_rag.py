import json

def transform_json(input_list):
    transformed_data = []

    for item in input_list:
        print("Traitement de l'élément :", item)  # Debug: afficher l'élément en cours

        # Vérifier si "input" est une liste et traiter le premier élément
        if 'input' in item and isinstance(item['input'], list):
            sub_item = item['input'][0]  # Supposer qu'il y a un seul élément dans la liste
            database = sub_item.get('database', {})
            print("Base de données :", database)  # Debug: afficher la base de données extraite

            nodes = {node['name']: node['value'] for node in database.get('nodes', [])}
            print("Nœuds extraits :", nodes)  # Debug: afficher les nœuds

            summary = ""
            for relation in database.get('relations', []):
                print("Relation en cours de traitement :", relation)  # Debug: afficher la relation actuelle

                source = relation['source']
                target = relation['target']
                relation_type = relation['relations']
                source_value = nodes.get(source, "")
                target_value = nodes.get(target, "")

                summary += (f"- **{source}: {source_value}**\n"
                            f"  └── **Relation : {relation_type}** → **{target}: {target_value}**\n")

            prompt = sub_item.get('prompt', 'Clé introuvable')
            question = sub_item.get('question', 'Question non spécifiée')
            response = item.get('output', 'Réponse non spécifiée')
        else:
            # Gestion des éléments sans "input" structuré comme attendu
            database = item.get('database', {})
            print("Base de données :", database)  # Debug: afficher la base de données extraite

            nodes = {node['name']: node['value'] for node in database.get('nodes', [])}
            print("Nœuds extraits :", nodes)  # Debug: afficher les nœuds

            summary = ""
            for relation in database.get('relations', []):
                print("Relation en cours de traitement :", relation)  # Debug: afficher la relation actuelle

                source = relation['source']
                target = relation['target']
                relation_type = relation['relations']
                source_value = nodes.get(source, "")
                target_value = nodes.get(target, "")

                summary += (f"- **{source}: {source_value}**\n"
                            f"  └── **Relation : {relation_type}** → **{target}: {target_value}**\n")

            prompt = item.get('prompt', 'Clé introuvable')
            question = item.get('question', 'Question non spécifiée')
            response = item.get('output', 'Réponse non spécifiée')

        transformed_data.append({
            "prompt": prompt,
            "database": summary.strip(),
            "question": question,
            "response": response
        })

    return transformed_data

# Charger le fichier rag_personnality_training.json
with open('training_version1_tinyollama.json', 'r', encoding='utf-8') as infile:
    data = json.load(infile)

print("Données brutes chargées :", data)  # Debug: afficher les données brutes

# Vérifier si les données sont une liste ou un objet
if isinstance(data, list):
    transformed = transform_json(data)
elif isinstance(data, dict) and "input" in data:
    transformed = transform_json(data["input"])
else:
    raise ValueError("Le fichier JSON n'est pas structuré comme prévu.")

# Enregistrer dans rag_training.json
with open('rag_training.json', 'w', encoding='utf-8') as outfile:
    json.dump(transformed, outfile, indent=4, ensure_ascii=False)

print("Transformation terminée et enregistrée dans rag_training.json")
