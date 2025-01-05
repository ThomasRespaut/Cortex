import json

# Chemin vers le fichier JSON
input_file = "fct_updated.json"
output_file = "fct.json"

# Charger le fichier JSON
with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# Ajouter la balise <function> avant chaque réponse
for item in data:
    if "response" in item:
        # Ajouter <function> uniquement si ce n'est pas déjà présent
        if not item["response"].startswith("<function>"):
            item["response"] = f"<function> {item['response']}"

    if "database" in item:  # Vérifie si la clé "database" existe
        item["is_rag"] = True
    else:
        item["is_rag"] = False  # Optionnel, selon vos besoins

    item["is_function"] = True

# Sauvegarder le fichier JSON mis à jour
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print(f"Fichier mis à jour sauvegardé sous : {output_file}")

