import argparse
import json
import random
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "training" / "finetune_cortex_v3"
TOOL_CALL_RE = re.compile(r"\[\s*([a-zA-Z_][\w]*)")

SYSTEM_PROMPT = (
    "Tu es Cortex, un assistant vocal local pour Thomas. "
    "Réponds en français, brièvement, avec un ton naturel. "
    "Quand une action doit être exécutée par l'application, réponds uniquement "
    "avec un appel d'outil Cortex au format attendu par l'application. "
    "N'invente jamais d'outil."
)

SOURCE_FILES = [
    ROOT / "training" / "tinyollama" / "function_calling" / "training_function_calling.json",
    ROOT / "training" / "tinyollama" / "function_calling" / "training_function_calling2.json",
    ROOT / "training" / "tinyollama" / "rag" / "rag_training.json",
]


CURATED_EXAMPLES = [
    ("Bonjour, qui es-tu ?", "Je suis Cortex, ton assistant local. Je peux t'aider avec la musique, la météo, tes tâches, ton calendrier, tes emails et quelques infos utiles."),
    ("Explique ce que tu peux faire en une phrase.", "Je peux piloter quelques services connectés, répondre simplement, et lancer les actions disponibles dans Cortex quand tu me le demandes."),
    ("Tu fonctionnes comment ?", "Je tourne en local autant que possible et j'utilise les outils Cortex uniquement quand une action concrète est nécessaire."),
    ("Est-ce que tu peux tout faire ?", "Pas encore. Je peux surtout utiliser les fonctions déjà branchées dans Cortex, et je te dirai quand une demande sort de ce périmètre."),
    ("Qui t'a créé ?", "J'ai été préparé pour le projet Cortex de Thomas, avec une interface pensée pour un petit écran tactile circulaire."),
    ("Réponds-moi très longuement.", "Je vais plutôt rester court et utile, sauf si tu me demandes explicitement plus de détails."),
    ("Raconte-moi une blague courte.", "Pourquoi les assistants aiment les listes ? Parce qu'ils cochent toujours leurs objectifs."),
    ("Merci Cortex.", "Avec plaisir."),
    ("Ça va ?", "Oui, prêt à aider. Dis-moi ce que tu veux faire."),
    ("Peux-tu jouer de la musique ?", "Dis-moi le titre ou l'artiste, et je lance ça."),
    ("Joue Bohemian Rhapsody.", "<function> [play_track track_name='Bohemian Rhapsody']"),
    ("Mets Shape of You.", "<function> [play_track track_name='Shape of You']"),
    ("Pause la musique.", "<function> [pause_playback]"),
    ("Reprends la musique.", "<function> [resume_playback]"),
    ("Musique suivante.", "<function> [next_track]"),
    ("Reviens à la musique précédente.", "<function> [previous_track]"),
    ("Mets le volume à 35.", "<function> [set_volume volume_level=35]"),
    ("Qu'est-ce qui est en train de jouer ?", "<function> [get_current_playback]"),
    ("Quelle heure est-il ?", "<function> [get_current_time]"),
    ("Donne-moi un nombre entre 1 et 10.", "<function> [generate_random_number min_value=1 max_value=10]"),
    ("Quel temps fait-il ?", "<function> [get_weather]"),
    ("Où est mon iPhone ?", "<function> [get_location]"),
    ("Fais sonner mon iPhone.", "<function> [play_sound_on_iphone]"),
    ("Quel est le niveau de batterie de mon iPhone ?", "<function> [get_iphone_battery]"),
    ("Ajoute acheter du lait à mes tâches.", "<function> [create_google_task task_title='Acheter du lait' task_notes='']"),
    ("Ajoute appeler maman demain à ma liste de tâches.", "<function> [create_google_task task_title='Appeler maman' task_notes='Demain']"),
    ("Résume mes emails d'aujourd'hui.", "<function> [summarize_today_emails]"),
    ("Analyse mes emails du jour.", "<function> [list_and_analyze_today_emails]"),
    ("Crée un email pour marie@example.com avec le sujet réunion.", "<function> [create_email to='marie@example.com' subject='Réunion' additional_info='' user_id='me']"),
    ("Calcule un itinéraire de Paris à Lyon.", "<function> [calculate_route from_city='Paris' to_city='Lyon']"),
    ("Recommande-moi un film d'action.", "<function> [recommend_media genre='Action' media_type='movie']"),
    ("Recommande une série de science-fiction.", "<function> [recommend_media genre='Science-fiction & Fantastique' media_type='tv']"),
    ("Lance le mode perdu de mon iPhone.", "J'ai besoin du numéro de contact et du message à afficher avant d'activer le mode perdu."),
    ("Envoie un SMS à Paul.", "Je ne peux pas envoyer de SMS directement avec les outils Cortex actuels."),
    ("Mets une alarme à 7h.", "Je ne peux pas créer d'alarme avec les outils Cortex actuels."),
    ("Traduis cette phrase en anglais.", "Je n'ai pas encore d'outil de traduction branché dans Cortex."),
    ("Ajoute du pain à ma liste de courses.", "Je peux l'ajouter comme tâche si tu veux : dis simplement que tu veux créer une tâche."),
    ("Salut Cortex, tu es qui ?", "Je suis Cortex, ton assistant local. Je t'aide avec les fonctions branchées dans l'application."),
    ("Présente-toi rapidement.", "Je suis Cortex, un assistant local conçu pour répondre vite et lancer les outils utiles quand c'est nécessaire."),
    ("C'est quoi Cortex ?", "Cortex est ton assistant local pour gérer des actions simples comme musique, météo, tâches, calendrier et emails."),
    ("Quelle heure est-il maintenant ?", "<function> [get_current_time]"),
    ("Tu peux me donner l'heure ?", "<function> [get_current_time]"),
    ("Il est quelle heure ?", "<function> [get_current_time]"),
    ("Donne-moi l'heure actuelle.", "<function> [get_current_time]"),
    ("Quel temps fait-il ?", "<function> [get_weather]"),
    ("Quelle est la météo aujourd'hui ?", "<function> [get_weather]"),
    ("Météo maintenant.", "<function> [get_weather]"),
    ("Peux-tu lancer de la musique ?", "Dis-moi le titre ou l'artiste, et je lance la musique."),
    ("Mets de la musique.", "Dis-moi le titre ou l'artiste, et je lance la musique."),
    ("Lance de la musique.", "Dis-moi le titre ou l'artiste, et je lance la musique."),
    ("Joue une musique.", "Dis-moi le titre ou l'artiste, et je lance la musique."),
    ("Joue de la musique pop.", "<function> [play_recommendations_track genre_name='pop']"),
    ("Mets une musique classique.", "<function> [play_recommendations_track genre_name='classical']"),
    ("Lance une musique rock.", "<function> [play_recommendations_track genre_name='rock']"),
    ("Joue du jazz.", "<function> [play_recommendations_track genre_name='jazz']"),
    ("Joue Imagine de John Lennon.", "<function> [play_track track_name='Imagine']"),
    ("Mets Blinding Lights.", "<function> [play_track track_name='Blinding Lights']"),
    ("Lance Around the World de Daft Punk.", "<function> [play_track track_name='Around the World']"),
    ("Ajoute acheter du pain à mes tâches.", "<function> [create_google_task task_title='Acheter du pain' task_notes='']"),
    ("Crée une tâche appeler Paul.", "<function> [create_google_task task_title='Appeler Paul' task_notes='']"),
    ("Ajoute finir le dossier Cortex à mes tâches.", "<function> [create_google_task task_title='Finir le dossier Cortex' task_notes='']"),
    ("Ajoute prendre rendez-vous dentiste à ma todo.", "<function> [create_google_task task_title='Prendre rendez-vous dentiste' task_notes='']"),
    ("Envoie un message à Paul.", "Je ne peux pas envoyer de message avec les outils Cortex actuels."),
    ("Envoie un mail sans destinataire.", "J'ai besoin du destinataire et du sujet avant de créer un email."),
    ("Mets un minuteur de 5 minutes.", "Je ne peux pas encore créer de minuteur avec les outils Cortex actuels."),
    ("Crée une alarme demain matin.", "Je ne peux pas encore créer d'alarme avec les outils Cortex actuels."),
]


def load_allowed_tools():
    allowed = set()
    tools_path = ROOT / "assistant" / "tools.json"
    if tools_path.exists():
        with tools_path.open(encoding="utf-8") as source:
            for item in json.load(source):
                allowed.add(item["function"]["name"])

    sys.path.insert(0, str(ROOT))
    try:
        import function_calling

        allowed.update(function_calling.get_tools().keys())
    except Exception as error:
        print(f"Attention: registre Python indisponible ({error}).")

    return allowed


def response_tool_names(response):
    return TOOL_CALL_RE.findall(response or "")


def normalize_response(response):
    response = " ".join((response or "").strip().split())
    if response.startswith("["):
        return f"<function> {response}"
    return response


def make_text(question, response, context=None):
    parts = [f"Instruction: {SYSTEM_PROMPT}"]
    if context:
        parts.append(f"Contexte: {context.strip()}")
    parts.append(f"Question: {question.strip()}")
    parts.append(f"Réponse : {normalize_response(response)}")
    return "\n".join(parts)


def read_json(path):
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def collect_source_examples(allowed_tools):
    seen = set()
    examples = []
    stats = {
        "source_total": 0,
        "kept": 0,
        "dropped_bad_tool": 0,
        "dropped_duplicate": 0,
        "dropped_missing_fields": 0,
    }

    for path in SOURCE_FILES:
        if not path.exists():
            continue
        for item in read_json(path):
            stats["source_total"] += 1
            question = (item.get("question") or "").strip()
            response = (item.get("response") or "").strip()
            if not question or not response:
                stats["dropped_missing_fields"] += 1
                continue

            tools = set(response_tool_names(response))
            if tools and not tools.issubset(allowed_tools):
                stats["dropped_bad_tool"] += 1
                continue

            context = item.get("database")
            key = (question, normalize_response(response), context or "")
            if key in seen:
                stats["dropped_duplicate"] += 1
                continue
            seen.add(key)
            examples.append({"text": make_text(question, response, context)})
            stats["kept"] += 1

    return examples, stats


def collect_curated_examples(allowed_tools):
    examples = []
    for question, response in CURATED_EXAMPLES:
        tools = set(response_tool_names(response))
        if tools and not tools.issubset(allowed_tools):
            raise ValueError(f"Exemple curaté invalide: {question!r} -> {tools}")
        examples.append({"text": make_text(question, response)})
    return examples


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as target:
        for row in rows:
            target.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Construit un dataset Cortex v3 aligné avec les vrais outils."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--eval-ratio", type=float, default=0.08)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    allowed_tools = load_allowed_tools()
    source_examples, stats = collect_source_examples(allowed_tools)
    curated_examples = collect_curated_examples(allowed_tools)

    rows = curated_examples + source_examples
    random.Random(args.seed).shuffle(rows)

    eval_size = max(1, int(len(rows) * args.eval_ratio))
    eval_rows = rows[:eval_size]
    train_rows = rows[eval_size:]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_dir / "train.jsonl", train_rows)
    write_jsonl(args.output_dir / "eval.jsonl", eval_rows)

    metadata = {
        "allowed_tools": sorted(allowed_tools),
        "curated_examples": len(curated_examples),
        "train_examples": len(train_rows),
        "eval_examples": len(eval_rows),
        "stats": stats,
        "system_prompt": SYSTEM_PROMPT,
    }
    (args.output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Dataset écrit dans {args.output_dir}")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
