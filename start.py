import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# Charger le modèle fine-tuné et le tokenizer
finetuned_model_path = "./tinyllama_cortex_finetuned"
tokenizer = AutoTokenizer.from_pretrained(finetuned_model_path)
model = AutoModelForCausalLM.from_pretrained(finetuned_model_path)
print("Modèle fine-tuné chargé avec succès.")

# Fonction pour générer une réponse
def generate_response(prompt):
    """
    Génère une réponse en utilisant le modèle fine-tuné TinyLlama.
    """
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
    outputs = model.generate(
        inputs["input_ids"],
        max_length=512,
        num_return_sequences=1,
        temperature=0.7,
        top_p=0.9,
        do_sample=True
    )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return response

# Interface utilisateur en boucle
if __name__ == "__main__":
    print("\nAssistant basé sur TinyLlama. Tapez 'stop' pour quitter.\n")
    while True:
        user_query = input("Votre question : ")
        if user_query.lower() == "stop":
            print("Assistant arrêté. À bientôt !")
            break
        else:
            response = generate_response(user_query)
            print(f"\nRéponse : {response}\n")
