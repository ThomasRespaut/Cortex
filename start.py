import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import re
from function_calling import execute_tool

class TinyCortex:
    def __init__(self, model_path="./tinyllama_cortex_finetuned"):
        """
        Initialise le modèle fine-tuné et le tokenizer.
        """
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForCausalLM.from_pretrained(model_path)
        print("Modèle fine-tuné TinyCortex chargé avec succès.")

    def generate_response(self, prompt):
        """
        Génère une réponse en utilisant le modèle fine-tuné TinyCortex.
        """
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        outputs = self.model.generate(
            inputs["input_ids"],
            max_length=512,
            num_return_sequences=1,
            temperature=0.7,
            top_p=0.9,
            do_sample=True
        )
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        match = re.search(r"Réponse :(.*)", response)
        if match:
            result = match.group(1).strip()
            response = result
        print("Réponse : " + response)

        return response

    def interactive_mode(self):
        """
        Lance une interface utilisateur interactive pour poser des questions au modèle.
        """
        print("\nAssistant basé sur TinyCortex. Tapez 'stop' pour quitter.\n")
        while True:
            user_query = input("Votre question : ")
            user_question = f"Question: {user_query}\nRéponse :"
            if user_query.lower() == "stop":
                print("Assistant arrêté. À bientôt !")
                break
            else:
                response = self.generate_response(user_question)
                print(execute_tool(response))

# Exemple d'utilisation de la classe TinyCortex
if __name__ == "__main__":
    assistant = TinyCortex()
    assistant.interactive_mode()
